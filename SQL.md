# Chess Game Analysis — SQL Reference

All queries run against `data/rathnakaragn.duckdb`.

```bash
python main.py query "<SQL>" --db data/rathnakaragn.duckdb
```

Replace `rathnakaragn` with your username where needed.

---

## Table Schema

| Column | Type | Description |
|--------|------|-------------|
| `url` | TEXT | Primary key — unique game URL |
| `pgn` | TEXT | Full PGN string |
| `time_class` | TEXT | `bullet`, `blitz`, `rapid`, `daily` |
| `time_control` | TEXT | e.g. `600`, `180+2` |
| `end_time` | INTEGER | Unix timestamp (seconds) |
| `white` | TEXT | White player username |
| `black` | TEXT | Black player username |
| `white_result` | TEXT | Raw result: `win`, `resigned`, `timeout`, etc. |
| `black_result` | TEXT | Raw result |
| `white_elo` | INTEGER | White rating at game time |
| `black_elo` | INTEGER | Black rating at game time |
| `eco` | TEXT | ECO code (e.g. `B20`) |
| `opening` | TEXT | Opening name (e.g. `Sicilian Defense`) |
| `move_count` | INTEGER | Total half-moves |
| `game_duration_secs` | INTEGER | Wall-clock duration |
| `termination` | TEXT | How game ended |
| `color` | TEXT | `white` or `black` (relative to tracked user) |
| `opponent` | TEXT | Opponent username |
| `user_result` | TEXT | `win`, `lose`, or `draw` (relative to tracked user) |
| `white_time_used_secs` | INTEGER | Clock time used by white |
| `black_time_used_secs` | INTEGER | Clock time used by black |

---

## Overall Summary

```sql
-- Total games by time control
SELECT time_class, COUNT(*) AS games,
       SUM(CASE WHEN user_result = 'win' THEN 1 ELSE 0 END) AS wins,
       ROUND(100.0 * SUM(CASE WHEN user_result = 'win' THEN 1 ELSE 0 END) / COUNT(*), 1) AS win_pct
FROM games
WHERE white = 'rathnakaragn' OR black = 'rathnakaragn'
GROUP BY time_class
ORDER BY games DESC
```

```sql
-- Games per month (all formats)
SELECT strftime(to_timestamp(end_time), '%Y-%m') AS month,
       COUNT(*) AS games
FROM games
WHERE (white = 'rathnakaragn' OR black = 'rathnakaragn')
  AND end_time IS NOT NULL
GROUP BY month
ORDER BY month DESC
LIMIT 24
```

---

## Win / Loss / Draw

```sql
-- W/L/D breakdown by format
SELECT time_class,
       SUM(CASE WHEN user_result = 'win'  THEN 1 ELSE 0 END) AS wins,
       SUM(CASE WHEN user_result = 'lose' THEN 1 ELSE 0 END) AS losses,
       SUM(CASE WHEN user_result = 'draw' THEN 1 ELSE 0 END) AS draws,
       COUNT(*) AS total,
       ROUND(100.0 * SUM(CASE WHEN user_result = 'win' THEN 1 ELSE 0 END) / COUNT(*), 1) AS win_pct
FROM games
WHERE (white = 'rathnakaragn' OR black = 'rathnakaragn')
  AND user_result IS NOT NULL
GROUP BY time_class
ORDER BY total DESC
```

```sql
-- Win rate by color
SELECT color,
       SUM(CASE WHEN user_result = 'win'  THEN 1 ELSE 0 END) AS wins,
       SUM(CASE WHEN user_result = 'lose' THEN 1 ELSE 0 END) AS losses,
       SUM(CASE WHEN user_result = 'draw' THEN 1 ELSE 0 END) AS draws,
       ROUND(100.0 * SUM(CASE WHEN user_result = 'win' THEN 1 ELSE 0 END) / COUNT(*), 1) AS win_pct
FROM games
WHERE (white = 'rathnakaragn' OR black = 'rathnakaragn')
  AND color IS NOT NULL AND user_result IS NOT NULL
GROUP BY color
```

```sql
-- How games end (termination types)
SELECT termination, COUNT(*) AS cnt
FROM games
WHERE white = 'rathnakaragn' OR black = 'rathnakaragn'
GROUP BY termination
ORDER BY cnt DESC
```

---

## Rating

```sql
-- Rating over time (rapid only, monthly)
SELECT strftime(to_timestamp(end_time), '%Y-%m') AS month,
       MAX(CASE WHEN color = 'white' THEN white_elo ELSE black_elo END) AS elo_end
FROM games
WHERE (white = 'rathnakaragn' OR black = 'rathnakaragn')
  AND time_class = 'rapid' AND end_time IS NOT NULL
GROUP BY month
ORDER BY month DESC
LIMIT 24
```

```sql
-- Current rating per format (last game played)
SELECT time_class,
       LAST(CASE WHEN color = 'white' THEN white_elo ELSE black_elo END
            ORDER BY end_time) AS current_elo
FROM games
WHERE (white = 'rathnakaragn' OR black = 'rathnakaragn')
  AND end_time IS NOT NULL
GROUP BY time_class
```

```sql
-- Biggest rating gains (single game, rapid)
SELECT strftime(to_timestamp(end_time), '%Y-%m-%d') AS date,
       opponent,
       CASE WHEN color = 'white' THEN black_elo ELSE white_elo END AS opp_elo,
       user_result, opening
FROM games
WHERE (white = 'rathnakaragn' OR black = 'rathnakaragn')
  AND time_class = 'rapid' AND user_result = 'win'
  AND (CASE WHEN color = 'white' THEN black_elo ELSE white_elo END) >
      (CASE WHEN color = 'white' THEN white_elo ELSE black_elo END) + 100
ORDER BY (CASE WHEN color = 'white' THEN black_elo ELSE white_elo END) -
         (CASE WHEN color = 'white' THEN white_elo ELSE black_elo END) DESC
LIMIT 20
```

---

## Openings

```sql
-- Top 20 openings by frequency (rapid)
SELECT opening, COUNT(*) AS games,
       SUM(CASE WHEN user_result = 'win'  THEN 1 ELSE 0 END) AS wins,
       SUM(CASE WHEN user_result = 'lose' THEN 1 ELSE 0 END) AS losses,
       SUM(CASE WHEN user_result = 'draw' THEN 1 ELSE 0 END) AS draws,
       ROUND(100.0 * SUM(CASE WHEN user_result = 'win' THEN 1 ELSE 0 END) / COUNT(*), 1) AS win_pct
FROM games
WHERE (white = 'rathnakaragn' OR black = 'rathnakaragn')
  AND time_class = 'rapid' AND opening IS NOT NULL
GROUP BY opening
ORDER BY games DESC
LIMIT 20
```

```sql
-- Best openings by win rate (min 10 games, rapid)
SELECT opening, COUNT(*) AS games,
       ROUND(100.0 * SUM(CASE WHEN user_result = 'win' THEN 1 ELSE 0 END) / COUNT(*), 1) AS win_pct
FROM games
WHERE (white = 'rathnakaragn' OR black = 'rathnakaragn')
  AND time_class = 'rapid' AND opening IS NOT NULL AND user_result IS NOT NULL
GROUP BY opening
HAVING COUNT(*) >= 10
ORDER BY win_pct DESC
LIMIT 10
```

```sql
-- Worst openings by win rate (min 10 games, rapid)
SELECT opening, COUNT(*) AS games,
       ROUND(100.0 * SUM(CASE WHEN user_result = 'win' THEN 1 ELSE 0 END) / COUNT(*), 1) AS win_pct
FROM games
WHERE (white = 'rathnakaragn' OR black = 'rathnakaragn')
  AND time_class = 'rapid' AND opening IS NOT NULL AND user_result IS NOT NULL
GROUP BY opening
HAVING COUNT(*) >= 10
ORDER BY win_pct ASC
LIMIT 10
```

```sql
-- Opening performance as white vs black
SELECT opening, color, COUNT(*) AS games,
       ROUND(100.0 * SUM(CASE WHEN user_result = 'win' THEN 1 ELSE 0 END) / COUNT(*), 1) AS win_pct
FROM games
WHERE (white = 'rathnakaragn' OR black = 'rathnakaragn')
  AND time_class = 'rapid' AND opening IS NOT NULL AND color IS NOT NULL
GROUP BY opening, color
HAVING COUNT(*) >= 5
ORDER BY opening, color
```

---

## Opponents

```sql
-- Most played opponents (rapid)
SELECT opponent, COUNT(*) AS games,
       SUM(CASE WHEN user_result = 'win'  THEN 1 ELSE 0 END) AS wins,
       SUM(CASE WHEN user_result = 'lose' THEN 1 ELSE 0 END) AS losses,
       ROUND(100.0 * SUM(CASE WHEN user_result = 'win' THEN 1 ELSE 0 END) / COUNT(*), 1) AS win_pct
FROM games
WHERE (white = 'rathnakaragn' OR black = 'rathnakaragn')
  AND time_class = 'rapid' AND opponent IS NOT NULL
GROUP BY opponent
ORDER BY games DESC
LIMIT 20
```

```sql
-- Toughest opponents (most losses, min 3 games)
SELECT opponent, COUNT(*) AS games,
       SUM(CASE WHEN user_result = 'lose' THEN 1 ELSE 0 END) AS losses,
       ROUND(100.0 * SUM(CASE WHEN user_result = 'win' THEN 1 ELSE 0 END) / COUNT(*), 1) AS win_pct
FROM games
WHERE (white = 'rathnakaragn' OR black = 'rathnakaragn')
  AND time_class = 'rapid' AND opponent IS NOT NULL
GROUP BY opponent
HAVING COUNT(*) >= 3
ORDER BY losses DESC
LIMIT 20
```

```sql
-- Performance vs opponent rating bands
SELECT
  CASE
    WHEN (CASE WHEN color = 'white' THEN black_elo ELSE white_elo END) -
         (CASE WHEN color = 'white' THEN white_elo ELSE black_elo END) < -200 THEN 'Much weaker  (<-200)'
    WHEN (CASE WHEN color = 'white' THEN black_elo ELSE white_elo END) -
         (CASE WHEN color = 'white' THEN white_elo ELSE black_elo END) < -100 THEN 'Weaker      (-200 to -100)'
    WHEN (CASE WHEN color = 'white' THEN black_elo ELSE white_elo END) -
         (CASE WHEN color = 'white' THEN white_elo ELSE black_elo END) <= 100 THEN 'Similar     (-100 to +100)'
    WHEN (CASE WHEN color = 'white' THEN black_elo ELSE white_elo END) -
         (CASE WHEN color = 'white' THEN white_elo ELSE black_elo END) <= 200 THEN 'Stronger    (+100 to +200)'
    ELSE                                                                            'Much stronger  (>+200)'
  END AS band,
  COUNT(*) AS games,
  ROUND(100.0 * SUM(CASE WHEN user_result = 'win' THEN 1 ELSE 0 END) / COUNT(*), 1) AS win_pct
FROM games
WHERE (white = 'rathnakaragn' OR black = 'rathnakaragn')
  AND time_class = 'rapid' AND color IS NOT NULL
  AND white_elo IS NOT NULL AND black_elo IS NOT NULL
GROUP BY band
ORDER BY band
```

---

## Time & Clock

```sql
-- Average game length by format (minutes)
SELECT time_class,
       ROUND(AVG(game_duration_secs) / 60.0, 1) AS avg_duration_min,
       ROUND(AVG(move_count) / 2.0, 1) AS avg_moves
FROM games
WHERE (white = 'rathnakaragn' OR black = 'rathnakaragn')
  AND game_duration_secs IS NOT NULL
GROUP BY time_class
```

```sql
-- Win rate by time of day (IST)
SELECT
  CASE
    WHEN hour(to_timestamp(end_time)) BETWEEN 6  AND 11 THEN 'Morning   (06-12)'
    WHEN hour(to_timestamp(end_time)) BETWEEN 12 AND 16 THEN 'Afternoon (12-17)'
    WHEN hour(to_timestamp(end_time)) BETWEEN 17 AND 20 THEN 'Evening   (17-21)'
    ELSE                                                      'Night     (21-06)'
  END AS period,
  COUNT(*) AS games,
  ROUND(100.0 * SUM(CASE WHEN user_result = 'win' THEN 1 ELSE 0 END) / COUNT(*), 1) AS win_pct
FROM games
WHERE (white = 'rathnakaragn' OR black = 'rathnakaragn')
  AND end_time IS NOT NULL AND user_result IS NOT NULL
  AND time_class = 'rapid'
GROUP BY period
ORDER BY period
```

```sql
-- Win rate by day of week (IST)
SELECT
  CASE dayofweek(to_timestamp(end_time))
    WHEN 0 THEN 'Sun' WHEN 1 THEN 'Mon' WHEN 2 THEN 'Tue'
    WHEN 3 THEN 'Wed' WHEN 4 THEN 'Thu' WHEN 5 THEN 'Fri' WHEN 6 THEN 'Sat'
  END AS day,
  COUNT(*) AS games,
  ROUND(100.0 * SUM(CASE WHEN user_result = 'win' THEN 1 ELSE 0 END) / COUNT(*), 1) AS win_pct
FROM games
WHERE (white = 'rathnakaragn' OR black = 'rathnakaragn')
  AND end_time IS NOT NULL AND user_result IS NOT NULL
  AND time_class = 'rapid'
GROUP BY day, dayofweek(to_timestamp(end_time))
ORDER BY dayofweek(to_timestamp(end_time))
```

```sql
-- Time pressure: % of clock used vs win rate (rapid)
SELECT
  CASE
    WHEN (CASE WHEN color = 'white' THEN white_time_used_secs ELSE black_time_used_secs END) * 100.0
         / CAST(regexp_extract(time_control, '^\d+') AS INTEGER) < 30 THEN '< 30% (comfortable)'
    WHEN (CASE WHEN color = 'white' THEN white_time_used_secs ELSE black_time_used_secs END) * 100.0
         / CAST(regexp_extract(time_control, '^\d+') AS INTEGER) < 70 THEN '30-70% (moderate)'
    ELSE '> 70% (under pressure)'
  END AS pressure_bucket,
  COUNT(*) AS games,
  ROUND(100.0 * SUM(CASE WHEN user_result = 'win' THEN 1 ELSE 0 END) / COUNT(*), 1) AS win_pct
FROM games
WHERE (white = 'rathnakaragn' OR black = 'rathnakaragn')
  AND time_class = 'rapid' AND color IS NOT NULL AND user_result IS NOT NULL
  AND white_time_used_secs IS NOT NULL AND black_time_used_secs IS NOT NULL
  AND time_control NOT LIKE '%/%'
GROUP BY pressure_bucket
ORDER BY pressure_bucket
```

---

## Streaks & Momentum

```sql
-- Longest losing streaks (rapid) — find consecutive losses
WITH ranked AS (
  SELECT end_time, user_result,
         ROW_NUMBER() OVER (ORDER BY end_time) -
         ROW_NUMBER() OVER (PARTITION BY user_result ORDER BY end_time) AS grp
  FROM games
  WHERE (white = 'rathnakaragn' OR black = 'rathnakaragn')
    AND time_class = 'rapid' AND user_result IS NOT NULL
),
streaks AS (
  SELECT user_result, COUNT(*) AS streak_len,
         MIN(end_time) AS started, MAX(end_time) AS ended
  FROM ranked
  GROUP BY user_result, grp
)
SELECT user_result,
       streak_len,
       strftime(to_timestamp(started), '%Y-%m-%d') AS started,
       strftime(to_timestamp(ended),   '%Y-%m-%d') AS ended
FROM streaks
WHERE user_result = 'lose'
ORDER BY streak_len DESC
LIMIT 10
```

```sql
-- Last 30 games trend (rapid)
SELECT strftime(to_timestamp(end_time), '%Y-%m-%d') AS date,
       user_result, opening, opponent,
       CASE WHEN color = 'white' THEN white_elo ELSE black_elo END AS my_elo
FROM games
WHERE (white = 'rathnakaragn' OR black = 'rathnakaragn')
  AND time_class = 'rapid' AND end_time IS NOT NULL
ORDER BY end_time DESC
LIMIT 30
```

---

## Game Quality

```sql
-- Games decided by timeout (flagging)
SELECT time_class,
       SUM(CASE WHEN white_result = 'timeout' OR black_result = 'timeout' THEN 1 ELSE 0 END) AS timeouts,
       COUNT(*) AS total,
       ROUND(100.0 * SUM(CASE WHEN white_result = 'timeout' OR black_result = 'timeout' THEN 1 ELSE 0 END)
             / COUNT(*), 1) AS timeout_pct
FROM games
WHERE white = 'rathnakaragn' OR black = 'rathnakaragn'
GROUP BY time_class
```

```sql
-- Short games (< 10 moves) — likely early resignations or blunders
SELECT strftime(to_timestamp(end_time), '%Y-%m-%d') AS date,
       time_class, move_count, user_result, opponent, opening
FROM games
WHERE (white = 'rathnakaragn' OR black = 'rathnakaragn')
  AND move_count IS NOT NULL AND move_count < 20
  AND time_class = 'rapid'
ORDER BY move_count ASC
LIMIT 20
```

```sql
-- Long games (most moves, rapid)
SELECT strftime(to_timestamp(end_time), '%Y-%m-%d') AS date,
       move_count, game_duration_secs / 60 AS duration_min,
       user_result, opponent, opening
FROM games
WHERE (white = 'rathnakaragn' OR black = 'rathnakaragn')
  AND time_class = 'rapid' AND move_count IS NOT NULL
ORDER BY move_count DESC
LIMIT 20
```

---

## Monthly Deep Dive

```sql
-- This month's rapid games
SELECT strftime(to_timestamp(end_time), '%Y-%m-%d') AS date,
       user_result, color, opponent,
       CASE WHEN color = 'white' THEN white_elo ELSE black_elo END AS my_elo,
       CASE WHEN color = 'white' THEN black_elo ELSE white_elo END AS opp_elo,
       opening
FROM games
WHERE (white = 'rathnakaragn' OR black = 'rathnakaragn')
  AND time_class = 'rapid'
  AND strftime(to_timestamp(end_time), '%Y-%m') = strftime(now(), '%Y-%m')
ORDER BY end_time DESC
```

```sql
-- Monthly win rate trend (rapid, last 12 months)
SELECT strftime(to_timestamp(end_time), '%Y-%m') AS month,
       COUNT(*) AS games,
       SUM(CASE WHEN user_result = 'win'  THEN 1 ELSE 0 END) AS wins,
       SUM(CASE WHEN user_result = 'lose' THEN 1 ELSE 0 END) AS losses,
       ROUND(100.0 * SUM(CASE WHEN user_result = 'win' THEN 1 ELSE 0 END) / COUNT(*), 1) AS win_pct
FROM games
WHERE (white = 'rathnakaragn' OR black = 'rathnakaragn')
  AND time_class = 'rapid' AND end_time IS NOT NULL
GROUP BY month
ORDER BY month DESC
LIMIT 12
```
