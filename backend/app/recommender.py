"""Content-based recommendation engine with explainable weighted preference matching.

Pipeline
--------
1. Feature vectors: every movie is represented by
   - a multi-hot genre vector,
   - a multi-hot mood vector,
   - a one-hot language vector,
   - a TF-IDF vector of its keywords and description,
   - its release year.
2. User profile: the user's preferences are mapped into the same spaces.
   Keywords (and, optionally, liked movies) form a TF-IDF profile vector.
3. Component scores, each in [0, 1]:
   - genre    cosine(user genres, movie genres)   = |U ∩ M| / sqrt(|U|·|M|)
   - mood     cosine(user moods, movie moods)
   - language 1 if the movie's language was preferred, else 0
   - keyword  cosine(TF-IDF profile, TF-IDF movie), divided by the best value in
              the catalogue so the strongest text match scores 1
   - year     1 inside the preferred range, linear decay outside it
4. Weighted score: weights of the components the user gave a preference for are
   re-normalised to sum to 1, and score = Σ weight_c · component_c.
5. Hard filters (minimum rating; optionally strict year range / languages),
   exclusion of liked movies, removal of zero-score movies, deterministic ranking.
6. Explanation: matched preferences, reasons ordered by contribution, and the
   full component breakdown for every recommendation.

The score is a relevance score in [0, 1]. It is a weighted similarity, not a
calibrated probability that the user will like the movie.
"""

import math
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix, hstack
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import MultiLabelBinarizer, normalize

from .config import (
    DATASET_INFO,
    DEFAULT_TOP_N,
    ITEM_SIMILARITY_WEIGHTS,
    KEYWORD_REPEAT,
    MAX_TOP_N,
    SCORE_WEIGHTS,
    YEAR_DECAY_YEARS,
)
from .data_loader import normalize_token

COMPONENTS = ("genre", "language", "mood", "keyword", "year")
SCORE_DECIMALS = 6  # scores are rounded before ranking so float noise cannot break ties


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


# ---------------------------------------------------------------------- #
# Pure scoring helpers (unit-tested directly)
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


class RecommendationEngine:
    def __init__(self, movies: pd.DataFrame, score_weights: dict | None = None):
        self.movies = movies.reset_index(drop=True)
        self.score_weights = {**SCORE_WEIGHTS, **(score_weights or {})}
        self.ids = self.movies["movie_id"].to_numpy(dtype=int)
        self.years = self.movies["year"].to_numpy(dtype=int)
        self.ratings = self.movies["rating"].to_numpy(dtype=float)
        self.id_to_index = {int(mid): i for i, mid in enumerate(self.ids)}
        self.token_labels: dict[str, str] = {}
        self._build_features()

    # ------------------------------------------------------------------ #
    # Step 1: feature vectors
    # ------------------------------------------------------------------ #
    def _build_features(self) -> None:
        # Structured attributes -> multi-hot / one-hot vectors.
        self.genre_encoder = MultiLabelBinarizer()
        self.genre_matrix = self.genre_encoder.fit_transform(self.movies["genres"]).astype(float)
        self.mood_encoder = MultiLabelBinarizer()
        self.mood_matrix = self.mood_encoder.fit_transform(self.movies["moods"]).astype(float)
        self.language_encoder = MultiLabelBinarizer()
        self.language_matrix = self.language_encoder.fit_transform(
            [[lang] for lang in self.movies["language"]]
        ).astype(float)

        # Case-insensitive lookup from user input to canonical labels.
        self.label_lookup = {
            "genre": {normalize_token(g): g for g in self.genre_encoder.classes_},
            "mood": {normalize_token(m): m for m in self.mood_encoder.classes_},
            "language": {normalize_token(lang): lang for lang in self.language_encoder.classes_},
        }

        # Keywords + description -> TF-IDF vectors.
        for keywords in self.movies["keywords"]:
            for kw in keywords:
                self.token_labels.setdefault(normalize_token(kw), kw)
        documents = [
            keyword_document(row.keywords, row.overview) for row in self.movies.itertuples(index=False)
        ]
        self.vectorizer = TfidfVectorizer(stop_words="english", sublinear_tf=True)
        self.text_matrix = self.vectorizer.fit_transform(documents)
        self.feature_names = self.vectorizer.get_feature_names_out()

        self.genre_sets = [set(gs) for gs in self.movies["genres"]]
        self.mood_sets = [set(ms) for ms in self.movies["moods"]]
        self.keyword_tokens = [{normalize_token(k) for k in ks} for ks in self.movies["keywords"]]
        self.cast_sets = [set(cs) for cs in self.movies["cast"]]

        # Combined movie feature vector for item-to-item similarity: each block is
        # L2-normalised and scaled by sqrt(weight), so the cosine of two combined
        # vectors equals the weighted average of the per-block cosines.
        blocks = []
        for name, matrix in (
            ("genre", csr_matrix(self.genre_matrix)),
            ("keyword", self.text_matrix),
            ("mood", csr_matrix(self.mood_matrix)),
            ("language", csr_matrix(self.language_matrix)),
        ):
            blocks.append(normalize(matrix) * math.sqrt(ITEM_SIMILARITY_WEIGHTS[name]))
        self.item_features = hstack(blocks).tocsr()
        self.item_similarity = cosine_similarity(self.item_features)

    # ------------------------------------------------------------------ #
    # Catalogue helpers
    # ------------------------------------------------------------------ #
    def movie_to_dict(self, index: int) -> dict:
        row = self.movies.iloc[index]
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
            mask &= (self.movies["language"] == lang).to_numpy()
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

    def _text_profile(self, keywords: list[str], liked: list[int], warnings: list[str]) -> np.ndarray | None:
        parts = []
        if keywords:
            vec = self.vectorizer.transform([keyword_document(keywords)])
            if vec.nnz:
                parts.append(normalize(vec).toarray().ravel())
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

    def _set_scores(self, matrix: np.ndarray, encoder: MultiLabelBinarizer, target: set) -> np.ndarray:
        """Vectorised cosine between a user multi-hot vector and every movie's vector."""
        if not target:
            return np.zeros(len(self.movies))
        user = np.array([1.0 if c in target else 0.0 for c in encoder.classes_])
        dots = matrix @ user
        norms = np.sqrt(matrix.sum(axis=1)) * math.sqrt(user.sum())
        return np.divide(dots, norms, out=np.zeros_like(dots), where=norms > 0)

    def _top_terms(self, vector: np.ndarray, n: int) -> list[dict]:
        idx = np.argsort(-vector, kind="stable")[:n]
        return [
            {"term": self.token_labels.get(self.feature_names[i], self.feature_names[i]),
             "weight": round(float(vector[i]), 4)}
            for i in idx if vector[i] > 0
        ]

    # ------------------------------------------------------------------ #
    # Steps 3-6: scoring, filtering, ranking, explanation
    # ------------------------------------------------------------------ #
    def _score_all(self, prefs: UserPreferences) -> dict:
        """Resolve preferences and compute every component score for every movie."""
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

        # --- component scores, all in [0, 1] ---------------------------------
        text_profile = self._text_profile(keywords, liked, warnings)
        if text_profile is not None:
            keyword_raw = cosine_similarity(text_profile.reshape(1, -1), self.text_matrix).ravel()
        else:
            keyword_raw = np.zeros(len(self.movies))
        best_text = float(keyword_raw.max())
        # Max-normalisation: raw TF-IDF cosines are small (typically < 0.5) while
        # genre/mood cosines reach 1, so the best text match in the catalogue is scaled to 1.
        keyword_scores = keyword_raw / best_text if best_text > 0 else keyword_raw

        scores = {
            "genre": self._set_scores(self.genre_matrix, self.genre_encoder, target_genres),
            "language": self._set_scores(self.language_matrix, self.language_encoder, target_languages)
            if target_languages else np.zeros(len(self.movies)),
            "mood": self._set_scores(self.mood_matrix, self.mood_encoder, target_moods),
            "keyword": keyword_scores,
            "year": np.array([year_score(y, prefs.year_min, prefs.year_max) for y in self.years])
            if has_year_pref else np.zeros(len(self.movies)),
        }
        # Language is a match / no-match indicator, not a cosine over all chosen languages.
        if target_languages:
            scores["language"] = (scores["language"] > 0).astype(float)
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
            genres_inferred, moods_inferred, text_profile, active, None,
        )
        if any(active.values()):
            weights = normalize_weights({**self.score_weights, **(prefs.weights or {})}, active)
            profile["weights"] = {c: round(w, 4) for c, w in weights.items()}
            final = np.round(sum(weights[c] * scores[c] for c in COMPONENTS), SCORE_DECIMALS)
        else:
            weights = {c: 0.0 for c in COMPONENTS}
            final = np.zeros(len(self.movies))

        return {
            "prefs": prefs, "warnings": warnings, "keywords": keywords, "liked": liked, "excluded": excluded,
            "has_year_pref": has_year_pref, "target_genres": target_genres, "target_moods": target_moods,
            "target_languages": target_languages, "genres_inferred": genres_inferred,
            "moods_inferred": moods_inferred, "text_profile": text_profile, "scores": scores,
            "raw_scores": raw_scores, "active": active, "weights": weights, "final": final, "profile": profile,
        }

    def _filter(self, ctx: dict) -> tuple[np.ndarray, dict, list[tuple[str, np.ndarray]]]:
        """Apply hard filters. Returns the mask, the per-step counts and each step's own mask."""
        prefs = ctx["prefs"]
        mask = np.ones(len(self.movies), dtype=bool)
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
                  np.isin(self.movies["language"].to_numpy(), list(ctx["target_languages"])))
        if ctx["liked"] or ctx["excluded"]:
            keep = np.ones(len(self.movies), dtype=bool)
            keep[ctx["liked"] + ctx["excluded"]] = False
            apply("after_exclusions", "You already marked this movie as liked or excluded", keep)
        apply("with_positive_score", "Does not match any of your preferences", ctx["final"] > 0)
        return mask, report, steps

    def _ranked(self, ctx: dict, mask: np.ndarray) -> np.ndarray:
        """Deterministic ranking: score desc, rating desc, movie_id asc."""
        candidates = np.where(mask)[0]
        order = np.lexsort((self.ids[candidates], -self.ratings[candidates], -ctx["final"][candidates]))
        return candidates[order]

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
        matched = self._matched(i, ctx["target_genres"], ctx["target_moods"], ctx["target_languages"],
                                ctx["keywords"], ctx["prefs"], ctx["has_year_pref"])
        text_profile = ctx["text_profile"]
        return {
            "rank": rank,
            "movie_id": int(self.ids[i]),
            "title": self.movies.iloc[i]["title"],
            "movie": self.movie_to_dict(i),
            "score": round(float(ctx["final"][i]), 4),
            "components": components,
            "matched": matched,
            "reasons": self._reasons(i, components, matched, ctx["liked"], ctx["prefs"], ctx["target_genres"],
                                     ctx["target_moods"], ctx["genres_inferred"], ctx["moods_inferred"]),
            "top_terms": self._shared_terms(text_profile, i) if text_profile is not None else [],
            "similar_to": self._similar_liked(i, ctx["liked"]),
        }

    def recommend(self, prefs: UserPreferences) -> dict:
        ctx = self._score_all(prefs)
        profile, warnings = ctx["profile"], ctx["warnings"]
        if not any(ctx["active"].values()):
            return self._empty_result(
                profile, warnings, {"total": len(self.movies)},
                "None of your preferences match anything in the catalogue.",
            )

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

    def explain(self, prefs: UserPreferences, movie_id: int) -> dict | None:
        """Score one movie against the preferences, whether or not it makes the top N.

        Uses exactly the same scoring, filters and ranking as recommend(); `rank` is the
        movie's position in the full ranking, or None when a hard filter removes it.
        """
        i = self.id_to_index.get(int(movie_id))
        if i is None:
            return None
        ctx = self._score_all(prefs)
        mask, _, steps = self._filter(ctx)
        ranked = self._ranked(ctx, mask)
        positions = {int(idx): pos + 1 for pos, idx in enumerate(ranked)}
        item = self._build_item(i, ctx, positions.get(i))
        item["passes_filters"] = bool(mask[i])
        item["filtered_by"] = [label for label, step_mask in steps if not step_mask[i]]
        item["candidates"] = int(len(ranked))
        item["weights"] = {c: round(w, 4) for c, w in ctx["weights"].items()}
        return item

    # ------------------------------------------------------------------ #
    # Result helpers
    # ------------------------------------------------------------------ #
    def _profile_summary(self, genres, moods, languages, keywords, liked, prefs,
                         genres_inferred, moods_inferred, text_profile, active, weights) -> dict:
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
            "liked_movies": [{"movie_id": int(self.ids[i]), "title": self.movies.iloc[i]["title"]} for i in liked],
            "top_terms": self._top_terms(text_profile, 12) if text_profile is not None else [],
            "active_components": [c for c in COMPONENTS if active[c]],
            "weights": weights or {c: 0.0 for c in COMPONENTS},
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
        ]
        for key, label in steps:
            if report.get(key) == 0:
                return f"No movies remain after applying {label}. Try relaxing that filter."
        return "No movies match any of your preferences. Try broader genres, moods or keywords."

    def _matched(self, i, genres, moods, languages, keywords, prefs, has_year_pref) -> dict:
        movie = self.movies.iloc[i]
        user_tokens = [normalize_token(k) for k in keywords]
        matched_keywords = [
            kw for kw in movie["keywords"]
            if any(
                t == normalize_token(kw)
                or (len(t) >= 4 and (t in normalize_token(kw) or normalize_token(kw) in t))
                for t in user_tokens
            )
        ]
        return {
            "genres": [g for g in movie["genres"] if g in genres],
            "moods": [m for m in movie["moods"] if m in moods],
            "language": movie["language"] if movie["language"] in languages else None,
            "keywords": matched_keywords,
            "year_in_range": (year_score(int(movie["year"]), prefs.year_min, prefs.year_max) == 1.0)
            if has_year_pref else None,
        }

    def _reasons(self, i, components, matched, liked, prefs, genres, moods,
                 genres_inferred, moods_inferred) -> list[str]:
        movie = self.movies.iloc[i]
        sentences = {}
        if components["genre"]["active"] and matched["genres"]:
            source = "genres from movies you liked" if genres_inferred else "your genres"
            sentences["genre"] = (
                f"Genre match ({len(matched['genres'])}/{len(genres)} of {source}): {', '.join(matched['genres'])}"
            )
        if components["mood"]["active"] and matched["moods"]:
            source = "moods from movies you liked" if moods_inferred else "your moods"
            sentences["mood"] = (
                f"Mood match ({len(matched['moods'])}/{len(moods)} of {source}): {', '.join(matched['moods'])}"
            )
        if components["language"]["active"] and matched["language"]:
            sentences["language"] = f"In your preferred language: {matched['language']}"
        if components["keyword"]["active"] and components["keyword"]["value"] > 0:
            if matched["keywords"]:
                sentences["keyword"] = f"Shares your themes: {', '.join(matched['keywords'])}"
            elif liked:
                sentences["keyword"] = "Keywords and description resemble the movies you liked"
            else:
                sentences["keyword"] = "Description is related to your keywords"
        if components["year"]["active"]:
            year = int(movie["year"])
            if matched["year_in_range"]:
                sentences["year"] = f"Released in {year}, inside your preferred years"
            elif components["year"]["value"] > 0:
                sentences["year"] = f"Released in {year}, close to your preferred years"
        # Most influential component first.
        order = sorted(sentences, key=lambda c: (-components[c]["contribution"], COMPONENTS.index(c)))
        return [sentences[c] for c in order] or ["Closest available match to your preferences"]

    def _shared_terms(self, profile: np.ndarray, i: int, n: int = 5) -> list[str]:
        """Terms contributing most to the TF-IDF cosine (largest profile_t × movie_t)."""
        movie_vec = self.text_matrix[i].toarray().ravel()
        product = profile * movie_vec
        top = np.argsort(-product, kind="stable")[:n]
        return [self.token_labels.get(self.feature_names[t], self.feature_names[t]) for t in top if product[t] > 0]

    def _similar_liked(self, i: int, liked: list[int]) -> dict | None:
        if not liked:
            return None
        sims = self.item_similarity[i, liked]
        best = int(np.argmax(sims))
        j = liked[best]
        return {
            "movie_id": int(self.ids[j]),
            "title": self.movies.iloc[j]["title"],
            "similarity": round(float(sims[best]), 4),
        }

    # ------------------------------------------------------------------ #
    # Item-to-item similarity ("more like this")
    # ------------------------------------------------------------------ #
    def similar_movies(self, movie_id: int, top_n: int = 8) -> list[dict] | None:
        i = self.id_to_index.get(int(movie_id))
        if i is None:
            return None
        sims = np.round(self.item_similarity[i], SCORE_DECIMALS)
        candidates = np.array([j for j in range(len(self.movies)) if j != i])
        order = np.lexsort((self.ids[candidates], -self.ratings[candidates], -sims[candidates]))
        source = self.movies.iloc[i]

        results = []
        for j in candidates[order][:top_n]:
            target = self.movies.iloc[j]
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
