# Chess Game Analysis — SQL Reference

Two ways to run queries (username read from `CHESS_USERNAME` env var):

```bash
# Inline SQL
python main.py query "SELECT COUNT(*) FROM games"

# From a file — $USERNAME is substituted automatically
python main.py query queries/summary.sql

# Override username for one query
python main.py query queries/summary.sql --username neopaque
```

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
| `move_count` | INTEGER | Last full-move number (e.g. 2 for a game ending on move 2) |
| `game_duration_secs` | INTEGER | Wall-clock duration |
| `termination` | TEXT | How game ended |
| `color` | TEXT | `white` or `black` (relative to tracked user) |
| `opponent` | TEXT | Opponent username |
| `user_result` | TEXT | `win`, `lose`, or `draw` (relative to tracked user) |
| `white_time_used_secs` | INTEGER | Clock time used by white |
| `black_time_used_secs` | INTEGER | Clock time used by black |

---

## Query Files

Pre-built queries in the `queries/` directory. Run with:

```bash
python main.py query queries/<file>.sql
```

### Basic Analysis

| File | Description |
|------|-------------|
| `summary.sql` | W/L/D and win% by time control |
| `monthly_trend.sql` | Monthly win rate (rapid, last 12 months) |
| `recent_games.sql` | Last 30 rapid games with rating and opening |

### Openings

| File | Description |
|------|-------------|
| `openings_best.sql` | Best openings by win rate (min 10 games) |
| `openings_worst.sql` | Worst openings by win rate (min 10 games) |
| `openings_by_color.sql` | Opening win rate split by color |
| `opening_loyalty.sql` | Core repertoire vs regular vs one-off experiments |
| `draw_by_opening.sql` | Openings with highest draw rate |
| `eco_family.sql` | Performance by ECO family (A/B/C/D/E) |

### Opponents

| File | Description |
|------|-------------|
| `opponents_most_played.sql` | Most played opponents |
| `opponents_toughest.sql` | Opponents with most wins against you |
| `biggest_upsets.sql` | Your wins against opponents rated 100+ higher |
| `rematch_record.sql` | Result in rematches — revenge or tilt? |

### Rating

| File | Description |
|------|-------------|
| `rating_history.sql` | Monthly rating high/low (rapid) |
| `rating_vs_opponent.sql` | Win rate vs opponent strength bands |
| `rating_momentum.sql` | Rolling 10-game win rate — hot and cold streaks |
| `draw_by_rating.sql` | Draw rate vs weaker / similar / stronger opponents |

### Patterns & Psychology

| File | Description |
|------|-------------|
| `tilt_detection.sql` | Win rate after a win/loss/draw — detects tilt |
| `session_fatigue.sql` | Win rate by game number in a session — detects fatigue |
| `game_length_sweet_spot.sql` | Win rate by move count — short tactical vs long grind |
| `time_pressure.sql` | Win rate by % of clock used |
| `time_of_day.sql` | Win rate by time of day (IST) |
| `day_of_week.sql` | Win rate by day of week |
| `losing_streaks.sql` | Longest losing streaks |

### Mindset & Psychology (Deep)

Run Python scripts directly (not via `query` command):

| File | Description |
|------|-------------|
| `revenge_spiral.sql` | Win rate in games 1–5 after a loss — revenge vs tilt |
| `rest_effect.sql` | Win rate by break length: same session → 7+ days |
| `format_switching.sql` | First-of-session vs same-format vs switched-format win rate |
| `collapse_recovery.sql` | Next game after long loss (collapse) vs short loss (blunder) |
| `day_time_combined.sql` | Day of week × time of day combined — peak performance slot |
| `rating_anxiety.sql` | Win rate near rating milestones (every 50 pts) — choke factor |
| `titled_opponent_effect.sql` | Intimidation factor vs GM/IM/FM/CM/NM vs untitled |
| `streak_day_performance.sql` | Consecutive-day streak: does momentum build or fatigue accumulate? |
| `color_gap_after_loss.sql` | White/black mindset gap — does losing as one color affect the other? |
| `first_move_speed.py` | First move response time vs win rate — impulsive vs deliberate openers |

> **Note:** `first_move_speed.py` parses `[%clk]` PGN annotations and runs as a standalone script:
> ```bash
> .venv/bin/python queries/first_move_speed.py [--user <username>]
> # username defaults to $CHESS_USERNAME
> ```

---

## Ad-hoc Query Examples

### Overall Summary

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

### Win / Loss / Draw

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

### Game Quality

```sql
-- Short games: likely early blunders or resignations (rapid, < 20 half-moves)
SELECT strftime(to_timestamp(end_time), '%Y-%m-%d') AS date,
       move_count, user_result, opponent, opening
FROM games
WHERE (white = 'rathnakaragn' OR black = 'rathnakaragn')
  AND move_count IS NOT NULL AND move_count < 20
  AND time_class = 'rapid'
ORDER BY move_count ASC
LIMIT 20
```

```sql
-- Longest games (most moves, rapid)
SELECT strftime(to_timestamp(end_time), '%Y-%m-%d') AS date,
       move_count, game_duration_secs / 60 AS duration_min,
       user_result, opponent, opening
FROM games
WHERE (white = 'rathnakaragn' OR black = 'rathnakaragn')
  AND time_class = 'rapid' AND move_count IS NOT NULL
ORDER BY move_count DESC
LIMIT 20
```

```sql
-- Average game length by format
SELECT time_class,
       ROUND(AVG(game_duration_secs) / 60.0, 1) AS avg_duration_min,
       ROUND(AVG(move_count) / 2.0, 1) AS avg_moves
FROM games
WHERE (white = 'rathnakaragn' OR black = 'rathnakaragn')
  AND game_duration_secs IS NOT NULL
GROUP BY time_class
```

```sql
-- Timeout (flagging) rate by format
SELECT time_class,
       SUM(CASE WHEN white_result = 'timeout' OR black_result = 'timeout' THEN 1 ELSE 0 END) AS timeouts,
       COUNT(*) AS total,
       ROUND(100.0 * SUM(CASE WHEN white_result = 'timeout' OR black_result = 'timeout' THEN 1 ELSE 0 END)
             / COUNT(*), 1) AS timeout_pct
FROM games
WHERE white = 'rathnakaragn' OR black = 'rathnakaragn'
GROUP BY time_class
```

### This Month

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
