"""Unit tests for the pure scoring helpers."""

import math

import pytest

from app.data_loader import normalize_token, split_pipe
from app.recommender import (
    InvalidPreferenceError,
    keyword_document,
    normalize_weights,
    set_cosine,
    unique,
    year_score,
)


def test_normalize_token():
    assert normalize_token("Science Fiction") == "sciencefiction"
    assert normalize_token("Mind-Bending") == "mindbending"


def test_split_pipe_strips_and_deduplicates():
    assert split_pipe(" Drama | drama |Crime|") == ["Drama", "Crime"]
    assert split_pipe(float("nan")) == []


def test_set_cosine():
    assert set_cosine({"a", "b"}, {"a", "b"}) == 1.0
    assert set_cosine({"a"}, {"b"}) == 0.0
    assert set_cosine({"a", "b"}, {"a"}) == pytest.approx(1 / math.sqrt(2))
    assert set_cosine(set(), {"a"}) == 0.0


@pytest.mark.parametrize(
    ("year", "lo", "hi", "expected"),
    [
        (2010, 2005, 2015, 1.0),   # inside
        (2005, 2005, 2015, 1.0),   # boundary
        (2000, 2005, 2015, 0.75),  # 5 years early -> 1 - 5/20
        (2025, 2005, 2015, 0.5),   # 10 years late
        (1950, 2005, 2015, 0.0),   # far away -> clipped at 0
        (1990, None, 2000, 1.0),   # open lower bound
        (1990, 2000, None, 0.5),   # open upper bound
    ],
)
def test_year_score(year, lo, hi, expected):
    assert year_score(year, lo, hi, decay=20) == pytest.approx(expected)


def test_normalize_weights_drops_inactive_and_sums_to_one():
    weights = {"genre": 0.3, "keyword": 0.25, "mood": 0.2, "language": 0.15, "year": 0.1}
    active = {"genre": True, "keyword": False, "mood": True, "language": False, "year": False}
    result = normalize_weights(weights, active)
    assert sum(result.values()) == pytest.approx(1.0)
    assert result["keyword"] == result["language"] == result["year"] == 0
    assert result["genre"] == pytest.approx(0.6)
    assert result["mood"] == pytest.approx(0.4)


def test_normalize_weights_rejects_zero_total():
    with pytest.raises(InvalidPreferenceError):
        normalize_weights({"genre": 0.0}, {"genre": True})


def test_unique_is_order_preserving_and_case_insensitive():
    assert unique(["Comedy", " comedy ", "Drama", "COMEDY"]) == ["Comedy", "Drama"]
    assert unique([3, 1, 3]) == [3, 1]


def test_keyword_document_contains_tag_and_words():
    doc = keyword_document(["time travel"], "overview")
    assert doc.split().count("timetravel") == 2
    assert "time travel" in doc and doc.endswith("overview")
