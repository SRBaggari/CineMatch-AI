"""Builds the analytics payload from the catalogue and the locally stored usage data.

Every number comes from either the dataset or the SQLite usage log. When nothing
has been logged yet the usage section is empty (zeros), never estimated.
"""

import numpy as np

from .recommender import RecommendationEngine
from .store import Store


def score_histogram(scores: list[float], bins: int = 10) -> list[dict]:
    """Counts of scores in equal-width bins over [0, 1]; the last bin includes 1.0."""
    edges = np.linspace(0.0, 1.0, bins + 1)
    counts, _ = np.histogram(np.asarray(scores, dtype=float), bins=edges) if scores else (np.zeros(bins, int), None)
    return [
        {"label": f"{edges[i]:.1f}–{edges[i + 1]:.1f}", "start": round(float(edges[i]), 2),
         "end": round(float(edges[i + 1]), 2), "count": int(counts[i])}
        for i in range(bins)
    ]


def build_analytics(engine: RecommendationEngine, store: Store) -> dict:
    usage = store.usage_stats()
    # Only count feedback for movies that are still in the catalogue (matches /api/feedback).
    feedback = [f for f in store.get_feedback().values() if engine.get_movie(f["movie_id"]) is not None]
    scores = usage["scores"]
    most_recommended = [
        {"movie_id": movie_id, "title": engine.get_movie(movie_id)["title"], "count": count}
        for movie_id, count in usage["most_recommended"]
        if engine.get_movie(movie_id) is not None
    ]
    notes = [
        "Dataset figures are computed from backend/data/movies.csv.",
        "Usage figures come from the local SQLite log of recommendation requests made on this installation.",
    ]
    if usage["total_requests"] == 0:
        notes.append("No recommendations have been requested yet, so usage charts are empty.")
    return {
        "dataset": engine.dataset_analytics(),
        "usage": {
            "total_requests": usage["total_requests"],
            "recommendations_served": len(scores),
            "genre_selections": usage["selections"]["genres"],
            "mood_selections": usage["selections"]["moods"],
            "language_selections": usage["selections"]["languages"],
            "keyword_selections": dict(list(usage["selections"]["keywords"].items())[:15]),
            "score_distribution": score_histogram(scores),
            "average_score": round(float(np.mean(scores)), 4) if scores else None,
            "most_recommended": most_recommended,
        },
        "feedback": {
            "likes": sum(1 for f in feedback if f["reaction"] == "like"),
            "dislikes": sum(1 for f in feedback if f["reaction"] == "dislike"),
            "favorites": sum(1 for f in feedback if f["favorite"]),
        },
        "notes": notes,
    }
