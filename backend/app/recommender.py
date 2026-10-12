"""Content-based recommendation engine.

Pipeline
--------
1. Feature engineering: every movie becomes a weighted "content soup" built from
   its genres, moods, keywords, director, cast and overview text.
2. Vectorisation: TF-IDF turns each soup into a sparse vector. Rare, specific
   terms (e.g. "time loop") get more weight than common ones (e.g. "drama").
3. User profile: the user's explicit preferences (genres, moods, keywords) and the
   averaged vectors of the movies they like are blended into one profile vector.
4. Similarity: cosine similarity between the profile vector and every movie.
5. Hybrid scoring: the content similarity is blended with genre overlap, mood
   overlap (both Jaccard) and a normalised quality score.
6. Explanation: every recommendation carries the matched genres, moods, keywords,
   the liked movie it most resembles, the strongest shared features and a full
   score breakdown.
"""

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import normalize

from .config import FIELD_WEIGHTS, SCORE_WEIGHTS
from .data_loader import normalize_token


class EmptyPreferencesError(ValueError):
    """Raised when a request contains no usable preference signal."""


@dataclass
class UserPreferences:
    genres: list[str] = field(default_factory=list)
    moods: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    liked_movie_ids: list[int] = field(default_factory=list)
    year_min: int | None = None
    year_max: int | None = None
    min_rating: float = 0.0
    languages: list[str] = field(default_factory=list)
    top_n: int = 12


def jaccard(a: set, b: set) -> float:
    """|A ∩ B| / |A ∪ B| — 1.0 means identical sets, 0.0 means nothing in common."""
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


class RecommendationEngine:
    def __init__(self, movies: pd.DataFrame, score_weights: dict | None = None):
        self.movies = movies.reset_index(drop=True)
        self.score_weights = {**SCORE_WEIGHTS, **(score_weights or {})}
        self.id_to_index = {int(mid): i for i, mid in enumerate(self.movies["movie_id"])}
        # Maps a squashed token back to a readable label ("sciencefiction" -> "Science Fiction").
        self.token_labels: dict[str, str] = {}
        self._build_features()

    # ------------------------------------------------------------------ #
    # Feature engineering
    # ------------------------------------------------------------------ #
    def _tag(self, value: str) -> str:
        token = normalize_token(value)
        if token:
            self.token_labels.setdefault(token, value)
        return token

    def _content_soup(self, row: pd.Series) -> str:
        parts: list[str] = []
        for column, repeat in FIELD_WEIGHTS.items():
            values = row[column] if isinstance(row[column], list) else [row[column]]
            tokens = [self._tag(v) for v in values if v]
            parts.extend(tokens * repeat)
        parts.append(row["overview"])
        return " ".join(parts)

    def _build_features(self) -> None:
        # Register genre and mood labels first so their capitalised form wins when
        # a keyword normalises to the same token (keyword "family" vs genre "Family").
        for column in ("genres", "moods"):
            for labels in self.movies[column]:
                for value in labels:
                    self._tag(value)
        self.movies["soup"] = self.movies.apply(self._content_soup, axis=1)

        self.vectorizer = TfidfVectorizer(stop_words="english", sublinear_tf=True)
        self.tfidf_matrix = self.vectorizer.fit_transform(self.movies["soup"])
        self.feature_names = self.vectorizer.get_feature_names_out()

        # Pre-computed movie-to-movie similarity matrix (n_movies x n_movies).
        self.item_similarity = cosine_similarity(self.tfidf_matrix)

        self.genre_sets = [{normalize_token(g) for g in gs} for gs in self.movies["genres"]]
        self.mood_sets = [{normalize_token(m) for m in ms} for ms in self.movies["moods"]]
        self.keyword_sets = [{normalize_token(k) for k in ks} for ks in self.movies["keywords"]]
        self.cast_sets = [{normalize_token(c) for c in cs} for cs in self.movies["cast"]]

        ratings = self.movies["rating"].to_numpy(dtype=float)
        spread = ratings.max() - ratings.min()
        self.quality_scores = (ratings - ratings.min()) / spread if spread else np.ones_like(ratings)

        self.all_genres = self._label_counts("genres")
        self.all_moods = self._label_counts("moods")
        self.all_keywords = self._label_counts("keywords")
        self.all_languages = self._label_counts_scalar("language")

    def _label_counts(self, column: str) -> dict[str, int]:
        counts = self.movies[column].explode().dropna().value_counts()
        return {str(k): int(v) for k, v in counts.items()}

    def _label_counts_scalar(self, column: str) -> dict[str, int]:
        counts = self.movies[column].value_counts()
        return {str(k): int(v) for k, v in counts.items()}

    # ------------------------------------------------------------------ #
    # Public helpers
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

    def search_movies(self, query: str = "", genre: str | None = None, limit: int = 20) -> list[dict]:
        df = self.movies
        mask = pd.Series(True, index=df.index)
        if query:
            q = query.strip().lower()
            mask &= df["title"].str.lower().str.contains(q, regex=False)
        if genre:
            g = normalize_token(genre)
            mask &= pd.Series([g in gs for gs in self.genre_sets], index=df.index)
        matches = df[mask].sort_values(["rating", "year"], ascending=False).head(limit)
        return [self.movie_to_dict(i) for i in matches.index]

    def metadata(self) -> dict:
        years = self.movies["year"]
        ratings = self.movies["rating"]
        return {
            "total_movies": len(self.movies),
            "vocabulary_size": len(self.feature_names),
            "genres": self.all_genres,
            "moods": self.all_moods,
            "popular_keywords": dict(list(self.all_keywords.items())[:40]),
            "languages": self.all_languages,
            "year_min": int(years.min()),
            "year_max": int(years.max()),
            "rating_min": float(ratings.min()),
            "rating_max": float(ratings.max()),
            "score_weights": self.score_weights,
            "field_weights": FIELD_WEIGHTS,
        }

    # ------------------------------------------------------------------ #
    # Step 3: user profile construction
    # ------------------------------------------------------------------ #
    def _resolve(self, values: list[str], known: dict[str, int]) -> tuple[list[str], list[str]]:
        """Match user-supplied labels against known labels case-insensitively."""
        lookup = {normalize_token(k): k for k in known}
        resolved, unknown = [], []
        for v in values:
            label = lookup.get(normalize_token(v))
            if label and label not in resolved:
                resolved.append(label)
            elif not label:
                unknown.append(v)
        return resolved, unknown

    def _build_profile(self, genres, moods, keywords, liked_indices, warnings) -> np.ndarray:
        components: list[np.ndarray] = []

        tokens: list[str] = []
        tokens += [normalize_token(g) for g in genres] * FIELD_WEIGHTS["genres"]
        tokens += [normalize_token(m) for m in moods] * FIELD_WEIGHTS["moods"]
        for kw in keywords:
            # Add the squashed tag ("timetravel") and the raw words ("time travel")
            # so a keyword can match both tags and overview text.
            tokens += [normalize_token(kw)] * FIELD_WEIGHTS["keywords"]
            tokens.append(kw.lower())

        if tokens:
            explicit = self.vectorizer.transform([" ".join(tokens)])
            if explicit.nnz:
                components.append(normalize(explicit).toarray()[0])
            else:
                warnings.append("None of your genres, moods or keywords appear in the dataset vocabulary.")

        if liked_indices:
            liked = np.asarray(self.tfidf_matrix[liked_indices].mean(axis=0)).ravel()
            components.append(normalize(liked.reshape(1, -1))[0])

        if not components:
            raise EmptyPreferencesError(
                "Select at least one genre, mood, keyword or favourite movie to build your taste profile."
            )

        # Equal blend of "what you told us" and "what you liked", then re-normalise.
        profile = np.mean(components, axis=0)
        return normalize(profile.reshape(1, -1))[0]

    def _top_features(self, vector: np.ndarray, n: int) -> list[dict]:
        idx = np.argsort(vector)[::-1][:n]
        return [
            {"term": self.token_labels.get(self.feature_names[i], self.feature_names[i]),
             "weight": round(float(vector[i]), 4)}
            for i in idx if vector[i] > 0
        ]

    # ------------------------------------------------------------------ #
    # Steps 4-6: scoring, ranking and explanation
    # ------------------------------------------------------------------ #
    def recommend(self, prefs: UserPreferences) -> dict:
        warnings: list[str] = []

        genres, unknown_g = self._resolve(prefs.genres, self.all_genres)
        moods, unknown_m = self._resolve(prefs.moods, self.all_moods)
        if unknown_g:
            warnings.append(f"Ignored unknown genres: {', '.join(unknown_g)}")
        if unknown_m:
            warnings.append(f"Ignored unknown moods: {', '.join(unknown_m)}")
        keywords = [k.strip() for k in prefs.keywords if k and k.strip()]

        liked_indices = []
        for mid in prefs.liked_movie_ids:
            idx = self.id_to_index.get(int(mid))
            if idx is None:
                warnings.append(f"Ignored unknown movie id {mid}")
            elif idx not in liked_indices:
                liked_indices.append(idx)

        profile = self._build_profile(genres, moods, keywords, liked_indices, warnings)

        # Target genre / mood sets: explicit choices win; otherwise infer them
        # from the movies the user liked (pattern extraction from behaviour).
        target_genres = {normalize_token(g) for g in genres}
        target_moods = {normalize_token(m) for m in moods}
        genres_inferred = moods_inferred = False
        if not target_genres and liked_indices:
            target_genres = set().union(*(self.genre_sets[i] for i in liked_indices))
            genres_inferred = True
        if not target_moods and liked_indices:
            target_moods = set().union(*(self.mood_sets[i] for i in liked_indices))
            moods_inferred = True
        keyword_tokens = {normalize_token(k) for k in keywords}

        # Step 4: cosine similarity between the profile and every movie.
        content_scores = cosine_similarity(profile.reshape(1, -1), self.tfidf_matrix).ravel()
        genre_scores = np.array([jaccard(target_genres, gs) for gs in self.genre_sets])
        mood_scores = np.array([jaccard(target_moods, ms) for ms in self.mood_sets])

        # Step 5: hybrid score using only the components that have a signal.
        active = {"content": True, "genre": bool(target_genres), "mood": bool(target_moods), "quality": True}
        raw = {k: w for k, w in self.score_weights.items() if active[k]}
        total = sum(raw.values())
        weights = {k: (raw.get(k, 0.0) / total) for k in self.score_weights}

        component_scores = {
            "content": content_scores,
            "genre": genre_scores,
            "mood": mood_scores,
            "quality": self.quality_scores,
        }
        final_scores = sum(weights[k] * component_scores[k] for k in weights)

        # Hard filters.
        mask = np.ones(len(self.movies), dtype=bool)
        years = self.movies["year"].to_numpy()
        if prefs.year_min is not None:
            mask &= years >= prefs.year_min
        if prefs.year_max is not None:
            mask &= years <= prefs.year_max
        if prefs.min_rating:
            mask &= self.movies["rating"].to_numpy() >= prefs.min_rating
        if prefs.languages:
            wanted = {normalize_token(lang) for lang in prefs.languages}
            mask &= np.array([normalize_token(lang) in wanted for lang in self.movies["language"]])
        mask[liked_indices] = False  # never recommend what the user already loves

        candidates = np.where(mask)[0]
        ranked = candidates[np.argsort(final_scores[candidates])[::-1]][: prefs.top_n]

        recommendations = []
        for rank, i in enumerate(ranked, start=1):
            breakdown = {
                k: {
                    "score": round(float(component_scores[k][i]), 4),
                    "weight": round(weights[k], 4),
                    "contribution": round(float(weights[k] * component_scores[k][i]), 4),
                }
                for k in weights
            }
            recommendations.append({
                "rank": rank,
                "movie": self.movie_to_dict(i),
                "score": round(float(final_scores[i]), 4),
                "match_percent": int(round(float(final_scores[i]) * 100)),
                "score_breakdown": breakdown,
                "explanation": self._explain(
                    i, profile, target_genres, target_moods, keyword_tokens, liked_indices
                ),
            })

        if not recommendations:
            warnings.append("No movies match your filters. Try widening the year range, rating or languages.")

        return {
            "recommendations": recommendations,
            "profile": {
                "top_terms": self._top_features(profile, 12),
                "genres": sorted(self.token_labels.get(g, g) for g in target_genres),
                "moods": sorted(self.token_labels.get(m, m) for m in target_moods),
                "genres_inferred": genres_inferred,
                "moods_inferred": moods_inferred,
                "liked_movies": [
                    {"movie_id": int(self.movies.iloc[i]["movie_id"]), "title": self.movies.iloc[i]["title"]}
                    for i in liked_indices
                ],
                "weights": {k: round(v, 4) for k, v in weights.items()},
            },
            "candidates_considered": int(len(candidates)),
            "total_movies": len(self.movies),
            "warnings": warnings,
        }

    def _shared_features(self, vector_a: np.ndarray, index_b: int, n: int = 5) -> list[str]:
        """Terms that contribute most to the cosine similarity (largest a_i * b_i)."""
        b = self.tfidf_matrix[index_b].toarray().ravel()
        product = vector_a * b
        top = np.argsort(product)[::-1][:n]
        return [self.token_labels.get(self.feature_names[t], self.feature_names[t]) for t in top if product[t] > 0]

    def _explain(self, i, profile, target_genres, target_moods, keyword_tokens, liked_indices) -> dict:
        movie = self.movies.iloc[i]
        label = self.token_labels.get

        matched_genres = [g for g in movie["genres"] if normalize_token(g) in target_genres]
        matched_moods = [m for m in movie["moods"] if normalize_token(m) in target_moods]
        matched_keywords = [
            k for k in movie["keywords"]
            if any(t == normalize_token(k) or (len(t) >= 4 and t in normalize_token(k)) for t in keyword_tokens)
        ]

        similar_to = None
        if liked_indices:
            sims = self.item_similarity[i, liked_indices]
            best = int(np.argmax(sims))
            j = liked_indices[best]
            if sims[best] > 0.05:
                liked_row = self.movies.iloc[j]
                similar_to = {
                    "movie_id": int(liked_row["movie_id"]),
                    "title": liked_row["title"],
                    "similarity": round(float(sims[best]), 4),
                    "shared_director": movie["director"] == liked_row["director"],
                    "shared_cast": sorted(
                        label(c, c) for c in self.cast_sets[i] & self.cast_sets[j]
                    ),
                    "shared_keywords": sorted(
                        label(k, k) for k in self.keyword_sets[i] & self.keyword_sets[j]
                    ),
                }

        reasons: list[str] = []
        if matched_genres:
            reasons.append(f"Matches your genres: {', '.join(matched_genres)}")
        if matched_moods:
            reasons.append(f"Fits the mood you want: {', '.join(matched_moods)}")
        if matched_keywords:
            reasons.append(f"Covers your themes: {', '.join(matched_keywords)}")
        if similar_to:
            reason = f"{round(similar_to['similarity'] * 100)}% similar to {similar_to['title']}, which you liked"
            if similar_to["shared_director"]:
                reason += f" (same director: {movie['director']})"
            reasons.append(reason)
            if similar_to["shared_cast"]:
                reasons.append(f"Shares cast with {similar_to['title']}: {', '.join(similar_to['shared_cast'])}")
        if movie["rating"] >= 8.0:
            reasons.append(f"Highly rated ({movie['rating']:.1f}/10)")
        if not reasons:
            reasons.append("Closest overall match to your taste profile")

        return {
            "reasons": reasons,
            "matched_genres": matched_genres,
            "matched_moods": matched_moods,
            "matched_keywords": matched_keywords,
            "shared_features": self._shared_features(profile, i),
            "similar_to": similar_to,
        }

    # ------------------------------------------------------------------ #
    # Item-to-item similarity ("more like this")
    # ------------------------------------------------------------------ #
    def similar_movies(self, movie_id: int, top_n: int = 8) -> list[dict] | None:
        i = self.id_to_index.get(int(movie_id))
        if i is None:
            return None
        sims = self.item_similarity[i].copy()
        sims[i] = -1.0  # exclude the movie itself
        source_vector = self.tfidf_matrix[i].toarray().ravel()
        source = self.movies.iloc[i]
        label = self.token_labels.get

        results = []
        for j in np.argsort(sims)[::-1][:top_n]:
            target = self.movies.iloc[j]
            results.append({
                "movie": self.movie_to_dict(j),
                "similarity": round(float(sims[j]), 4),
                "match_percent": int(round(float(sims[j]) * 100)),
                "shared_genres": [g for g in target["genres"] if normalize_token(g) in self.genre_sets[i]],
                "shared_moods": [m for m in target["moods"] if normalize_token(m) in self.mood_sets[i]],
                "shared_keywords": sorted(label(k, k) for k in self.keyword_sets[i] & self.keyword_sets[j]),
                "shared_cast": sorted(label(c, c) for c in self.cast_sets[i] & self.cast_sets[j]),
                "shared_director": source["director"] == target["director"],
                "shared_features": self._shared_features(source_vector, j),
            })
        return results
