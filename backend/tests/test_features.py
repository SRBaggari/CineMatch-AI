"""Tests for explanations, feedback personalisation, search and caching (synthetic fixture)."""

import numpy as np
import pytest
from sklearn.feature_extraction.text import TfidfVectorizer

from app.config import FEEDBACK_WEIGHT
from app.data_loader import clean_movies
from app.recommender import (
    FeedbackProfile,
    InvalidPreferenceError,
    RecommendationEngine,
    UserPreferences,
    join_phrases,
    title_relevance,
    year_score,
    year_scores,
)
from tests.conftest import FIXTURE_ROWS, fixture_frame
from tests.test_engine import SCI_FI_PREFS, by_id, ids


# ------------------------------------------------------------- explanation summaries
def test_join_phrases():
    assert join_phrases([]) == ""
    assert join_phrases(["a"]) == "a"
    assert join_phrases(["a", "b"]) == "a and b"
    assert join_phrases(["a", "b", "c"]) == "a, b, and c"


def test_summary_for_full_match_lists_every_matched_attribute_by_contribution(engine):
    top = engine.recommend(UserPreferences(**SCI_FI_PREFS))["recommendations"][0]
    assert top["summary"] == (
        "Recommended because you enjoy Science Fiction and Thriller movies, "
        "selected time travel and dreams as favourite themes, "
        "are in the mood for something Mind-Bending, prefer English-language content, "
        "and like movies released between 2005 and 2015."
    )


def test_summary_mentions_only_attributes_that_matched(engine):
    genre_only = by_id(engine.recommend(UserPreferences(**SCI_FI_PREFS, top_n=50)), 2)
    # Movie 2 is Science Fiction (not Thriller), French, Funny, from 1980: only the genre matches.
    assert genre_only["summary"] == "Recommended because you enjoy Science Fiction movies."


def test_summary_uses_inferred_patterns_and_liked_movies(engine):
    rec = engine.recommend(UserPreferences(liked_movie_ids=[1]))["recommendations"][0]
    assert rec["summary"].startswith("Recommended because you loved movies in the ")


def test_summary_falls_back_when_nothing_matched(engine):
    explained = engine.explain(UserPreferences(genres=["Comedy"]), 4)  # the Western
    assert explained["summary"] == "Recommended as the closest available match to your preferences."


# ------------------------------------------------------------- feedback personalisation
COMEDY_DRAMA = dict(genres=["Comedy", "Romance"])  # twins score 1/sqrt(2), leaving room for a boost


def twins(result):
    """Relative order of the three identical-content twins (5, 6, 7)."""
    return [i for i in ids(result) if i in (5, 6, 7)]


def test_no_feedback_means_no_adjustment(engine):
    for rec in engine.recommend(UserPreferences(**SCI_FI_PREFS, top_n=50))["recommendations"]:
        assert rec["feedback_adjustment"] == 0
        assert rec["score"] == rec["base_score"]
        assert rec["feedback"]["applied"] is False


def test_like_boosts_similar_movies_and_keeps_base_score_separate(engine):
    prefs = UserPreferences(**COMEDY_DRAMA)
    plain = engine.recommend(prefs)
    liked = engine.recommend(prefs, FeedbackProfile(liked=[7]))
    assert twins(plain) == [6, 7, 5]           # equal base scores -> rating, then id
    assert twins(liked) == [6, 5, 7]           # 5 and 6 resemble the liked twin; 7 cannot vouch for itself
    for movie_id in (5, 6):
        rec = by_id(liked, movie_id)
        assert rec["base_score"] == by_id(plain, movie_id)["base_score"]   # preference score untouched
        assert rec["components"] == by_id(plain, movie_id)["components"]
        assert rec["feedback_adjustment"] == pytest.approx(FEEDBACK_WEIGHT * 1.0, abs=1e-4)
        assert rec["score"] == pytest.approx(rec["base_score"] + rec["feedback_adjustment"], abs=1e-4)
        assert rec["feedback"]["closest_liked"] == {"movie_id": 7, "title": "Twin C"}
    assert by_id(liked, 7)["feedback_adjustment"] == 0
    assert "liked Twin C" in by_id(liked, 6)["summary"]


def test_favorites_count_as_positive_feedback(engine):
    prefs = UserPreferences(**COMEDY_DRAMA)
    assert ids(engine.recommend(prefs, FeedbackProfile(favorites=[7]))) == ids(
        engine.recommend(prefs, FeedbackProfile(liked=[7]))
    )


def test_dislike_hides_movie_and_penalises_similar_ones(engine):
    prefs = UserPreferences(**COMEDY_DRAMA)
    result = engine.recommend(prefs, FeedbackProfile(disliked=[7]))
    assert 7 not in ids(result)
    assert result["filter_report"]["after_dislikes"] == len(FIXTURE_ROWS) - 1
    for movie_id in (5, 6):
        rec = by_id(result, movie_id)
        assert rec["feedback_adjustment"] == pytest.approx(-FEEDBACK_WEIGHT, abs=1e-4)
        assert rec["feedback"]["closest_disliked"]["movie_id"] == 7


def test_feedback_cannot_add_movies_that_match_no_preference(engine):
    result = engine.recommend(UserPreferences(genres=["Comedy"]), FeedbackProfile(liked=[4]))
    assert 4 not in ids(result) and all(r["base_score"] > 0 for r in result["recommendations"])


def test_final_scores_are_clipped_to_unit_interval(engine):
    boosted = engine.recommend(UserPreferences(genres=["Comedy"]), FeedbackProfile(liked=[7]))
    assert all(0 <= r["score"] <= 1 for r in boosted["recommendations"])
    assert by_id(boosted, 6)["base_score"] == 1.0 and by_id(boosted, 6)["score"] == 1.0


def test_explain_applies_feedback_like_recommend(engine):
    prefs, feedback = UserPreferences(**COMEDY_DRAMA), FeedbackProfile(liked=[7], disliked=[3])
    for rec in engine.recommend(prefs, feedback)["recommendations"]:
        explained = engine.explain(prefs, rec["movie_id"], feedback)
        assert (explained["rank"], explained["score"], explained["base_score"]) == (rec["rank"], rec["score"], rec["base_score"])
    hidden = engine.explain(prefs, 3, feedback)
    assert hidden["rank"] is None and "You disliked this movie" in hidden["filtered_by"]


def test_unknown_feedback_ids_are_ignored(engine):
    result = engine.recommend(UserPreferences(**COMEDY_DRAMA), FeedbackProfile(liked=[999], disliked=[998]))
    assert result["recommendations"]


# ------------------------------------------------------------- search & filtering
def test_title_relevance_ordering():
    assert title_relevance("inception", "Inception") == 1.0
    assert title_relevance("the dark", "The Dark Knight") == 0.9
    assert title_relevance("knight", "The Dark Knight") == 0.75
    assert title_relevance("ark kn", "The Dark Knight") == 0.6
    assert title_relevance("dark the", "The Dark Knight") == 0.5
    assert title_relevance("zebra", "The Dark Knight") == 0.0
    assert title_relevance("", "Anything") == 0.0


def test_search_by_title_ranks_by_title_relevance_then_rating(engine):
    result = engine.search(query="twin")
    assert [i["movie"]["movie_id"] for i in result["items"]] == [6, 7, 5]
    assert engine.search(query="exact match")["items"][0]["title_relevance"] == 1.0
    assert engine.search(query="nothing like this")["total"] == 0


def test_search_filters(engine):
    by_genre = engine.search(genres=["Romance", "Western"])
    assert {i["movie"]["movie_id"] for i in by_genre["items"]} == {3, 4}            # OR across genres
    by_language = engine.search(languages=["french"])
    assert {i["movie"]["movie_id"] for i in by_language["items"]} == {2, 3}
    by_year = engine.search(year_min=2000, year_max=2010)
    assert all(2000 <= i["movie"]["year"] <= 2010 for i in by_year["items"]) and by_year["total"] == 4
    combined = engine.search(query="twin", languages=["Spanish"], year_min=2001)
    assert combined["total"] == 0


def test_search_sorting(engine):
    by_rating = [i["movie"]["rating"] for i in engine.search(sort="rating")["items"]]
    assert by_rating == sorted(by_rating, reverse=True)
    by_title = [i["movie"]["title"] for i in engine.search(sort="title")["items"]]
    assert by_title == sorted(by_title, key=str.lower)
    by_year = [i["movie"]["year"] for i in engine.search(sort="year")["items"]]
    assert by_year == sorted(by_year, reverse=True)


def test_personalised_relevance_matches_recommendation_scores(engine):
    prefs = UserPreferences(**SCI_FI_PREFS)
    result = engine.search(prefs=prefs)
    assert result["personalized"] and result["items"][0]["movie"]["movie_id"] == 1
    recs = {r["movie_id"]: r["score"] for r in engine.recommend(UserPreferences(**SCI_FI_PREFS, top_n=50))["recommendations"]}
    for item in result["items"]:
        if item["movie"]["movie_id"] in recs:
            assert item["match_score"] == recs[item["movie"]["movie_id"]]
    scores = [i["match_score"] for i in result["items"]]
    assert scores == sorted(scores, reverse=True)


def test_search_pagination_and_validation(engine):
    first, second = engine.search(sort="rating", limit=3), engine.search(sort="rating", limit=3, offset=3)
    assert first["total"] == second["total"] == len(FIXTURE_ROWS)
    assert not {i["movie"]["movie_id"] for i in first["items"]} & {i["movie"]["movie_id"] for i in second["items"]}
    with pytest.raises(InvalidPreferenceError):
        engine.search(sort="popularity")
    with pytest.raises(InvalidPreferenceError):
        engine.search(genres=["Horror"])


# ------------------------------------------------------------- similar movies
def test_similar_movies_use_cached_item_vectors(engine):
    similar = engine.similar_movies(1, top_n=6)
    sims = [s["similarity"] for s in similar]
    assert 1 not in [s["movie"]["movie_id"] for s in similar]
    assert sims == sorted(sims, reverse=True)
    assert sims[0] == pytest.approx(engine.item_similarity[0, engine.id_to_index[similar[0]["movie"]["movie_id"]]], abs=1e-4)


# ------------------------------------------------------------- performance & caching
def test_year_scores_vectorised_matches_scalar():
    years = np.array([1950, 2000, 2005, 2010, 2015, 2025, 2040])
    assert list(year_scores(years, 2005, 2015)) == [year_score(int(y), 2005, 2015) for y in years]


def test_score_cache_reuses_component_scores_and_respects_filters():
    engine = RecommendationEngine(clean_movies(fixture_frame()))
    first = engine.recommend(UserPreferences(genres=["Science Fiction"]))
    assert engine.cache_stats == {"hits": 0, "misses": 1}
    # Same preference set, different min_rating: cache hit, but the new filter still applies.
    filtered = engine.recommend(UserPreferences(genres=["Science Fiction"], min_rating=7.5))
    assert engine.cache_stats == {"hits": 1, "misses": 1}
    assert ids(first) == [2, 1] and ids(filtered) == [1]  # movie 2 (pure sci-fi) is rated 7.0
    assert filtered["profile"]["min_rating"] == 7.5 and first["profile"]["min_rating"] == 0
    assert engine.recommend(UserPreferences(genres=["Science Fiction"])) == first


def test_keyword_vectors_are_cached(monkeypatch):
    engine = RecommendationEngine(clean_movies(fixture_frame()))
    calls = []
    original = engine.vectorizer.transform
    monkeypatch.setattr(engine.vectorizer, "transform", lambda docs: calls.append(docs) or original(docs))
    engine.recommend(UserPreferences(keywords=["party"]))
    engine.recommend(UserPreferences(keywords=["party"], genres=["Comedy"]))  # new prefs, same keywords
    assert len(calls) == 1


def test_feature_cache_is_written_reused_and_invalidated(tmp_path, monkeypatch):
    movies = clean_movies(fixture_frame())
    built = RecommendationEngine(movies, cache_dir=tmp_path)
    assert built.feature_source == "computed"
    assert len(list(tmp_path.glob("features-*.pkl"))) == 1

    # A second engine on the same data must not fit TF-IDF again.
    def no_refit(*args, **kwargs):
        raise AssertionError("TF-IDF was re-fitted despite a valid cache")

    monkeypatch.setattr(TfidfVectorizer, "fit_transform", no_refit)
    cached = RecommendationEngine(movies, cache_dir=tmp_path)
    assert cached.feature_source == "disk-cache"
    prefs = UserPreferences(**SCI_FI_PREFS, top_n=50)
    assert cached.recommend(prefs) == built.recommend(prefs)
    monkeypatch.undo()

    # Changing the data changes the fingerprint: features are rebuilt and the stale file removed.
    rows = [list(r) for r in FIXTURE_ROWS]
    rows[0][6] = "A completely different description about pirates."
    changed = RecommendationEngine(clean_movies(fixture_frame([tuple(r) for r in rows])), cache_dir=tmp_path)
    assert changed.feature_source == "computed"
    assert len(list(tmp_path.glob("features-*.pkl"))) == 1
    assert changed.fingerprint != built.fingerprint


def test_corrupt_feature_cache_is_rebuilt(tmp_path):
    movies = clean_movies(fixture_frame())
    path = RecommendationEngine(movies, cache_dir=tmp_path)._cache_file(tmp_path)
    path.write_bytes(b"not a pickle")
    engine = RecommendationEngine(movies, cache_dir=tmp_path)
    assert engine.feature_source == "computed" and engine.recommend(UserPreferences(genres=["Comedy"]))["recommendations"]
