# DuckDB Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Persist chess.com games to a per-user DuckDB file, replacing in-memory filtering with SQL queries and adding sync/export/query/stats subcommands.

**Architecture:** Add `src/store.py` as a thin DuckDB layer (init, upsert, query, stats). Refactor `src/cli.py` from a single `main()` into four subcommands: `sync` (download → DB), `export` (DB → PGN), `query` (raw SQL), `stats` (dashboard). `src/downloader.py` is unchanged.

**Tech Stack:** Python 3.11+, duckdb 1.x, pytest, unittest.mock

---

## File Map

| Action | Path | Responsibility |
|--------|------|---------------|
| Create | `src/store.py` | All DuckDB interaction |
| Modify | `src/cli.py` | Subcommand dispatcher, replaces single main() |
| Create | `tests/test_store.py` | Unit tests for store layer (in-memory DuckDB) |
| Replace | `tests/test_cli.py` | Tests for all four subcommands |
| Delete | `tests/test_filter.py` | Filtering now done in DuckDB |
| Create | `requirements.txt` | Pin duckdb dependency |
| Modify | `.gitignore` | Ignore `data/` directory |

---

## Task 1: Project Setup

**Files:**
- Create: `requirements.txt`
- Modify: `.gitignore`

- [ ] **Step 1: Create requirements.txt**

```
duckdb>=1.0.0
```

- [ ] **Step 2: Install duckdb into the virtualenv**

Run: `.venv/bin/pip install duckdb`
Expected: `Successfully installed duckdb-...`

- [ ] **Step 3: Update .gitignore to exclude data directory**

Add to `.gitignore`:
```
# DuckDB files
data/
```

- [ ] **Step 4: Commit**

```bash
git add requirements.txt .gitignore
git commit -m "chore: add duckdb dependency and gitignore data dir"
```

---

## Task 2: store.py — Schema, init_db, upsert_games

**Files:**
- Create: `tests/test_store.py`
- Create: `src/store.py`

- [ ] **Step 1: Write failing tests for init_db and upsert_games**

Create `tests/test_store.py`:

```python
"""Unit tests for src.store — all use in-memory DuckDB."""

import pytest
import duckdb

from src.store import init_db, upsert_games


def make_game(**overrides):
    g = {
        "url": "https://chess.com/game/1",
        "pgn": '[ECO "B20"]\n[Opening "Sicilian Defense"]\n\n1. e4 c5 *',
        "time_class": "rapid",
        "time_control": "600",
        "end_time": 1704067200,  # 2024-01-01 00:00:00 UTC
        "white": {"username": "rathnakaragn", "result": "win"},
        "black": {"username": "opponent", "result": "lose"},
        "rated": True,
        "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
    }
    g.update(overrides)
    return g


@pytest.fixture
def conn():
    c = init_db(":memory:")
    yield c
    c.close()


class TestInitDb:
    def test_creates_games_table(self, conn):
        tables = {r[0] for r in conn.execute("SHOW TABLES").fetchall()}
        assert "games" in tables

    def test_creates_synced_archives_table(self, conn):
        tables = {r[0] for r in conn.execute("SHOW TABLES").fetchall()}
        assert "synced_archives" in tables


class TestUpsertGames:
    def test_inserts_game(self, conn):
        count = upsert_games(conn, [make_game()])
        assert count == 1
        row = conn.execute("SELECT url, white, eco, opening FROM games").fetchone()
        assert row[0] == "https://chess.com/game/1"
        assert row[1] == "rathnakaragn"
        assert row[2] == "B20"
        assert row[3] == "Sicilian Defense"

    def test_deduplicates_on_url(self, conn):
        upsert_games(conn, [make_game()])
        second = upsert_games(conn, [make_game()])
        assert second == 0
        assert conn.execute("SELECT COUNT(*) FROM games").fetchone()[0] == 1

    def test_inserts_multiple(self, conn):
        games = [make_game(url="https://chess.com/game/1"),
                 make_game(url="https://chess.com/game/2")]
        count = upsert_games(conn, games)
        assert count == 2

    def test_empty_list(self, conn):
        assert upsert_games(conn, []) == 0

    def test_flattens_white_black(self, conn):
        upsert_games(conn, [make_game(
            white={"username": "alice", "result": "win"},
            black={"username": "bob", "result": "lose"},
        )])
        row = conn.execute("SELECT white, black, white_result, black_result FROM games").fetchone()
        assert row == ("alice", "bob", "win", "lose")

    def test_eco_missing_from_pgn(self, conn):
        upsert_games(conn, [make_game(pgn="1. e4 e5 *")])
        row = conn.execute("SELECT eco, opening FROM games").fetchone()
        assert row[0] is None
        assert row[1] is None
```

- [ ] **Step 2: Run tests to confirm they fail**

Run: `.venv/bin/python -m pytest tests/test_store.py -v`
Expected: `ModuleNotFoundError: No module named 'src.store'`

- [ ] **Step 3: Implement init_db and upsert_games in src/store.py**

Create `src/store.py`:

```python
"""DuckDB persistence layer for chess.com games."""

from __future__ import annotations

import datetime
import re
import time
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
```

- [ ] **Step 4: Run tests to confirm they pass**

Run: `.venv/bin/python -m pytest tests/test_store.py::TestInitDb tests/test_store.py::TestUpsertGames -v`
Expected: 8 tests PASSED

- [ ] **Step 5: Commit**

```bash
git add src/store.py tests/test_store.py
git commit -m "feat: add store.py with init_db and upsert_games"
```

---

## Task 3: store.py — Archive Tracking

**Files:**
- Modify: `tests/test_store.py` (append)
- Modify: `src/store.py` (append)

- [ ] **Step 1: Write failing tests for archive tracking**

Append to `tests/test_store.py`:

```python
from src.store import get_synced_archives, mark_archive_synced


class TestArchiveTracking:
    def test_empty_initially(self, conn):
        assert get_synced_archives(conn) == set()

    def test_mark_and_retrieve(self, conn):
        url = "https://api.chess.com/pub/player/rathnakaragn/games/2024/01"
        mark_archive_synced(conn, url)
        assert url in get_synced_archives(conn)

    def test_mark_idempotent(self, conn):
        url = "https://api.chess.com/pub/player/rathnakaragn/games/2024/01"
        mark_archive_synced(conn, url)
        mark_archive_synced(conn, url)  # should not raise
        assert len(get_synced_archives(conn)) == 1
```

- [ ] **Step 2: Run tests to confirm they fail**

Run: `.venv/bin/python -m pytest tests/test_store.py::TestArchiveTracking -v`
Expected: `ImportError: cannot import name 'get_synced_archives'`

- [ ] **Step 3: Implement in src/store.py**

Append to `src/store.py`:

```python
def get_synced_archives(conn: duckdb.DuckDBPyConnection) -> set[str]:
    rows = conn.execute("SELECT url FROM synced_archives").fetchall()
    return {r[0] for r in rows}


def mark_archive_synced(conn: duckdb.DuckDBPyConnection, archive_url: str) -> None:
    conn.execute(
        "INSERT INTO synced_archives VALUES (?, ?) ON CONFLICT (url) DO NOTHING",
        [archive_url, int(time.time())],
    )
```

- [ ] **Step 4: Run tests to confirm they pass**

Run: `.venv/bin/python -m pytest tests/test_store.py::TestArchiveTracking -v`
Expected: 3 tests PASSED

- [ ] **Step 5: Commit**

```bash
git add src/store.py tests/test_store.py
git commit -m "feat: add archive tracking to store"
```

---

## Task 4: store.py — query_games

**Files:**
- Modify: `tests/test_store.py` (append)
- Modify: `src/store.py` (append)

- [ ] **Step 1: Write failing tests for query_games**

Append to `tests/test_store.py`:

```python
from src.store import query_games


class TestQueryGames:
    def test_returns_all(self, conn):
        upsert_games(conn, [make_game(url="u1"), make_game(url="u2")])
        assert len(query_games(conn)) == 2

    def test_filter_time_class(self, conn):
        upsert_games(conn, [
            make_game(url="u1", time_class="rapid"),
            make_game(url="u2", time_class="blitz"),
        ])
        results = query_games(conn, time_class="rapid")
        assert len(results) == 1
        assert results[0]["time_class"] == "rapid"

    def test_filter_since(self, conn):
        upsert_games(conn, [
            make_game(url="u1", end_time=1704067200),  # 2024-01-01
            make_game(url="u2", end_time=1706745600),  # 2024-02-01
        ])
        results = query_games(conn, since="20240201")
        assert len(results) == 1
        assert results[0]["url"] == "u2"

    def test_filter_until(self, conn):
        upsert_games(conn, [
            make_game(url="u1", end_time=1704067200),  # 2024-01-01
            make_game(url="u2", end_time=1706745600),  # 2024-02-01
        ])
        results = query_games(conn, until="20240131")
        assert len(results) == 1
        assert results[0]["url"] == "u1"

    def test_filter_n_last(self, conn):
        games = [
            make_game(url=f"u{i}", end_time=1704067200 + i * 86400)
            for i in range(5)
        ]
        upsert_games(conn, games)
        results = query_games(conn, n=2)
        assert len(results) == 2
        assert results[0]["url"] == "u3"
        assert results[1]["url"] == "u4"

    def test_returns_dicts(self, conn):
        upsert_games(conn, [make_game()])
        results = query_games(conn)
        assert isinstance(results[0], dict)
        assert "url" in results[0]
        assert "pgn" in results[0]
```

- [ ] **Step 2: Run tests to confirm they fail**

Run: `.venv/bin/python -m pytest tests/test_store.py::TestQueryGames -v`
Expected: `ImportError: cannot import name 'query_games'`

- [ ] **Step 3: Implement in src/store.py**

Append to `src/store.py` (note: `import datetime` is already at the top from Task 2):

```python
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
```

- [ ] **Step 4: Run tests to confirm they pass**

Run: `.venv/bin/python -m pytest tests/test_store.py::TestQueryGames -v`
Expected: 6 tests PASSED

- [ ] **Step 5: Commit**

```bash
git add src/store.py tests/test_store.py
git commit -m "feat: add query_games with time_class, since, until, n filters"
```

---

## Task 5: store.py — raw_sql + stats

**Files:**
- Modify: `tests/test_store.py` (append)
- Modify: `src/store.py` (append)

- [ ] **Step 1: Write failing tests for raw_sql and stats**

Append to `tests/test_store.py`:

```python
from src.store import raw_sql, stats


class TestRawSql:
    def test_returns_rows(self, conn):
        upsert_games(conn, [make_game()])
        rows = raw_sql(conn, "SELECT url FROM games")
        assert len(rows) == 1
        assert rows[0][0] == "https://chess.com/game/1"

    def test_empty_result(self, conn):
        assert raw_sql(conn, "SELECT url FROM games") == []


class TestStats:
    def test_total(self, conn):
        upsert_games(conn, [make_game(url="u1"), make_game(url="u2")])
        result = stats(conn, "rathnakaragn")
        assert result["total"] == 2

    def test_win_loss_count(self, conn):
        upsert_games(conn, [
            make_game(url="u1",
                      white={"username": "rathnakaragn", "result": "win"},
                      black={"username": "opp", "result": "lose"}),
            make_game(url="u2",
                      white={"username": "opp", "result": "win"},
                      black={"username": "rathnakaragn", "result": "lose"}),
        ])
        result = stats(conn, "rathnakaragn")
        rapid = result["by_time_class"]["rapid"]
        assert rapid["win"] == 1
        assert rapid["lose"] == 1
        assert rapid["draw"] == 0

    def test_longest_streak(self, conn):
        # 3 wins then 2 losses
        games = [
            make_game(
                url=f"u{i}",
                end_time=1704067200 + i * 86400,
                white={"username": "rathnakaragn",
                       "result": "win" if i < 3 else "lose"},
                black={"username": "opp",
                       "result": "lose" if i < 3 else "win"},
            )
            for i in range(5)
        ]
        upsert_games(conn, games)
        result = stats(conn, "rathnakaragn")
        assert result["longest_streak"] == 3
        assert result["current_streak"] == 0

    def test_current_streak(self, conn):
        # 1 loss then 2 wins (current streak = 2)
        games = [
            make_game(
                url=f"u{i}",
                end_time=1704067200 + i * 86400,
                white={"username": "rathnakaragn",
                       "result": "lose" if i == 0 else "win"},
                black={"username": "opp",
                       "result": "win" if i == 0 else "lose"},
            )
            for i in range(3)
        ]
        upsert_games(conn, games)
        result = stats(conn, "rathnakaragn")
        assert result["current_streak"] == 2

    def test_top_openings(self, conn):
        upsert_games(conn, [
            make_game(url=f"u{i}",
                      pgn=f'[Opening "Sicilian Defense"]\n\n1. e4 c5 *')
            for i in range(3)
        ] + [
            make_game(url="u99",
                      pgn='[Opening "Ruy Lopez"]\n\n1. e4 e5 *')
        ])
        result = stats(conn, "rathnakaragn")
        openings = [o for o, _ in result["top_openings"]]
        assert openings[0] == "Sicilian Defense"
```

- [ ] **Step 2: Run tests to confirm they fail**

Run: `.venv/bin/python -m pytest tests/test_store.py::TestRawSql tests/test_store.py::TestStats -v`
Expected: `ImportError: cannot import name 'raw_sql'`

- [ ] **Step 3: Implement raw_sql and stats in src/store.py**

Append to `src/store.py`:

```python
def raw_sql(conn: duckdb.DuckDBPyConnection, sql: str) -> list[tuple]:
    return conn.execute(sql).fetchall()


def stats(conn: duckdb.DuckDBPyConnection, username: str) -> dict:
    total = conn.execute("SELECT COUNT(*) FROM games").fetchone()[0]

    rows = conn.execute("""
        SELECT time_class,
               CASE WHEN white = ? THEN white_result ELSE black_result END AS result,
               COUNT(*) AS cnt
        FROM games
        WHERE white = ? OR black = ?
        GROUP BY time_class, result
    """, [username, username, username]).fetchall()

    by_time_class: dict = {}
    for tc, result, cnt in rows:
        tc = tc or "unknown"
        if tc not in by_time_class:
            by_time_class[tc] = {"win": 0, "lose": 0, "draw": 0}
        key = result if result in ("win", "lose", "draw") else "draw"
        by_time_class[tc][key] += cnt

    top_openings = conn.execute("""
        SELECT opening, COUNT(*) AS cnt
        FROM games
        WHERE (white = ? OR black = ?) AND opening IS NOT NULL
        GROUP BY opening
        ORDER BY cnt DESC
        LIMIT 5
    """, [username, username]).fetchall()

    game_results = conn.execute("""
        SELECT CASE WHEN white = ? THEN white_result ELSE black_result END AS result
        FROM games
        WHERE white = ? OR black = ?
        ORDER BY end_time ASC
    """, [username, username, username]).fetchall()

    streak = 0
    longest_streak = 0
    for (result,) in game_results:
        if result == "win":
            streak += 1
            if streak > longest_streak:
                longest_streak = streak
        else:
            streak = 0
    current_streak = streak

    return {
        "total": total,
        "by_time_class": by_time_class,
        "top_openings": top_openings,
        "current_streak": current_streak,
        "longest_streak": longest_streak,
    }
```

- [ ] **Step 4: Run all store tests**

Run: `.venv/bin/python -m pytest tests/test_store.py -v`
Expected: All tests PASSED

- [ ] **Step 5: Commit**

```bash
git add src/store.py tests/test_store.py
git commit -m "feat: add raw_sql and stats to store"
```

---

## Task 6: cli.py — Refactor to Subcommands + sync

**Files:**
- Replace: `tests/test_cli.py`
- Replace: `src/cli.py`

- [ ] **Step 1: Write failing tests for sync subcommand**

Replace `tests/test_cli.py` with:

```python
"""Integration tests for CLI subcommands."""

from __future__ import annotations

import sys
from unittest.mock import patch, MagicMock

import pytest

from src.store import init_db


ARCHIVE_URL = "https://api.chess.com/pub/player/rathnakaragn/games/2024/01"

SAMPLE_GAME = {
    "url": "https://chess.com/game/1",
    "pgn": '[ECO "B20"]\n[Opening "Sicilian Defense"]\n\n1. e4 c5 *',
    "time_class": "rapid",
    "time_control": "600",
    "end_time": 1704067200,
    "white": {"username": "rathnakaragn", "result": "win"},
    "black": {"username": "opponent", "result": "lose"},
    "rated": True,
    "fen": "",
}


def run_cli(*args):
    with patch("sys.argv", ["prog"] + list(args)):
        from src.cli import main
        main()


class TestSync:
    def test_creates_db_and_inserts_games(self, tmp_path):
        db_path = str(tmp_path / "test.duckdb")
        with patch("src.cli._api_get", side_effect=[
            {"archives": [ARCHIVE_URL]},
            {"games": [SAMPLE_GAME]},
        ]):
            run_cli("sync", "rathnakaragn", "--db", db_path)

        conn = init_db(db_path)
        count = conn.execute("SELECT COUNT(*) FROM games").fetchone()[0]
        assert count == 1

    def test_skips_already_synced_archive(self, tmp_path):
        db_path = str(tmp_path / "test.duckdb")
        api_calls = []

        def fake_api(url, retries=3):
            api_calls.append(url)
            if "archives" in url:
                return {"archives": [ARCHIVE_URL]}
            return {"games": [SAMPLE_GAME]}

        # First sync
        with patch("src.cli._api_get", side_effect=fake_api):
            run_cli("sync", "rathnakaragn", "--db", db_path)

        api_calls.clear()

        # Second sync — archive already cached, only archive list fetched
        with patch("src.cli._api_get", side_effect=fake_api):
            run_cli("sync", "rathnakaragn", "--db", db_path)

        assert ARCHIVE_URL not in api_calls

    def test_default_db_path_uses_username(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        with patch("src.cli._api_get", side_effect=[
            {"archives": [ARCHIVE_URL]},
            {"games": [SAMPLE_GAME]},
        ]):
            run_cli("sync", "rathnakaragn")

        assert (tmp_path / "data" / "rathnakaragn.duckdb").exists()
```

- [ ] **Step 2: Run tests to confirm they fail**

Run: `.venv/bin/python -m pytest tests/test_cli.py::TestSync -v`
Expected: `error: argument command: invalid choice` or `AttributeError` (old CLI has no subcommands)

- [ ] **Step 3: Replace src/cli.py with subcommand-based CLI**

Replace `src/cli.py` with:

```python
"""Chess.com Game Downloader — subcommand CLI."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import duckdb

from src.downloader import _api_get, API_BASE
from src import store

DEFAULT_USERNAME = "rathnakaragn"


def _default_db(username: str) -> str:
    return f"./data/{username}.duckdb"


def _validate_date(value: str) -> str:
    if not re.fullmatch(r"\d{8}", value):
        raise argparse.ArgumentTypeError(
            f"invalid date '{value}': expected YYYYMMDD format"
        )
    return value


def _open_existing_db(db_path: str) -> duckdb.DuckDBPyConnection:
    if not Path(db_path).exists():
        print(f"Error: database not found at {db_path}. Run 'sync' first.",
              file=sys.stderr)
        sys.exit(1)
    return store.init_db(db_path)


def _archive_ym(url: str) -> str:
    parts = url.rstrip("/").split("/")
    return parts[-2] + parts[-1]  # e.g. "202401"


def cmd_sync(args: argparse.Namespace) -> None:
    import time as _time
    username = args.username
    db_path = args.db or _default_db(username)
    conn = store.init_db(db_path)

    import urllib.error
    try:
        archives_data = _api_get(f"{API_BASE}/{username}/games/archives")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            print(f"Error: Player '{username}' not found on chess.com",
                  file=sys.stderr)
            sys.exit(1)
        raise

    archive_urls = archives_data.get("archives", [])
    synced = store.get_synced_archives(conn)

    t = _time.gmtime()
    current_ym = f"{t.tm_year}{t.tm_mon:02d}"

    since_ym = args.since[:6] if args.since else None
    until_ym = args.until[:6] if args.until else None

    to_fetch = []
    for url in archive_urls:
        ym = _archive_ym(url)
        if since_ym and ym < since_ym:
            continue
        if until_ym and ym > until_ym:
            continue
        if url in synced and ym != current_ym:
            continue
        to_fetch.append(url)

    skip_count = len(archive_urls) - len(to_fetch)
    print(f"Syncing {len(to_fetch)} archives (skipping {skip_count} cached)...",
          file=sys.stderr)

    total_new = 0
    for i, url in enumerate(to_fetch, 1):
        ym = _archive_ym(url)
        data = _api_get(url)
        games = data.get("games", [])
        new = store.upsert_games(conn, games)
        total_new += new
        if ym != current_ym:
            store.mark_archive_synced(conn, url)
        print(f"  [{i}/{len(to_fetch)}] {ym[:4]}/{ym[4:]}: {len(games)} games ({new} new)",
              file=sys.stderr)

    print(f"Sync complete. {total_new} new games added.", file=sys.stderr)


def cmd_export(args: argparse.Namespace) -> None:
    username = args.username
    db_path = args.db or _default_db(username)
    conn = _open_existing_db(db_path)

    games = store.query_games(conn, args.time_class, args.since, args.until, args.n)
    if not games:
        print("No games match the given filters.", file=sys.stderr)
        return

    pgn_parts = [g["pgn"].strip() for g in games if g.get("pgn")]
    pgn_text = "\n\n".join(pgn_parts) + "\n"

    if args.output:
        with open(args.output, "w") as f:
            f.write(pgn_text)
        print(f"{len(pgn_parts)} games written to {args.output}", file=sys.stderr)
    else:
        print(pgn_text)


def cmd_query(args: argparse.Namespace) -> None:
    conn = _open_existing_db(args.db)
    try:
        rows = store.raw_sql(conn, args.sql)
    except duckdb.Error as e:
        print(f"Query error: {e}", file=sys.stderr)
        sys.exit(1)
    for row in rows:
        print("\t".join(str(v) for v in row))


def cmd_stats(args: argparse.Namespace) -> None:
    username = args.username
    db_path = args.db or _default_db(username)
    conn = _open_existing_db(db_path)
    result = store.stats(conn, username)

    print(f"\n=== Stats for {username} ===")
    print(f"Total games: {result['total']}\n")
    for tc, counts in sorted(result["by_time_class"].items()):
        total_tc = sum(counts.values())
        win_pct = counts["win"] / total_tc * 100 if total_tc else 0
        print(f"{tc:10s}  W:{counts['win']}  L:{counts['lose']}  "
              f"D:{counts['draw']}  ({win_pct:.0f}% win)")
    if result["top_openings"]:
        print("\nTop openings:")
        for opening, cnt in result["top_openings"]:
            print(f"  {opening}: {cnt}")
    print(f"\nCurrent win streak : {result['current_streak']}")
    print(f"Longest win streak : {result['longest_streak']}")


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Chess.com game downloader and analyzer."
    )
    sub = ap.add_subparsers(dest="command", required=True)

    # sync
    p_sync = sub.add_parser("sync", help="Download and store games from chess.com")
    p_sync.add_argument("username", nargs="?", default=DEFAULT_USERNAME)
    p_sync.add_argument("--db", help="Path to DuckDB file (default: ./data/{username}.duckdb)")
    p_sync.add_argument("--since", type=_validate_date,
                        help="Only sync archives on or after YYYYMMDD")
    p_sync.add_argument("--until", type=_validate_date,
                        help="Only sync archives on or before YYYYMMDD")
    p_sync.set_defaults(func=cmd_sync)

    # export
    p_export = sub.add_parser("export", help="Export games from DB as PGN")
    p_export.add_argument("username", nargs="?", default=DEFAULT_USERNAME)
    p_export.add_argument("--db", help="Path to DuckDB file")
    p_export.add_argument("--time-class", dest="time_class",
                          choices=["bullet", "blitz", "rapid", "daily"])
    p_export.add_argument("--since", type=_validate_date)
    p_export.add_argument("--until", type=_validate_date)
    p_export.add_argument("-n", type=int, metavar="N",
                          help="Only export last N games")
    p_export.add_argument("-o", "--output", help="Write PGN to file instead of stdout")
    p_export.set_defaults(func=cmd_export)

    # query
    p_query = sub.add_parser("query", help="Run raw SQL against the DB")
    p_query.add_argument("sql", help="SQL query string")
    p_query.add_argument("--db", required=True, help="Path to DuckDB file")
    p_query.set_defaults(func=cmd_query)

    # stats
    p_stats = sub.add_parser("stats", help="Show game statistics dashboard")
    p_stats.add_argument("username", nargs="?", default=DEFAULT_USERNAME)
    p_stats.add_argument("--db", help="Path to DuckDB file")
    p_stats.set_defaults(func=cmd_stats)

    args = ap.parse_args()
    args.func(args)
```

- [ ] **Step 4: Run sync tests**

Run: `.venv/bin/python -m pytest tests/test_cli.py::TestSync -v`
Expected: 3 tests PASSED

- [ ] **Step 5: Commit**

```bash
git add src/cli.py tests/test_cli.py
git commit -m "feat: refactor cli to subcommands, implement sync"
```

---

## Task 7: cli.py — export command tests

**Files:**
- Modify: `tests/test_cli.py` (append)

- [ ] **Step 1: Write failing tests for export subcommand**

Append to `tests/test_cli.py`:

```python
class TestExport:
    def _seed_db(self, db_path):
        conn = init_db(db_path)
        from src.store import upsert_games
        upsert_games(conn, [SAMPLE_GAME])
        conn.close()

    def test_export_to_file(self, tmp_path):
        db_path = str(tmp_path / "test.duckdb")
        self._seed_db(db_path)
        out = tmp_path / "out.pgn"
        run_cli("export", "--db", db_path, "-o", str(out))
        assert "Sicilian Defense" in out.read_text()

    def test_export_to_stdout(self, tmp_path, capsys):
        db_path = str(tmp_path / "test.duckdb")
        self._seed_db(db_path)
        run_cli("export", "--db", db_path)
        assert "Sicilian Defense" in capsys.readouterr().out

    def test_export_filter_time_class(self, tmp_path):
        db_path = str(tmp_path / "test.duckdb")
        conn = init_db(db_path)
        from src.store import upsert_games
        upsert_games(conn, [
            SAMPLE_GAME,
            {**SAMPLE_GAME, "url": "u2", "time_class": "blitz"},
        ])
        conn.close()
        out = tmp_path / "rapid.pgn"
        run_cli("export", "--db", db_path, "--time-class", "blitz", "-o", str(out))
        content = out.read_text()
        assert content.count("Sicilian Defense") == 1

    def test_export_missing_db_exits(self, tmp_path):
        with pytest.raises(SystemExit) as exc:
            run_cli("export", "--db", str(tmp_path / "missing.duckdb"))
        assert exc.value.code == 1
```

- [ ] **Step 2: Run tests to confirm they pass (export is already implemented)**

Run: `.venv/bin/python -m pytest tests/test_cli.py::TestExport -v`
Expected: 4 tests PASSED

- [ ] **Step 3: Commit**

```bash
git add tests/test_cli.py
git commit -m "test: add export subcommand tests"
```

---

## Task 8: cli.py — query + stats command tests

**Files:**
- Modify: `tests/test_cli.py` (append)

- [ ] **Step 1: Write failing tests for query and stats subcommands**

Append to `tests/test_cli.py`:

```python
class TestQuery:
    def test_query_prints_rows(self, tmp_path, capsys):
        db_path = str(tmp_path / "test.duckdb")
        conn = init_db(db_path)
        from src.store import upsert_games
        upsert_games(conn, [SAMPLE_GAME])
        conn.close()
        run_cli("query", "SELECT url FROM games", "--db", db_path)
        out = capsys.readouterr().out
        assert "https://chess.com/game/1" in out

    def test_query_invalid_sql_exits(self, tmp_path):
        db_path = str(tmp_path / "test.duckdb")
        init_db(db_path)
        with pytest.raises(SystemExit) as exc:
            run_cli("query", "SELECT FROM NOWHERE", "--db", db_path)
        assert exc.value.code == 1


class TestStats:
    def test_stats_prints_total(self, tmp_path, capsys):
        db_path = str(tmp_path / "test.duckdb")
        conn = init_db(db_path)
        from src.store import upsert_games
        upsert_games(conn, [SAMPLE_GAME])
        conn.close()
        run_cli("stats", "rathnakaragn", "--db", db_path)
        out = capsys.readouterr().out
        assert "Total games: 1" in out

    def test_stats_missing_db_exits(self, tmp_path):
        with pytest.raises(SystemExit) as exc:
            run_cli("stats", "rathnakaragn", "--db", str(tmp_path / "missing.duckdb"))
        assert exc.value.code == 1
```

- [ ] **Step 2: Run tests to confirm they pass (query + stats already implemented)**

Run: `.venv/bin/python -m pytest tests/test_cli.py::TestQuery tests/test_cli.py::TestStats -v`
Expected: 4 tests PASSED

- [ ] **Step 3: Commit**

```bash
git add tests/test_cli.py
git commit -m "test: add query and stats subcommand tests"
```

---

## Task 9: Cleanup and Full Test Suite

**Files:**
- Delete: `tests/test_filter.py`

- [ ] **Step 1: Delete test_filter.py**

```bash
git rm tests/test_filter.py
```

- [ ] **Step 2: Run full test suite**

Run: `.venv/bin/python -m pytest tests/ -v`
Expected: All tests PASSED, no failures

- [ ] **Step 3: Commit**

```bash
git commit -m "chore: remove test_filter.py, filtering now done in DuckDB"
```

---

## Verification

After all tasks complete, verify the full workflow manually:

```bash
# Sync games to DB
.venv/bin/python main.py sync rathnakaragn --db data/rathnakaragn.duckdb

# Export rapid games from the last year
.venv/bin/python main.py export rathnakaragn --time-class rapid --since 20250101 -o rapid_2025.pgn

# Run a SQL query
.venv/bin/python main.py query "SELECT white_result, COUNT(*) FROM games GROUP BY white_result" --db data/rathnakaragn.duckdb

# Show stats dashboard
.venv/bin/python main.py stats rathnakaragn
```
