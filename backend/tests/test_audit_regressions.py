"""Regression tests for defects found in the QA audit, plus the audit's user scenarios."""

import io
from concurrent.futures import ThreadPoolExecutor

import pandas as pd
import pytest

from app.data_loader import clean_movies
from app.recommender import FeedbackProfile, RecommendationEngine, UserPreferences
from tests.conftest import fixture_frame

MESSY_CSV = """movie_id,title,year,genres,director,cast,keywords,moods,overview,rating,runtime,language
1,Complete,2001,Drama|Crime,D,A|B,heist|crew,Dark,A heist goes wrong.,8.1,120,English
2,No Optional Fields,2005,,,,,,,7.0,,
3,,2010,Comedy,X,,party,Funny,Missing title.,7.5,90,English
4,Bad Year,unknown,Comedy,X,C,family,Feel-Good,Invalid year.,6.5,100,French
5,Bad Rating,2004,Drama,X,A,heist,Dark,Rating is text.,abc,100,English
6,Out Of Range Rating,2004,Drama,X,A,heist,Dark,Rating too high.,11,100,English
,No Id,2002,Drama,D,A,x,Dark,No id.,5,100,English
7,Year Zero,0,Drama,D,A,x,Dark,Year zero.,5,100,English
8,Negative Runtime,2006,Drama,D,A,x,Dark,Odd runtime.,6,-30,English
1,Duplicate Id,2003,Drama,D,A,x,Dark,Duplicate id.,5,100,English
"""


# ------------------------------------------------------------- dataset with missing values
def test_missing_values_are_dropped_or_filled_honestly():
    df = clean_movies(pd.read_csv(io.StringIO(MESSY_CSV)))
    assert df["movie_id"].tolist() == [1, 2, 8]
    assert df.attrs["dropped"] == {
        "missing or invalid movie_id": 1,
        "missing title": 1,
        "missing or invalid year": 2,
        "missing or out-of-range rating": 2,
        "duplicate": 1,
    }
    blank = df.set_index("movie_id").loc[2]
    assert blank["genres"] == [] and blank["moods"] == [] and blank["keywords"] == [] and blank["cast"] == []
    assert blank["director"] == "Unknown" and blank["language"] == "Unknown" and blank["overview"] == ""
    assert blank["runtime"] == 0                                    # 0 = unknown, never invented
    assert df.set_index("movie_id").loc[8]["runtime"] == 0           # negative runtime treated as unknown
    assert all(isinstance(t, str) and t for t in df["title"])       # no NaN / "nan" titles (pandas 3)


def test_engine_works_end_to_end_on_messy_dataset():
    engine = RecommendationEngine(clean_movies(pd.read_csv(io.StringIO(MESSY_CSV))))
    assert engine.preference_options()["year_min"] == 2001          # not polluted by a 0 placeholder
    assert engine.recommend(UserPreferences(genres=["Drama"]))["recommendations"]
    assert engine.search(query="no", sort="title")["total"] >= 1
    assert engine.similar_movies(2) is not None
    engine.dataset_analytics()


def test_empty_dataset_raises_a_clear_error():
    with pytest.raises(ValueError, match="no valid movies"):
        clean_movies(pd.read_csv(io.StringIO(MESSY_CSV.splitlines()[0] + "\n,,,,,,,,,,,\n")))


def test_catalogue_without_genres_moods_or_text_still_builds():
    rows = [(i, f"Movie {i}", 2000 + i, "", "", "", "the and of", 7.0, "English") for i in range(1, 5)]
    engine = RecommendationEngine(clean_movies(fixture_frame(rows)))
    assert engine.vectorizer is None and len(engine.feature_names) == 0
    result = engine.recommend(UserPreferences(languages=["English"], keywords=["heist"]))
    assert len(result["recommendations"]) == 4
    assert any("no keyword or description text" in w for w in result["warnings"])
    assert engine.similar_movies(1)


def test_rating_histogram_has_a_bin_when_all_ratings_are_equal():
    rows = [(i, f"Movie {i}", 2000, "Drama", "Dark", "x", "Plot.", 8.0, "English") for i in range(1, 4)]
    hist = RecommendationEngine(clean_movies(fixture_frame(rows))).dataset_analytics()["rating_distribution"]
    assert sum(b["count"] for b in hist) == 3 and len(hist) >= 1


# ------------------------------------------------------------- user scenarios (fixture)
def test_single_genre(engine):
    recs = engine.recommend(UserPreferences(genres=["Comedy"]))["recommendations"]
    assert recs and all("Comedy" in r["movie"]["genres"] for r in recs)
    assert recs[0]["summary"] == "Recommended because you enjoy Comedy movies."


def test_multiple_genres_rank_better_overlap_first(engine):
    recs = engine.recommend(UserPreferences(genres=["Science Fiction", "Thriller"], top_n=50))["recommendations"]
    assert recs[0]["movie_id"] == 1                                  # has both genres
    assert {r["movie_id"] for r in recs} == {1, 2}                   # only movies with at least one


def test_language_with_no_matching_movies(engine):
    strict = engine.recommend(UserPreferences(genres=["Western"], languages=["English"], strict_languages=True))
    assert strict["recommendations"] == [] and strict["message"]
    soft = engine.recommend(UserPreferences(genres=["Western"], languages=["English"]))
    assert [r["movie_id"] for r in soft["recommendations"]][0] == 4  # genre match outranks a language-only match


def test_changing_preferences_never_returns_stale_cached_results():
    engine = RecommendationEngine(clean_movies(fixture_frame()))
    first = engine.recommend(UserPreferences(genres=["Comedy"]))
    other = engine.recommend(UserPreferences(genres=["Romance"]))
    filtered = engine.recommend(UserPreferences(genres=["Comedy"], min_rating=6.5))
    assert first != other
    assert [r["movie_id"] for r in filtered["recommendations"]] == [6, 7]   # 6.0-rated twin removed
    assert engine.recommend(UserPreferences(genres=["Comedy"])) == first


def test_symbol_only_keywords_produce_a_warning(engine):
    result = engine.recommend(UserPreferences(genres=["Comedy"], keywords=["!!!"]))
    assert any("without letters or digits" in w for w in result["warnings"])


def test_liked_feedback_movies_stay_eligible_but_never_boost_themselves(engine):
    result = engine.recommend(UserPreferences(genres=["Comedy", "Romance"]), FeedbackProfile(liked=[6]))
    twin = next(r for r in result["recommendations"] if r["movie_id"] == 6)
    assert twin["feedback"]["closest_liked"] is None or twin["feedback"]["closest_liked"]["movie_id"] != 6


def test_repeated_and_concurrent_requests_are_consistent():
    engine = RecommendationEngine(clean_movies(fixture_frame()))
    prefs = dict(genres=["Comedy", "Romance"], moods=["Funny"], keywords=["party"])
    expected = engine.recommend(UserPreferences(**prefs))
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda _: engine.recommend(UserPreferences(**prefs)), range(64)))
    assert all(r == expected for r in results)
    assert engine.cache_stats["misses"] == 1


# ------------------------------------------------------------- API regressions
@pytest.mark.parametrize("method,path", [
    ("delete", "/api/feedback/1180591620717411303424"),
    ("put", "/api/feedback/1180591620717411303424"),
    ("get", "/api/movies/1180591620717411303424"),
    ("get", "/api/movies/0"),
    ("get", "/api/movies/-3/similar"),
])
def test_out_of_range_movie_ids_are_422_not_500(client, store, method, path):
    kwargs = {"json": {"reaction": "like"}} if method == "put" else {}
    assert getattr(client, method)(path, **kwargs).status_code == 422


def test_analytics_ignores_feedback_for_movies_not_in_catalogue(client, store):
    store.set_feedback(999999, reaction="like")            # e.g. a movie removed from the CSV
    client.put("/api/feedback/6", json={"reaction": "like"})
    assert client.get("/api/analytics").json()["feedback"]["likes"] == 1
    assert client.get("/api/feedback").json()["counts"]["likes"] == 1


def test_no_match_message_names_the_strict_filter_when_it_narrowed_the_list(engine):
    # The strict language filter leaves the two French movies, but neither is a Western.
    result = engine.recommend(UserPreferences(genres=["Western"], languages=["French"], strict_languages=True))
    assert result["recommendations"] == []
    assert result["filter_report"]["after_languages"] == 2
    assert "2 movies left after your strict language filter" in result["message"]
    assert "Only these languages" in result["message"]


def test_no_match_message_grammar_for_a_single_movie(engine):
    # Only movie 4 is Italian, and it is not a Comedy.
    message = engine.recommend(UserPreferences(genres=["Comedy"], languages=["Italian"], strict_languages=True))["message"]
    assert message.startswith("The 1 movie left after your strict language filter matches none")
