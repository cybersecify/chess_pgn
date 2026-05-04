"""DuckDB persistence layer for chess.com games."""

from __future__ import annotations

import datetime
import re
import time
from pathlib import Path

import duckdb

_LOSS_RESULTS = {"lose", "checkmated", "timeout", "resigned", "abandoned"}
_DOW_NAMES = {0: "Sun", 1: "Mon", 2: "Tue", 3: "Wed", 4: "Thu", 5: "Fri", 6: "Sat"}


def _derive_player_fields(
    username: str,
    white_user: str | None,
    black_user: str | None,
    white_res: str | None,
    black_res: str | None,
) -> tuple[str, str | None, str]:
    color = "white" if white_user == username else "black"
    opponent = black_user if color == "white" else white_user
    raw = white_res if color == "white" else black_res
    if raw == "win":
        user_result = "win"
    elif raw in _LOSS_RESULTS:
        user_result = "lose"
    else:
        user_result = "draw"
    return color, opponent, user_result


def _parse_pgn_header(pgn: str | None, tag: str) -> str | None:
    m = re.search(rf'\[{tag} "([^"]*)"\]', pgn or "")
    return m.group(1) if m else None


def _parse_opening(pgn: str | None) -> str | None:
    # chess.com PGNs use ECOUrl instead of Opening tag
    url = _parse_pgn_header(pgn, "ECOUrl")
    if url:
        slug = url.rstrip("/").rsplit("/", 1)[-1]
        return slug.replace("-", " ")
    return _parse_pgn_header(pgn, "Opening")


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


_CLK_RE = re.compile(r'\[%clk (\d+:\d{2}:\d{2}(?:\.\d+)?)\]')


def _parse_clock_times(pgn: str | None) -> tuple[int | None, int | None]:
    if not pgn:
        return None, None
    tc = _parse_pgn_header(pgn, "TimeControl")
    if not tc or '/' in tc:   # daily chess: N/seconds-per-move format
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
    # Increment is intentionally ignored: used = initial - last_clock underestimates
    # true time spent per move when there is an increment, but is consistent and simple.
    return (
        max(0, initial - white_last) if white_last is not None else None,
        max(0, initial - black_last) if black_last is not None else None,
    )


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
        ("white_time_used_secs",  "INTEGER"),
        ("black_time_used_secs",  "INTEGER"),
    ]:
        if col not in existing:
            conn.execute(f"ALTER TABLE games ADD COLUMN {col} {typ}")


def init_db(db_path: str) -> duckdb.DuckDBPyConnection:
    if db_path != ":memory:":
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = duckdb.connect(db_path)
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
            user_result       TEXT,
            white_time_used_secs  INTEGER,
            black_time_used_secs  INTEGER
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


def upsert_games(
    conn: duckdb.DuckDBPyConnection,
    games: list[dict],
    username: str | None = None,
) -> int:
    """Insert new games; skip duplicates (ON CONFLICT DO NOTHING).

    When username is given, also populates color/opponent/user_result.
    Already-stored games are not updated — call backfill_derived_columns
    to fill derived columns for existing rows.
    """
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
            color, opponent, user_result = _derive_player_fields(
                username, white_user, black_user, white_res, black_res
            )
        else:
            color = opponent = user_result = None

        white_time_used, black_time_used = _parse_clock_times(pgn)
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
    if not rows:
        return 0
    before = conn.execute("SELECT COUNT(*) FROM games").fetchone()[0]
    conn.executemany("""
        INSERT INTO games VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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


def backfill_derived_columns(
    conn: duckdb.DuckDBPyConnection,
    username: str | None = None,
) -> int:
    null_checks = """white_elo IS NULL OR black_elo IS NULL OR move_count IS NULL
               OR game_duration_secs IS NULL OR termination IS NULL OR opening IS NULL
               OR (white_time_used_secs IS NULL AND strpos(pgn, '[%clk ') > 0)"""
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
        if username:
            color, opp, user_result = _derive_player_fields(
                username, white_user, black_user, white_res, black_res
            )
            updates.append(base + (color, opp, user_result, url))
        else:
            updates.append(base + (url,))

    if username:
        conn.executemany("""
            UPDATE games SET
                white_elo = ?, black_elo = ?, move_count = ?,
                game_duration_secs = ?, termination = ?, opening = ?,
                white_time_used_secs = ?, black_time_used_secs = ?,
                color = ?, opponent = ?, user_result = ?
            WHERE url = ?
        """, updates)
    else:
        conn.executemany("""
            UPDATE games SET
                white_elo = ?, black_elo = ?, move_count = ?,
                game_duration_secs = ?, termination = ?, opening = ?,
                white_time_used_secs = ?, black_time_used_secs = ?
            WHERE url = ?
        """, updates)
    return len(updates)


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

    if n is not None:
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


def raw_sql(conn: duckdb.DuckDBPyConnection, sql: str) -> list[tuple]:
    """Execute SQL and return all rows. Accepts any SQL including DDL — caller is responsible for safety."""
    return conn.execute(sql).fetchall()


def stats(conn: duckdb.DuckDBPyConnection, username: str, time_class: str | None = None) -> dict:
    tc_filter = "AND time_class = ?" if time_class else ""
    tc_params = [time_class] if time_class else []

    total = conn.execute(
        f"SELECT COUNT(*) FROM games WHERE (white = ? OR black = ?) {tc_filter}",
        [username, username] + tc_params,
    ).fetchone()[0]

    rows = conn.execute(f"""
        SELECT time_class,
               CASE WHEN white = ? THEN white_result ELSE black_result END AS result,
               COUNT(*) AS cnt
        FROM games
        WHERE (white = ? OR black = ?) {tc_filter}
        GROUP BY time_class, result
    """, [username, username, username] + tc_params).fetchall()

    by_time_class: dict = {}
    for tc, result, cnt in rows:
        tc = tc or "unknown"
        if tc not in by_time_class:
            by_time_class[tc] = {"win": 0, "lose": 0, "draw": 0}
        key = "win" if result == "win" else ("lose" if result in _LOSS_RESULTS else "draw")
        by_time_class[tc][key] += cnt

    top_openings = conn.execute(f"""
        SELECT opening, COUNT(*) AS cnt
        FROM games
        WHERE (white = ? OR black = ?) AND opening IS NOT NULL {tc_filter}
        GROUP BY opening
        ORDER BY cnt DESC
        LIMIT 5
    """, [username, username] + tc_params).fetchall()

    game_results = conn.execute(f"""
        SELECT CASE WHEN white = ? THEN white_result ELSE black_result END AS result
        FROM games
        WHERE (white = ? OR black = ?) {tc_filter}
        ORDER BY end_time ASC NULLS LAST
    """, [username, username, username] + tc_params).fetchall()

    streak = 0
    longest_streak = 0
    for (game_result,) in game_results:
        if game_result == "win":
            streak += 1
            if streak > longest_streak:
                longest_streak = streak
        else:
            streak = 0
    current_streak = streak

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
    for tc_name, ym, games_cnt, wins_count in trend_rows:
        tc_name = tc_name or "unknown"
        if tc_name not in trend:
            trend[tc_name] = {}
        pct = round(wins_count / games_cnt * 100, 1) if games_cnt else 0.0
        trend[tc_name][ym] = {"games": games_cnt, "win_pct": pct}

    tod_rows = conn.execute(f"""
        SELECT
            CASE
                WHEN hour(timezone('Asia/Kolkata', to_timestamp(end_time))) BETWEEN 6  AND 11 THEN 'morning'
                WHEN hour(timezone('Asia/Kolkata', to_timestamp(end_time))) BETWEEN 12 AND 17 THEN 'afternoon'
                WHEN hour(timezone('Asia/Kolkata', to_timestamp(end_time))) BETWEEN 18 AND 23 THEN 'evening'
                ELSE 'night'
            END AS period,
            CASE WHEN white = ? THEN white_result ELSE black_result END AS outcome,
            COUNT(*) AS cnt
        FROM games
        WHERE (white = ? OR black = ?) {tc_filter} AND end_time IS NOT NULL
        GROUP BY period, outcome
    """, [username, username, username] + tc_params).fetchall()

    time_of_day: dict = {}
    for period, outcome, cnt in tod_rows:
        if period not in time_of_day:
            time_of_day[period] = {"win": 0, "lose": 0, "draw": 0}
        key = "win" if outcome == "win" else ("lose" if outcome in _LOSS_RESULTS else "draw")
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

    dow_rows = conn.execute(f"""
        SELECT dayofweek(timezone('Asia/Kolkata', to_timestamp(end_time))) AS dow,
               user_result, COUNT(*) AS cnt
        FROM games
        WHERE (white = ? OR black = ?) AND end_time IS NOT NULL
          AND user_result IS NOT NULL {tc_filter}
        GROUP BY dow, user_result
    """, [username, username] + tc_params).fetchall()

    day_of_week: dict = {}
    for dow_int, outcome, cnt in dow_rows:
        name = _DOW_NAMES.get(dow_int, str(dow_int))
        if name not in day_of_week:
            day_of_week[name] = {"win": 0, "lose": 0, "draw": 0}
        key = "win" if outcome == "win" else ("lose" if outcome in _LOSS_RESULTS else "draw")
        day_of_week[name][key] += cnt

    return {
        "total": total,
        "by_time_class": by_time_class,
        "top_openings": top_openings,
        "current_streak": current_streak,
        "longest_streak": longest_streak,
        "trend": trend,
        "time_of_day": time_of_day,
        "game_phase_losses": game_phase_losses,
        "by_color": by_color,
        "best_openings": best_opening_rows,
        "worst_openings": worst_opening_rows,
        "time_pressure": time_pressure,
        "rating_range": rating_range,
        "day_of_week": day_of_week,
    }


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
    current = {(tc or "unknown"): elo for tc, elo in rows}

    t = time.gmtime()
    month_start = int(datetime.datetime(t.tm_year, t.tm_mon, 1,
                                        tzinfo=datetime.timezone.utc).timestamp())
    first_rows = conn.execute("""
        SELECT time_class,
               CASE WHEN white = ? THEN white_elo ELSE black_elo END AS elo
        FROM games
        WHERE (white = ? OR black = ?) AND end_time >= ? AND end_time IS NOT NULL
          AND CASE WHEN white = ? THEN white_elo ELSE black_elo END IS NOT NULL
        QUALIFY ROW_NUMBER() OVER (PARTITION BY time_class ORDER BY end_time ASC) = 1
    """, [username, username, username, month_start, username]).fetchall()
    first_of_month = {(tc or "unknown"): elo for tc, elo in first_rows}

    result = {}
    for tc, elo in current.items():
        first_elo = first_of_month.get(tc)
        delta = (elo - first_elo) if first_elo is not None else None
        result[tc] = {"current": elo, "delta": delta}
    return result


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
