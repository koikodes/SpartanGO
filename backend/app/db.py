"""Tiny SQLite layer using the standard library. Fine for the capstone; swap to Postgres
(e.g. Supabase or Railway) for a real deployment by replacing these functions."""
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

from .config import settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    email         TEXT UNIQUE NOT NULL,
    name          TEXT NOT NULL,
    student_id    TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    role          TEXT NOT NULL DEFAULT 'student',
    active        INTEGER NOT NULL DEFAULT 1,
    created_at    TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS ride_requests (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL REFERENCES users(id),
    route_id        TEXT NOT NULL,
    pickup_stop_id  TEXT NOT NULL,
    dropoff_stop_id TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'pending',
    note            TEXT,
    created_at      TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS boardings (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL REFERENCES users(id),
    vehicle_id  TEXT,
    boarded_at  TEXT NOT NULL
);
"""

_db_path = settings.database_path


def configure(path: str) -> None:
    """Point at a different database (used by tests)."""
    global _db_path
    _db_path = path
    init()


@contextmanager
def connect():
    conn = sqlite3.connect(_db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init() -> None:
    with connect() as c:
        c.executescript(SCHEMA)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
