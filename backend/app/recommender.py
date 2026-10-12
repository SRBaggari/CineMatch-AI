"""Content-based recommendation engine with explainable weighted preference matching.

Pipeline
--------
1. Feature vectors: every movie is represented by
   - a multi-hot genre vector,
   - a multi-hot mood vector,
   - a one-hot language vector,
   - a TF-IDF vector of its keywords and description,
   - its release year.
   They are fitted once and cached on disk (keyed by a hash of the dataset).
2. User profile: the user's preferences are mapped into the same spaces.
   Keywords (and, optionally, liked movies) form a TF-IDF profile vector.
3. Component scores, each in [0, 1]:
   - genre    cosine(user genres, movie genres)   = |U ∩ M| / sqrt(|U|·|M|)
   - mood     cosine(user moods, movie moods)
   - language 1 if the movie's language was preferred, else 0
   - keyword  cosine(TF-IDF profile, TF-IDF movie), divided by the best value in
              the catalogue so the strongest text match scores 1
   - year     1 inside the preferred range, linear decay outside it
4. Base (preference) score: weights of the components the user gave a preference
   for are re-normalised to sum to 1, and base = Σ weight_c · component_c.
   Component scores for a preference set are cached in memory.
5. Feedback adjustment (optional, kept separate from the base score):
   adjustment = FEEDBACK_WEIGHT · (max similarity to liked/favourite movies
                                   − max similarity to disliked movies)
   score = clip(base + adjustment, 0, 1)
6. Hard filters (minimum rating; optionally strict year range / languages),
   exclusion of liked/excluded/disliked movies, removal of movies whose base score
   is 0, deterministic ranking (score, rating, movie_id).
7. Explanation: a summary sentence built from matched attributes, matched
   preferences, reasons ordered by contribution, and the full component breakdown.

The score is a relevance score in [0, 1]. It is a weighted similarity, not a
calibrated probability that the user will like the movie.
"""

import hashlib
import json
import logging
import math
import pickle
import threading
from collections import OrderedDict
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd
import sklearn
from scipy.sparse import csr_matrix, hstack
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import MultiLabelBinarizer, normalize

from .config import (
    DATASET_INFO,
    DEFAULT_TOP_N,
    FEATURE_CACHE_VERSION,
    FEEDBACK_WEIGHT,
    ITEM_SIMILARITY_WEIGHTS,
    KEYWORD_REPEAT,
    MAX_TOP_N,
    SCORE_CACHE_SIZE,
    SCORE_WEIGHTS,
    YEAR_DECAY_YEARS,
)
from .data_loader import normalize_token

logger = logging.getLogger("cinematch")

COMPONENTS = ("genre", "language", "mood", "keyword", "year")
SCORE_DECIMALS = 6  # scores are rounded before ranking so float noise cannot break ties
SORT_OPTIONS = ("relevance", "rating", "year", "title")


class EmptyPreferencesError(ValueError):
    """Raised when a request contains no preference to match against."""


class InvalidPreferenceError(ValueError):
    """Raised when a request references values that do not exist in the catalogue."""


@dataclass
class UserPreferences:
    genres: list[str] = field(default_factory=list)
    languages: list[str] = field(default_factory=list)
    moods: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    liked_movie_ids: list[int] = field(default_factory=list)
    year_min: int | None = None
    year_max: int | None = None
    min_rating: float = 0.0
    strict_years: bool = False
    strict_languages: bool = False
    exclude_movie_ids: list[int] = field(default_factory=list)
    top_n: int = DEFAULT_TOP_N
    weights: dict[str, float] | None = None


@dataclass
class FeedbackProfile:
    """Saved user feedback. Favourites count as positive feedback, like likes."""

    liked: list[int] = field(default_factory=list)
    disliked: list[int] = field(default_factory=list)
    favorites: list[int] = field(default_factory=list)

    @property
    def is_empty(self) -> bool:
        return not (self.liked or self.disliked or self.favorites)


# ---------------------------------------------------------------------- #
# Pure helpers (unit-tested directly)
# ---------------------------------------------------------------------- #
def set_cosine(a: set, b: set) -> float:
    """Cosine similarity of two binary (multi-hot) vectors: |A ∩ B| / sqrt(|A|·|B|)."""
    if not a or not b:
        return 0.0
    return len(a & b) / math.sqrt(len(a) * len(b))


def year_score(year: int, year_min: int | None, year_max: int | None, decay: int = YEAR_DECAY_YEARS) -> float:
    """1.0 inside [year_min, year_max]; loses 1/decay per year outside; never below 0."""
    if year_min is not None and year < year_min:
        distance = year_min - year
    elif year_max is not None and year > year_max:
        distance = year - year_max
    else:
        distance = 0
    return max(0.0, 1.0 - distance / decay)


def year_scores(years: np.ndarray, year_min: int | None, year_max: int | None,
                decay: int = YEAR_DECAY_YEARS) -> np.ndarray:
    """Vectorised year_score for an array of release years."""
    distance = np.zeros(len(years), dtype=float)
    if year_min is not None:
        distance = np.where(years < year_min, year_min - years, distance)
    if year_max is not None:
        distance = np.where(years > year_max, years - year_max, distance)
    return np.clip(1.0 - distance / decay, 0.0, 1.0)


def normalize_weights(weights: dict[str, float], active: dict[str, bool]) -> dict[str, float]:
    """Zero the weights of inactive components and scale the rest to sum to 1."""
    raw = {c: (float(weights.get(c, 0.0)) if active.get(c) else 0.0) for c in COMPONENTS}
    total = sum(raw.values())
    if total <= 0:
        raise InvalidPreferenceError(
            "The weights of the preferences you provided are all zero, so no score can be computed."
        )
    return {c: raw[c] / total for c in COMPONENTS}


def unique(values) -> list:
    """De-duplicate while preserving order (case/spacing-insensitive for strings)."""
    seen, result = set(), []
    for v in values:
        key = normalize_token(v) if isinstance(v, str) else v
        if key not in seen and key != "":
            seen.add(key)
            result.append(v.strip() if isinstance(v, str) else v)
    return result


def keyword_document(keywords: list[str], text: str = "") -> str:
    """Text used for TF-IDF: each keyword as a squashed tag (repeated) and as raw words."""
    parts = []
    for kw in keywords:
        parts.extend([normalize_token(kw)] * KEYWORD_REPEAT)
        parts.append(kw.lower())
    parts.append(text)
    return " ".join(p for p in parts if p)


def join_phrases(items: list[str], conjunction: str = "and") -> str:
    """["a"] -> "a"; ["a", "b"] -> "a and b"; ["a", "b", "c"] -> "a, b, and c"."""
    items = [i for i in items if i]
    if len(items) <= 1:
        return "".join(items)
    if len(items) == 2:
        return f"{items[0]} {conjunction} {items[1]}"
    return f"{', '.join(items[:-1])}, {conjunction} {items[-1]}"


def title_relevance(query: str, title: str) -> float:
    """How well a title matches a search query, in [0, 1] (0 = no match).

    exact title 1.0 > title starts with query 0.9 > a word starts with query 0.75
    > query appears anywhere 0.6 > every query word appears 0.5.
    """
    q = " ".join(query.lower().split())
    t = title.lower()
    if not q:
        return 0.0
    if t == q:
        return 1.0
    if t.startswith(q):
        return 0.9
    words = [w for w in "".join(c if c.isalnum() else " " for c in t).split()]
    if any(w.startswith(q) for w in words):
        return 0.75
    if q in t:
        return 0.6
    if all(any(w.startswith(part) for w in words) for part in q.split()):
        return 0.5
    return 0.0


def dataset_fingerprint(movies: pd.DataFrame) -> str:
    """Hash of everything the fitted features depend on, used as the disk-cache key."""
    columns = ["movie_id", "title", "year", "genres", "moods", "keywords", "overview", "language"]
    payload = {
        "version": FEATURE_CACHE_VERSION,
        "sklearn": sklearn.__version__,
        "item_weights": ITEM_SIMILARITY_WEIGHTS,
        "keyword_repeat": KEYWORD_REPEAT,
        "rows": movies[columns].to_dict(orient="records"),
    }
    blob = json.dumps(payload, sort_keys=True, default=lambda o: o.item() if hasattr(o, "item") else str(o))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


class RecommendationEngine:
    def __init__(self, movies: pd.DataFrame, score_weights: dict | None = None, cache_dir: Path | None = None):
        self.movies = movies.reset_index(drop=True)
        self.score_weights = {**SCORE_WEIGHTS, **(score_weights or {})}
        self.ids = self.movies["movie_id"].to_numpy(dtype=int)
        self.years = self.movies["year"].to_numpy(dtype=int)
        self.ratings = self.movies["rating"].to_numpy(dtype=float)
        self.id_to_index = {int(mid): i for i, mid in enumerate(self.ids)}
        self.fingerprint = dataset_fingerprint(self.movies)
        self.feature_source = "computed"

        fitted = self._load_cached_features(cache_dir)
        if fitted is None:
            fitted = self._fit_features()
            self._save_cached_features(cache_dir, fitted)
        self.__dict__.update(fitted)
        self._derive_lookups()

        # Small in-memory caches: component scores per preference set, and keyword vectors.
        self._score_cache: OrderedDict = OrderedDict()
        self._keyword_cache: OrderedDict = OrderedDict()
        self._cache_lock = threading.Lock()
        self.cache_stats = {"hits": 0, "misses": 0}

    # ------------------------------------------------------------------ #
    # Step 1: feature vectors (fitted once, cached on disk)
    # ------------------------------------------------------------------ #
    def _fit_features(self) -> dict:
        genre_encoder = MultiLabelBinarizer()
        genre_matrix = genre_encoder.fit_transform(self.movies["genres"]).astype(float)
        mood_encoder = MultiLabelBinarizer()
        mood_matrix = mood_encoder.fit_transform(self.movies["moods"]).astype(float)
        language_encoder = MultiLabelBinarizer()
        language_matrix = language_encoder.fit_transform([[lang] for lang in self.movies["language"]]).astype(float)

        documents = [keyword_document(row.keywords, row.overview) for row in self.movies.itertuples(index=False)]
        vectorizer = TfidfVectorizer(stop_words="english", sublinear_tf=True)
        text_matrix = vectorizer.fit_transform(documents)

        # Combined movie feature vector for item-to-item similarity: each block is
        # L2-normalised and scaled by sqrt(weight), so the cosine of two combined
        # vectors equals the weighted average of the per-block cosines.
        blocks = []
        for name, matrix in (
            ("genre", csr_matrix(genre_matrix)),
            ("keyword", text_matrix),
            ("mood", csr_matrix(mood_matrix)),
            ("language", csr_matrix(language_matrix)),
        ):
            blocks.append(normalize(matrix) * math.sqrt(ITEM_SIMILARITY_WEIGHTS[name]))
        item_features = hstack(blocks).tocsr()

        return {
            "genre_encoder": genre_encoder,
            "genre_matrix": genre_matrix,
            "mood_encoder": mood_encoder,
            "mood_matrix": mood_matrix,
            "language_encoder": language_encoder,
            "language_matrix": language_matrix,
            "vectorizer": vectorizer,
            "text_matrix": text_matrix,
            "item_features": item_features,
            "item_similarity": cosine_similarity(item_features),
        }

    def _cache_file(self, cache_dir: Path | None) -> Path | None:
        return Path(cache_dir) / f"features-{self.fingerprint[:16]}.pkl" if cache_dir else None

    def _load_cached_features(self, cache_dir: Path | None) -> dict | None:
        path = self._cache_file(cache_dir)
        if not path or not path.exists():
            return None
        try:
            # The cache is written only by this application into its own data folder.
            with path.open("rb") as fh:
                payload = pickle.load(fh)
            if payload.get("fingerprint") != self.fingerprint:
                return None
            self.feature_source = "disk-cache"
            return payload["features"]
        except Exception as exc:  # corrupt / incompatible cache -> rebuild
            logger.warning("Ignoring unreadable feature cache %s: %s", path, exc)
            return None

    def _save_cached_features(self, cache_dir: Path | None, features: dict) -> None:
        path = self._cache_file(cache_dir)
        if not path:
            return
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            for stale in path.parent.glob("features-*.pkl"):
                if stale != path:
                    stale.unlink(missing_ok=True)
            tmp = path.with_suffix(".tmp")
            with tmp.open("wb") as fh:
                pickle.dump({"fingerprint": self.fingerprint, "features": features}, fh)
            tmp.replace(path)
        except OSError as exc:
            logger.warning("Could not write feature cache %s: %s", path, exc)

    def _derive_lookups(self) -> None:
        """Cheap per-movie structures derived from the dataset (not worth caching on disk)."""
        self.feature_names = self.vectorizer.get_feature_names_out()
        self.label_lookup = {
            "genre": {normalize_token(g): g for g in self.genre_encoder.classes_},
            "mood": {normalize_token(m): m for m in self.mood_encoder.classes_},
            "language": {normalize_token(lang): lang for lang in self.language_encoder.classes_},
        }
        self.token_labels: dict[str, str] = {}
        for keywords in self.movies["keywords"]:
            for kw in keywords:
                self.token_labels.setdefault(normalize_token(kw), kw)
        self.genre_sets = [set(gs) for gs in self.movies["genres"]]
        self.mood_sets = [set(ms) for ms in self.movies["moods"]]
        self.keyword_tokens = [{normalize_token(k) for k in ks} for ks in self.movies["keywords"]]
        # (keyword, normalised token) pairs so explanations don't re-normalise on every request.
        self.keyword_pairs = [[(k, normalize_token(k)) for k in ks] for ks in self.movies["keywords"]]
        self.cast_sets = [set(cs) for cs in self.movies["cast"]]
        self.languages = self.movies["language"].to_numpy()
        self.titles = self.movies["title"].tolist()
        # Row norms for the multi-hot cosines, computed once.
        self.genre_norms = np.sqrt(self.genre_matrix.sum(axis=1))
        self.mood_norms = np.sqrt(self.mood_matrix.sum(axis=1))
        self.language_norms = np.sqrt(self.language_matrix.sum(axis=1))
        # Serialised movies, built once instead of on every response.
        self._movie_dicts = [self._row_to_dict(row) for row in self.movies.to_dict(orient="records")]

    @staticmethod
    def _row_to_dict(row: dict) -> dict:
        return {
            "movie_id": int(row["movie_id"]),
            "title": row["title"],
            "year": int(row["year"]),
            "genres": list(row["genres"]),
            "director": row["director"],
            "cast": list(row["cast"]),
            "keywords": list(row["keywords"]),
            "moods": list(row["moods"]),
            "overview": row["overview"],
            "rating": float(row["rating"]),
            "runtime": int(row["runtime"]),
            "language": row["language"],
        }

    # ------------------------------------------------------------------ #
    # Catalogue helpers
    # ------------------------------------------------------------------ #
    def movie_to_dict(self, index: int) -> dict:
        movie = self._movie_dicts[index]
        return {**movie, "genres": list(movie["genres"]), "cast": list(movie["cast"]),
                "keywords": list(movie["keywords"]), "moods": list(movie["moods"])}

    def get_movie(self, movie_id: int) -> dict | None:
        index = self.id_to_index.get(int(movie_id))
        return None if index is None else self.movie_to_dict(index)

    def list_movies(self, search: str = "", genre: str | None = None, language: str | None = None,
                    limit: int = 20, offset: int = 0) -> dict:
        mask = np.ones(len(self.movies), dtype=bool)
        if search:
            mask &= self.movies["title"].str.lower().str.contains(search.strip().lower(), regex=False).to_numpy()
        if genre:
            g = self.label_lookup["genre"].get(normalize_token(genre))
            mask &= np.array([g in gs for gs in self.genre_sets])
        if language:
            lang = self.label_lookup["language"].get(normalize_token(language))
            mask &= self.languages == lang
        indices = np.where(mask)[0]
        # Highest rated first, then newest, then id for a stable order.
        order = np.lexsort((self.ids[indices], -self.years[indices], -self.ratings[indices]))
        indices = indices[order]
        return {
            "total": int(len(indices)),
            "limit": limit,
            "offset": offset,
            "items": [self.movie_to_dict(i) for i in indices[offset: offset + limit]],
        }

    @staticmethod
    def _counts(series: pd.Series) -> dict[str, int]:
        counts = series.explode().dropna().value_counts()
        return {str(k): int(v) for k, v in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))}

    def preference_options(self) -> dict:
        return {
            "genres": self._counts(self.movies["genres"]),
            "moods": self._counts(self.movies["moods"]),
            "languages": self._counts(self.movies["language"]),
            "popular_keywords": dict(list(self._counts(self.movies["keywords"]).items())[:40]),
            "year_min": int(self.years.min()),
            "year_max": int(self.years.max()),
            "rating_min": float(self.ratings.min()),
            "rating_max": float(self.ratings.max()),
            "default_weights": dict(self.score_weights),
            "year_decay_years": YEAR_DECAY_YEARS,
            "default_top_n": DEFAULT_TOP_N,
            "max_top_n": MAX_TOP_N,
        }

    def dataset_info(self) -> dict:
        return {
            **DATASET_INFO,
            "total_movies": len(self.movies),
            "genres": len(self.genre_encoder.classes_),
            "moods": len(self.mood_encoder.classes_),
            "languages": len(self.language_encoder.classes_),
            "vocabulary_size": len(self.feature_names),
            "year_range": [int(self.years.min()), int(self.years.max())],
        }

    def dataset_analytics(self) -> dict:
        """Distributions computed from the catalogue itself."""
        decades = pd.Series((self.years // 10) * 10).value_counts().sort_index()
        bins = np.arange(math.floor(self.ratings.min() * 2) / 2, self.ratings.max() + 0.5, 0.5)
        hist, edges = np.histogram(self.ratings, bins=bins)
        return {
            "total_movies": len(self.movies),
            "genre_distribution": self._counts(self.movies["genres"]),
            "mood_distribution": self._counts(self.movies["moods"]),
            "language_distribution": self._counts(self.movies["language"]),
            "decade_distribution": {f"{int(d)}s": int(n) for d, n in decades.items()},
            "rating_distribution": [
                {"label": f"{edges[i]:.1f}–{edges[i + 1]:.1f}", "start": float(edges[i]),
                 "end": float(edges[i + 1]), "count": int(hist[i])}
                for i in range(len(hist))
            ],
            "average_rating": round(float(self.ratings.mean()), 2),
            "average_runtime": round(float(self.movies["runtime"].mean()), 1),
            "vocabulary_size": len(self.feature_names),
            "feature_source": self.feature_source,
            "score_cache": {**self.cache_stats, "size": len(self._score_cache), "capacity": SCORE_CACHE_SIZE},
        }

    # ------------------------------------------------------------------ #
    # Step 2: user profile
    # ------------------------------------------------------------------ #
    def _resolve_labels(self, kind: str, values: list[str]) -> list[str]:
        lookup = self.label_lookup[kind]
        resolved, unknown = [], []
        for value in unique(values):
            label = lookup.get(normalize_token(value))
            (resolved if label else unknown).append(label or value)
        if unknown:
            raise InvalidPreferenceError(
                f"Unknown {kind}{'s' if len(unknown) > 1 else ''}: {', '.join(unknown)}. "
                f"Valid options: {', '.join(sorted(lookup.values()))}"
            )
        return resolved

    def _resolve_ids(self, ids: list[int], what: str) -> list[int]:
        indices, unknown = [], []
        for mid in unique(ids):
            idx = self.id_to_index.get(int(mid))
            if idx is None:
                unknown.append(str(mid))
            else:
                indices.append(idx)
        if unknown:
            raise InvalidPreferenceError(f"Unknown movie id(s) in {what}: {', '.join(unknown)}")
        return indices

    def _keyword_vector(self, keywords: list[str]) -> np.ndarray | None:
        """Normalised TF-IDF vector for a keyword list, cached so repeat queries skip transform()."""
        key = tuple(k.lower() for k in keywords)
        with self._cache_lock:
            if key in self._keyword_cache:
                self._keyword_cache.move_to_end(key)
                return self._keyword_cache[key]
        vec = self.vectorizer.transform([keyword_document(keywords)])
        result = normalize(vec).toarray().ravel() if vec.nnz else None
        with self._cache_lock:
            self._keyword_cache[key] = result
            if len(self._keyword_cache) > 512:
                self._keyword_cache.popitem(last=False)
        return result

    def _text_profile(self, keywords: list[str], liked: list[int], warnings: list[str]) -> np.ndarray | None:
        parts = []
        if keywords:
            vec = self._keyword_vector(keywords)
            if vec is not None:
                parts.append(vec)
            else:
                warnings.append(
                    f"None of the keywords ({', '.join(keywords)}) appear in the catalogue vocabulary."
                )
        if liked:
            mean = np.asarray(self.text_matrix[liked].mean(axis=0)).ravel()
            parts.append(normalize(mean.reshape(1, -1)).ravel())
        if not parts:
            return None
        return normalize(np.mean(parts, axis=0).reshape(1, -1)).ravel()

    def _set_scores(self, matrix: np.ndarray, norms: np.ndarray, encoder: MultiLabelBinarizer,
                    target: set) -> np.ndarray:
        """Vectorised cosine between a user multi-hot vector and every movie's vector."""
        if not target:
            return np.zeros(len(self.movies))
        user = np.array([1.0 if c in target else 0.0 for c in encoder.classes_])
        dots = matrix @ user
        denom = norms * math.sqrt(user.sum())
        return np.divide(dots, denom, out=np.zeros_like(dots), where=denom > 0)

    def _top_terms(self, vector: np.ndarray, n: int) -> list[dict]:
        idx = np.argsort(-vector, kind="stable")[:n]
        return [
            {"term": self.token_labels.get(self.feature_names[i], self.feature_names[i]),
             "weight": round(float(vector[i]), 4)}
            for i in idx if vector[i] > 0
        ]

    # ------------------------------------------------------------------ #
    # Steps 3-4: preference (base) scores, cached per preference set
    # ------------------------------------------------------------------ #
    @staticmethod
    def _prefs_key(prefs: UserPreferences) -> tuple:
        # Everything that influences component scores; top_n and min_rating only
        # affect filtering and are read from the live request instead.
        return (
            tuple(prefs.genres), tuple(prefs.languages), tuple(prefs.moods), tuple(prefs.keywords),
            tuple(prefs.liked_movie_ids), tuple(prefs.exclude_movie_ids), prefs.year_min, prefs.year_max,
            prefs.strict_years, prefs.strict_languages, tuple(sorted((prefs.weights or {}).items())),
        )

    def _score_all(self, prefs: UserPreferences) -> dict:
        """Component and base scores for every movie. Cached; callers must not mutate the result."""
        key = self._prefs_key(prefs)
        with self._cache_lock:
            cached = self._score_cache.get(key)
            if cached is not None:
                self._score_cache.move_to_end(key)
                self.cache_stats["hits"] += 1
        if cached is None:
            cached = self._compute_scores(prefs)
            with self._cache_lock:
                self.cache_stats["misses"] += 1
                self._score_cache[key] = cached
                if len(self._score_cache) > SCORE_CACHE_SIZE:
                    self._score_cache.popitem(last=False)
        # Request-specific values are attached fresh so cached entries stay correct.
        return {
            **cached,
            "prefs": prefs,
            "warnings": list(cached["warnings"]),
            "profile": {**cached["profile"], "min_rating": prefs.min_rating},
        }

    def _compute_scores(self, prefs: UserPreferences) -> dict:
        warnings: list[str] = []
        genres = self._resolve_labels("genre", prefs.genres)
        moods = self._resolve_labels("mood", prefs.moods)
        languages = self._resolve_labels("language", prefs.languages)
        keywords = unique(k for k in prefs.keywords if k and k.strip())
        liked = self._resolve_ids(prefs.liked_movie_ids, "liked_movie_ids")
        excluded = self._resolve_ids(prefs.exclude_movie_ids, "exclude_movie_ids")
        has_year_pref = prefs.year_min is not None or prefs.year_max is not None

        if not (genres or moods or languages or keywords or liked or has_year_pref):
            raise EmptyPreferencesError(
                "Provide at least one preference: genres, languages, moods, keywords, "
                "liked movies or a release-year range."
            )

        # Explicit choices win; otherwise infer genre / mood patterns from liked movies.
        target_genres, target_moods = set(genres), set(moods)
        genres_inferred = moods_inferred = False
        if not target_genres and liked:
            target_genres = set().union(*(self.genre_sets[i] for i in liked))
            genres_inferred = True
        if not target_moods and liked:
            target_moods = set().union(*(self.mood_sets[i] for i in liked))
            moods_inferred = True
        target_languages = set(languages)

        text_profile = self._text_profile(keywords, liked, warnings)
        if text_profile is not None:
            keyword_raw = cosine_similarity(text_profile.reshape(1, -1), self.text_matrix).ravel()
        else:
            keyword_raw = np.zeros(len(self.movies))
        best_text = float(keyword_raw.max())
        # Max-normalisation: raw TF-IDF cosines are small (typically < 0.5) while
        # genre/mood cosines reach 1, so the best text match in the catalogue is scaled to 1.
        keyword_scores = keyword_raw / best_text if best_text > 0 else keyword_raw

        n = len(self.movies)
        scores = {
            "genre": self._set_scores(self.genre_matrix, self.genre_norms, self.genre_encoder, target_genres),
            # Language is a match / no-match indicator, not a cosine over all chosen languages.
            "language": np.isin(self.languages, list(target_languages)).astype(float)
            if target_languages else np.zeros(n),
            "mood": self._set_scores(self.mood_matrix, self.mood_norms, self.mood_encoder, target_moods),
            "keyword": keyword_scores,
            "year": year_scores(self.years, prefs.year_min, prefs.year_max) if has_year_pref else np.zeros(n),
        }
        raw_scores = {**scores, "keyword": keyword_raw}

        active = {
            "genre": bool(target_genres),
            "language": bool(target_languages),
            "mood": bool(target_moods),
            "keyword": best_text > 0,
            "year": has_year_pref,
        }
        # A preference applied as a hard filter is constant (1.0) for every remaining
        # movie, so it would only inflate scores. It is scored only when it is the
        # user's sole preference (then ranking falls back to the tie-breakers).
        for component, strict in (("language", prefs.strict_languages), ("year", prefs.strict_years)):
            others = any(v for c, v in active.items() if c != component)
            if strict and active[component] and others:
                active[component] = False

        profile = self._profile_summary(
            target_genres, target_moods, target_languages, keywords, liked, prefs,
            genres_inferred, moods_inferred, text_profile, active,
        )
        if any(active.values()):
            weights = normalize_weights({**self.score_weights, **(prefs.weights or {})}, active)
            profile["weights"] = {c: round(w, 4) for c, w in weights.items()}
            base = np.round(sum(weights[c] * scores[c] for c in COMPONENTS), SCORE_DECIMALS)
        else:
            weights = {c: 0.0 for c in COMPONENTS}
            base = np.zeros(n)

        return {
            "warnings": warnings, "keywords": keywords, "keyword_query_tokens": [normalize_token(k) for k in keywords],
            "liked": liked, "excluded": excluded,
            "has_year_pref": has_year_pref, "target_genres": target_genres, "target_moods": target_moods,
            "target_languages": target_languages, "genres_inferred": genres_inferred,
            "moods_inferred": moods_inferred, "text_profile": text_profile, "scores": scores,
            "raw_scores": raw_scores, "active": active, "weights": weights, "base": base, "profile": profile,
        }

    # ------------------------------------------------------------------ #
    # Step 5: feedback adjustment (kept separate from the base score)
    # ------------------------------------------------------------------ #
    def _closest(self, indices: list[int]) -> tuple[np.ndarray, np.ndarray]:
        """For every movie: highest item similarity to any of `indices` (excluding itself)."""
        n = len(self.movies)
        if not indices:
            return np.zeros(n), np.full(n, -1)
        sims = self.item_similarity[:, indices].copy()
        sims[indices, np.arange(len(indices))] = -np.inf  # a movie cannot vouch for itself
        best = np.argmax(sims, axis=1)
        best_sim = sims[np.arange(n), best]
        valid = np.isfinite(best_sim)
        return np.where(valid, best_sim, 0.0), np.where(valid, np.array(indices)[best], -1)

    def _feedback_scores(self, feedback: FeedbackProfile | None) -> dict:
        n = len(self.movies)
        if feedback is None or feedback.is_empty:
            return {"applied": False, "adjustment": np.zeros(n), "pos_sim": np.zeros(n), "pos_idx": np.full(n, -1),
                    "neg_sim": np.zeros(n), "neg_idx": np.full(n, -1), "disliked": []}
        positive = unique([self.id_to_index[m] for m in feedback.liked + feedback.favorites if m in self.id_to_index])
        negative = unique([self.id_to_index[m] for m in feedback.disliked if m in self.id_to_index])
        pos_sim, pos_idx = self._closest(positive)
        neg_sim, neg_idx = self._closest(negative)
        adjustment = np.round(FEEDBACK_WEIGHT * (pos_sim - neg_sim), SCORE_DECIMALS)
        return {"applied": True, "adjustment": adjustment, "pos_sim": pos_sim, "pos_idx": pos_idx,
                "neg_sim": neg_sim, "neg_idx": neg_idx, "disliked": negative}

    def _with_feedback(self, ctx: dict, feedback: FeedbackProfile | None) -> dict:
        fb = self._feedback_scores(feedback)
        final = np.round(np.clip(ctx["base"] + fb["adjustment"], 0.0, 1.0), SCORE_DECIMALS)
        return {**ctx, "feedback": fb, "final": final}

    # ------------------------------------------------------------------ #
    # Step 6: filtering and ranking
    # ------------------------------------------------------------------ #
    def _filter(self, ctx: dict) -> tuple[np.ndarray, dict, list[tuple[str, np.ndarray]]]:
        """Apply hard filters. Returns the mask, the per-step counts and each step's own mask."""
        prefs = ctx["prefs"]
        n = len(self.movies)
        mask = np.ones(n, dtype=bool)
        report = {"total": int(mask.sum())}
        steps: list[tuple[str, np.ndarray]] = []

        def apply(key: str, label: str, step_mask: np.ndarray) -> None:
            nonlocal mask
            steps.append((label, step_mask))
            mask &= step_mask
            report[key] = int(mask.sum())

        if prefs.min_rating > 0:
            apply("after_min_rating", f"Rated below your minimum of {prefs.min_rating:g}",
                  self.ratings >= prefs.min_rating)
        if prefs.strict_years and ctx["has_year_pref"]:
            lo = prefs.year_min if prefs.year_min is not None else -10**9
            hi = prefs.year_max if prefs.year_max is not None else 10**9
            apply("after_year_range", "Released outside your strict year range",
                  (self.years >= lo) & (self.years <= hi))
        if prefs.strict_languages and ctx["target_languages"]:
            apply("after_languages", "Not in one of your strict languages",
                  np.isin(self.languages, list(ctx["target_languages"])))
        if ctx["liked"] or ctx["excluded"]:
            keep = np.ones(n, dtype=bool)
            keep[ctx["liked"] + ctx["excluded"]] = False
            apply("after_exclusions", "You already marked this movie as liked or excluded", keep)
        if ctx["feedback"]["disliked"]:
            keep = np.ones(n, dtype=bool)
            keep[ctx["feedback"]["disliked"]] = False
            apply("after_dislikes", "You disliked this movie", keep)
        # Feedback can only re-rank movies that match a preference, never add new ones.
        apply("with_positive_score", "Does not match any of your preferences", ctx["base"] > 0)
        return mask, report, steps

    def _ranked(self, ctx: dict, mask: np.ndarray) -> np.ndarray:
        """Deterministic ranking: final score desc, rating desc, movie_id asc."""
        candidates = np.where(mask)[0]
        order = np.lexsort((self.ids[candidates], -self.ratings[candidates], -ctx["final"][candidates]))
        return candidates[order]

    # ------------------------------------------------------------------ #
    # Step 7: explanation
    # ------------------------------------------------------------------ #
    def _feedback_item(self, i: int, ctx: dict) -> dict:
        fb = ctx["feedback"]
        pos_idx, neg_idx = int(fb["pos_idx"][i]), int(fb["neg_idx"][i])
        ref = lambda j: {"movie_id": int(self.ids[j]), "title": self.titles[j]} if j >= 0 else None  # noqa: E731
        return {
            "applied": fb["applied"],
            "adjustment": round(float(fb["adjustment"][i]), 4),
            "liked_similarity": round(float(fb["pos_sim"][i]), 4),
            "closest_liked": ref(pos_idx),
            "disliked_similarity": round(float(fb["neg_sim"][i]), 4),
            "closest_disliked": ref(neg_idx),
        }

    def _build_item(self, i: int, ctx: dict, rank: int | None) -> dict:
        scores, weights, active = ctx["scores"], ctx["weights"], ctx["active"]
        components = {
            c: {
                "value": round(float(scores[c][i]), 4),
                "raw": round(float(ctx["raw_scores"][c][i]), 4),
                "weight": round(weights[c], 4),
                "contribution": round(float(weights[c] * scores[c][i]), 4),
                "active": active[c],
            }
            for c in COMPONENTS
        }
        matched = self._matched(i, ctx)
        similar_to = self._similar_liked(i, ctx["liked"])
        feedback = self._feedback_item(i, ctx)
        text_profile = ctx["text_profile"]
        return {
            "rank": rank,
            "movie_id": int(self.ids[i]),
            "title": self.titles[i],
            "movie": self.movie_to_dict(i),
            "base_score": round(float(ctx["base"][i]), 4),
            "feedback_adjustment": feedback["adjustment"],
            "score": round(float(ctx["final"][i]), 4),
            "components": components,
            "matched": matched,
            "summary": self._summary(i, ctx, components, matched, similar_to, feedback),
            "reasons": self._reasons(i, ctx, components, matched),
            "top_terms": self._shared_terms(text_profile, i) if text_profile is not None else [],
            "similar_to": similar_to,
            "feedback": feedback,
        }

    def _matched(self, i: int, ctx: dict) -> dict:
        movie = self._movie_dicts[i]
        prefs = ctx["prefs"]
        user_tokens = ctx["keyword_query_tokens"]
        matched_keywords = [
            kw for kw, token in self.keyword_pairs[i]
            if any(t == token or (len(t) >= 4 and (t in token or token in t)) for t in user_tokens)
        ]
        return {
            "genres": [g for g in movie["genres"] if g in ctx["target_genres"]],
            "moods": [m for m in movie["moods"] if m in ctx["target_moods"]],
            "language": movie["language"] if movie["language"] in ctx["target_languages"] else None,
            "keywords": matched_keywords,
            "year_in_range": (year_score(movie["year"], prefs.year_min, prefs.year_max) == 1.0)
            if ctx["has_year_pref"] else None,
        }

    @staticmethod
    def _year_phrase(prefs: UserPreferences) -> str:
        if prefs.year_min is not None and prefs.year_max is not None:
            return f"like movies released between {prefs.year_min} and {prefs.year_max}"
        if prefs.year_min is not None:
            return f"like movies released from {prefs.year_min} onwards"
        return f"like movies released up to {prefs.year_max}"

    def _summary(self, i, ctx, components, matched, similar_to, feedback) -> str:
        """One sentence built only from attributes that actually matched, biggest contribution first."""
        phrases: list[tuple[float, int, str]] = []  # (contribution, tie-break order, phrase)

        def add(component: str, phrase: str) -> None:
            phrases.append((components[component]["contribution"], COMPONENTS.index(component), phrase))

        if components["genre"]["active"] and matched["genres"]:
            genres = join_phrases(matched["genres"])
            add("genre", f"loved movies in the {genres} genre{'s' if len(matched['genres']) > 1 else ''}"
                if ctx["genres_inferred"] else f"enjoy {genres} movies")
        if components["language"]["active"] and matched["language"]:
            add("language", f"prefer {matched['language']}-language content")
        if components["mood"]["active"] and matched["moods"]:
            moods = join_phrases(matched["moods"])
            add("mood", f"loved {moods} movies" if ctx["moods_inferred"] else f"are in the mood for something {moods}")
        if components["keyword"]["active"] and components["keyword"]["value"] > 0:
            if matched["keywords"]:
                kws = matched["keywords"]
                add("keyword", f"selected {join_phrases(kws)} as favourite theme{'s' if len(kws) > 1 else ''}")
            elif similar_to:
                add("keyword", f"loved {similar_to['title']}")
        if components["year"]["active"] and matched["year_in_range"]:
            add("year", self._year_phrase(ctx["prefs"]))
        if feedback["applied"] and feedback["adjustment"] >= 0.01 and feedback["closest_liked"]:
            phrases.append((feedback["adjustment"], len(COMPONENTS), f"liked {feedback['closest_liked']['title']}"))

        if not phrases:
            return "Recommended as the closest available match to your preferences."
        phrases.sort(key=lambda p: (-p[0], p[1]))
        return f"Recommended because you {join_phrases([p[2] for p in phrases])}."

    def _reasons(self, i, ctx, components, matched) -> list[str]:
        movie = self._movie_dicts[i]
        genres, moods = ctx["target_genres"], ctx["target_moods"]
        sentences = {}
        if components["genre"]["active"] and matched["genres"]:
            source = "genres from movies you liked" if ctx["genres_inferred"] else "your genres"
            sentences["genre"] = (
                f"Genre match ({len(matched['genres'])}/{len(genres)} of {source}): {', '.join(matched['genres'])}"
            )
        if components["mood"]["active"] and matched["moods"]:
            source = "moods from movies you liked" if ctx["moods_inferred"] else "your moods"
            sentences["mood"] = (
                f"Mood match ({len(matched['moods'])}/{len(moods)} of {source}): {', '.join(matched['moods'])}"
            )
        if components["language"]["active"] and matched["language"]:
            sentences["language"] = f"In your preferred language: {matched['language']}"
        if components["keyword"]["active"] and components["keyword"]["value"] > 0:
            if matched["keywords"]:
                sentences["keyword"] = f"Shares your themes: {', '.join(matched['keywords'])}"
            elif ctx["liked"]:
                sentences["keyword"] = "Keywords and description resemble the movies you liked"
            else:
                sentences["keyword"] = "Description is related to your keywords"
        if components["year"]["active"]:
            if matched["year_in_range"]:
                sentences["year"] = f"Released in {movie['year']}, inside your preferred years"
            elif components["year"]["value"] > 0:
                sentences["year"] = f"Released in {movie['year']}, close to your preferred years"
        # Most influential component first.
        order = sorted(sentences, key=lambda c: (-components[c]["contribution"], COMPONENTS.index(c)))
        return [sentences[c] for c in order] or ["Closest available match to your preferences"]

    def _shared_terms(self, profile: np.ndarray, i: int, n: int = 5) -> list[str]:
        """Terms contributing most to the TF-IDF cosine (largest profile_t × movie_t)."""
        # Read the CSR row directly (much cheaper than slicing a sparse row object).
        start, end = self.text_matrix.indptr[i], self.text_matrix.indptr[i + 1]
        terms = self.text_matrix.indices[start:end]
        product = profile[terms] * self.text_matrix.data[start:end]
        order = np.lexsort((terms, -product))[:n]  # ties broken by term index, as before
        return [self.token_labels.get(self.feature_names[terms[k]], self.feature_names[terms[k]])
                for k in order if product[k] > 0]

    def _similar_liked(self, i: int, liked: list[int]) -> dict | None:
        if not liked:
            return None
        sims = self.item_similarity[i, liked]
        best = int(np.argmax(sims))
        j = liked[best]
        return {"movie_id": int(self.ids[j]), "title": self.titles[j], "similarity": round(float(sims[best]), 4)}

    def _profile_summary(self, genres, moods, languages, keywords, liked, prefs,
                         genres_inferred, moods_inferred, text_profile, active) -> dict:
        return {
            "genres": sorted(genres),
            "moods": sorted(moods),
            "languages": sorted(languages),
            "keywords": keywords,
            "year_min": prefs.year_min,
            "year_max": prefs.year_max,
            "min_rating": prefs.min_rating,
            "genres_inferred": genres_inferred,
            "moods_inferred": moods_inferred,
            "liked_movies": [{"movie_id": int(self.ids[i]), "title": self.titles[i]} for i in liked],
            "top_terms": self._top_terms(text_profile, 12) if text_profile is not None else [],
            "active_components": [c for c in COMPONENTS if active[c]],
            "weights": {c: 0.0 for c in COMPONENTS},
        }

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def recommend(self, prefs: UserPreferences, feedback: FeedbackProfile | None = None) -> dict:
        ctx = self._with_feedback(self._score_all(prefs), feedback)
        profile = {**ctx["profile"], "feedback_applied": ctx["feedback"]["applied"]}
        warnings = ctx["warnings"]
        if not any(ctx["active"].values()):
            return self._empty_result(profile, warnings, {"total": len(self.movies)},
                                      "None of your preferences match anything in the catalogue.")

        mask, report, _ = self._filter(ctx)
        ranked = self._ranked(ctx, mask)[: prefs.top_n]
        if len(ranked) == 0:
            return self._empty_result(profile, warnings, report, self._no_match_message(report, prefs))

        recommendations, seen = [], set()
        for i in ranked:
            movie_id = int(self.ids[i])
            if movie_id in seen:  # defensive: indices are unique, but never emit duplicates
                continue
            seen.add(movie_id)
            recommendations.append(self._build_item(i, ctx, len(recommendations) + 1))

        return {
            "recommendations": recommendations,
            "profile": profile,
            "filter_report": report,
            "total_movies": len(self.movies),
            "message": None,
            "warnings": warnings,
        }

    def explain(self, prefs: UserPreferences, movie_id: int, feedback: FeedbackProfile | None = None) -> dict | None:
        """Score one movie against the preferences, whether or not it makes the top N.

        Uses exactly the same scoring, feedback, filters and ranking as recommend();
        `rank` is the movie's position in the full ranking, or None when filtered out.
        """
        i = self.id_to_index.get(int(movie_id))
        if i is None:
            return None
        ctx = self._with_feedback(self._score_all(prefs), feedback)
        mask, _, steps = self._filter(ctx)
        ranked = self._ranked(ctx, mask)
        positions = {int(idx): pos + 1 for pos, idx in enumerate(ranked)}
        item = self._build_item(i, ctx, positions.get(i))
        item["passes_filters"] = bool(mask[i])
        item["filtered_by"] = [label for label, step_mask in steps if not step_mask[i]]
        item["candidates"] = int(len(ranked))
        item["weights"] = {c: round(w, 4) for c, w in ctx["weights"].items()}
        return item

    def search(self, query: str = "", genres: list[str] | None = None, languages: list[str] | None = None,
               year_min: int | None = None, year_max: int | None = None, sort: str = "relevance",
               prefs: UserPreferences | None = None, feedback: FeedbackProfile | None = None,
               limit: int = 24, offset: int = 0) -> dict:
        """Title search with genre / language / year filters and relevance or rating sorting.

        Relevance = match score for the user's preferences when given (base + feedback),
        otherwise how well the title matches the query, otherwise rating.
        """
        if sort not in SORT_OPTIONS:
            raise InvalidPreferenceError(f"Unknown sort '{sort}'. Use one of: {', '.join(SORT_OPTIONS)}")
        genre_filter = set(self._resolve_labels("genre", genres or []))
        language_filter = self._resolve_labels("language", languages or [])
        n = len(self.movies)

        title_scores = np.array([title_relevance(query, t) for t in self.titles]) if query.strip() else np.zeros(n)
        mask = np.ones(n, dtype=bool)
        if query.strip():
            mask &= title_scores > 0
        if genre_filter:
            mask &= np.array([bool(gs & genre_filter) for gs in self.genre_sets])
        if language_filter:
            mask &= np.isin(self.languages, language_filter)
        if year_min is not None:
            mask &= self.years >= year_min
        if year_max is not None:
            mask &= self.years <= year_max

        ctx = self._with_feedback(self._score_all(prefs), feedback) if prefs is not None else None
        indices = np.where(mask)[0]
        ids, ratings, years = self.ids[indices], self.ratings[indices], self.years[indices]
        if sort == "relevance" and ctx is not None:
            order = np.lexsort((ids, -ratings, -title_scores[indices], -ctx["final"][indices]))
        elif sort == "relevance" and query.strip():
            order = np.lexsort((ids, -ratings, -title_scores[indices]))
        elif sort == "year":
            order = np.lexsort((ids, -ratings, -years))
        elif sort == "title":
            order = np.lexsort((ids, np.array([self.titles[i].lower() for i in indices])))
        else:  # rating, or relevance with nothing to be relevant to
            order = np.lexsort((ids, -years, -ratings))
        indices = indices[order]

        items = []
        for i in indices[offset: offset + limit]:
            item = {
                "movie": self.movie_to_dict(i),
                "title_relevance": round(float(title_scores[i]), 4) if query.strip() else None,
                "match_score": None, "base_score": None, "feedback_adjustment": None,
            }
            if ctx is not None:
                item.update(match_score=round(float(ctx["final"][i]), 4),
                            base_score=round(float(ctx["base"][i]), 4),
                            feedback_adjustment=round(float(ctx["feedback"]["adjustment"][i]), 4))
            items.append(item)
        return {
            "total": int(len(indices)),
            "limit": limit,
            "offset": offset,
            "sort": sort,
            "personalized": ctx is not None,
            "items": items,
        }

    def _empty_result(self, profile, warnings, report, message) -> dict:
        return {
            "recommendations": [],
            "profile": profile,
            "filter_report": report,
            "total_movies": len(self.movies),
            "message": message,
            "warnings": warnings,
        }

    @staticmethod
    def _no_match_message(report: dict, prefs: UserPreferences) -> str:
        steps = [
            ("after_min_rating", f"a minimum rating of {prefs.min_rating:g}"),
            ("after_year_range", "the strict release-year range"),
            ("after_languages", "the strict language filter"),
            ("after_exclusions", "excluding movies you already liked"),
            ("after_dislikes", "hiding movies you disliked"),
        ]
        for key, label in steps:
            if report.get(key) == 0:
                return f"No movies remain after applying {label}. Try relaxing that filter."
        return "No movies match any of your preferences. Try broader genres, moods or keywords."

    # ------------------------------------------------------------------ #
    # Item-to-item similarity ("more like this")
    # ------------------------------------------------------------------ #
    def similar_movies(self, movie_id: int, top_n: int = 8) -> list[dict] | None:
        """Nearest neighbours in the cached item-similarity matrix (cosine of feature vectors)."""
        i = self.id_to_index.get(int(movie_id))
        if i is None:
            return None
        sims = np.round(self.item_similarity[i], SCORE_DECIMALS)
        candidates = np.delete(np.arange(len(self.movies)), i)
        order = np.lexsort((self.ids[candidates], -self.ratings[candidates], -sims[candidates]))
        source = self._movie_dicts[i]

        results = []
        for j in candidates[order][:top_n]:
            target = self._movie_dicts[j]
            results.append({
                "movie": self.movie_to_dict(j),
                "similarity": round(float(sims[j]), 4),
                "shared_genres": [g for g in target["genres"] if g in self.genre_sets[i]],
                "shared_moods": [m for m in target["moods"] if m in self.mood_sets[i]],
                "shared_keywords": sorted(
                    self.token_labels.get(k, k) for k in self.keyword_tokens[i] & self.keyword_tokens[j]
                ),
                "same_language": source["language"] == target["language"],
                "same_director": source["director"] == target["director"],
                "shared_cast": sorted(self.cast_sets[i] & self.cast_sets[j]),
            })
        return results
