"""Loading, validation and cleaning of the movie dataset."""

import re
from pathlib import Path

import pandas as pd

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

    "Science Fiction" -> "sciencefiction", "Christopher Nolan" -> "christophernolan".
    Squashing keeps a person or tag as a single feature, so "Christopher Nolan"
    does not partially match "Christopher Lloyd".
    """
    return _NON_ALNUM.sub("", str(value).lower())


def split_pipe(value) -> list[str]:
    if pd.isna(value):
        return []
    return [part.strip() for part in str(value).split("|") if part.strip()]


def load_movies(path: Path) -> pd.DataFrame:
    if not Path(path).exists():
        raise FileNotFoundError(f"Movie dataset not found at {path}")

    df = pd.read_csv(path, encoding="utf-8")

    missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing:
        raise ValueError(f"Dataset is missing required columns: {', '.join(missing)}")

    df = df.drop_duplicates(subset="movie_id").copy()

    for col in LIST_COLUMNS:
        df[col] = df[col].apply(split_pipe)

    df["title"] = df["title"].astype(str).str.strip()
    df["director"] = df["director"].fillna("Unknown").astype(str).str.strip()
    df["overview"] = df["overview"].fillna("").astype(str).str.strip()
    df["language"] = df["language"].fillna("Unknown").astype(str).str.strip()
    df["movie_id"] = df["movie_id"].astype(int)
    df["year"] = pd.to_numeric(df["year"], errors="coerce").fillna(0).astype(int)
    df["runtime"] = pd.to_numeric(df["runtime"], errors="coerce").fillna(0).astype(int)
    df["rating"] = pd.to_numeric(df["rating"], errors="coerce").fillna(0.0).astype(float)

    return df.sort_values("movie_id").reset_index(drop=True)
