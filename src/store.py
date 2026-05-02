"""DuckDB persistence layer for chess.com games."""

from __future__ import annotations

import datetime
import re
import time
from pathlib import Path

import duckdb


def _parse_pgn_header(pgn: str | None, tag: str) -> str | None:
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
        url = g.get("url")
        if not url:
            continue
        pgn = g.get("pgn", "")
        rows.append((
            url,
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


def get_synced_archives(conn: duckdb.DuckDBPyConnection) -> set[str]:
    rows = conn.execute("SELECT url FROM synced_archives").fetchall()
    return {r[0] for r in rows}


def mark_archive_synced(conn: duckdb.DuckDBPyConnection, archive_url: str) -> None:
    conn.execute(
        "INSERT INTO synced_archives VALUES (?, ?) ON CONFLICT (url) DO NOTHING",
        [archive_url, int(time.time())],
    )


def _yyyymmdd_to_ts(date_str: str, end_of_day: bool = False) -> int:
    year, month, day = int(date_str[:4]), int(date_str[4:6]), int(date_str[6:8])
    hour, minute, second = (23, 59, 59) if end_of_day else (0, 0, 0)
    dt = datetime.datetime(year, month, day, hour, minute, second,
                           tzinfo=datetime.timezone.utc)
    return int(dt.timestamp())


def query_games(
    conn: duckdb.DuckDBPyConnection,
    time_class: str | None = None,
    since: str | None = None,
    until: str | None = None,
    n: int | None = None,
) -> list[dict]:
    conditions: list[str] = []
    params: list = []

    if time_class:
        conditions.append("time_class = ?")
        params.append(time_class)
    if since:
        conditions.append("end_time >= ?")
        params.append(_yyyymmdd_to_ts(since))
    if until:
        conditions.append("end_time <= ?")
        params.append(_yyyymmdd_to_ts(until, end_of_day=True))

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    if n:
        sql = f"""
            SELECT * FROM (
                SELECT * FROM games {where} ORDER BY end_time DESC LIMIT ?
            ) sub ORDER BY end_time ASC
        """
        params.append(n)
    else:
        sql = f"SELECT * FROM games {where} ORDER BY end_time ASC"

    result = conn.execute(sql, params)
    cols = [d[0] for d in result.description]
    return [dict(zip(cols, row)) for row in result.fetchall()]
