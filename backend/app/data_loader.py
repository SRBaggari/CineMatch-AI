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


def clean_movies(df: pd.DataFrame) -> pd.DataFrame:
    """Validate columns, coerce types, parse list columns and drop duplicates."""
    missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing:
        raise ValueError(f"Dataset is missing required columns: {', '.join(missing)}")

    df = df.copy()
    for col in LIST_COLUMNS:
        df[col] = df[col].apply(split_pipe)

    df["title"] = df["title"].astype(str).str.strip()
    df["director"] = df["director"].fillna("Unknown").astype(str).str.strip()
    df["overview"] = df["overview"].fillna("").astype(str).str.strip()
    df["language"] = df["language"].fillna("Unknown").astype(str).str.strip()
    df["movie_id"] = pd.to_numeric(df["movie_id"], errors="coerce")
    df = df.dropna(subset=["movie_id"])
    df["movie_id"] = df["movie_id"].astype(int)
    df["year"] = pd.to_numeric(df["year"], errors="coerce").fillna(0).astype(int)
    df["runtime"] = pd.to_numeric(df["runtime"], errors="coerce").fillna(0).astype(int)
    df["rating"] = pd.to_numeric(df["rating"], errors="coerce").fillna(0.0).astype(float).clip(0, 10)

    # Duplicate prevention: the same id, or the same title released in the same year.
    before = len(df)
    df = df.sort_values("movie_id").drop_duplicates(subset="movie_id", keep="first")
    title_key = df["title"].map(normalize_token) + "|" + df["year"].astype(str)
    df = df[~title_key.duplicated(keep="first")]
    if len(df) < before:
        logger.warning("Dropped %d duplicate movie rows", before - len(df))

    return df.reset_index(drop=True)


def load_movies(path: Path) -> pd.DataFrame:
    if not Path(path).exists():
        raise FileNotFoundError(f"Movie dataset not found at {path}")
    return clean_movies(pd.read_csv(path, encoding="utf-8"))
