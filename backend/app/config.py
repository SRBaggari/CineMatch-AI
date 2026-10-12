"""Central configuration for the CineMatch AI backend."""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_PATH = BASE_DIR / "data" / "movies.csv"

APP_NAME = "CineMatch AI"
APP_DESCRIPTION = (
    "Content-based movie recommendation engine using feature vectors, TF-IDF, "
    "cosine similarity and explainable weighted preference matching."
)

# Origins allowed to call the API directly (the Vite dev server also proxies /api).
CORS_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:4173",
    "http://127.0.0.1:4173",
]

# Default weights of the five preference-matching components. They are
# re-normalised at request time over the components the user actually
# expressed a preference for, so the effective weights always sum to 1.
# Every component score lies in [0, 1], which keeps the components comparable.
SCORE_WEIGHTS = {
    "genre": 0.30,     # cosine similarity of multi-hot genre vectors
    "keyword": 0.25,   # TF-IDF cosine of keywords + description, max-normalised
    "mood": 0.20,      # cosine similarity of multi-hot mood vectors
    "language": 0.15,  # 1 if the movie is in a preferred language, else 0
    "year": 0.10,      # 1 inside the preferred year range, linear decay outside
}

# Outside the preferred year range the year score drops by 1/YEAR_DECAY_YEARS per
# year, reaching 0 at YEAR_DECAY_YEARS years away from the range.
YEAR_DECAY_YEARS = 20

# Block weights of the movie feature vector used for item-to-item similarity.
ITEM_SIMILARITY_WEIGHTS = {
    "genre": 0.35,
    "keyword": 0.30,
    "mood": 0.25,
    "language": 0.10,
}

# Keyword tags are repeated in a movie's text document so they outweigh
# incidental words in the description.
KEYWORD_REPEAT = 2

DEFAULT_TOP_N = 10
MAX_TOP_N = 50

DATASET_INFO = {
    "name": "CineMatch curated movie catalogue",
    "synthetic": False,
    "verified": False,
    "provenance": (
        "Hand-curated for educational use. Titles, release years, directors and cast "
        "refer to real films, but ratings, runtimes, keywords, moods and descriptions "
        "were written from general knowledge for this project. They are approximate "
        "and have not been verified against an authoritative source such as IMDb or TMDB."
    ),
}
