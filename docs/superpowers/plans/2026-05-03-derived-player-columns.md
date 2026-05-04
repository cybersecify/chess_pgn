# Derived Player Columns Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add three derived columns — `color`, `opponent`, `user_result` — to the `games` table so every query can filter and group without repeating `CASE WHEN white = ? THEN ... ELSE ...` boilerplate.

**Architecture:** `_migrate_db()` adds the three columns to existing DBs. `upsert_games()` gains an optional `username` parameter; when provided it populates all three columns at insert time. `backfill_derived_columns()` gains the same `username` parameter to fill NULLs in existing rows. The CLI already has `username` at every call site, so threading it through is the only wiring change needed.

**Tech Stack:** Python 3.11+, DuckDB, argparse, pytest

---

## File Map

```
src/store.py       — _migrate_db (3 new cols), CREATE TABLE DDL, upsert_games(username=),
                     backfill_derived_columns(username=)
src/cli.py         — cmd_sync and cmd_backfill pass username to store functions
tests/test_store.py — new tests for all three columns; update TestBackfill
```

---

## Task 1: Schema + upsert_games + backfill

**Files:**
- Modify: `src/store.py`
- Modify: `tests/test_store.py`

**Context:** The `games` table needs three new columns. `color` is "white" or "black" (which side the tracked user played). `opponent` is the other player's username. `user_result` is "win", "draw", or "lose" — a simplified form of `white_result`/`black_result` that doesn't require knowing which side the user played. All three are NULL when `username` is not provided to `upsert_games`.

The `_LOSS_RESULTS` set already in `store.py` is `{"lose", "checkmated", "timeout", "resigned", "abandoned"}` — use it for the "lose" mapping.

`make_game()` in `tests/test_store.py` produces a game where `white.username = "rathnakaragn"` and `black.username = "opponent"`, `white.result = "win"`, `black.result = "lose"`.

- [ ] **Step 1: Write failing tests**

Add to `TestUpsertGames` in `tests/test_store.py`:

```python
def test_derived_columns_populated_when_username_given(self, conn):
    upsert_games(conn, [make_game()], username="rathnakaragn")
    row = conn.execute(
        "SELECT color, opponent, user_result FROM games"
    ).fetchone()
    assert row[0] == "white"       # rathnakaragn played white
    assert row[1] == "opponent"    # the other player
    assert row[2] == "win"         # rathnakaragn won

def test_derived_columns_null_when_no_username(self, conn):
    upsert_games(conn, [make_game()])  # no username
    row = conn.execute(
        "SELECT color, opponent, user_result FROM games"
    ).fetchone()
    assert row[0] is None
    assert row[1] is None
    assert row[2] is None

def test_derived_columns_black_side(self, conn):
    upsert_games(conn, [make_game(
        white={"username": "other", "result": "win"},
        black={"username": "rathnakaragn", "result": "lose"},
    )], username="rathnakaragn")
    row = conn.execute(
        "SELECT color, opponent, user_result FROM games"
    ).fetchone()
    assert row[0] == "black"
    assert row[1] == "other"
    assert row[2] == "lose"

def test_derived_columns_draw(self, conn):
    upsert_games(conn, [make_game(
        white={"username": "rathnakaragn", "result": "stalemate"},
        black={"username": "opp", "result": "stalemate"},
    )], username="rathnakaragn")
    row = conn.execute("SELECT user_result FROM games").fetchone()
    assert row[0] == "draw"
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
.venv/bin/python -m pytest tests/test_store.py::TestUpsertGames::test_derived_columns_populated_when_username_given -v
```

Expected: FAIL — column `color` does not exist.

- [ ] **Step 3: Update `_migrate_db` in `src/store.py`**

Add three new entries to the loop in `_migrate_db`:

```python
def _migrate_db(conn: duckdb.DuckDBPyConnection) -> None:
    existing = {r[0] for r in conn.execute("DESCRIBE games").fetchall()}
    for col, typ in [
        ("white_elo",          "INTEGER"),
        ("black_elo",          "INTEGER"),
        ("move_count",         "INTEGER"),
        ("game_duration_secs", "INTEGER"),
        ("termination",        "TEXT"),
        ("color",              "TEXT"),
        ("opponent",           "TEXT"),
        ("user_result",        "TEXT"),
    ]:
        if col not in existing:
            conn.execute(f"ALTER TABLE games ADD COLUMN {col} {typ}")
```

- [ ] **Step 4: Update `CREATE TABLE` DDL in `init_db` to include all 21 columns**

Replace the `CREATE TABLE IF NOT EXISTS games` block in `init_db`:

```python
    conn.execute("""
        CREATE TABLE IF NOT EXISTS games (
            url               TEXT PRIMARY KEY,
            pgn               TEXT,
            time_class        TEXT,
            time_control      TEXT,
            end_time          INTEGER,
            white             TEXT,
            black             TEXT,
            white_result      TEXT,
            black_result      TEXT,
            rated             BOOLEAN,
            fen               TEXT,
            eco               TEXT,
            opening           TEXT,
            white_elo         INTEGER,
            black_elo         INTEGER,
            move_count        INTEGER,
            game_duration_secs INTEGER,
            termination       TEXT,
            color             TEXT,
            opponent          TEXT,
            user_result       TEXT
        )
    """)
```

- [ ] **Step 5: Update `upsert_games` signature and row building in `src/store.py`**

Replace the full `upsert_games` function:

```python
def upsert_games(
    conn: duckdb.DuckDBPyConnection,
    games: list[dict],
    username: str | None = None,
) -> int:
    if not games:
        return 0
    rows = []
    for g in games:
        url = g.get("url")
        if not url:
            continue
        pgn = g.get("pgn", "")
        white_user = g.get("white", {}).get("username")
        black_user = g.get("black", {}).get("username")
        white_res  = g.get("white", {}).get("result")
        black_res  = g.get("black", {}).get("result")

        if username:
            color = "white" if white_user == username else "black"
            opponent = black_user if color == "white" else white_user
            raw_result = white_res if color == "white" else black_res
            if raw_result == "win":
                user_result = "win"
            elif raw_result in _LOSS_RESULTS:
                user_result = "lose"
            else:
                user_result = "draw"
        else:
            color = opponent = user_result = None

        rows.append((
            url,
            pgn,
            g.get("time_class"),
            g.get("time_control"),
            g.get("end_time"),
            white_user,
            black_user,
            white_res,
            black_res,
            g.get("rated"),
            g.get("fen"),
            _parse_pgn_header(pgn, "ECO"),
            _parse_opening(pgn),
            _parse_elo(pgn, "White"),
            _parse_elo(pgn, "Black"),
            _parse_move_count(pgn),
            _parse_duration_secs(pgn),
            _parse_pgn_header(pgn, "Termination"),
            color,
            opponent,
            user_result,
        ))
    if not rows:
        return 0
    before = conn.execute("SELECT COUNT(*) FROM games").fetchone()[0]
    conn.executemany("""
        INSERT INTO games VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT (url) DO NOTHING
    """, rows)
    after = conn.execute("SELECT COUNT(*) FROM games").fetchone()[0]
    return after - before
```

- [ ] **Step 6: Update `backfill_derived_columns` to accept and use `username`**

Replace the full `backfill_derived_columns` function:

```python
def backfill_derived_columns(
    conn: duckdb.DuckDBPyConnection,
    username: str | None = None,
) -> int:
    null_checks = """white_elo IS NULL OR black_elo IS NULL OR move_count IS NULL
               OR game_duration_secs IS NULL OR termination IS NULL OR opening IS NULL"""
    if username:
        null_checks += " OR color IS NULL OR opponent IS NULL OR user_result IS NULL"

    rows = conn.execute(f"""
        SELECT url, pgn, white, black, white_result, black_result FROM games
        WHERE pgn IS NOT NULL AND ({null_checks})
    """).fetchall()
    if not rows:
        return 0

    updates = []
    for url, pgn, white_user, black_user, white_res, black_res in rows:
        if username:
            color = "white" if white_user == username else "black"
            opp = black_user if color == "white" else white_user
            raw_result = white_res if color == "white" else black_res
            if raw_result == "win":
                user_result = "win"
            elif raw_result in _LOSS_RESULTS:
                user_result = "lose"
            else:
                user_result = "draw"
        else:
            color = opp = user_result = None

        updates.append((
            _parse_elo(pgn, "White"),
            _parse_elo(pgn, "Black"),
            _parse_move_count(pgn),
            _parse_duration_secs(pgn),
            _parse_pgn_header(pgn, "Termination"),
            _parse_opening(pgn),
            color,
            opp,
            user_result,
            url,
        ))

    conn.executemany("""
        UPDATE games SET
            white_elo = ?, black_elo = ?, move_count = ?,
            game_duration_secs = ?, termination = ?, opening = ?,
            color = ?, opponent = ?, user_result = ?
        WHERE url = ?
    """, updates)
    return len(updates)
```

- [ ] **Step 7: Update `TestBackfill` to pass username and assert new columns**

Update `test_backfills_nulled_columns` in `TestBackfill`:

```python
def test_backfills_nulled_columns(self, conn):
    upsert_games(conn, [make_game()], username="rathnakaragn")
    conn.execute("UPDATE games SET white_elo = NULL, move_count = NULL, termination = NULL, color = NULL")
    updated = backfill_derived_columns(conn, username="rathnakaragn")
    assert updated == 1
    row = conn.execute("SELECT white_elo, move_count, termination, color, opponent, user_result FROM games").fetchone()
    assert row[0] == 1200
    assert row[1] == 2
    assert row[2] == "rathnakaragn won by resignation"
    assert row[3] == "white"
    assert row[4] == "opponent"
    assert row[5] == "win"
```

- [ ] **Step 8: Run all tests**

```bash
.venv/bin/python -m pytest tests/test_store.py -v 2>&1 | tail -25
```

Expected: All tests pass including the 4 new `test_derived_columns_*` tests.

- [ ] **Step 9: Commit**

```bash
git add src/store.py tests/test_store.py
git commit -m "feat: add color, opponent, user_result derived columns to games table"
```

---

## Task 2: Wire username through CLI + backfill real DB

**Files:**
- Modify: `src/cli.py`
- Modify: `tests/test_cli.py`

**Context:** `cmd_sync` calls `store.upsert_games(conn, games)` without passing `username`. After this task it passes `username`. Same for `cmd_backfill` which calls `store.backfill_derived_columns(conn)` — it must pass `username`. Then we run backfill against the real DB to populate the new columns for all 9k+ existing games.

- [ ] **Step 1: Write failing CLI test**

Add to `tests/test_cli.py` — add a new `TestDerivedColumns` class:

```python
class TestDerivedColumns:
    def test_sync_populates_derived_columns(self, tmp_path):
        from unittest.mock import patch
        db_path = str(tmp_path / "test.duckdb")
        games = [
            {
                "url": "https://chess.com/game/1",
                "pgn": '[ECO "B20"]\n[ECOUrl "https://www.chess.com/openings/Sicilian-Defense"]\n[WhiteElo "1200"]\n[BlackElo "1100"]\n[UTCDate "2024.01.01"]\n[StartTime "00:00:00"]\n[EndDate "2024.01.01"]\n[EndTime "00:15:00"]\n[Termination "rathnakaragn won by resignation"]\n\n1. e4 c5 2. Nf3 *',
                "time_class": "rapid", "time_control": "600", "end_time": 1704067200,
                "white": {"username": "rathnakaragn", "result": "win"},
                "black": {"username": "fischer", "result": "lose"},
                "rated": True, "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
            }
        ]
        with patch("src.cli._api_get") as mock_api:
            mock_api.side_effect = [
                {"archives": ["https://api.chess.com/pub/player/rathnakaragn/games/2024/01"]},
                {"games": games},
            ]
            run_cli("sync", "rathnakaragn", "--db", db_path)

        import duckdb
        conn = duckdb.connect(db_path, read_only=True)
        row = conn.execute("SELECT color, opponent, user_result FROM games").fetchone()
        conn.close()
        assert row[0] == "white"
        assert row[1] == "fischer"
        assert row[2] == "win"
```

- [ ] **Step 2: Run test to confirm it fails**

```bash
.venv/bin/python -m pytest tests/test_cli.py::TestDerivedColumns::test_sync_populates_derived_columns -v
```

Expected: FAIL — `color` is None (username not passed to upsert_games yet).

- [ ] **Step 3: Update `cmd_sync` in `src/cli.py` to pass username**

In `cmd_sync`, change the `upsert_games` call at line 95:

```python
            new = store.upsert_games(conn, games, username=username)
```

- [ ] **Step 4: Update `cmd_backfill` in `src/cli.py` to pass username**

In `cmd_backfill`, change the `backfill_derived_columns` call:

```python
        updated = store.backfill_derived_columns(conn, username=username)
```

- [ ] **Step 5: Run all tests**

```bash
.venv/bin/python -m pytest tests/ -v 2>&1 | tail -15
```

Expected: All tests pass.

- [ ] **Step 6: Run backfill on real DB**

```bash
python main.py backfill rathnakaragn
```

Expected output: `Backfilling derived columns from stored PGNs... Done. N rows updated.`
(N should be close to the total game count ~9k since color/opponent/user_result were all NULL before)

- [ ] **Step 7: Verify columns populated on real DB**

```bash
python main.py query "SELECT color, COUNT(*) FROM games GROUP BY color" --db data/rathnakaragn.duckdb
```

Expected: Two rows — `white  NNNN` and `black  MMMM` (no NULLs).

```bash
python main.py query "SELECT user_result, COUNT(*) FROM games GROUP BY user_result ORDER BY user_result" --db data/rathnakaragn.duckdb
```

Expected: Three rows — `draw`, `lose`, `win` with counts.

- [ ] **Step 8: Commit**

```bash
git add src/cli.py tests/test_cli.py
git commit -m "feat: pass username through CLI so sync and backfill populate color/opponent/user_result"
```

---

## Final Verification

- [ ] **Run complete test suite**

```bash
.venv/bin/python -m pytest tests/ -v 2>&1 | tail -10
```

Expected: All tests pass, no failures.

- [ ] **Confirm no NULL color rows remain**

```bash
python main.py query "SELECT COUNT(*) FROM games WHERE color IS NULL" --db data/rathnakaragn.duckdb
```

Expected: `0`
