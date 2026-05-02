"""DuckDB persistence layer for chess.com games."""

from __future__ import annotations

import re
from pathlib import Path

import duckdb


def _parse_pgn_header(pgn: str, tag: str) -> str | None:
    m = re.search(rf'\[{tag} "([^"]*)"\]', pgn or "")
    return m.group(1) if m else None


def init_db(db_path: str) -> duckdb.DuckDBPyConnection:
    if db_path != ":memory:":
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = duckdb.connect(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS games (
            url          TEXT PRIMARY KEY,
            pgn          TEXT,
            time_class   TEXT,
            time_control TEXT,
            end_time     INTEGER,
            white        TEXT,
            black        TEXT,
            white_result TEXT,
            black_result TEXT,
            rated        BOOLEAN,
            fen          TEXT,
            eco          TEXT,
            opening      TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS synced_archives (
            url       TEXT PRIMARY KEY,
            synced_at INTEGER
        )
    """)
    return conn


def upsert_games(conn: duckdb.DuckDBPyConnection, games: list[dict]) -> int:
    if not games:
        return 0
    rows = []
    for g in games:
        pgn = g.get("pgn", "")
        rows.append((
            g.get("url", ""),
            pgn,
            g.get("time_class"),
            g.get("time_control"),
            g.get("end_time"),
            g.get("white", {}).get("username"),
            g.get("black", {}).get("username"),
            g.get("white", {}).get("result"),
            g.get("black", {}).get("result"),
            g.get("rated"),
            g.get("fen"),
            _parse_pgn_header(pgn, "ECO"),
            _parse_pgn_header(pgn, "Opening"),
        ))
    before = conn.execute("SELECT COUNT(*) FROM games").fetchone()[0]
    conn.executemany("""
        INSERT INTO games VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT (url) DO NOTHING
    """, rows)
    after = conn.execute("SELECT COUNT(*) FROM games").fetchone()[0]
    return after - before
