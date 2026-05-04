# Chess PGN Project Improvements Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix 8 identified issues: ECOUrl opening tests, new schema columns (elo/moves/duration/termination), automatic DB migrations, backfill subcommand, rating subcommand, opponent subcommand, enhanced stats (trend/time-of-day/game-phase), and portable MCP path.

**Architecture:** All changes are additive — new columns via `_migrate_db()` called from `init_db()`, new store functions, new CLI subcommands, enhanced stats output. No breaking changes to existing API surface.

**Tech Stack:** Python 3.11+, DuckDB, argparse, pytest, uvx/mcp-server-duckdb

---

## File Map

```
src/store.py          — add parsers, _migrate_db, backfill_derived_columns,
                        rating_history, opponent_stats; extend upsert_games, stats
src/cli.py            — add cmd_backfill, cmd_rating, cmd_opponent; update cmd_stats
tests/test_store.py   — update make_game, fix ECOUrl tests, add tests for new functions
scripts/mcp_chess.sh  — NEW: portable wrapper for mcp-server-duckdb
.mcp.json             — update to use wrapper script instead of absolute path
```

---

## Task 1: Fix ECOUrl Opening Tests

**Files:**
- Modify: `tests/test_store.py:8-21` (make_game), `:42-49` (test_inserts_game), `:74-78` (test_eco_missing_from_pgn), `:215-227` (test_top_openings)

**Context:** `_parse_opening()` was updated to read `ECOUrl` tags (chess.com's actual format) with fallback to `Opening` tag. The tests still use `[Opening "Sicilian Defense"]` which only exercises the fallback. We need tests that cover the primary `ECOUrl` path. The existing code already works — this task only fixes test coverage.

- [ ] **Step 1: Run current tests to confirm baseline passes**

```bash
.venv/bin/python -m pytest tests/test_store.py -v 2>&1 | tail -20
```

Expected: All tests pass.

- [ ] **Step 2: Update `make_game()` to use chess.com PGN format with ECOUrl**

In `tests/test_store.py`, replace the `make_game` function (lines 8–21):

```python
def make_game(**overrides):
    g = {
        "url": "https://chess.com/game/1",
        "pgn": (
            '[ECO "B20"]\n'
            '[ECOUrl "https://www.chess.com/openings/Sicilian-Defense"]\n'
            '[WhiteElo "1200"]\n'
            '[BlackElo "1100"]\n'
            '[UTCDate "2024.01.01"]\n'
            '[StartTime "00:00:00"]\n'
            '[EndDate "2024.01.01"]\n'
            '[EndTime "00:15:00"]\n'
            '[Termination "rathnakaragn won by resignation"]\n'
            '\n'
            '1. e4 c5 2. Nf3 *'
        ),
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
```

- [ ] **Step 3: Update `test_inserts_game` to verify ECOUrl parsing**

Replace the `test_inserts_game` method in `TestUpsertGames`:

```python
def test_inserts_game(self, conn):
    count = upsert_games(conn, [make_game()])
    assert count == 1
    row = conn.execute("SELECT url, white, eco, opening FROM games").fetchone()
    assert row[0] == "https://chess.com/game/1"
    assert row[1] == "rathnakaragn"
    assert row[2] == "B20"
    assert row[3] == "Sicilian Defense"  # parsed from ECOUrl slug
```

- [ ] **Step 4: Add ECOUrl and fallback tests to `TestUpsertGames`**

Add after `test_eco_missing_from_pgn`:

```python
def test_eco_url_parsed_as_opening(self, conn):
    upsert_games(conn, [make_game(
        pgn='[ECO "C41"]\n[ECOUrl "https://www.chess.com/openings/Philidor-Defense"]\n\n1. e4 e5 *'
    )])
    row = conn.execute("SELECT opening FROM games").fetchone()
    assert row[0] == "Philidor Defense"

def test_opening_tag_fallback(self, conn):
    upsert_games(conn, [make_game(
        pgn='[ECO "B20"]\n[Opening "Sicilian Defense"]\n\n1. e4 c5 *'
    )])
    row = conn.execute("SELECT opening FROM games").fetchone()
    assert row[0] == "Sicilian Defense"
```

- [ ] **Step 5: Update `test_top_openings` in `TestStats` to use ECOUrl format**

Replace the `test_top_openings` method:

```python
def test_top_openings(self, conn):
    upsert_games(conn, [
        make_game(url=f"u{i}",
                  pgn='[ECOUrl "https://www.chess.com/openings/Sicilian-Defense"]\n\n1. e4 c5 *')
        for i in range(3)
    ] + [
        make_game(url="u99",
                  pgn='[ECOUrl "https://www.chess.com/openings/Ruy-Lopez"]\n\n1. e4 e5 *')
    ])
    result = stats(conn, "rathnakaragn")
    openings = [o for o, _ in result["top_openings"]]
    assert openings[0] == "Sicilian Defense"
```

- [ ] **Step 6: Run tests to confirm all pass**

```bash
.venv/bin/python -m pytest tests/test_store.py -v 2>&1 | tail -20
```

Expected: All tests pass (including new ECOUrl tests).

- [ ] **Step 7: Commit**

```bash
git add tests/test_store.py
git commit -m "test: update store tests to use ECOUrl format matching chess.com PGNs"
```

---

## Task 2: Schema Migration + New Columns + Updated upsert_games

**Files:**
- Modify: `src/store.py`
- Modify: `tests/test_store.py`

**Context:** Add 5 new columns to the `games` table: `white_elo`, `black_elo`, `move_count`, `game_duration_secs`, `termination`. A `_migrate_db()` function called from `init_db()` adds missing columns to existing DBs via `ALTER TABLE`. `upsert_games()` is updated to populate them. All tests must use `:memory:` so no real DB is touched.

New columns:
- `white_elo INTEGER` — from `[WhiteElo "1200"]` PGN header
- `black_elo INTEGER` — from `[BlackElo "1100"]` PGN header
- `move_count INTEGER` — last move number in game (e.g. `30` means 30 full moves played)
- `game_duration_secs INTEGER` — seconds between `[StartTime]` and `[EndTime]` PGN headers
- `termination TEXT` — from `[Termination "..."]` PGN header, e.g. `"rathnakaragn won by resignation"`

- [ ] **Step 1: Write failing tests for new columns**

Add to `tests/test_store.py` in `TestUpsertGames`:

```python
def test_new_columns_populated(self, conn):
    upsert_games(conn, [make_game()])
    row = conn.execute(
        "SELECT white_elo, black_elo, move_count, game_duration_secs, termination FROM games"
    ).fetchone()
    assert row[0] == 1200   # white_elo
    assert row[1] == 1100   # black_elo
    assert row[2] == 2      # move_count: last move number is "2. Nf3"
    assert row[3] == 900    # game_duration_secs: 00:00:00 to 00:15:00 = 900s
    assert row[4] == "rathnakaragn won by resignation"
```

- [ ] **Step 2: Run test to confirm it fails**

```bash
.venv/bin/python -m pytest tests/test_store.py::TestUpsertGames::test_new_columns_populated -v
```

Expected: FAIL — column `white_elo` does not exist.

- [ ] **Step 3: Add helper parsers to `src/store.py`**

Add after `_parse_opening()`:

```python
def _parse_elo(pgn: str | None, color: str) -> int | None:
    val = _parse_pgn_header(pgn, f"{color}Elo")
    try:
        return int(val) if val else None
    except ValueError:
        return None


def _parse_move_count(pgn: str | None) -> int | None:
    if not pgn:
        return None
    parts = re.split(r'\n\n', pgn, maxsplit=1)
    moves = parts[1] if len(parts) > 1 else parts[0]
    numbers = re.findall(r'\b(\d+)\.\s', moves)
    return int(numbers[-1]) if numbers else None


def _parse_duration_secs(pgn: str | None) -> int | None:
    start_date = _parse_pgn_header(pgn, "UTCDate")
    start_time = _parse_pgn_header(pgn, "StartTime")
    end_date   = _parse_pgn_header(pgn, "EndDate")
    end_time   = _parse_pgn_header(pgn, "EndTime")
    if not all([start_date, start_time, end_date, end_time]):
        return None
    try:
        fmt = "%Y.%m.%d %H:%M:%S"
        start = datetime.datetime.strptime(f"{start_date} {start_time}", fmt)
        end   = datetime.datetime.strptime(f"{end_date} {end_time}", fmt)
        secs = int((end - start).total_seconds())
        return secs if secs >= 0 else None
    except ValueError:
        return None


def _migrate_db(conn: duckdb.DuckDBPyConnection) -> None:
    existing = {r[0] for r in conn.execute("DESCRIBE games").fetchall()}
    for col, typ in [
        ("white_elo",          "INTEGER"),
        ("black_elo",          "INTEGER"),
        ("move_count",         "INTEGER"),
        ("game_duration_secs", "INTEGER"),
        ("termination",        "TEXT"),
    ]:
        if col not in existing:
            conn.execute(f"ALTER TABLE games ADD COLUMN {col} {typ}")
```

- [ ] **Step 4: Call `_migrate_db` at end of `init_db()`**

In `init_db()`, add before `return conn`:

```python
    _migrate_db(conn)
    return conn
```

The full `init_db` function becomes:

```python
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
    _migrate_db(conn)
    return conn
```

- [ ] **Step 5: Update `upsert_games` to populate new columns**

Replace the entire `upsert_games` function:

```python
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
            _parse_opening(pgn),
            _parse_elo(pgn, "White"),
            _parse_elo(pgn, "Black"),
            _parse_move_count(pgn),
            _parse_duration_secs(pgn),
            _parse_pgn_header(pgn, "Termination"),
        ))
    if not rows:
        return 0
    before = conn.execute("SELECT COUNT(*) FROM games").fetchone()[0]
    conn.executemany("""
        INSERT INTO games VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT (url) DO NOTHING
    """, rows)
    after = conn.execute("SELECT COUNT(*) FROM games").fetchone()[0]
    return after - before
```

- [ ] **Step 6: Run tests to confirm all pass**

```bash
.venv/bin/python -m pytest tests/test_store.py -v 2>&1 | tail -25
```

Expected: All tests pass including `test_new_columns_populated`.

- [ ] **Step 7: Commit**

```bash
git add src/store.py tests/test_store.py
git commit -m "feat: add white_elo, black_elo, move_count, game_duration_secs, termination columns with auto-migration"
```

---

## Task 3: Backfill Subcommand

**Files:**
- Modify: `src/store.py`
- Modify: `src/cli.py`
- Modify: `tests/test_store.py`

**Context:** Existing games in the DB have `NULL` in the new columns. `backfill_derived_columns()` re-parses PGNs for rows that have any NULL derived column and updates them. The `backfill` CLI subcommand runs this and reports how many rows were updated. This also fixes the `opening` column for games that had it NULL before the ECOUrl fix.

- [ ] **Step 1: Write failing test for `backfill_derived_columns`**

Add import at top of `tests/test_store.py`:

```python
from src.store import (init_db, upsert_games, get_synced_archives,
                        mark_archive_synced, query_games, raw_sql, stats,
                        backfill_derived_columns)
```

Add at end of `tests/test_store.py`:

```python
class TestBackfill:
    def test_backfills_nulled_columns(self, conn):
        upsert_games(conn, [make_game()])
        # Simulate old rows with NULLs in derived columns
        conn.execute("UPDATE games SET white_elo = NULL, move_count = NULL, termination = NULL")
        updated = backfill_derived_columns(conn)
        assert updated == 1
        row = conn.execute("SELECT white_elo, move_count, termination FROM games").fetchone()
        assert row[0] == 1200
        assert row[1] == 2
        assert row[2] == "rathnakaragn won by resignation"

    def test_skips_complete_rows(self, conn):
        upsert_games(conn, [make_game()])
        # All derived columns already populated — nothing to do
        updated = backfill_derived_columns(conn)
        assert updated == 0

    def test_returns_zero_when_no_games(self, conn):
        updated = backfill_derived_columns(conn)
        assert updated == 0
```

- [ ] **Step 2: Run test to confirm it fails**

```bash
.venv/bin/python -m pytest tests/test_store.py::TestBackfill -v
```

Expected: FAIL — `cannot import name 'backfill_derived_columns'`.

- [ ] **Step 3: Add `backfill_derived_columns` to `src/store.py`**

Add after `mark_archive_synced`:

```python
def backfill_derived_columns(conn: duckdb.DuckDBPyConnection) -> int:
    rows = conn.execute("""
        SELECT url, pgn FROM games
        WHERE pgn IS NOT NULL
          AND (white_elo IS NULL OR black_elo IS NULL OR move_count IS NULL
               OR game_duration_secs IS NULL OR termination IS NULL OR opening IS NULL)
    """).fetchall()
    if not rows:
        return 0
    updates = [
        (
            _parse_elo(pgn, "White"),
            _parse_elo(pgn, "Black"),
            _parse_move_count(pgn),
            _parse_duration_secs(pgn),
            _parse_pgn_header(pgn, "Termination"),
            _parse_opening(pgn),
            url,
        )
        for url, pgn in rows
    ]
    conn.executemany("""
        UPDATE games SET
            white_elo = ?, black_elo = ?, move_count = ?,
            game_duration_secs = ?, termination = ?, opening = ?
        WHERE url = ?
    """, updates)
    return len(updates)
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
.venv/bin/python -m pytest tests/test_store.py::TestBackfill -v
```

Expected: All 3 tests pass.

- [ ] **Step 5: Add `cmd_backfill` to `src/cli.py`**

Add after `cmd_sync`:

```python
def cmd_backfill(args: argparse.Namespace) -> None:
    username = args.username
    db_path = args.db or _default_db(username)
    conn = _open_existing_db(db_path)
    try:
        print("Backfilling derived columns from stored PGNs...", file=sys.stderr)
        updated = store.backfill_derived_columns(conn)
        print(f"Done. {updated} rows updated.", file=sys.stderr)
    finally:
        conn.close()
```

- [ ] **Step 6: Register `backfill` subcommand in `main()` in `src/cli.py`**

In `main()`, after the `stats` subcommand block and before `args = ap.parse_args()`:

```python
    # backfill
    p_backfill = sub.add_parser("backfill", help="Re-parse PGNs to fill missing derived columns")
    p_backfill.add_argument("username", nargs="?", default=DEFAULT_USERNAME)
    p_backfill.add_argument("--db", help="Path to DuckDB file")
    p_backfill.set_defaults(func=cmd_backfill)
```

- [ ] **Step 7: Run full test suite**

```bash
.venv/bin/python -m pytest tests/ -v 2>&1 | tail -20
```

Expected: All tests pass.

- [ ] **Step 8: Run backfill against real DB to verify**

```bash
python main.py backfill rathnakaragn
```

Expected output (stderr): `Backfilling derived columns from stored PGNs... Done. 9151 rows updated.`

- [ ] **Step 9: Commit**

```bash
git add src/store.py src/cli.py tests/test_store.py
git commit -m "feat: add backfill subcommand to re-parse PGNs for new derived columns"
```

---

## Task 4: Rating Subcommand

**Files:**
- Modify: `src/store.py`
- Modify: `src/cli.py`
- Modify: `tests/test_store.py`

**Context:** `rating_history()` queries the most recent game per time class to get current Elo, and the first game of the current calendar month to compute delta. `cmd_rating` prints the table. Elo values come from the new `white_elo`/`black_elo` columns populated in Task 2.

- [ ] **Step 1: Write failing tests for `rating_history`**

Add import line update at top of `tests/test_store.py`:

```python
from src.store import (init_db, upsert_games, get_synced_archives,
                        mark_archive_synced, query_games, raw_sql, stats,
                        backfill_derived_columns, rating_history)
```

Add at end of `tests/test_store.py`:

```python
class TestRatingHistory:
    def test_returns_current_elo_per_format(self, conn):
        upsert_games(conn, [make_game()])  # rapid, white_elo=1200
        result = rating_history(conn, "rathnakaragn")
        assert "rapid" in result
        assert result["rapid"]["current"] == 1200

    def test_delta_is_none_when_no_prior_game_this_month(self, conn):
        # make_game end_time = 2024-01-01, which is not current month (2026-05)
        upsert_games(conn, [make_game()])
        result = rating_history(conn, "rathnakaragn")
        assert result["rapid"]["delta"] is None

    def test_empty_when_no_elo_in_pgn(self, conn):
        upsert_games(conn, [make_game(pgn="1. e4 *")])
        result = rating_history(conn, "rathnakaragn")
        assert result == {}
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
.venv/bin/python -m pytest tests/test_store.py::TestRatingHistory -v
```

Expected: FAIL — `cannot import name 'rating_history'`.

- [ ] **Step 3: Add `rating_history` to `src/store.py`**

Add after `backfill_derived_columns`:

```python
def rating_history(conn: duckdb.DuckDBPyConnection, username: str) -> dict:
    rows = conn.execute("""
        SELECT time_class,
               CASE WHEN white = ? THEN white_elo ELSE black_elo END AS elo
        FROM games
        WHERE (white = ? OR black = ?)
          AND CASE WHEN white = ? THEN white_elo ELSE black_elo END IS NOT NULL
          AND end_time IS NOT NULL
        QUALIFY ROW_NUMBER() OVER (PARTITION BY time_class ORDER BY end_time DESC) = 1
    """, [username] * 4).fetchall()
    if not rows:
        return {}
    current = {tc: elo for tc, elo in rows}

    t = time.gmtime()
    month_start = int(datetime.datetime(t.tm_year, t.tm_mon, 1,
                                        tzinfo=datetime.timezone.utc).timestamp())
    first_rows = conn.execute("""
        SELECT time_class,
               CASE WHEN white = ? THEN white_elo ELSE black_elo END AS elo
        FROM games
        WHERE (white = ? OR black = ?) AND end_time >= ?
          AND CASE WHEN white = ? THEN white_elo ELSE black_elo END IS NOT NULL
        QUALIFY ROW_NUMBER() OVER (PARTITION BY time_class ORDER BY end_time ASC) = 1
    """, [username, username, username, month_start, username]).fetchall()
    first_of_month = {tc: elo for tc, elo in first_rows}

    result = {}
    for tc, elo in current.items():
        first_elo = first_of_month.get(tc)
        delta = (elo - first_elo) if first_elo is not None else None
        result[tc] = {"current": elo, "delta": delta}
    return result
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
.venv/bin/python -m pytest tests/test_store.py::TestRatingHistory -v
```

Expected: All 3 tests pass.

- [ ] **Step 5: Add `cmd_rating` to `src/cli.py`**

Add after `cmd_backfill`:

```python
def cmd_rating(args: argparse.Namespace) -> None:
    username = args.username
    db_path = args.db or _default_db(username)
    conn = _open_existing_db(db_path)
    try:
        result = store.rating_history(conn, username)
        if not result:
            print("No rating data found. Run 'backfill' first.", file=sys.stderr)
            return
        print(f"\n=== Rating for {username} ===\n")
        for tc, data in sorted(result.items()):
            delta = data["delta"]
            if delta is not None:
                sign = "+" if delta >= 0 else ""
                delta_str = f"  ({sign}{delta} this month)"
            else:
                delta_str = ""
            print(f"{tc:8s}  {data['current']}{delta_str}")
    finally:
        conn.close()
```

- [ ] **Step 6: Register `rating` subcommand in `main()` in `src/cli.py`**

After the `backfill` subcommand block:

```python
    # rating
    p_rating = sub.add_parser("rating", help="Show current rating and monthly delta per format")
    p_rating.add_argument("username", nargs="?", default=DEFAULT_USERNAME)
    p_rating.add_argument("--db", help="Path to DuckDB file")
    p_rating.set_defaults(func=cmd_rating)
```

- [ ] **Step 7: Run full test suite**

```bash
.venv/bin/python -m pytest tests/ -v 2>&1 | tail -20
```

Expected: All tests pass.

- [ ] **Step 8: Smoke-test against real DB**

```bash
python main.py rating rathnakaragn
```

Expected output (example):
```
=== Rating for rathnakaragn ===

blitz    582  (+12 this month)
bullet   264
daily    714
rapid    751  (-3 this month)
```

- [ ] **Step 9: Commit**

```bash
git add src/store.py src/cli.py tests/test_store.py
git commit -m "feat: add rating subcommand with current Elo and monthly delta per format"
```

---

## Task 5: Opponent Subcommand

**Files:**
- Modify: `src/store.py`
- Modify: `src/cli.py`
- Modify: `tests/test_store.py`

**Context:** `opponent_stats()` queries W/L/D record against a specific opponent, broken down by time class, with top 5 openings. `cmd_opponent` prints the formatted dashboard. The opponent name is a positional arg.

- [ ] **Step 1: Write failing tests for `opponent_stats`**

Add import at top of `tests/test_store.py`:

```python
from src.store import (init_db, upsert_games, get_synced_archives,
                        mark_archive_synced, query_games, raw_sql, stats,
                        backfill_derived_columns, rating_history, opponent_stats)
```

Add at end of `tests/test_store.py`:

```python
class TestOpponentStats:
    def test_returns_wld_record(self, conn):
        upsert_games(conn, [
            make_game(url="u1",
                      white={"username": "rathnakaragn", "result": "win"},
                      black={"username": "fischer", "result": "lose"}),
            make_game(url="u2",
                      white={"username": "fischer", "result": "win"},
                      black={"username": "rathnakaragn", "result": "lose"}),
        ])
        result = opponent_stats(conn, "rathnakaragn", "fischer")
        assert result["total"] == 2
        assert result["wins"] == 1
        assert result["losses"] == 1
        assert result["draws"] == 0
        assert result["win_pct"] == 50.0

    def test_by_time_class(self, conn):
        upsert_games(conn, [
            make_game(url="u1", time_class="rapid",
                      white={"username": "rathnakaragn", "result": "win"},
                      black={"username": "fischer", "result": "lose"}),
            make_game(url="u2", time_class="blitz",
                      white={"username": "rathnakaragn", "result": "lose"},
                      black={"username": "fischer", "result": "win"}),
        ])
        result = opponent_stats(conn, "rathnakaragn", "fischer")
        assert result["by_time_class"]["rapid"]["win"] == 1
        assert result["by_time_class"]["blitz"]["lose"] == 1

    def test_no_games_returns_zero(self, conn):
        result = opponent_stats(conn, "rathnakaragn", "kasparov")
        assert result["total"] == 0
        assert result["win_pct"] == 0.0
        assert result["by_time_class"] == {}
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
.venv/bin/python -m pytest tests/test_store.py::TestOpponentStats -v
```

Expected: FAIL — `cannot import name 'opponent_stats'`.

- [ ] **Step 3: Add `opponent_stats` to `src/store.py`**

Add after `rating_history`:

```python
def opponent_stats(conn: duckdb.DuckDBPyConnection, username: str, opponent: str) -> dict:
    rows = conn.execute("""
        SELECT time_class,
               CASE WHEN white = ? THEN white_result ELSE black_result END AS result,
               COUNT(*) AS cnt
        FROM games
        WHERE (white = ? AND black = ?) OR (black = ? AND white = ?)
        GROUP BY time_class, result
    """, [username, username, opponent, username, opponent]).fetchall()

    total = sum(cnt for _, _, cnt in rows)
    wins = sum(cnt for _, r, cnt in rows if r == "win")
    losses = sum(cnt for _, r, cnt in rows if r in _LOSS_RESULTS)
    draws = total - wins - losses

    by_time_class: dict = {}
    for tc, result, cnt in rows:
        tc = tc or "unknown"
        if tc not in by_time_class:
            by_time_class[tc] = {"win": 0, "lose": 0, "draw": 0}
        key = "win" if result == "win" else ("lose" if result in _LOSS_RESULTS else "draw")
        by_time_class[tc][key] += cnt

    top_openings = conn.execute("""
        SELECT opening, COUNT(*) AS cnt
        FROM games
        WHERE ((white = ? AND black = ?) OR (black = ? AND white = ?))
          AND opening IS NOT NULL
        GROUP BY opening ORDER BY cnt DESC LIMIT 5
    """, [username, opponent, username, opponent]).fetchall()

    return {
        "total": total,
        "wins": wins,
        "losses": losses,
        "draws": draws,
        "win_pct": wins / total * 100 if total else 0.0,
        "by_time_class": by_time_class,
        "top_openings": top_openings,
    }
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
.venv/bin/python -m pytest tests/test_store.py::TestOpponentStats -v
```

Expected: All 3 tests pass.

- [ ] **Step 5: Add `cmd_opponent` to `src/cli.py`**

Add after `cmd_rating`:

```python
def cmd_opponent(args: argparse.Namespace) -> None:
    username = args.username
    db_path = args.db or _default_db(username)
    conn = _open_existing_db(db_path)
    try:
        result = store.opponent_stats(conn, username, args.opponent)
        if result["total"] == 0:
            print(f"No games found against '{args.opponent}'.", file=sys.stderr)
            return
        print(f"\n=== {username} vs {args.opponent} ===")
        print(f"Total: {result['total']}  W:{result['wins']}  L:{result['losses']}  "
              f"D:{result['draws']}  ({result['win_pct']:.0f}% win)\n")
        if result["by_time_class"]:
            print("By format:")
            for tc, counts in sorted(result["by_time_class"].items()):
                total_tc = sum(counts.values())
                pct = counts["win"] / total_tc * 100 if total_tc else 0
                print(f"  {tc:8s}  W:{counts['win']}  L:{counts['lose']}  "
                      f"D:{counts['draw']}  ({pct:.0f}%)")
        if result["top_openings"]:
            print("\nTop openings played:")
            for opening, cnt in result["top_openings"]:
                print(f"  {opening}: {cnt}")
    finally:
        conn.close()
```

- [ ] **Step 6: Register `opponent` subcommand in `main()` in `src/cli.py`**

After the `rating` subcommand block:

```python
    # opponent
    p_opponent = sub.add_parser("opponent", help="Show record against a specific player")
    p_opponent.add_argument("opponent", help="Opponent username")
    p_opponent.add_argument("--username", default=DEFAULT_USERNAME)
    p_opponent.add_argument("--db", help="Path to DuckDB file")
    p_opponent.set_defaults(func=cmd_opponent)
```

- [ ] **Step 7: Run full test suite**

```bash
.venv/bin/python -m pytest tests/ -v 2>&1 | tail -20
```

Expected: All tests pass.

- [ ] **Step 8: Smoke-test against real DB**

```bash
python main.py opponent SamRonanGM
```

Expected: Shows W/L/D record against SamRonanGM with openings.

- [ ] **Step 9: Commit**

```bash
git add src/store.py src/cli.py tests/test_store.py
git commit -m "feat: add opponent subcommand showing record, format breakdown, and top openings"
```

---

## Task 6: Enhanced Stats (Trend, Time-of-Day, Game Phase)

**Files:**
- Modify: `src/store.py`
- Modify: `src/cli.py`
- Modify: `tests/test_store.py`

**Context:** Extend `store.stats()` to return three new keys: `trend` (this month vs last month win% per format), `time_of_day` (morning/afternoon/evening/night win rates), `game_phase_losses` (losses in opening/middlegame/endgame using `move_count`). Update `cmd_stats` to print these sections. Time periods are UTC-based.

Phase thresholds: opening ≤ 15 moves, middlegame 16–40 moves, endgame > 40 moves.

Time-of-day periods (UTC hour): morning 6–11, afternoon 12–17, evening 18–23, night 0–5.

- [ ] **Step 1: Write failing tests for enhanced stats**

Add to `TestStats` class in `tests/test_store.py`:

```python
def test_trend_has_current_month(self, conn):
    import time as _time
    t = _time.gmtime()
    # Use current timestamp so it falls in this month
    now_ts = int(_time.time())
    upsert_games(conn, [
        make_game(url="u_now", end_time=now_ts,
                  white={"username": "rathnakaragn", "result": "win"},
                  black={"username": "opp", "result": "lose"}),
    ])
    result = stats(conn, "rathnakaragn")
    current_ym = f"{t.tm_year}{t.tm_mon:02d}"
    assert "trend" in result
    # At least one format should have current month data
    has_current = any(
        current_ym in months
        for months in result["trend"].values()
    )
    assert has_current

def test_time_of_day_keys(self, conn):
    result = stats(conn, "rathnakaragn")
    assert "time_of_day" in result
    assert isinstance(result["time_of_day"], dict)

def test_game_phase_losses_keys(self, conn):
    result = stats(conn, "rathnakaragn")
    assert "game_phase_losses" in result
    assert isinstance(result["game_phase_losses"], dict)
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
.venv/bin/python -m pytest tests/test_store.py::TestStats::test_trend_has_current_month tests/test_store.py::TestStats::test_time_of_day_keys tests/test_store.py::TestStats::test_game_phase_losses_keys -v
```

Expected: FAIL — `'trend'` key not in result.

- [ ] **Step 3: Extend `stats()` in `src/store.py`**

In the `stats` function, add after the streak calculation block and before `return`:

```python
    # Trend: current month vs previous month win% per time class
    t = time.gmtime()
    current_ym = f"{t.tm_year}{t.tm_mon:02d}"
    prev_dt = datetime.datetime(t.tm_year, t.tm_mon, 1,
                                tzinfo=datetime.timezone.utc) - datetime.timedelta(days=1)
    prev_ym = f"{prev_dt.year}{prev_dt.month:02d}"

    trend_rows = conn.execute(f"""
        SELECT time_class,
               strftime(to_timestamp(end_time), '%Y%m') AS ym,
               COUNT(*) AS games,
               SUM(CASE WHEN white = ? THEN CASE WHEN white_result = 'win' THEN 1 ELSE 0 END
                        ELSE CASE WHEN black_result = 'win' THEN 1 ELSE 0 END END) AS wins
        FROM games
        WHERE (white = ? OR black = ?) {tc_filter}
          AND strftime(to_timestamp(end_time), '%Y%m') IN (?, ?)
          AND end_time IS NOT NULL
        GROUP BY time_class, ym
    """, [username, username, username] + tc_params + [current_ym, prev_ym]).fetchall()

    trend: dict = {}
    for tc, ym, games, wins in trend_rows:
        tc = tc or "unknown"
        if tc not in trend:
            trend[tc] = {}
        pct = round(wins / games * 100, 1) if games else 0.0
        trend[tc][ym] = {"games": games, "win_pct": pct}

    # Time of day (UTC hours)
    tod_rows = conn.execute(f"""
        SELECT
            CASE
                WHEN hour(to_timestamp(end_time)) BETWEEN 6 AND 11 THEN 'morning'
                WHEN hour(to_timestamp(end_time)) BETWEEN 12 AND 17 THEN 'afternoon'
                WHEN hour(to_timestamp(end_time)) BETWEEN 18 AND 23 THEN 'evening'
                ELSE 'night'
            END AS period,
            CASE WHEN white = ? THEN white_result ELSE black_result END AS result,
            COUNT(*) AS cnt
        FROM games
        WHERE (white = ? OR black = ?) {tc_filter} AND end_time IS NOT NULL
        GROUP BY period, result
    """, [username, username, username] + tc_params).fetchall()

    time_of_day: dict = {}
    for period, result, cnt in tod_rows:
        if period not in time_of_day:
            time_of_day[period] = {"win": 0, "lose": 0, "draw": 0}
        key = "win" if result == "win" else ("lose" if result in _LOSS_RESULTS else "draw")
        time_of_day[period][key] += cnt

    # Game phase losses (requires move_count column from migration)
    phase_rows = conn.execute(f"""
        SELECT
            CASE
                WHEN move_count <= 15 THEN 'opening'
                WHEN move_count <= 40 THEN 'middlegame'
                ELSE 'endgame'
            END AS phase,
            COUNT(*) AS cnt
        FROM games
        WHERE (white = ? OR black = ?) {tc_filter}
          AND move_count IS NOT NULL
          AND (
              (white = ? AND white_result IN ('lose','checkmated','timeout','resigned','abandoned'))
              OR
              (black = ? AND black_result IN ('lose','checkmated','timeout','resigned','abandoned'))
          )
        GROUP BY phase
    """, [username, username] + tc_params + [username, username]).fetchall()

    game_phase_losses = {phase: cnt for phase, cnt in phase_rows}
```

Update the `return` statement to include new keys:

```python
    return {
        "total": total,
        "by_time_class": by_time_class,
        "top_openings": top_openings,
        "current_streak": current_streak,
        "longest_streak": longest_streak,
        "trend": trend,
        "time_of_day": time_of_day,
        "game_phase_losses": game_phase_losses,
    }
```

- [ ] **Step 4: Update `cmd_stats` in `src/cli.py` to print new sections**

In `cmd_stats`, after the win streak lines, add:

```python
        if result["trend"]:
            print("\nTrend (this month vs last):")
            for tc, months in sorted(result["trend"].items()):
                parts = []
                for ym in sorted(months):
                    d = months[ym]
                    parts.append(f"{ym}: {d['win_pct']}% ({d['games']}g)")
                print(f"  {tc:10s}  " + "  →  ".join(parts))

        if result["time_of_day"]:
            print("\nBy time of day (UTC):")
            for period in ["morning", "afternoon", "evening", "night"]:
                if period not in result["time_of_day"]:
                    continue
                counts = result["time_of_day"][period]
                total_p = sum(counts.values())
                pct = counts["win"] / total_p * 100 if total_p else 0
                print(f"  {period:12s}  W:{counts['win']}  L:{counts['lose']}  "
                      f"D:{counts['draw']}  ({pct:.0f}%)")

        if result["game_phase_losses"]:
            print("\nLosses by game phase:")
            for phase in ["opening", "middlegame", "endgame"]:
                cnt = result["game_phase_losses"].get(phase, 0)
                print(f"  {phase:12s}  {cnt}")
```

- [ ] **Step 5: Run full test suite**

```bash
.venv/bin/python -m pytest tests/ -v 2>&1 | tail -25
```

Expected: All tests pass.

- [ ] **Step 6: Smoke-test against real DB**

```bash
python main.py stats rathnakaragn
```

Expected: Stats output now includes "Trend", "By time of day", and "Losses by game phase" sections.

- [ ] **Step 7: Commit**

```bash
git add src/store.py src/cli.py tests/test_store.py
git commit -m "feat: extend stats with monthly trend, time-of-day win rates, and game phase loss breakdown"
```

---

## Task 7: Portable MCP Server Path

**Files:**
- Create: `scripts/mcp_chess.sh`
- Modify: `.mcp.json`

**Context:** `.mcp.json` currently hard-codes `/Users/rathnakara/project/chess_pgn/data/rathnakaragn.duckdb`. This breaks for anyone who clones the repo to a different path. A wrapper shell script uses `BASH_SOURCE[0]` to compute the DB path relative to its own location, making it portable.

- [ ] **Step 1: Create `scripts/` directory and wrapper script**

```bash
mkdir -p /Users/rathnakara/project/chess_pgn/scripts
```

Create `/Users/rathnakara/project/chess_pgn/scripts/mcp_chess.sh`:

```bash
#!/bin/bash
# Portable MCP server launcher — DB path computed relative to this script.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DB_PATH="${CHESS_DB_PATH:-$SCRIPT_DIR/../data/rathnakaragn.duckdb}"
exec uvx mcp-server-duckdb --db-path "$DB_PATH" --readonly
```

Make it executable:

```bash
chmod +x /Users/rathnakara/project/chess_pgn/scripts/mcp_chess.sh
```

- [ ] **Step 2: Test the script runs correctly**

```bash
echo "test" | /Users/rathnakara/project/chess_pgn/scripts/mcp_chess.sh --help 2>&1 | head -5
```

Expected: shows `mcp-server-duckdb` usage without errors.

- [ ] **Step 3: Update `.mcp.json` to use the wrapper**

Replace the contents of `.mcp.json`:

```json
{
  "mcpServers": {
    "chess-duckdb": {
      "command": "/bin/bash",
      "args": ["scripts/mcp_chess.sh"]
    }
  }
}
```

- [ ] **Step 4: Commit**

```bash
git add scripts/mcp_chess.sh .mcp.json
git commit -m "fix: make MCP server path portable via wrapper script using BASH_SOURCE"
```

---

## Final Verification

- [ ] **Run complete test suite**

```bash
.venv/bin/python -m pytest tests/ -v
```

Expected: All tests pass, no failures.

- [ ] **Run backfill on real DB**

```bash
python main.py backfill rathnakaragn
```

- [ ] **Verify all new subcommands work**

```bash
python main.py rating rathnakaragn
python main.py stats rathnakaragn
python main.py opponent SamRonanGM
```

- [ ] **Run full test suite one final time**

```bash
.venv/bin/python -m pytest tests/ -v 2>&1 | tail -10
```

Expected: All green.
