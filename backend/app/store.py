"""SQLite persistence for user feedback and anonymous usage statistics.

There is no authentication, so this models a single local profile: the person
using this installation. Nothing leaves the machine.

Tables
------
feedback                movie_id, reaction (+1 like / -1 dislike / NULL), favorite flag
recommendation_requests one row per /recommendations call: the preferences used
recommendation_results  the movies served for each request, with base and final scores
"""

import json
import sqlite3
import threading
from collections import Counter
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS feedback (
    movie_id   INTEGER PRIMARY KEY,
    reaction   INTEGER CHECK (reaction IN (-1, 1)),
    favorite   INTEGER NOT NULL DEFAULT 0 CHECK (favorite IN (0, 1)),
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS recommendation_requests (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at    TEXT NOT NULL,
    genres        TEXT NOT NULL,
    moods         TEXT NOT NULL,
    languages     TEXT NOT NULL,
    keywords      TEXT NOT NULL,
    used_feedback INTEGER NOT NULL,
    result_count  INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS recommendation_results (
    request_id INTEGER NOT NULL REFERENCES recommendation_requests (id) ON DELETE CASCADE,
    rank       INTEGER NOT NULL,
    movie_id   INTEGER NOT NULL,
    base_score REAL NOT NULL,
    score      REAL NOT NULL
);
"""

REACTIONS = {"like": 1, "dislike": -1, None: None}
REACTION_NAMES = {1: "like", -1: "dislike", None: None}
UNSET = object()  # sentinel: "leave this field unchanged"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Store:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        with self._connect() as conn:
            conn.executescript(SCHEMA)

    @contextmanager
    def _connect(self):
        # One short-lived connection per operation keeps this safe under FastAPI's thread pool.
        conn = sqlite3.connect(self.path, timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    # ------------------------------------------------------------------ feedback
    def get_feedback(self) -> dict[int, dict]:
        with self._connect() as conn:
            rows = conn.execute("SELECT movie_id, reaction, favorite, updated_at FROM feedback").fetchall()
        return {
            row["movie_id"]: {
                "movie_id": row["movie_id"],
                "reaction": REACTION_NAMES[row["reaction"]],
                "favorite": bool(row["favorite"]),
                "updated_at": row["updated_at"],
            }
            for row in rows
        }

    def set_feedback(self, movie_id: int, reaction=UNSET, favorite=UNSET) -> dict | None:
        """Update one movie's feedback. Returns the new state, or None once it is empty."""
        with self._lock, self._connect() as conn:
            row = conn.execute("SELECT reaction, favorite FROM feedback WHERE movie_id = ?", (movie_id,)).fetchone()
            current_reaction = row["reaction"] if row else None
            current_favorite = bool(row["favorite"]) if row else False
            new_reaction = current_reaction if reaction is UNSET else REACTIONS[reaction]
            new_favorite = current_favorite if favorite is UNSET else bool(favorite)

            if new_reaction is None and not new_favorite:
                conn.execute("DELETE FROM feedback WHERE movie_id = ?", (movie_id,))
                return None
            updated_at = _now()
            conn.execute(
                """INSERT INTO feedback (movie_id, reaction, favorite, updated_at) VALUES (?, ?, ?, ?)
                   ON CONFLICT (movie_id) DO UPDATE SET reaction = excluded.reaction,
                   favorite = excluded.favorite, updated_at = excluded.updated_at""",
                (movie_id, new_reaction, int(new_favorite), updated_at),
            )
        return {
            "movie_id": movie_id,
            "reaction": REACTION_NAMES[new_reaction],
            "favorite": new_favorite,
            "updated_at": updated_at,
        }

    def clear_feedback(self, movie_id: int | None = None) -> int:
        with self._lock, self._connect() as conn:
            if movie_id is None:
                return conn.execute("DELETE FROM feedback").rowcount
            return conn.execute("DELETE FROM feedback WHERE movie_id = ?", (movie_id,)).rowcount

    def feedback_sets(self) -> dict[str, list[int]]:
        """Movie ids grouped for the recommendation engine."""
        items = self.get_feedback().values()
        return {
            "liked": sorted(i["movie_id"] for i in items if i["reaction"] == "like"),
            "disliked": sorted(i["movie_id"] for i in items if i["reaction"] == "dislike"),
            "favorites": sorted(i["movie_id"] for i in items if i["favorite"]),
        }

    # ------------------------------------------------------------------ usage log
    def log_recommendation(self, profile: dict, recommendations: list[dict], used_feedback: bool) -> int:
        with self._lock, self._connect() as conn:
            cursor = conn.execute(
                """INSERT INTO recommendation_requests
                   (created_at, genres, moods, languages, keywords, used_feedback, result_count)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    _now(),
                    # Only explicit choices are logged as "selected"; inferred genres are not.
                    json.dumps([] if profile.get("genres_inferred") else profile.get("genres", [])),
                    json.dumps([] if profile.get("moods_inferred") else profile.get("moods", [])),
                    json.dumps(profile.get("languages", [])),
                    json.dumps(profile.get("keywords", [])),
                    int(used_feedback),
                    len(recommendations),
                ),
            )
            request_id = cursor.lastrowid
            conn.executemany(
                "INSERT INTO recommendation_results (request_id, rank, movie_id, base_score, score) VALUES (?, ?, ?, ?, ?)",
                [(request_id, r["rank"], r["movie_id"], r["base_score"], r["score"]) for r in recommendations],
            )
        return request_id

    def usage_stats(self) -> dict:
        with self._connect() as conn:
            requests = conn.execute("SELECT genres, moods, languages, keywords FROM recommendation_requests").fetchall()
            scores = [row["score"] for row in conn.execute("SELECT score FROM recommendation_results")]
            served = Counter(row["movie_id"] for row in conn.execute("SELECT movie_id FROM recommendation_results"))
        counters = {name: Counter() for name in ("genres", "moods", "languages", "keywords")}
        for row in requests:
            for name, counter in counters.items():
                counter.update(json.loads(row[name]))
        return {
            "total_requests": len(requests),
            "selections": {name: dict(counter.most_common()) for name, counter in counters.items()},
            "scores": scores,
            "most_recommended": served.most_common(10),
        }

    def clear_usage(self) -> None:
        with self._lock, self._connect() as conn:
            conn.execute("DELETE FROM recommendation_results")
            conn.execute("DELETE FROM recommendation_requests")
