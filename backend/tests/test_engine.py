"""Behavioural tests of the engine on the synthetic fixture catalogue (see conftest.py)."""

import math

import pytest

from app.data_loader import clean_movies
from app.recommender import (
    EmptyPreferencesError,
    InvalidPreferenceError,
    RecommendationEngine,
    UserPreferences,
)
from tests.conftest import FIXTURE_ROWS, fixture_frame

SCI_FI_PREFS = dict(
    genres=["Science Fiction", "Thriller"],
    moods=["Mind-Bending"],
    keywords=["time travel", "dreams"],
    languages=["English"],
    year_min=2005,
    year_max=2015,
)


def ids(result):
    return [r["movie_id"] for r in result["recommendations"]]


def by_id(result, movie_id):
    return next(r for r in result["recommendations"] if r["movie_id"] == movie_id)


# ------------------------------------------------------------- exact match
def test_exact_preference_match_scores_one_and_ranks_first(engine):
    result = engine.recommend(UserPreferences(**SCI_FI_PREFS))
    top = result["recommendations"][0]
    assert top["movie_id"] == 1
    assert top["score"] == pytest.approx(1.0)
    for name, component in top["components"].items():
        assert component["active"], name
        assert component["value"] == pytest.approx(1.0), name
    assert top["matched"] == {
        "genres": ["Science Fiction", "Thriller"],
        "moods": ["Mind-Bending"],
        "language": "English",
        "keywords": ["time travel", "dreams"],
        "year_in_range": True,
    }


# ------------------------------------------------------------- partial match
def test_partial_matches_score_between_zero_and_one(engine):
    result = engine.recommend(UserPreferences(**SCI_FI_PREFS))
    genre_only, mood_only = by_id(result, 2), by_id(result, 3)

    # Genre-only movie: cosine({SciFi, Thriller}, {SciFi}) = 1/sqrt(2).
    assert genre_only["components"]["genre"]["value"] == pytest.approx(1 / math.sqrt(2), abs=1e-4)
    assert genre_only["components"]["mood"]["value"] == 0
    assert genre_only["components"]["language"]["value"] == 0
    assert 0 < genre_only["score"] < 1
    assert genre_only["matched"]["genres"] == ["Science Fiction"]

    assert mood_only["components"]["mood"]["value"] == pytest.approx(1.0)
    assert mood_only["components"]["genre"]["value"] == 0
    assert 0 < mood_only["score"] < 1

    assert ids(result).index(1) < ids(result).index(2)
    assert ids(result).index(1) < ids(result).index(3)


def test_reasons_are_ordered_by_contribution(engine):
    result = engine.recommend(UserPreferences(**SCI_FI_PREFS))
    top = result["recommendations"][0]
    # Genre has the largest weight (0.30) and a full match, so it is the leading reason.
    assert top["reasons"][0] == "Genre match (2/2 of your genres): Science Fiction, Thriller"
    contributions = [top["components"][c]["contribution"] for c in ("genre", "keyword", "mood", "language", "year")]
    assert contributions == sorted(contributions, reverse=True)


# ------------------------------------------------------------- no match
def test_hard_filter_removing_everything_returns_explained_empty_result(engine):
    result = engine.recommend(UserPreferences(genres=["Comedy"], min_rating=9.5))
    assert result["recommendations"] == []
    assert result["filter_report"]["after_min_rating"] == 0
    assert "minimum rating" in result["message"]


def test_preferences_matching_nothing_return_empty_result(engine):
    # The only Western is excluded, so no remaining movie shares any preference.
    result = engine.recommend(UserPreferences(genres=["Western"], exclude_movie_ids=[4]))
    assert result["recommendations"] == []
    assert result["filter_report"]["with_positive_score"] == 0
    assert "No movies match" in result["message"]


def test_keywords_outside_vocabulary_return_empty_result_with_warning(engine):
    result = engine.recommend(UserPreferences(keywords=["zzqqxx"]))
    assert result["recommendations"] == []
    assert result["message"]
    assert any("vocabulary" in w for w in result["warnings"])


def test_strict_language_filter(engine):
    result = engine.recommend(UserPreferences(genres=["Science Fiction"], languages=["French"], strict_languages=True))
    assert ids(result) and all(r["movie"]["language"] == "French" for r in result["recommendations"])
    assert result["filter_report"]["after_languages"] == 2


def test_soft_language_preference_keeps_other_languages(engine):
    result = engine.recommend(UserPreferences(genres=["Science Fiction"], languages=["French"]))
    assert 1 in ids(result)  # English movie still recommended, just without the language points
    assert by_id(result, 1)["components"]["language"]["value"] == 0


def test_strict_year_filter_and_soft_year_decay(engine):
    strict = engine.recommend(UserPreferences(genres=["Science Fiction"], year_min=2005, year_max=2015, strict_years=True))
    # Movie 3 (2012) passes the filter but shares no genre: the year is not scored
    # once it is a hard filter, so movie 3 has score 0 and is dropped.
    assert ids(strict) == [1]
    assert strict["profile"]["weights"]["year"] == 0
    only_years = engine.recommend(UserPreferences(year_min=2005, year_max=2015, strict_years=True))
    assert ids(only_years) == [1, 3]  # sole preference: equal scores, ordered by rating
    soft = engine.recommend(UserPreferences(genres=["Science Fiction"], year_min=2005, year_max=2015))
    # Movie 2 (1980) is 25 years before the range -> year score 0, but still ranked on genre.
    assert by_id(soft, 2)["components"]["year"]["value"] == 0
    assert by_id(soft, 1)["components"]["year"]["value"] == 1


# ------------------------------------------------------------- empty / invalid
def test_empty_preferences_raise(engine):
    with pytest.raises(EmptyPreferencesError):
        engine.recommend(UserPreferences())
    with pytest.raises(EmptyPreferencesError):
        engine.recommend(UserPreferences(min_rating=7))  # a filter alone is not a preference


@pytest.mark.parametrize(
    "prefs",
    [
        UserPreferences(genres=["Horror"]),
        UserPreferences(moods=["Sleepy"]),
        UserPreferences(languages=["Klingon"]),
        UserPreferences(liked_movie_ids=[999]),
        UserPreferences(genres=["Comedy"], weights={"genre": 0, "keyword": 1}),
    ],
)
def test_invalid_preferences_raise(engine, prefs):
    with pytest.raises(InvalidPreferenceError):
        engine.recommend(prefs)


# ------------------------------------------------------------- duplicates
def test_loader_drops_duplicate_ids_and_titles():
    rows = FIXTURE_ROWS + [
        (1, "Exact Match Copy", 2011, "Drama", "Funny", "x", "dup id", 5.0, "English"),
        (99, "exact match", 2010, "Drama", "Funny", "y", "dup title+year", 5.0, "English"),
    ]
    df = clean_movies(fixture_frame(rows))
    assert len(df) == len(FIXTURE_ROWS)
    assert df["movie_id"].is_unique


def test_duplicate_request_values_do_not_change_results(engine):
    once = engine.recommend(UserPreferences(genres=["Comedy"], keywords=["party"]))
    repeated = engine.recommend(UserPreferences(genres=["Comedy", "comedy", " Comedy "], keywords=["party", "Party"]))
    assert once["recommendations"] == repeated["recommendations"]


def test_results_have_no_duplicates_and_exclude_liked(engine):
    result = engine.recommend(UserPreferences(liked_movie_ids=[5], top_n=50))
    result_ids = ids(result)
    assert len(result_ids) == len(set(result_ids))
    assert 5 not in result_ids


# ------------------------------------------------------------- ranking
def test_ranking_is_sorted_and_scores_are_consistent(engine):
    result = engine.recommend(UserPreferences(**SCI_FI_PREFS, top_n=50))
    recs = result["recommendations"]
    assert [r["rank"] for r in recs] == list(range(1, len(recs) + 1))
    assert [r["score"] for r in recs] == sorted((r["score"] for r in recs), reverse=True)
    for r in recs:
        assert 0 < r["score"] <= 1
        total = sum(c["contribution"] for c in r["components"].values())
        assert total == pytest.approx(r["score"], abs=1e-3)
    assert sum(result["profile"]["weights"].values()) == pytest.approx(1.0, abs=1e-3)


def test_top_n_limits_results(engine):
    assert len(engine.recommend(UserPreferences(genres=["Comedy"], languages=["English"], top_n=2))["recommendations"]) == 2


def test_inactive_components_get_zero_weight(engine):
    result = engine.recommend(UserPreferences(genres=["Comedy"]))
    weights = result["profile"]["weights"]
    assert weights["genre"] == pytest.approx(1.0)
    assert weights["mood"] == weights["keyword"] == weights["language"] == weights["year"] == 0
    assert result["profile"]["active_components"] == ["genre"]


def test_custom_weights_change_ranking(engine):
    prefs = dict(genres=["Science Fiction"], moods=["Mind-Bending"])
    genre_heavy = engine.recommend(UserPreferences(**prefs, weights={"genre": 1, "mood": 0}))
    assert ids(genre_heavy)[0] == 2  # pure Science Fiction -> genre cosine 1.0
    mood_heavy = engine.recommend(UserPreferences(**prefs, weights={"genre": 0, "mood": 1}))
    assert ids(mood_heavy)[:2] == [1, 3]  # both Mind-Bending; tie broken by rating 8.0 > 7.5
    assert 2 not in ids(mood_heavy)  # score 0 once genre has no weight


def test_keyword_component_is_max_normalised(engine):
    result = engine.recommend(UserPreferences(keywords=["party"]))
    values = [r["components"]["keyword"]["value"] for r in result["recommendations"]]
    assert max(values) == pytest.approx(1.0)
    raw = result["recommendations"][0]["components"]["keyword"]["raw"]
    assert 0 < raw <= 1


def test_genres_and_moods_are_inferred_from_liked_movies(engine):
    result = engine.recommend(UserPreferences(liked_movie_ids=[1]))
    assert result["profile"]["genres_inferred"] and result["profile"]["moods_inferred"]
    assert result["profile"]["genres"] == ["Science Fiction", "Thriller"]
    assert result["recommendations"][0]["similar_to"]["movie_id"] == 1


# ------------------------------------------------------------- determinism
def test_results_are_deterministic(engine):
    prefs = UserPreferences(**SCI_FI_PREFS, top_n=50)
    assert engine.recommend(prefs) == engine.recommend(prefs)
    fresh = RecommendationEngine(clean_movies(fixture_frame()))
    assert fresh.recommend(prefs) == engine.recommend(prefs)


def test_ties_are_broken_by_rating_then_movie_id(engine):
    result = engine.recommend(UserPreferences(genres=["Comedy"]))
    # Identical scores: Twin B (7.0, id 6), Twin C (7.0, id 7), Twin A (6.0, id 5).
    assert ids(result) == [6, 7, 5]
    assert len({r["score"] for r in result["recommendations"]}) == 1


def test_similar_movies_ranks_identical_content_first(engine):
    similar = engine.similar_movies(5, top_n=3)
    assert [s["movie"]["movie_id"] for s in similar[:2]] == [6, 7]
    assert similar[0]["similarity"] == pytest.approx(1.0)
    assert engine.similar_movies(12345) is None
