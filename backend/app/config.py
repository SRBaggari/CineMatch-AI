"""Central configuration for the CineMatch AI backend."""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_PATH = BASE_DIR / "data" / "movies.csv"

APP_NAME = "CineMatch AI"
APP_DESCRIPTION = (
    "Content-based movie recommendation engine using TF-IDF vectorization, "
    "cosine similarity and explainable hybrid scoring."
)

# Origins allowed to call the API directly (the Vite dev server also proxies /api).
CORS_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:4173",
    "http://127.0.0.1:4173",
]

# How many times each metadata field is repeated in a movie's "content soup".
# Repetition raises the term frequency, so these fields dominate the TF-IDF vector.
FIELD_WEIGHTS = {
    "genres": 3,
    "moods": 2,
    "keywords": 2,
    "director": 1,
    "cast": 1,
}

# Weights of the hybrid score components. Inactive components (for example the
# mood score when the user picked no moods) are dropped and the rest re-normalised.
SCORE_WEIGHTS = {
    "content": 0.55,  # cosine similarity between user profile and movie TF-IDF vector
    "genre": 0.20,    # Jaccard overlap of genres
    "mood": 0.15,     # Jaccard overlap of moods
    "quality": 0.10,  # min-max normalised rating
}

DEFAULT_TOP_N = 12
MAX_TOP_N = 50
