import os
import tempfile
from pathlib import Path

# Isolate tests from the real feedback database and feature cache. This must run
# before `app` is imported, because app.config reads these variables at import time.
_TEST_DIR = Path(tempfile.mkdtemp(prefix="cinematch-tests-"))
os.environ["CINEMATCH_DB_PATH"] = str(_TEST_DIR / "test.db")
os.environ["CINEMATCH_CACHE_DIR"] = ""

import pandas as pd  # noqa: E402
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.data_loader import clean_movies  # noqa: E402
from app.main import app  # noqa: E402
from app.recommender import RecommendationEngine  # noqa: E402

# A tiny synthetic catalogue (not real films) with hand-checkable properties:
#   1  matches the "sci-fi mind-bender" preferences on every component
#   2  matches the genre only partially (Science Fiction, not Thriller)
#   3  matches the mood only
#   4  matches nothing in those preferences
#   5, 6, 7  identical content -> ties broken by rating, then movie_id
FIXTURE_ROWS = [
    (1, "Exact Match", 2010, "Science Fiction|Thriller", "Mind-Bending", "time travel|dreams",
     "A scientist travels through dreams to change time.", 8.0, "English"),
    (2, "Genre Only", 1980, "Science Fiction", "Funny", "cooking|family",
     "A family runs a restaurant on a space station.", 7.0, "French"),
    (3, "Mood Only", 2012, "Romance", "Mind-Bending", "love|letters",
     "Two pen pals fall in love through letters.", 7.5, "French"),
    (4, "Unrelated", 1950, "Western", "Gritty", "gold|outlaws",
     "Outlaws fight over buried gold in the desert.", 9.0, "Italian"),
    (5, "Twin A", 2000, "Comedy", "Funny", "party|friends",
     "Friends throw the biggest party in town.", 6.0, "Spanish"),
    (6, "Twin B", 2000, "Comedy", "Funny", "party|friends",
     "Friends throw the biggest party in town.", 7.0, "Spanish"),
    (7, "Twin C", 2000, "Comedy", "Funny", "party|friends",
     "Friends throw the biggest party in town.", 7.0, "Spanish"),
]


def fixture_frame(rows=FIXTURE_ROWS) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "movie_id": mid, "title": title, "year": year, "genres": genres, "director": f"Director {mid}",
                "cast": f"Actor {mid}a|Actor {mid}b", "keywords": keywords, "moods": moods,
                "overview": overview, "rating": rating, "runtime": 100, "language": language,
            }
            for mid, title, year, genres, moods, keywords, overview, rating, language in rows
        ]
    )


@pytest.fixture(scope="session")
def engine() -> RecommendationEngine:
    return RecommendationEngine(clean_movies(fixture_frame()))


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def store(client):
    """The API's SQLite store, emptied before and after each test that uses it."""
    store = client.app.state.store
    store.clear_feedback()
    store.clear_usage()
    yield store
    store.clear_feedback()
    store.clear_usage()
