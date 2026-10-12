"""API tests against the real catalogue in data/movies.csv."""

import pytest

from app.config import DATA_PATH
from app.data_loader import load_movies

INCEPTION, SE7EN, TOY_STORY = 6, 15, 30


def test_dataset_file_is_clean():
    df = load_movies(DATA_PATH)
    assert len(df) >= 100
    assert df["movie_id"].is_unique
    assert not df[["title", "year"]].duplicated().any()


def test_health(client):
    body = client.get("/api/health").json()
    assert body == {"status": "ok", "movies_loaded": body["movies_loaded"], "version": body["version"]}
    assert body["movies_loaded"] >= 100


def test_dataset_info_discloses_provenance(client):
    body = client.get("/api/dataset").json()
    assert body["verified"] is False
    assert "not been verified" in body["provenance"]


def test_preference_options(client):
    body = client.get("/api/preferences/options").json()
    assert "Science Fiction" in body["genres"]
    assert "Mind-Bending" in body["moods"]
    assert "Hindi" in body["languages"]
    assert sum(body["default_weights"].values()) == pytest.approx(1.0)


def test_list_movies_search_and_pagination(client):
    body = client.get("/api/movies", params={"search": "harry"}).json()
    assert body["total"] == 2 and all("harry" in m["title"].lower() for m in body["items"])
    page = client.get("/api/movies", params={"limit": 5, "offset": 5}).json()
    assert len(page["items"]) == 5 and page["total"] >= 100
    hindi = client.get("/api/movies", params={"language": "hindi", "limit": 200}).json()
    assert hindi["items"] and all(m["language"] == "Hindi" for m in hindi["items"])


def test_movie_details(client):
    assert client.get(f"/api/movies/{INCEPTION}").json()["title"] == "Inception"
    assert client.get("/api/movies/99999").status_code == 404


def test_similar_movies(client):
    body = client.get(f"/api/movies/{SE7EN}/similar", params={"top_n": 5}).json()
    titles = [s["movie"]["title"] for s in body["similar"]]
    assert "Se7en" not in titles
    assert {"Zodiac", "Prisoners", "The Silence of the Lambs"} & set(titles)


def test_recommendations_endpoint(client):
    response = client.post(
        "/api/recommendations",
        json={"genres": ["Animation"], "moods": ["Heartwarming"], "liked_movie_ids": [TOY_STORY]},
    )
    assert response.status_code == 200
    body = response.json()
    recs = body["recommendations"]
    assert len(recs) == 10  # default top_n
    assert all("Animation" in r["movie"]["genres"] for r in recs[:5])
    assert TOY_STORY not in [r["movie_id"] for r in recs]
    assert recs[0]["reasons"] and recs[0]["components"]["genre"]["active"]


def test_recommendations_no_match_is_200_with_message(client):
    response = client.post(
        "/api/recommendations",
        json={"genres": ["Horror"], "languages": ["Telugu"], "strict_languages": True},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["recommendations"] == [] and body["message"]


@pytest.mark.parametrize(
    "payload",
    [
        {},                                                     # empty preferences
        {"min_rating": 8},                                      # filter only, no preference
        {"genres": ["Drama"], "min_rating": 11},                # out of range
        {"genres": ["Drama"], "top_n": 0},
        {"genres": ["Drama"], "top_n": 51},
        {"genres": ["Drama"], "year_min": 2020, "year_max": 2000},
        {"genres": ["Not A Genre"]},                            # unknown label
        {"languages": ["Klingon"]},
        {"genres": "Drama"},                                    # wrong type
        {"genres": [""]},                                       # blank label
        {"genres": ["Drama"], "unexpected": True},              # unknown field
        {"genres": ["Drama"], "weights": {"genre": -1}},        # negative weight
        {"genres": ["Drama"], "weights": {"genre": 0, "keyword": 0, "mood": 0, "language": 0, "year": 0}},
        {"liked_movie_ids": [0]},
        {"liked_movie_ids": [99999]},
    ],
)
def test_invalid_requests_return_422(client, payload):
    assert client.post("/api/recommendations", json=payload).status_code == 422
