"""SQLite store unit tests and API tests for feedback, search and analytics (real dataset)."""

import pytest

from app.analytics import score_histogram
from app.store import UNSET, Store

INCEPTION, SE7EN, ZODIAC, TOY_STORY = 6, 15, 81, 30
CRIME = {"genres": ["Crime", "Thriller"], "moods": ["Dark"]}


# ------------------------------------------------------------- store (unit)
@pytest.fixture
def db(tmp_path):
    return Store(tmp_path / "unit.db")


def test_store_feedback_lifecycle(db):
    assert db.get_feedback() == {}
    assert db.set_feedback(1, reaction="like")["reaction"] == "like"
    state = db.set_feedback(1, favorite=True)
    assert state["reaction"] == "like" and state["favorite"] is True       # reaction kept
    assert db.set_feedback(1, reaction="dislike")["favorite"] is True      # favourite kept
    assert db.set_feedback(1, reaction=None)["favorite"] is True
    assert db.set_feedback(1, favorite=False) is None                      # empty row deleted
    assert db.get_feedback() == {}


def test_store_feedback_sets_and_clear(db):
    db.set_feedback(1, reaction="like")
    db.set_feedback(2, reaction="dislike")
    db.set_feedback(3, favorite=True)
    db.set_feedback(4, reaction="like", favorite=True)
    assert db.feedback_sets() == {"liked": [1, 4], "disliked": [2], "favorites": [3, 4]}
    assert db.clear_feedback(2) == 1
    assert db.clear_feedback() == 3 and db.get_feedback() == {}


def test_store_persists_across_instances(tmp_path):
    Store(tmp_path / "p.db").set_feedback(9, reaction="like")
    assert Store(tmp_path / "p.db").get_feedback()[9]["reaction"] == "like"


def test_store_usage_log_counts_explicit_selections_only(db):
    rec = [{"rank": 1, "movie_id": 5, "base_score": 0.5, "score": 0.6}]
    db.log_recommendation({"genres": ["Drama"], "moods": ["Dark"], "languages": ["English"], "keywords": ["heist"]}, rec, True)
    db.log_recommendation({"genres": ["Drama", "Crime"], "genres_inferred": True, "moods": [], "languages": [], "keywords": []}, rec, False)
    stats = db.usage_stats()
    assert stats["total_requests"] == 2
    assert stats["selections"]["genres"] == {"Drama": 1}                     # inferred genres not counted
    assert stats["scores"] == [0.6, 0.6] and stats["most_recommended"] == [(5, 2)]
    db.clear_usage()
    assert db.usage_stats()["total_requests"] == 0


def test_store_unset_sentinel_leaves_fields(db):
    db.set_feedback(1, reaction="like", favorite=True)
    assert db.set_feedback(1, reaction=UNSET, favorite=UNSET)["favorite"] is True


def test_score_histogram():
    bins = score_histogram([0.0, 0.05, 0.15, 0.99, 1.0])
    assert len(bins) == 10 and sum(b["count"] for b in bins) == 5
    assert bins[0]["count"] == 2 and bins[1]["count"] == 1 and bins[-1]["count"] == 2   # 1.0 in last bin
    assert all(b["count"] == 0 for b in score_histogram([]))


# ------------------------------------------------------------- feedback API
def test_feedback_endpoints(client, store):
    assert client.put(f"/api/feedback/{INCEPTION}", json={"reaction": "like"}).json() == {
        "movie_id": INCEPTION, "reaction": "like", "favorite": False}
    assert client.put(f"/api/feedback/{INCEPTION}", json={"favorite": True}).json()["reaction"] == "like"
    client.put(f"/api/feedback/{SE7EN}", json={"reaction": "dislike"})
    body = client.get("/api/feedback").json()
    assert body["counts"] == {"likes": 1, "dislikes": 1, "favorites": 1}
    assert {i["movie"]["title"] for i in body["items"]} == {"Inception", "Se7en"}
    assert client.put(f"/api/feedback/{INCEPTION}", json={"reaction": None, "favorite": False}).json()["reaction"] is None
    assert client.delete(f"/api/feedback/{SE7EN}").status_code == 204
    assert client.get("/api/feedback").json()["items"] == []
    client.put(f"/api/feedback/{SE7EN}", json={"reaction": "like"})
    assert client.delete("/api/feedback").status_code == 204 and store.get_feedback() == {}


@pytest.mark.parametrize("payload", [{}, {"reaction": "love"}, {"favorite": None}, {"favorite": True, "x": 1}])
def test_feedback_validation(client, store, payload):
    assert client.put(f"/api/feedback/{INCEPTION}", json=payload).status_code == 422


def test_feedback_unknown_movie(client, store):
    assert client.put("/api/feedback/99999", json={"reaction": "like"}).status_code == 404


def test_recommendations_use_saved_feedback(client, store):
    plain = client.post("/api/recommendations", json=CRIME).json()["recommendations"]
    top_id = plain[0]["movie_id"]
    client.put(f"/api/feedback/{top_id}", json={"reaction": "dislike"})
    after = client.post("/api/recommendations", json=CRIME).json()
    assert top_id not in [r["movie_id"] for r in after["recommendations"]]
    assert after["profile"]["feedback_applied"] is True
    assert "after_dislikes" in after["filter_report"]
    # Turning feedback off restores the original preference-only ranking.
    off = client.post("/api/recommendations", json={**CRIME, "use_feedback": False}).json()
    assert [r["movie_id"] for r in off["recommendations"]] == [r["movie_id"] for r in plain]
    assert all(r["feedback_adjustment"] == 0 for r in off["recommendations"])


def test_like_boosts_neighbours_without_touching_base_scores(client, store):
    before = {r["movie_id"]: r for r in client.post("/api/recommendations", json={**CRIME, "top_n": 50}).json()["recommendations"]}
    client.put(f"/api/feedback/{SE7EN}", json={"reaction": "like"})
    after = {r["movie_id"]: r for r in client.post("/api/recommendations", json={**CRIME, "top_n": 50}).json()["recommendations"]}
    zodiac = after[ZODIAC]
    assert zodiac["base_score"] == before[ZODIAC]["base_score"]
    assert zodiac["feedback_adjustment"] > 0 and zodiac["score"] > before[ZODIAC]["score"]
    assert zodiac["feedback"]["closest_liked"]["title"] == "Se7en"
    assert all(r["score"] == pytest.approx(min(1, max(0, r["base_score"] + r["feedback_adjustment"])), abs=1e-3)
               for r in after.values())


def test_recommendation_summary_is_built_from_matches(client, store):
    payload = {"genres": ["Action", "Adventure"], "languages": ["English"], "keywords": ["superhero"]}
    for rec in client.post("/api/recommendations", json=payload).json()["recommendations"]:
        assert rec["summary"].startswith("Recommended because you") or rec["summary"].startswith("Recommended as")
        for genre in ("Action", "Adventure"):
            assert (genre in rec["summary"]) == (genre in rec["matched"]["genres"])
        assert ("English-language" in rec["summary"]) == (rec["matched"]["language"] == "English")


# ------------------------------------------------------------- search API
def test_search_endpoint(client, store):
    body = client.post("/api/movies/search", json={"query": "lord of the rings"}).json()
    assert body["total"] == 2 and all("Lord of the Rings" in i["movie"]["title"] for i in body["items"])
    hindi = client.post("/api/movies/search", json={"languages": ["Hindi"], "sort": "rating", "limit": 200}).json()
    ratings = [i["movie"]["rating"] for i in hindi["items"]]
    assert hindi["total"] == 10 and ratings == sorted(ratings, reverse=True)
    nineties = client.post("/api/movies/search", json={"genres": ["Animation"], "year_min": 1990, "year_max": 1999}).json()
    assert nineties["items"] and all(1990 <= i["movie"]["year"] <= 1999 and "Animation" in i["movie"]["genres"]
                                     for i in nineties["items"])
    personal = client.post("/api/movies/search", json={"genres": ["Crime"], "preferences": CRIME}).json()
    scores = [i["match_score"] for i in personal["items"]]
    assert personal["personalized"] and scores == sorted(scores, reverse=True)


@pytest.mark.parametrize("payload", [
    {"sort": "popularity"}, {"year_min": 2010, "year_max": 2000}, {"genres": ["Nope"]},
    {"preferences": {}}, {"limit": 0}, {"unexpected": 1},
])
def test_search_validation(client, store, payload):
    assert client.post("/api/movies/search", json=payload).status_code == 422


# ------------------------------------------------------------- analytics API
def test_analytics_reports_dataset_and_empty_usage(client, store):
    body = client.get("/api/analytics").json()
    assert body["dataset"]["total_movies"] == 130
    assert sum(b["count"] for b in body["dataset"]["rating_distribution"]) == 130
    assert body["dataset"]["genre_distribution"]["Drama"] == max(body["dataset"]["genre_distribution"].values())
    assert body["usage"]["total_requests"] == 0 and body["usage"]["genre_selections"] == {}
    assert body["usage"]["average_score"] is None
    assert any("No recommendations" in n for n in body["notes"])


def test_analytics_reflects_logged_usage_and_feedback(client, store):
    client.post("/api/recommendations", json={"genres": ["Comedy", "Drama"], "top_n": 5})
    client.post("/api/recommendations", json={"genres": ["Comedy"], "moods": ["Funny"], "top_n": 3})
    client.post("/api/movies/search", json={"query": "toy"})                     # searches are not logged
    client.put(f"/api/feedback/{TOY_STORY}", json={"reaction": "like", "favorite": True})
    body = client.get("/api/analytics").json()
    usage = body["usage"]
    assert usage["total_requests"] == 2 and usage["recommendations_served"] == 8
    assert usage["genre_selections"] == {"Comedy": 2, "Drama": 1}
    assert usage["mood_selections"] == {"Funny": 1}
    assert sum(b["count"] for b in usage["score_distribution"]) == 8
    assert 0 < usage["average_score"] <= 1
    assert body["feedback"] == {"likes": 1, "dislikes": 0, "favorites": 1}
