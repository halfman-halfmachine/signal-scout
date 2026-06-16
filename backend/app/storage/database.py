"""SQLite persistence (stdlib `sqlite3`, no external dependency).

One database file under DATA_DIR, mounted as a volume in Docker so the queue,
learned engine state, config, and generated outputs survive restarts. A new
connection is opened per operation (cheap for SQLite) with WAL enabled for
concurrent readers.
"""
from __future__ import annotations

import json
import sqlite3
import time
from contextlib import contextmanager
from typing import Any, Iterator

from .. import config
from ..defaults_app import default_app_settings, default_ingestion
from ..engine.defaults import default_engine_config

SCHEMA = """
CREATE TABLE IF NOT EXISTS signals (
    id          TEXT PRIMARY KEY,
    payload     TEXT NOT NULL,           -- full (scored) signal object as JSON
    score       REAL    DEFAULT 0,
    tier        TEXT    DEFAULT 'LOG',
    kept        INTEGER DEFAULT 0,
    dismissed   INTEGER DEFAULT 0,
    origin      TEXT    DEFAULT 'automated',
    created_at  TEXT    NOT NULL,
    updated_at  TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_signals_score ON signals(score DESC);
CREATE INDEX IF NOT EXISTS idx_signals_dismissed ON signals(dismissed);

CREATE TABLE IF NOT EXISTS config (
    section     TEXT PRIMARY KEY,        -- 'engine' | 'ingestion' | 'app_settings'
    data        TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS learned_state (
    key         TEXT PRIMARY KEY,        -- one of the 6 accumulator maps
    data        TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS outputs (
    id          TEXT PRIMARY KEY,
    signal_id   TEXT,
    output_type TEXT,
    framework   TEXT,
    content     TEXT NOT NULL,
    is_live     INTEGER DEFAULT 0,
    meta        TEXT,
    created_at  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_outputs_created ON outputs(created_at DESC);
"""

LEARNED_STATE_KEYS = [
    "conceptHistory", "questionClusters", "sourceTrust",
    "topicSentiment", "competitorCoverage", "platformTopicWindow",
]


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(config.DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    """Create tables and seed config / learned-state defaults if empty."""
    config.ensure_dirs()
    with connect() as conn:
        conn.executescript(SCHEMA)

        # Seed config sections if missing.
        seeds = {
            "engine": default_engine_config(),
            "ingestion": default_ingestion(),
            "app_settings": default_app_settings(),
        }
        for section, data in seeds.items():
            row = conn.execute("SELECT 1 FROM config WHERE section=?", (section,)).fetchone()
            if row is None:
                conn.execute(
                    "INSERT INTO config(section, data, updated_at) VALUES (?,?,?)",
                    (section, json.dumps(data), _now()),
                )

        # Seed empty learned-state maps.
        for key in LEARNED_STATE_KEYS:
            row = conn.execute("SELECT 1 FROM learned_state WHERE key=?", (key,)).fetchone()
            if row is None:
                conn.execute(
                    "INSERT INTO learned_state(key, data) VALUES (?,?)",
                    (key, json.dumps({})),
                )


# ── Config ─────────────────────────────────────────────────────────────────

def get_config(section: str) -> dict[str, Any]:
    with connect() as conn:
        row = conn.execute("SELECT data FROM config WHERE section=?", (section,)).fetchone()
    return json.loads(row["data"]) if row else {}


def set_config(section: str, data: dict[str, Any]) -> None:
    with connect() as conn:
        conn.execute(
            "INSERT INTO config(section, data, updated_at) VALUES (?,?,?) "
            "ON CONFLICT(section) DO UPDATE SET data=excluded.data, updated_at=excluded.updated_at",
            (section, json.dumps(data), _now()),
        )


# ── Learned engine state (the 6 accumulator maps) ───────────────────────────

def load_learned_state() -> dict[str, Any]:
    with connect() as conn:
        rows = conn.execute("SELECT key, data FROM learned_state").fetchall()
    return {r["key"]: json.loads(r["data"]) for r in rows}


def save_learned_state(state: dict[str, Any]) -> None:
    with connect() as conn:
        for key in LEARNED_STATE_KEYS:
            conn.execute(
                "INSERT INTO learned_state(key, data) VALUES (?,?) "
                "ON CONFLICT(key) DO UPDATE SET data=excluded.data",
                (key, json.dumps(state.get(key, {}))),
            )


# ── Signals / queue ──────────────────────────────────────────────────────────

def upsert_signal(signal: dict[str, Any], origin: str = "automated") -> None:
    sid = signal["id"]
    score = float(signal.get("scores", {}).get("final", signal.get("score", 0)) or 0)
    tier = signal.get("routing", {}).get("tier") or signal.get("tier") or "LOG"
    with connect() as conn:
        existing = conn.execute(
            "SELECT kept, dismissed, created_at FROM signals WHERE id=?", (sid,)
        ).fetchone()
        kept = existing["kept"] if existing else int(bool(signal.get("kept", 0)))
        dismissed = existing["dismissed"] if existing else 0
        created = existing["created_at"] if existing else _now()
        conn.execute(
            "INSERT INTO signals(id, payload, score, tier, kept, dismissed, origin, created_at, updated_at) "
            "VALUES (?,?,?,?,?,?,?,?,?) "
            "ON CONFLICT(id) DO UPDATE SET payload=excluded.payload, score=excluded.score, "
            "tier=excluded.tier, updated_at=excluded.updated_at",
            (sid, json.dumps(signal), score, tier, kept, dismissed, origin, created, _now()),
        )


def list_signals(include_dismissed: bool = False, min_score: float | None = None,
                 limit: int = 200) -> list[dict[str, Any]]:
    q = "SELECT * FROM signals"
    clauses, params = [], []
    if not include_dismissed:
        clauses.append("dismissed=0")
    if min_score is not None:
        clauses.append("score>=?")
        params.append(min_score)
    if clauses:
        q += " WHERE " + " AND ".join(clauses)
    q += " ORDER BY score DESC LIMIT ?"
    params.append(limit)
    with connect() as conn:
        rows = conn.execute(q, params).fetchall()
    return [_row_to_signal(r) for r in rows]


def get_signal(sid: str) -> dict[str, Any] | None:
    with connect() as conn:
        row = conn.execute("SELECT * FROM signals WHERE id=?", (sid,)).fetchone()
    return _row_to_signal(row) if row else None


def update_signal_flags(sid: str, *, kept: bool | None = None,
                        dismissed: bool | None = None) -> bool:
    sets, params = [], []
    if kept is not None:
        sets.append("kept=?")
        params.append(int(kept))
    if dismissed is not None:
        sets.append("dismissed=?")
        params.append(int(dismissed))
    if not sets:
        return False
    sets.append("updated_at=?")
    params.extend([_now(), sid])
    with connect() as conn:
        cur = conn.execute(f"UPDATE signals SET {', '.join(sets)} WHERE id=?", params)
    return cur.rowcount > 0


def delete_signal(sid: str) -> bool:
    with connect() as conn:
        cur = conn.execute("DELETE FROM signals WHERE id=?", (sid,))
    return cur.rowcount > 0


def _row_to_signal(row: sqlite3.Row) -> dict[str, Any]:
    payload = json.loads(row["payload"])
    payload["kept"] = bool(row["kept"])
    payload["dismissed"] = bool(row["dismissed"])
    payload["origin"] = row["origin"]
    return payload


# ── Outputs (generation history) ─────────────────────────────────────────────

def save_output(record: dict[str, Any]) -> None:
    with connect() as conn:
        conn.execute(
            "INSERT INTO outputs(id, signal_id, output_type, framework, content, is_live, meta, created_at) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (record["id"], record.get("signal_id"), record.get("output_type"),
             record.get("framework"), record["content"], int(record.get("is_live", 0)),
             json.dumps(record.get("meta", {})), _now()),
        )


def list_outputs(limit: int = 100) -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute("SELECT * FROM outputs ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["is_live"] = bool(d["is_live"])
        d["meta"] = json.loads(d["meta"]) if d["meta"] else {}
        out.append(d)
    return out
