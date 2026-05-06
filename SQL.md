# Chess Game Analysis — SQL Reference

Run queries with `CHESS_USERNAME` set (or pass `--username`):

```bash
# Inline SQL — $USERNAME is substituted automatically
python main.py query "SELECT COUNT(*) FROM games WHERE white = $USERNAME OR black = $USERNAME"

# From a file
python main.py query queries/general/summary.sql

# Override username for one query
python main.py query queries/general/summary.sql --username neopaque
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
| `move_count` | INTEGER | Last full-move number |
| `game_duration_secs` | INTEGER | Wall-clock duration in seconds |
| `termination` | TEXT | How game ended |
| `color` | TEXT | `white` or `black` (relative to tracked user) |
| `opponent` | TEXT | Opponent username |
| `user_result` | TEXT | `win`, `lose`, or `draw` (relative to tracked user) |
| `white_time_used_secs` | INTEGER | Total clock time used by white |
| `black_time_used_secs` | INTEGER | Total clock time used by black |

---

## Query Files

94 pre-built queries organised into 7 categories. All use `$USERNAME` substituted at runtime.

```bash
python main.py query queries/<category>/<file>.sql
```

### General

| File | Description |
|------|-------------|
| `general/summary.sql` | W/L/D and win% by time control |
| `general/recent_games.sql` | Last 30 rapid games with rating and opening |

### Performance

| File | Description |
|------|-------------|
| `performance/monthly_trend.sql` | Monthly win rate (rapid, last 12 months) |
| `performance/rating_history.sql` | Monthly rating high/low (rapid) |
| `performance/rating_momentum.sql` | Rolling 10-game win% — hot/cold streaks |
| `performance/draw_by_rating.sql` | Draw rate vs weaker/equal/stronger |
| `performance/format_switching.sql` | First-of-session vs warmed-up win rate |
| `performance/game_length_sweet_spot.sql` | Win rate by move count bucket |
| `performance/termination_breakdown.sql` | How games end — resignation/checkmate/timeout |
| `performance/volume_vs_quality.sql` | Monthly game count vs win rate |

### Openings — General

| File | Description |
|------|-------------|
| `openings/openings_best.sql` | Best openings by win% (min 10 games) |
| `openings/openings_worst.sql` | Worst openings by win% |
| `openings/openings_by_color.sql` | Opening win% split by color |
| `openings/opening_loyalty.sql` | Core repertoire vs regular vs one-off |
| `openings/opening_trend.sql` | Win% by 6-month period per opening |
| `openings/draw_by_opening.sql` | Openings with highest draw rate |
| `openings/eco_family.sql` | Performance by ECO family (A/B/C/D/E) |

### Openings — White Responses

| File | Description |
|------|-------------|
| `openings/white_responses/white_first_move_summary.sql` | Your 2nd move vs every Black reply |
| `openings/white_responses/vs_e5_wayward_queen.sql` | WQ monthly trend by time class |
| `openings/white_responses/vs_d5_gap.sql` | Biggest gap — responses to 1...d5 |
| `openings/white_responses/vs_c5_sicilian.sql` | Responses to 1...c5 Sicilian |
| `openings/white_responses/vs_nc6_gap.sql` | Responses to 1...Nc6 (5-move chaos) |
| `openings/white_responses/vs_c6_e6.sql` | Consistent d4 system vs 1...c6/e6 |
| `openings/white_responses/white_move_sequence_wins_vs_losses.sql` | WQ moves 3-8 win% per move choice |

### Openings — Black Responses

| File | Description |
|------|-------------|
| `openings/black_responses/black_first_move_summary.sql` | Your reply to every White first move |
| `openings/black_responses/vs_e4_scandinavian.sql` | Scandinavian monthly trend |
| `openings/black_responses/vs_d4_replies.sql` | Replies to 1.d4 — c5 vs d5 |
| `openings/black_responses/vs_nf3_gap.sql` | Biggest gap — vs 1.Nf3 (26% win rate) |
| `openings/black_responses/vs_nc3_gap.sql` | Second gap — vs 1.Nc3 (~22%) |
| `openings/black_responses/vs_c4_strong.sql` | Strongest area — vs 1.c4 (71%) |
| `openings/black_responses/black_move_sequence_wins_vs_losses.sql` | Scandinavian moves 2-6 win% |

### Openings — Traps

| File | Description |
|------|-------------|
| `openings/traps/wayward_queen_attack/wayward_queen.sql` | WQ summary by format |
| `openings/traps/wayward_queen_attack/wayward_queen_monthly.sql` | Monthly win rate trend |
| `openings/traps/wayward_queen_attack/wayward_queen_responses.sql` | Black's 2nd move and win rate |
| `openings/traps/wayward_queen_attack/wayward_queen_opp_rating.sql` | Win% by opponent ELO bucket |
| `openings/traps/wayward_queen_attack/wayward_queen_length.sql` | Win% by game length |
| `openings/traps/wayward_queen_attack/wayward_queen_termination.sql` | How WQ games end |
| `openings/traps/wayward_queen_attack/wayward_queen_posttrap.sql` | Post-trap conversion rate |
| `openings/traps/wayward_queen_attack/wayward_queen_recent.sql` | 20 most recent WQ games |
| `openings/traps/wayward_queen_attack/wayward_queen_top_wins.sql` | Highest rated opponents beaten |
| `openings/traps/wayward_queen_attack/wayward_queen_overall_monthly.sql` | All-termination monthly trend |

### Openings — Gambits

| File | Description |
|------|-------------|
| `openings/gambits/icelandic_gambit/icelandic_gambit.sql` | Icelandic summary by format (Black) |
| `openings/gambits/icelandic_gambit/icelandic_gambit_monthly.sql` | Monthly trend |
| `openings/gambits/icelandic_gambit/icelandic_gambit_responses.sql` | White's 4th move responses |
| `openings/gambits/icelandic_gambit/icelandic_gambit_opp_rating.sql` | Win% by ELO |
| `openings/gambits/icelandic_gambit/icelandic_gambit_length.sql` | Win% by game length |
| `openings/gambits/icelandic_gambit/icelandic_gambit_termination.sql` | How games end |
| `openings/gambits/icelandic_gambit/icelandic_gambit_recent.sql` | 20 most recent games |
| `openings/gambits/icelandic_gambit/icelandic_gambit_top_wins.sql` | Highest rated opponents beaten |
| `openings/gambits/blackmar_diemer_gambit/blackmar_diemer.sql` | BDG summary (White vs 1...d5) |
| `openings/gambits/blackmar_diemer_gambit/blackmar_diemer_monthly.sql` | Monthly trend |
| `openings/gambits/blackmar_diemer_gambit/blackmar_diemer_responses.sql` | Black's 3rd move |
| `openings/gambits/blackmar_diemer_gambit/blackmar_diemer_opp_rating.sql` | Win% by ELO |
| `openings/gambits/blackmar_diemer_gambit/blackmar_diemer_length.sql` | Win% by game length |
| `openings/gambits/blackmar_diemer_gambit/blackmar_diemer_termination.sql` | How games end |
| `openings/gambits/blackmar_diemer_gambit/blackmar_diemer_recent.sql` | 20 most recent games |
| `openings/gambits/blackmar_diemer_gambit/blackmar_diemer_top_wins.sql` | Highest rated opponents beaten |
| `openings/gambits/smith_morra_gambit/smith_morra.sql` | Smith-Morra summary (White vs 1...c5) |
| `openings/gambits/smith_morra_gambit/smith_morra_monthly.sql` | Monthly trend |
| `openings/gambits/smith_morra_gambit/smith_morra_responses.sql` | Black's 3rd move |
| `openings/gambits/smith_morra_gambit/smith_morra_length.sql` | Win% by game length |
| `openings/gambits/smith_morra_gambit/smith_morra_termination.sql` | How games end |
| `openings/gambits/smith_morra_gambit/smith_morra_recent.sql` | 20 most recent games |
| `openings/gambits/smith_morra_gambit/smith_morra_top_wins.sql` | Highest rated opponents beaten |

### Opponents

| File | Description |
|------|-------------|
| `opponents/opponents_most_played.sql` | Most frequent opponents |
| `opponents/opponents_toughest.sql` | Opponents with most wins against you |
| `opponents/biggest_upsets.sql` | Wins against opponents rated 100+ higher |
| `opponents/rematch_record.sql` | Revenge vs tilt in rematches |
| `opponents/rating_vs_opponent.sql` | Win% by opponent rating band |
| `opponents/draw_by_rating.sql` | Draw rate vs weaker/equal/stronger |
| `opponents/fresh_vs_repeat.sql` | First game vs repeat opponents |
| `opponents/titled_opponent_effect.sql` | Win% vs GM/IM/FM/CM/NM vs untitled |

### Psychology

| File | Description |
|------|-------------|
| `psychology/tilt_detection.sql` | Win% after win/loss/draw — detects tilt |
| `psychology/revenge_spiral.sql` | Win% in games 1-5 after a loss |
| `psychology/losing_streaks.sql` | Longest losing streaks |
| `psychology/win_streaks.sql` | Longest winning streaks |
| `psychology/color_gap_after_loss.sql` | Does losing as White affect Black games? |
| `psychology/collapse_recovery.sql` | Next game after a long vs short loss |
| `psychology/rating_anxiety.sql` | Win% near rating milestones (every 50 pts) |
| `psychology/session_fatigue.sql` | Win% by game number in a session |
| `psychology/rest_effect.sql` | Win% by break length before session |
| `psychology/streak_day_performance.sql` | Multi-day streaks: momentum or burnout? |

### Time

| File | Description |
|------|-------------|
| `time/time_pressure.sql` | Win% by % of clock used |
| `time/time_pressure_monthly.sql` | Time pressure trend month by month |
| `time/clock_battle.sql` | Win% by clock ratio (you vs opponent) |
| `time/time_of_day.sql` | Win% by time of day (IST) |
| `time/day_of_week.sql` | Win% by day of week |
| `time/day_time_combined.sql` | Day × time slot peak performance |

> `time/first_move_speed.py` parses `[%clk]` PGN annotations:
> ```bash
> .venv/bin/python queries/time/first_move_speed.py
> ```

### Checkmates

| File | Description |
|------|-------------|
| `checkmates/checkmate_distribution.sql` | Checkmate win/loss ratio by opening |
| `checkmates/checkmate_openings.sql` | Which openings end in checkmate most |
| `checkmates/fastest_checkmates.sql` | Your fastest checkmate wins |
| `checkmates/fastest_mated.sql` | Games where you were mated fastest |
| `checkmates/missed_mates_summary.sql` | Monthly missed M1/M2 summary |
| `checkmates/missed_mates_by_opening.sql` | Which openings produce most missed mates |
| `checkmates/missed_mates_recent.sql` | Recent missed mates with game links |

> `checkmates/missed_mates.py` — one-time scan (requires python-chess):
> ```bash
> .venv/bin/python queries/checkmates/missed_mates.py
> .venv/bin/python queries/checkmates/missed_mates.py --force  # full rescan
> ```

---

## Ad-hoc Query Examples

### Overall Summary

```sql
-- Games per month (all formats)
SELECT strftime(to_timestamp(end_time), '%Y-%m') AS month,
       COUNT(*) AS games
FROM games
WHERE (white = $USERNAME OR black = $USERNAME)
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
WHERE (white = $USERNAME OR black = $USERNAME)
  AND color IS NOT NULL AND user_result IS NOT NULL
GROUP BY color
```

```sql
-- How games end (termination types)
SELECT termination, COUNT(*) AS cnt
FROM games
WHERE white = $USERNAME OR black = $USERNAME
GROUP BY termination
ORDER BY cnt DESC
```

### Opening Move Analysis

```sql
-- Your 2nd move vs every Black first move (White games)
SELECT regexp_extract(pgn, '1\.\.\. ([A-Za-z][A-Za-z0-9x+#=-]*)', 1) AS black_1st,
       regexp_extract(pgn, '2\. ([A-Za-z][A-Za-z0-9x+#=-]*)', 1)     AS your_2nd,
       COUNT(*) AS games,
       ROUND(100.0 * SUM(CASE WHEN user_result = 'win' THEN 1 ELSE 0 END) / COUNT(*), 1) AS win_pct
FROM games
WHERE white = $USERNAME AND time_class = 'rapid'
GROUP BY black_1st, your_2nd
HAVING COUNT(*) >= 5
ORDER BY black_1st, games DESC
```

```sql
-- Win rate at each move number in WQ games (move 3-8)
SELECT 3 AS move, regexp_extract(pgn, '3\. ([A-Za-z][A-Za-z0-9x+#=-]*)', 1) AS white_move,
       COUNT(*) AS games,
       ROUND(100.0 * SUM(CASE WHEN user_result = 'win' THEN 1 ELSE 0 END) / COUNT(*), 1) AS win_pct
FROM games
WHERE white = $USERNAME AND regexp_matches(pgn, '(^|[\s}])2\. Qh5')
GROUP BY white_move HAVING COUNT(*) >= 5
ORDER BY games DESC
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
WHERE (white = $USERNAME OR black = $USERNAME)
  AND time_class = 'rapid'
  AND strftime(to_timestamp(end_time), '%Y-%m') = strftime(now(), '%Y-%m')
ORDER BY end_time DESC
```
