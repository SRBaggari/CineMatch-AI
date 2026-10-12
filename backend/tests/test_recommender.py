import pytest
from fastapi.testclient import TestClient

from app.config import DATA_PATH
from app.data_loader import load_movies, normalize_token
from app.main import app
from app.recommender import EmptyPreferencesError, RecommendationEngine, UserPreferences, jaccard

INCEPTION, INTERSTELLAR, TOY_STORY = 6, 9, 30


@pytest.fixture(scope="module")
def engine():
    return RecommendationEngine(load_movies(DATA_PATH))


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


# ---------------------------------------------------------------- unit tests
def test_dataset_loads_with_list_columns():
    df = load_movies(DATA_PATH)
    assert len(df) >= 100
    assert df["movie_id"].is_unique
    assert isinstance(df.iloc[0]["genres"], list)


def test_normalize_token():
    assert normalize_token("Science Fiction") == "sciencefiction"
    assert normalize_token("Mind-Bending") == "mindbending"


def test_jaccard():
    assert jaccard({"a", "b"}, {"a", "b"}) == 1.0
    assert jaccard({"a"}, {"b"}) == 0.0
    assert jaccard({"a", "b"}, {"b", "c"}) == pytest.approx(1 / 3)
    assert jaccard(set(), {"a"}) == 0.0


def test_item_similarity_is_symmetric_with_unit_diagonal(engine):
    sim = engine.item_similarity
    assert sim.shape == (len(engine.movies), len(engine.movies))
    assert sim[0, 1] == pytest.approx(sim[1, 0])
    assert sim[0, 0] == pytest.approx(1.0)


def test_similar_movies_ranks_related_titles(engine):
    titles = [r["movie"]["title"] for r in engine.similar_movies(INCEPTION, 5)]
    assert "Inception" not in titles
    # A Nolan mind-bender should sit close to other Nolan / mind-bending sci-fi.
    assert {"Interstellar", "The Prestige", "Memento", "The Matrix"} & set(titles)


def test_recommendations_are_deterministic_and_sorted(engine):
    prefs = UserPreferences(genres=["Science Fiction"], moods=["Mind-Bending"], top_n=10)
    first, second = engine.recommend(prefs), engine.recommend(prefs)
    assert [r["movie"]["movie_id"] for r in first["recommendations"]] == [
        r["movie"]["movie_id"] for r in second["recommendations"]
    ]
    scores = [r["score"] for r in first["recommendations"]]
    assert scores == sorted(scores, reverse=True)


def test_genre_preference_is_respected(engine):
    result = engine.recommend(UserPreferences(genres=["Horror"], moods=["Scary"], top_n=5))
    for rec in result["recommendations"]:
        assert "Horror" in rec["movie"]["genres"]


def test_liked_movies_are_excluded_and_explained(engine):
    result = engine.recommend(UserPreferences(liked_movie_ids=[INCEPTION, INTERSTELLAR], top_n=8))
    ids = {r["movie"]["movie_id"] for r in result["recommendations"]}
    assert INCEPTION not in ids and INTERSTELLAR not in ids
    assert result["profile"]["genres_inferred"] is True
    assert any(r["explanation"]["similar_to"] for r in result["recommendations"])


def test_score_breakdown_sums_to_final_score(engine):
    result = engine.recommend(UserPreferences(genres=["Comedy"], keywords=["friendship"], top_n=5))
    for rec in result["recommendations"]:
        total = sum(c["contribution"] for c in rec["score_breakdown"].values())
        assert total == pytest.approx(rec["score"], abs=1e-3)
    weights = result["profile"]["weights"]
    assert sum(weights.values()) == pytest.approx(1.0, abs=1e-3)
    assert weights["mood"] == 0  # no moods given -> component disabled


def test_filters_are_applied(engine):
    prefs = UserPreferences(genres=["Drama"], year_min=2010, year_max=2020, min_rating=8.0,
                            languages=["Hindi"], top_n=20)
    for rec in engine.recommend(prefs)["recommendations"]:
        movie = rec["movie"]
        assert 2010 <= movie["year"] <= 2020
        assert movie["rating"] >= 8.0
        assert movie["language"] == "Hindi"


def test_empty_preferences_raise(engine):
    with pytest.raises(EmptyPreferencesError):
        engine.recommend(UserPreferences())


# ---------------------------------------------------------------- API tests
def test_health(client):
    body = client.get("/api/health").json()
    assert body["status"] == "ok"
    assert body["movies_loaded"] >= 100


def test_meta(client):
    body = client.get("/api/meta").json()
    assert "Science Fiction" in body["genres"]
    assert "Mind-Bending" in body["moods"]


def test_search_movies(client):
    body = client.get("/api/movies", params={"search": "harry"}).json()
    assert body and all("harry" in m["title"].lower() for m in body)


def test_movie_not_found(client):
    assert client.get("/api/movies/99999").status_code == 404


def test_recommend_endpoint(client):
    response = client.post("/api/recommend", json={"genres": ["Animation"], "liked_movie_ids": [TOY_STORY]})
    assert response.status_code == 200
    body = response.json()
    assert body["recommendations"]
    assert body["recommendations"][0]["explanation"]["reasons"]


def test_recommend_endpoint_validation(client):
    assert client.post("/api/recommend", json={}).status_code == 422
    assert client.post("/api/recommend", json={"genres": ["Drama"], "year_min": 2020, "year_max": 2000}).status_code == 422
