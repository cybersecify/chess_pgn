# Clock Time Columns Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `white_time_used_secs` and `black_time_used_secs` columns to the `games` table, derived from the `[%clk H:MM:SS.s]` annotations embedded in each PGN's move list.

**Architecture:** A new `_parse_clock_times(pgn)` parser reads the `[TimeControl "..."]` PGN header for the initial time and scans alternating `[%clk ...]` annotations to find each player's final remaining clock; `time_used = initial - final`. `_migrate_db`, `init_db` DDL, `upsert_games`, and `backfill_derived_columns` are all updated to include the two new columns. The backfill null-check is scoped with `strpos(pgn, '[%clk ') > 0` so games with no clock annotations are never endlessly reprocessed.

**Tech Stack:** Python 3.11+, DuckDB, re, pytest

---

## File Map

```
src/store.py       — _parse_clock_times (new), _migrate_db (2 new cols),
                     CREATE TABLE DDL (23 cols), upsert_games (23 values),
                     backfill_derived_columns (null_checks + both UPDATE branches)
tests/test_store.py — make_game() updated with TimeControl + [%clk],
                      test_new_columns_populated updated, TestMigrateDb column
                      counts updated, 3 new clock tests in TestUpsertGames,
                      TestBackfill.test_skips_complete_rows updated
```

---

## Task 1: Clock time columns

**Files:**
- Modify: `src/store.py`
- Modify: `tests/test_store.py`

**Context:**

Every chess.com PGN contains clock annotations on each move, e.g.:
```
1. e4 {[%clk 0:09:50]} 1... c5 {[%clk 0:09:40]} 2. Nf3 {[%clk 0:09:30]} *
```
Annotations alternate: index 0 = white move 1, index 1 = black move 1, index 2 = white move 2, etc.
The `[TimeControl "600"]` or `[TimeControl "600+5"]` header gives the starting seconds.
`time_used = initial_secs - last_clock_secs` for each side.

The current `make_game()` PGN in `tests/test_store.py` has no `[TimeControl]` or `[%clk]`. After this task it will include them so all fixture-based tests pick up real clock data.

With the updated `make_game()` PGN (`[TimeControl "600"]`, white clocks 0:09:50 and 0:09:30, black clock 0:09:40):
- white_time_used_secs = 600 − 570 = **30**
- black_time_used_secs = 600 − 580 = **20**

---

- [ ] **Step 1: Write failing tests**

Add the following to `tests/test_store.py`. Place the three new upsert tests inside the existing `TestUpsertGames` class (after `test_derived_columns_draw`). Update `test_new_columns_populated` to also assert clock values. Update `TestMigrateDb` column counts. Update `test_skips_complete_rows`.

**Update `test_new_columns_populated` in `TestUpsertGames`** (currently ends at `assert row[4] == ...`):

```python
def test_new_columns_populated(self, conn):
    upsert_games(conn, [make_game()])
    row = conn.execute(
        "SELECT white_elo, black_elo, move_count, game_duration_secs, termination,"
        "       white_time_used_secs, black_time_used_secs FROM games"
    ).fetchone()
    assert row[0] == 1200   # white_elo
    assert row[1] == 1100   # black_elo
    assert row[2] == 2      # move_count
    assert row[3] == 900    # game_duration_secs (00:00:00 to 00:15:00)
    assert row[4] == "rathnakaragn won by resignation"
    assert row[5] == 30     # white used 600 - 570 = 30s
    assert row[6] == 20     # black used 600 - 580 = 20s
```

**Three new tests in `TestUpsertGames`:**

```python
def test_clock_times_null_when_no_clk_annotations(self, conn):
    upsert_games(conn, [make_game(
        url="https://chess.com/game/2",
        pgn=(
            '[ECO "B20"]\n'
            '[WhiteElo "1200"]\n'
            '[BlackElo "1100"]\n'
            '[UTCDate "2024.01.01"]\n'
            '[StartTime "00:00:00"]\n'
            '[EndDate "2024.01.01"]\n'
            '[EndTime "00:15:00"]\n'
            '[Termination "Draw"]\n'
            '[TimeControl "600"]\n'
            '\n'
            '1. e4 c5 2. Nf3 *'
        ),
    )])
    row = conn.execute(
        "SELECT white_time_used_secs, black_time_used_secs FROM games"
    ).fetchone()
    assert row[0] is None
    assert row[1] is None

def test_clock_times_null_when_no_time_control_header(self, conn):
    upsert_games(conn, [make_game(
        url="https://chess.com/game/3",
        pgn=(
            '[ECO "B20"]\n'
            '[WhiteElo "1200"]\n'
            '[BlackElo "1100"]\n'
            '\n'
            '1. e4 {[%clk 0:09:50]} 1... c5 {[%clk 0:09:40]} *'
        ),
    )])
    row = conn.execute(
        "SELECT white_time_used_secs, black_time_used_secs FROM games"
    ).fetchone()
    assert row[0] is None
    assert row[1] is None

def test_clock_times_with_increment_time_control(self, conn):
    # TimeControl "60+5" → initial = 60s (ignore increment for used-time calc)
    upsert_games(conn, [make_game(
        url="https://chess.com/game/4",
        pgn=(
            '[ECO "B20"]\n'
            '[WhiteElo "1200"]\n'
            '[BlackElo "1100"]\n'
            '[TimeControl "60+5"]\n'
            '\n'
            '1. e4 {[%clk 0:00:55]} 1... c5 {[%clk 0:00:58]} *'
        ),
    )])
    row = conn.execute(
        "SELECT white_time_used_secs, black_time_used_secs FROM games"
    ).fetchone()
    assert row[0] == 5   # 60 - 55
    assert row[1] == 2   # 60 - 58
```

**Update `TestMigrateDb.test_idempotent_on_full_schema`** — change `len(cols) == 21` to `len(cols) == 23`.

**Update `TestMigrateDb.test_adds_missing_columns_to_old_schema`** — add `assert "white_time_used_secs" in cols` and `assert "black_time_used_secs" in cols`.

**Update `TestBackfill.test_skips_complete_rows`** — this test currently passes because make_game() produces a complete row. After we update make_game() to include clocks, it will still pass only if white_time_used_secs and black_time_used_secs are populated on insert. No code change needed here — just verify it still says `updated == 0`.

- [ ] **Step 2: Run tests to confirm they fail**

```bash
.venv/bin/python -m pytest tests/test_store.py::TestUpsertGames::test_clock_times_null_when_no_clk_annotations -v
```

Expected: FAIL — `column "white_time_used_secs" does not exist`

- [ ] **Step 3: Update `make_game()` in `tests/test_store.py`**

Update the `pgn` string in `make_game()` to include `[TimeControl "600"]` and clock annotations:

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
            '[TimeControl "600"]\n'
            '\n'
            '1. e4 {[%clk 0:09:50]} 1... c5 {[%clk 0:09:40]} 2. Nf3 {[%clk 0:09:30]} *'
        ),
        "time_class": "rapid",
        "time_control": "600",
        "end_time": 1704067200,
        "white": {"username": "rathnakaragn", "result": "win"},
        "black": {"username": "opponent", "result": "lose"},
        "rated": True,
        "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
    }
    g.update(overrides)
    return g
```

Clock arithmetic for the new fixture:
- `[%clk 0:09:50]` → 590s (white move 1)
- `[%clk 0:09:40]` → 580s (black move 1)
- `[%clk 0:09:30]` → 570s (white move 2)
- white_time_used = 600 − 570 = 30
- black_time_used = 600 − 580 = 20

- [ ] **Step 4: Add `_parse_clock_times` to `src/store.py`**

Place this function after `_parse_duration_secs` (around line 80):

```python
_CLK_RE = re.compile(r'\[%clk (\d+:\d{2}:\d{2}(?:\.\d+)?)\]')


def _parse_clock_times(pgn: str | None) -> tuple[int | None, int | None]:
    if not pgn:
        return None, None
    tc = _parse_pgn_header(pgn, "TimeControl")
    if not tc:
        return None, None
    tc_match = re.match(r'^(\d+)', tc)
    if not tc_match:
        return None, None
    initial = int(tc_match.group(1))
    clocks_raw = _CLK_RE.findall(pgn)
    if not clocks_raw:
        return None, None

    def _to_secs(s: str) -> int:
        h, m, sec = s.split(':')
        return int(h) * 3600 + int(m) * 60 + int(float(sec))

    clocks = [_to_secs(c) for c in clocks_raw]
    white_last = clocks[0::2][-1] if clocks[0::2] else None
    black_last = clocks[1::2][-1] if clocks[1::2] else None
    return (
        initial - white_last if white_last is not None else None,
        initial - black_last if black_last is not None else None,
    )
```

- [ ] **Step 5: Update `_migrate_db` in `src/store.py`**

Add two new entries to the loop (after `"user_result"`):

```python
def _migrate_db(conn: duckdb.DuckDBPyConnection) -> None:
    existing = {r[0] for r in conn.execute("DESCRIBE games").fetchall()}
    for col, typ in [
        ("white_elo",             "INTEGER"),
        ("black_elo",             "INTEGER"),
        ("move_count",            "INTEGER"),
        ("game_duration_secs",    "INTEGER"),
        ("termination",           "TEXT"),
        ("color",                 "TEXT"),
        ("opponent",              "TEXT"),
        ("user_result",           "TEXT"),
        ("white_time_used_secs",  "INTEGER"),
        ("black_time_used_secs",  "INTEGER"),
    ]:
        if col not in existing:
            conn.execute(f"ALTER TABLE games ADD COLUMN {col} {typ}")
```

- [ ] **Step 6: Update `CREATE TABLE` DDL in `init_db` to 23 columns**

Replace the `CREATE TABLE IF NOT EXISTS games` block:

```python
    conn.execute("""
        CREATE TABLE IF NOT EXISTS games (
            url                   TEXT PRIMARY KEY,
            pgn                   TEXT,
            time_class            TEXT,
            time_control          TEXT,
            end_time              INTEGER,
            white                 TEXT,
            black                 TEXT,
            white_result          TEXT,
            black_result          TEXT,
            rated                 BOOLEAN,
            fen                   TEXT,
            eco                   TEXT,
            opening               TEXT,
            white_elo             INTEGER,
            black_elo             INTEGER,
            move_count            INTEGER,
            game_duration_secs    INTEGER,
            termination           TEXT,
            color                 TEXT,
            opponent              TEXT,
            user_result           TEXT,
            white_time_used_secs  INTEGER,
            black_time_used_secs  INTEGER
        )
    """)
```

- [ ] **Step 7: Update `upsert_games` in `src/store.py`**

Add clock parsing and two new values to the row tuple. The INSERT placeholder count goes from 21 to 23.

In the row-building loop, after the existing derived-columns block and before `rows.append(...)`, add:

```python
        white_time_used, black_time_used = _parse_clock_times(pgn)
```

Extend `rows.append(...)` with the two new values at the end:

```python
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
            white_time_used,
            black_time_used,
        ))
```

Update the INSERT statement to 23 placeholders:

```python
    conn.executemany("""
        INSERT INTO games VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT (url) DO NOTHING
    """, rows)
```

- [ ] **Step 8: Update `backfill_derived_columns` in `src/store.py`**

Three changes:

**1. Add to null_checks** (always-on, but scoped to games with actual clock annotations so games without clocks are never endlessly reprocessed):

```python
    null_checks = """white_elo IS NULL OR black_elo IS NULL OR move_count IS NULL
               OR game_duration_secs IS NULL OR termination IS NULL OR opening IS NULL
               OR (white_time_used_secs IS NULL AND strpos(pgn, '[%clk ') > 0)"""
    if username:
        null_checks += " OR color IS NULL OR opponent IS NULL OR user_result IS NULL"
```

**2. Extend `base` tuple with clock values** (inside the for loop, replace the `base = (...)` block):

```python
        white_time_used, black_time_used = _parse_clock_times(pgn)
        base = (
            _parse_elo(pgn, "White"),
            _parse_elo(pgn, "Black"),
            _parse_move_count(pgn),
            _parse_duration_secs(pgn),
            _parse_pgn_header(pgn, "Termination"),
            _parse_opening(pgn),
            white_time_used,
            black_time_used,
        )
```

**3. Update both `executemany` UPDATE statements** to include the two new columns:

With username (12 values + url = 13 total):
```python
    if username:
        conn.executemany("""
            UPDATE games SET
                white_elo = ?, black_elo = ?, move_count = ?,
                game_duration_secs = ?, termination = ?, opening = ?,
                white_time_used_secs = ?, black_time_used_secs = ?,
                color = ?, opponent = ?, user_result = ?
            WHERE url = ?
        """, updates)
```

Without username (8 values + url = 9 total):
```python
    else:
        conn.executemany("""
            UPDATE games SET
                white_elo = ?, black_elo = ?, move_count = ?,
                game_duration_secs = ?, termination = ?, opening = ?,
                white_time_used_secs = ?, black_time_used_secs = ?
            WHERE url = ?
        """, updates)
```

Note: the `updates.append(base + ...)` lines build tuples from `base` (now 8 elements), so:
- With username: `updates.append(base + (color, opp, user_result, url))` → 12 values ✓
- Without username: `updates.append(base + (url,))` → 9 values ✓

No change needed to the `updates.append(...)` lines since `base` is now longer.

- [ ] **Step 9: Run all store tests**

```bash
.venv/bin/python -m pytest tests/test_store.py -v 2>&1 | tail -20
```

Expected: All tests pass (should be 69 total — 3 new clock tests added, count was 46 in store, now 49; cli tests are 23; total stays 69+3=72).

- [ ] **Step 10: Run backfill on real DB**

```bash
python main.py backfill rathnakaragn
```

Expected: `Done. N rows updated.` where N is close to total game count (~9k) since all existing rows have NULL clock columns.

- [ ] **Step 11: Verify clock columns populated**

```bash
python main.py query "SELECT COUNT(*) FROM games WHERE white_time_used_secs IS NOT NULL" --db data/rathnakaragn.duckdb
```

Expected: large number (most games have clocks). Also verify no unexpected NULLs:

```bash
python main.py query "SELECT COUNT(*) FROM games WHERE white_time_used_secs IS NULL AND strpos(pgn, '[%clk ') > 0" --db data/rathnakaragn.duckdb
```

Expected: 0 (all games with clock annotations are populated).

- [ ] **Step 12: Commit**

```bash
git add src/store.py tests/test_store.py
git commit -m "feat: add white_time_used_secs and black_time_used_secs derived columns"
```

---

## Final Verification

- [ ] **Run complete test suite**

```bash
.venv/bin/python -m pytest tests/ -v 2>&1 | tail -10
```

Expected: All tests pass, no failures.
