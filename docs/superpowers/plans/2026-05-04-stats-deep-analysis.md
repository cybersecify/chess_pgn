# Stats Deep Analysis Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add five new analysis sections to the `stats` command: win rate by color, best/worst openings by win rate, time pressure performance, performance vs opponent rating range, and win rate by day of week.

**Architecture:** Each section is a new query block appended to `stats()` in `src/store.py` (returns a new key in the result dict) plus a new display block in `cmd_stats` in `src/cli.py`. All five use the derived columns (`color`, `user_result`, `white_time_used_secs`, `black_time_used_secs`) and existing columns (`white_elo`, `black_elo`, `time_control`, `end_time`, `opening`). Tasks 3 and 4 fetch raw rows and bucket in Python because their grouping logic requires arithmetic on column values.

**Tech Stack:** Python 3.11+, DuckDB, pytest

---

## File Map

```
src/store.py        — stats() gains 5 new query blocks + 5 new keys in return dict
src/cli.py          — cmd_stats gains 5 new display blocks
tests/test_store.py — 5 new tests in TestStats, one per feature
```

---

## Shared context for all tasks

`make_game()` in `tests/test_store.py` produces (after `upsert_games(..., username="rathnakaragn")`):
- `color = "white"`, `user_result = "win"`
- `white_elo = 1200`, `black_elo = 1100`  (from `[WhiteElo "1200"]`, `[BlackElo "1100"]` PGN headers)
- `white_time_used_secs = 30`, `black_time_used_secs = 20`  (600s base, last clocks 570s/580s)
- `time_control = "600"`, `opening = "Sicilian Defense"`, `end_time = 1704067200`
- `end_time 1704067200` = 2024-01-01 00:00:00 UTC = Monday, `dayofweek()` = 1

The `stats()` function in `src/store.py` (around line 359) uses a `tc_filter` / `tc_params` pattern for optional time-class filtering. Every new query must follow this same pattern:
- Filter string: `tc_filter = "AND time_class = ?" if time_class else ""`
- Params list: `tc_params = [time_class] if time_class else []`
- Append to WHERE clause and params list exactly as existing queries do.

`_LOSS_RESULTS` is a module-level set: `{"lose", "checkmated", "timeout", "resigned", "abandoned"}`.

---

## Task 1: Win rate by color

**Files:**
- Modify: `src/store.py` (inside `stats()`, before the `return` dict)
- Modify: `src/cli.py` (inside `cmd_stats`, after the game-phase-losses block)
- Modify: `tests/test_store.py` (inside `TestStats`)

- [ ] **Step 1: Write failing test**

Add inside `class TestStats` in `tests/test_store.py`:

```python
def test_by_color(self, conn):
    upsert_games(conn, [
        make_game(url="u1",
                  white={"username": "rathnakaragn", "result": "win"},
                  black={"username": "opp", "result": "lose"}),
        make_game(url="u2",
                  white={"username": "opp", "result": "win"},
                  black={"username": "rathnakaragn", "result": "lose"}),
    ], username="rathnakaragn")
    result = stats(conn, "rathnakaragn")
    assert "by_color" in result
    assert result["by_color"]["white"]["win"] == 1
    assert result["by_color"]["white"]["lose"] == 0
    assert result["by_color"]["black"]["lose"] == 1
    assert result["by_color"]["black"]["win"] == 0
```

- [ ] **Step 2: Run to confirm failure**

```bash
.venv/bin/python -m pytest tests/test_store.py::TestStats::test_by_color -v
```

Expected: FAIL — `KeyError: 'by_color'`

- [ ] **Step 3: Add query to `stats()` in `src/store.py`**

Insert this block immediately before the `return {` at the end of `stats()`:

```python
    color_rows = conn.execute(f"""
        SELECT color, user_result, COUNT(*) AS cnt
        FROM games
        WHERE color IS NOT NULL AND user_result IS NOT NULL
          AND (white = ? OR black = ?) {tc_filter}
        GROUP BY color, user_result
    """, [username, username] + tc_params).fetchall()

    by_color: dict = {}
    for color_val, outcome, cnt in color_rows:
        if color_val not in by_color:
            by_color[color_val] = {"win": 0, "lose": 0, "draw": 0}
        key = "win" if outcome == "win" else ("lose" if outcome in _LOSS_RESULTS else "draw")
        by_color[color_val][key] += cnt
```

Add `"by_color": by_color,` to the `return` dict.

- [ ] **Step 4: Add display to `cmd_stats` in `src/cli.py`**

Add after the `game_phase_losses` block (after the `print(f"  {phase:12s}  {cnt}")` line):

```python
        if result["by_color"]:
            print("\nBy color:")
            for color_val in ["white", "black"]:
                if color_val not in result["by_color"]:
                    continue
                counts = result["by_color"][color_val]
                total_c = sum(counts.values())
                pct = counts["win"] / total_c * 100 if total_c else 0
                print(f"  {color_val:8s}  W:{counts['win']}  L:{counts['lose']}  "
                      f"D:{counts['draw']}  ({pct:.0f}%)")
```

- [ ] **Step 5: Run all tests**

```bash
.venv/bin/python -m pytest tests/test_store.py -v 2>&1 | tail -10
```

Expected: all pass (75 total).

- [ ] **Step 6: Smoke test on real DB**

```bash
python main.py stats rathnakaragn --time-class rapid 2>&1 | grep -A3 "By color"
```

Expected:
```
By color:
  white       W:...  L:...  D:...  (...%)
  black       W:...  L:...  D:...  (...%)
```

- [ ] **Step 7: Commit**

```bash
git add src/store.py src/cli.py tests/test_store.py
git commit -m "feat: add win rate by color to stats"
```

---

## Task 2: Best and worst openings by win rate

**Files:** same as Task 1

- [ ] **Step 1: Write failing test**

Add inside `class TestStats` in `tests/test_store.py`:

```python
def test_best_worst_openings(self, conn):
    # 5 wins with Sicilian Defense
    for i in range(5):
        upsert_games(conn, [make_game(
            url=f"sic{i}",
            pgn='[ECOUrl "https://www.chess.com/openings/Sicilian-Defense"]\n\n1. e4 c5 *',
            white={"username": "rathnakaragn", "result": "win"},
            black={"username": "opp", "result": "lose"},
        )], username="rathnakaragn")
    # 5 losses with French Defense
    for i in range(5):
        upsert_games(conn, [make_game(
            url=f"fr{i}",
            pgn='[ECOUrl "https://www.chess.com/openings/French-Defense"]\n\n1. e4 e6 *',
            white={"username": "opp", "result": "win"},
            black={"username": "rathnakaragn", "result": "lose"},
        )], username="rathnakaragn")
    result = stats(conn, "rathnakaragn")
    assert "best_openings" in result
    assert result["best_openings"][0][0] == "Sicilian Defense"
    assert result["best_openings"][0][2] == 5    # 5 games
    assert "worst_openings" in result
    assert result["worst_openings"][0][0] == "French Defense"
```

- [ ] **Step 2: Run to confirm failure**

```bash
.venv/bin/python -m pytest tests/test_store.py::TestStats::test_best_worst_openings -v
```

Expected: FAIL — `KeyError: 'best_openings'`

- [ ] **Step 3: Add queries to `stats()` in `src/store.py`**

Insert before the `return {`:

```python
    best_opening_rows = conn.execute(f"""
        SELECT opening,
               SUM(CASE WHEN user_result = 'win' THEN 1 ELSE 0 END) AS wins,
               COUNT(*) AS games
        FROM games
        WHERE (white = ? OR black = ?) AND opening IS NOT NULL
          AND user_result IS NOT NULL {tc_filter}
        GROUP BY opening
        HAVING COUNT(*) >= 5
        ORDER BY wins * 1.0 / COUNT(*) DESC
        LIMIT 5
    """, [username, username] + tc_params).fetchall()

    worst_opening_rows = conn.execute(f"""
        SELECT opening,
               SUM(CASE WHEN user_result = 'win' THEN 1 ELSE 0 END) AS wins,
               COUNT(*) AS games
        FROM games
        WHERE (white = ? OR black = ?) AND opening IS NOT NULL
          AND user_result IS NOT NULL {tc_filter}
        GROUP BY opening
        HAVING COUNT(*) >= 5
        ORDER BY wins * 1.0 / COUNT(*) ASC
        LIMIT 5
    """, [username, username] + tc_params).fetchall()
```

Add to the `return` dict:
```python
        "best_openings": best_opening_rows,
        "worst_openings": worst_opening_rows,
```

- [ ] **Step 4: Add display to `cmd_stats` in `src/cli.py`**

Add after the by-color block:

```python
        if result["best_openings"]:
            print("\nBest openings (min 5 games):")
            for opening, wins, games in result["best_openings"]:
                pct = wins / games * 100 if games else 0
                print(f"  {opening:35s}  {pct:.0f}%  ({games}g)")
        if result["worst_openings"]:
            print("\nWorst openings (min 5 games):")
            for opening, wins, games in result["worst_openings"]:
                pct = wins / games * 100 if games else 0
                print(f"  {opening:35s}  {pct:.0f}%  ({games}g)")
```

- [ ] **Step 5: Run all tests**

```bash
.venv/bin/python -m pytest tests/test_store.py -v 2>&1 | tail -10
```

Expected: all pass (76 total).

- [ ] **Step 6: Smoke test**

```bash
python main.py stats rathnakaragn --time-class rapid 2>&1 | grep -A6 "openings"
```

- [ ] **Step 7: Commit**

```bash
git add src/store.py src/cli.py tests/test_store.py
git commit -m "feat: add best/worst openings by win rate to stats"
```

---

## Task 3: Time pressure performance

**Files:** same as Task 1

**Context:** Fetch raw rows and bucket in Python. `time_control` format is `"600"` or `"600+5"` — extract the leading integer as initial seconds. `time_control NOT LIKE '%/%'` excludes daily games. `used_secs / initial * 100` gives pressure percentage. Buckets: `< 30%` (light), `30–70%` (moderate), `> 70%` (heavy).

- [ ] **Step 1: Write failing test**

Add inside `class TestStats`:

```python
def test_time_pressure(self, conn):
    # make_game: time_control="600", white_time_used=30 → 30/600=5% → "< 30%"
    upsert_games(conn, [make_game(
        white={"username": "rathnakaragn", "result": "win"},
        black={"username": "opp", "result": "lose"},
    )], username="rathnakaragn")
    result = stats(conn, "rathnakaragn")
    assert "time_pressure" in result
    assert result["time_pressure"]["< 30%"]["win"] == 1
    assert result["time_pressure"]["30-70%"]["win"] == 0
```

- [ ] **Step 2: Run to confirm failure**

```bash
.venv/bin/python -m pytest tests/test_store.py::TestStats::test_time_pressure -v
```

Expected: FAIL — `KeyError: 'time_pressure'`

- [ ] **Step 3: Add query to `stats()` in `src/store.py`**

Insert before the `return {`:

```python
    time_rows = conn.execute(f"""
        SELECT color, user_result, time_control,
               white_time_used_secs, black_time_used_secs
        FROM games
        WHERE color IS NOT NULL AND user_result IS NOT NULL
          AND white_time_used_secs IS NOT NULL AND black_time_used_secs IS NOT NULL
          AND time_control IS NOT NULL AND time_control NOT LIKE '%/%'
          AND (white = ? OR black = ?) {tc_filter}
    """, [username, username] + tc_params).fetchall()

    time_pressure: dict = {k: {"win": 0, "lose": 0, "draw": 0}
                           for k in ["< 30%", "30-70%", "> 70%"]}
    for color_val, outcome, tc_str, white_used, black_used in time_rows:
        m = re.match(r'^(\d+)', tc_str)
        if not m:
            continue
        initial = int(m.group(1))
        if initial == 0:
            continue
        used = white_used if color_val == "white" else black_used
        pct = used * 100 / initial
        bucket = "< 30%" if pct < 30 else ("> 70%" if pct > 70 else "30-70%")
        key = "win" if outcome == "win" else ("lose" if outcome in _LOSS_RESULTS else "draw")
        time_pressure[bucket][key] += 1
    if not any(sum(v.values()) for v in time_pressure.values()):
        time_pressure = {}
```

Add to `return` dict: `"time_pressure": time_pressure,`

- [ ] **Step 4: Add display to `cmd_stats` in `src/cli.py`**

```python
        if result["time_pressure"]:
            print("\nTime pressure (% of clock used):")
            for bucket in ["< 30%", "30-70%", "> 70%"]:
                counts = result["time_pressure"].get(bucket, {"win": 0, "lose": 0, "draw": 0})
                total_b = sum(counts.values())
                if total_b == 0:
                    continue
                pct = counts["win"] / total_b * 100
                print(f"  {bucket:8s}  W:{counts['win']}  L:{counts['lose']}  "
                      f"D:{counts['draw']}  ({pct:.0f}%)")
```

- [ ] **Step 5: Run all tests**

```bash
.venv/bin/python -m pytest tests/test_store.py -v 2>&1 | tail -10
```

Expected: all pass (77 total).

- [ ] **Step 6: Smoke test**

```bash
python main.py stats rathnakaragn --time-class rapid 2>&1 | grep -A4 "Time pressure"
```

- [ ] **Step 7: Commit**

```bash
git add src/store.py src/cli.py tests/test_store.py
git commit -m "feat: add time pressure win rate to stats"
```

---

## Task 4: Performance vs opponent rating range

**Files:** same as Task 1

**Context:** `diff = opponent_elo - user_elo`. Positive diff means stronger opponent. Buckets: `much weaker` (diff < −100), `similar` (−100 to +100 inclusive), `much stronger` (diff > +100).

- [ ] **Step 1: Write failing test**

Add inside `class TestStats`:

```python
def test_rating_range(self, conn):
    # rathnakaragn=1200 (white), opp=900 (black) → diff = 900-1200 = -300 → "much weaker"
    upsert_games(conn, [make_game(
        url="u_rating",
        pgn=(
            '[ECO "B20"]\n'
            '[ECOUrl "https://www.chess.com/openings/Sicilian-Defense"]\n'
            '[WhiteElo "1200"]\n'
            '[BlackElo "900"]\n'
            '[UTCDate "2024.01.01"]\n'
            '[StartTime "00:00:00"]\n'
            '[EndDate "2024.01.01"]\n'
            '[EndTime "00:15:00"]\n'
            '[Termination "rathnakaragn won by resignation"]\n'
            '[TimeControl "600"]\n'
            '\n'
            '1. e4 {[%clk 0:09:50]} 1... c5 {[%clk 0:09:40]} 2. Nf3 {[%clk 0:09:30]} *'
        ),
        white={"username": "rathnakaragn", "result": "win"},
        black={"username": "opp", "result": "lose"},
    )], username="rathnakaragn")
    result = stats(conn, "rathnakaragn")
    assert "rating_range" in result
    assert result["rating_range"]["much weaker"]["win"] == 1
    assert result["rating_range"]["similar"]["win"] == 0
```

- [ ] **Step 2: Run to confirm failure**

```bash
.venv/bin/python -m pytest tests/test_store.py::TestStats::test_rating_range -v
```

Expected: FAIL — `KeyError: 'rating_range'`

- [ ] **Step 3: Add query to `stats()` in `src/store.py`**

Insert before the `return {`:

```python
    rating_rows = conn.execute(f"""
        SELECT color, user_result, white_elo, black_elo
        FROM games
        WHERE color IS NOT NULL AND user_result IS NOT NULL
          AND white_elo IS NOT NULL AND black_elo IS NOT NULL
          AND (white = ? OR black = ?) {tc_filter}
    """, [username, username] + tc_params).fetchall()

    rating_range: dict = {k: {"win": 0, "lose": 0, "draw": 0}
                          for k in ["much weaker", "similar", "much stronger"]}
    for color_val, outcome, white_elo_val, black_elo_val in rating_rows:
        user_elo = white_elo_val if color_val == "white" else black_elo_val
        opp_elo  = black_elo_val if color_val == "white" else white_elo_val
        diff = opp_elo - user_elo
        bucket = "much weaker" if diff < -100 else ("much stronger" if diff > 100 else "similar")
        key = "win" if outcome == "win" else ("lose" if outcome in _LOSS_RESULTS else "draw")
        rating_range[bucket][key] += 1
    if not any(sum(v.values()) for v in rating_range.values()):
        rating_range = {}
```

Add to `return` dict: `"rating_range": rating_range,`

- [ ] **Step 4: Add display to `cmd_stats` in `src/cli.py`**

```python
        if result["rating_range"]:
            print("\nvs opponent rating:")
            labels = {"much weaker": "< -100", "similar": "  ±100", "much stronger": "> +100"}
            for bucket in ["much weaker", "similar", "much stronger"]:
                counts = result["rating_range"].get(bucket, {"win": 0, "lose": 0, "draw": 0})
                total_b = sum(counts.values())
                if total_b == 0:
                    continue
                pct = counts["win"] / total_b * 100
                print(f"  {bucket:14s} ({labels[bucket]})  W:{counts['win']}  "
                      f"L:{counts['lose']}  D:{counts['draw']}  ({pct:.0f}%)")
```

- [ ] **Step 5: Run all tests**

```bash
.venv/bin/python -m pytest tests/test_store.py -v 2>&1 | tail -10
```

Expected: all pass (78 total).

- [ ] **Step 6: Smoke test**

```bash
python main.py stats rathnakaragn --time-class rapid 2>&1 | grep -A4 "opponent rating"
```

- [ ] **Step 7: Commit**

```bash
git add src/store.py src/cli.py tests/test_store.py
git commit -m "feat: add performance vs opponent rating range to stats"
```

---

## Task 5: Win rate by day of week

**Files:** same as Task 1

**Context:** DuckDB's `dayofweek(timestamp)` returns 0=Sunday, 1=Monday, …, 6=Saturday (PostgreSQL compatible). `to_timestamp(end_time)` uses local timezone (machine is IST), so days are in IST. Display order: Mon → Sun.

- [ ] **Step 1: Write failing test**

Add inside `class TestStats`:

```python
def test_day_of_week(self, conn):
    # end_time 1704067200 = 2024-01-01 00:00:00 UTC = Monday, dayofweek=1
    upsert_games(conn, [make_game(
        end_time=1704067200,
        white={"username": "rathnakaragn", "result": "win"},
        black={"username": "opp", "result": "lose"},
    )], username="rathnakaragn")
    result = stats(conn, "rathnakaragn")
    assert "day_of_week" in result
    assert "Mon" in result["day_of_week"]
    assert result["day_of_week"]["Mon"]["win"] == 1
```

- [ ] **Step 2: Run to confirm failure**

```bash
.venv/bin/python -m pytest tests/test_store.py::TestStats::test_day_of_week -v
```

Expected: FAIL — `KeyError: 'day_of_week'`

- [ ] **Step 3: Add query to `stats()` in `src/store.py`**

Insert before the `return {`:

```python
    dow_rows = conn.execute(f"""
        SELECT dayofweek(to_timestamp(end_time)) AS dow,
               user_result, COUNT(*) AS cnt
        FROM games
        WHERE (white = ? OR black = ?) AND end_time IS NOT NULL
          AND user_result IS NOT NULL {tc_filter}
        GROUP BY dow, user_result
    """, [username, username] + tc_params).fetchall()

    _dow_names = {0: "Sun", 1: "Mon", 2: "Tue", 3: "Wed", 4: "Thu", 5: "Fri", 6: "Sat"}
    day_of_week: dict = {}
    for dow_int, outcome, cnt in dow_rows:
        name = _dow_names.get(int(dow_int), str(dow_int))
        if name not in day_of_week:
            day_of_week[name] = {"win": 0, "lose": 0, "draw": 0}
        key = "win" if outcome == "win" else ("lose" if outcome in _LOSS_RESULTS else "draw")
        day_of_week[name][key] += cnt
```

Add to `return` dict: `"day_of_week": day_of_week,`

- [ ] **Step 4: Add display to `cmd_stats` in `src/cli.py`**

```python
        if result["day_of_week"]:
            print("\nBy day of week:")
            parts = []
            for day in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]:
                if day not in result["day_of_week"]:
                    continue
                counts = result["day_of_week"][day]
                total_d = sum(counts.values())
                pct = counts["win"] / total_d * 100 if total_d else 0
                parts.append(f"{day} {pct:.0f}%({total_d}g)")
            print("  " + "  ".join(parts))
```

- [ ] **Step 5: Run full test suite**

```bash
.venv/bin/python -m pytest tests/ -v 2>&1 | tail -10
```

Expected: all pass (79 total).

- [ ] **Step 6: Smoke test**

```bash
python main.py stats rathnakaragn --time-class rapid 2>&1 | grep -A2 "day of week"
```

Expected:
```
By day of week:
  Mon 49%(120g)  Tue 51%(105g)  ...  Sun 50%(90g)
```

- [ ] **Step 7: Commit**

```bash
git add src/store.py src/cli.py tests/test_store.py
git commit -m "feat: add win rate by day of week to stats"
```

---

## Final Verification

```bash
.venv/bin/python -m pytest tests/ -v 2>&1 | tail -5
python main.py stats rathnakaragn
```

Expected: 79 tests pass. Full stats output includes all 5 new sections.
