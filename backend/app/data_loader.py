"""Loading, validation, cleaning and de-duplication of the movie dataset."""

import logging
import re
from pathlib import Path

import pandas as pd

logger = logging.getLogger("cinematch")

REQUIRED_COLUMNS = [
    "movie_id",
    "title",
    "year",
    "genres",
    "director",
    "cast",
    "keywords",
    "moods",
    "overview",
    "rating",
    "runtime",
    "language",
]

# Columns stored as pipe-separated lists in the CSV, e.g. "Action|Drama".
LIST_COLUMNS = ["genres", "cast", "keywords", "moods"]

_NON_ALNUM = re.compile(r"[^0-9a-z]+")


def normalize_token(value: str) -> str:
    """Turn a multi-word label into one comparable token.

    "Science Fiction" -> "sciencefiction", "time travel" -> "timetravel".
    Squashing keeps a tag as a single feature, so "time travel" does not
    partially match every movie whose description mentions "time".
    """
    return _NON_ALNUM.sub("", str(value).lower())


def split_pipe(value) -> list[str]:
    if isinstance(value, list):
        items = value
    elif pd.isna(value):
        return []
    else:
        items = str(value).split("|")
    seen, result = set(), []
    for item in (str(i).strip() for i in items):
        if item and normalize_token(item) not in seen:
            seen.add(normalize_token(item))
            result.append(item)
    return result


YEAR_RANGE = (1880, 2100)


def _text(series: pd.Series, default: str) -> pd.Series:
    """Strip text and replace missing/blank values with a default.

    Done element-wise on purpose: with pandas 3's string dtype, astype(str) keeps
    NaN as missing instead of producing the text "nan".
    """
    return series.map(lambda v: default if pd.isna(v) or not str(v).strip() else str(v).strip())


def clean_movies(df: pd.DataFrame) -> pd.DataFrame:
    """Validate columns, coerce types, parse list columns and drop invalid or duplicate rows.

    Policy: values that identify, filter or rank a movie (id, title, year, rating) are
    never invented. Rows where they are missing or invalid are dropped and logged.
    Optional fields get explicit empty values: no genres/moods/keywords/cast,
    director "Unknown", empty overview, language "Unknown", runtime 0 (= unknown).
    The number of dropped rows per reason is kept in df.attrs["dropped"].
    """
    missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing:
        raise ValueError(f"Dataset is missing required columns: {', '.join(missing)}")

    df = df.copy()
    for col in LIST_COLUMNS:
        df[col] = df[col].apply(split_pipe)

    df["title"] = _text(df["title"], "")
    df["director"] = _text(df["director"], "Unknown")
    df["overview"] = _text(df["overview"], "")
    df["language"] = _text(df["language"], "Unknown")
    movie_id = pd.to_numeric(df["movie_id"], errors="coerce")
    year = pd.to_numeric(df["year"], errors="coerce")
    rating = pd.to_numeric(df["rating"], errors="coerce")
    runtime = pd.to_numeric(df["runtime"], errors="coerce")

    invalid = {
        "missing or invalid movie_id": movie_id.isna() | (movie_id < 1) | (movie_id % 1 != 0),
        "missing title": df["title"] == "",
        "missing or invalid year": year.isna() | ~year.between(*YEAR_RANGE) | (year % 1 != 0),
        "missing or out-of-range rating": rating.isna() | ~rating.between(0, 10),
    }
    dropped: dict[str, int] = {}
    keep = pd.Series(True, index=df.index)
    for reason, bad in invalid.items():
        count = int((bad & keep).sum())  # count each dropped row once, under its first reason
        if count:
            dropped[reason] = count
        keep &= ~bad
    df, movie_id, year, rating, runtime = df[keep], movie_id[keep], year[keep], rating[keep], runtime[keep]

    df["movie_id"] = movie_id.astype(int)
    df["year"] = year.astype(int)
    df["rating"] = rating.astype(float)
    df["runtime"] = runtime.where(runtime > 0, 0).fillna(0).astype(int)

    # Duplicate prevention: the same id, or the same title released in the same year.
    before = len(df)
    df = df.sort_values("movie_id").drop_duplicates(subset="movie_id", keep="first")
    title_key = df["title"].map(normalize_token) + "|" + df["year"].astype(str)
    df = df[~title_key.duplicated(keep="first")]
    if len(df) < before:
        dropped["duplicate"] = before - len(df)

    if dropped:
        logger.warning("Dropped invalid movie rows: %s", dropped)
    if df.empty:
        raise ValueError("Dataset contains no valid movies after cleaning")

    df = df.reset_index(drop=True)
    df.attrs["dropped"] = dropped
    return df


def load_movies(path: Path) -> pd.DataFrame:
    if not Path(path).exists():
        raise FileNotFoundError(f"Movie dataset not found at {path}")
    return clean_movies(pd.read_csv(path, encoding="utf-8"))
