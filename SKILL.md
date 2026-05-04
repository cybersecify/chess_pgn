# Chess Analysis Skills Guide

A practical reference for analysing your chess.com games with this tool — what questions you can ask, which commands answer them, and how to interpret the results.

---

## Setup

```bash
export CHESS_USERNAME=your_username   # set once in ~/.zshrc or .envrc
python main.py sync                   # download all games
```

All commands below read `CHESS_USERNAME` from the environment. Pass `--username <name>` to override for a single command.

---

## Core Skills

### 1. Overall Performance Picture

**Question:** How am I doing overall? What's my win rate by format?

```bash
python main.py stats                        # full dashboard
python main.py stats --time-class rapid     # rapid only
python main.py query queries/summary.sql    # W/L/D + win% per time control
```

The `stats` dashboard shows: win/loss/draw by time control, top openings, current and longest win streak, monthly trend, time-of-day breakdown, color win rates, best/worst openings, time pressure performance, opponent rating bands, and day-of-week performance.

---

### 2. Rating Trajectory

**Question:** Is my rating going up, down, or flat? When was I at my best?

```bash
python main.py rating                           # current rating + monthly delta
python main.py query queries/rating_history.sql # monthly high/low (rapid)
python main.py query queries/rating_momentum.sql # rolling 10-game win% — hot/cold streaks
python main.py query queries/monthly_trend.sql   # monthly win rate, last 12 months
```

`rating_momentum.sql` is the best signal for identifying hot and cold patches — look for stretches where rolling win% stays above 55% or drops below 40%.

---

### 3. Opening Repertoire

**Question:** Which openings win for me? Which am I wasting time on?

```bash
python main.py query queries/openings_best.sql    # top 10 openings by win% (min 10 games)
python main.py query queries/openings_worst.sql   # worst 10 openings by win%
python main.py query queries/openings_by_color.sql # win% split by white/black
python main.py query queries/opening_loyalty.sql   # core repertoire vs experiments
python main.py query queries/draw_by_opening.sql   # openings that end in draws most
python main.py query queries/eco_family.sql         # performance by ECO family (A/B/C/D/E)
```

**How to read `opening_loyalty.sql`:**
- **Core** (10+ games): your actual repertoire — invest here
- **Regular** (4–9 games): developing repertoire — worth continuing if win% is good
- **One-off** (1–3 games): experiments — either commit or drop

**Actionable rule:** If an opening in your Core has win% below 40%, consider replacing it. If a one-off has a perfect record, try it more.

---

### 4. Opponent Analysis

**Question:** Who beats me the most? How do I do against stronger players?

```bash
python main.py opponent <username>                    # full record vs one player
python main.py query queries/opponents_most_played.sql # most frequent opponents
python main.py query queries/opponents_toughest.sql    # opponents with most wins against you
python main.py query queries/biggest_upsets.sql        # your wins against 100+ higher rated
python main.py query queries/rematch_record.sql        # revenge vs tilt in rematches
python main.py query queries/rating_vs_opponent.sql    # win% by opponent rating band
python main.py query queries/draw_by_rating.sql        # draw rate vs weaker/equal/stronger
```

`rating_vs_opponent.sql` shows whether you punch above your weight or collapse against higher-rated players. Common pattern: win rate drops sharply vs +100 opponents — this is normal, but a drop vs equal opponents signals inconsistency.

---

### 5. Tilt & Emotional Patterns

**Question:** Do I lose it after a bad game? Am I tilting?

```bash
python main.py query queries/tilt_detection.sql     # win% after a win / loss / draw
python main.py query queries/revenge_spiral.sql     # win% in games 1-5 after a loss
python main.py query queries/losing_streaks.sql     # longest losing runs
python main.py query queries/color_gap_after_loss.sql # does losing as white affect black games?
```

**How to read `tilt_detection.sql`:**
| after_a | Healthy range | Red flag |
|---------|--------------|----------|
| win     | 50–60%       | < 45% (overconfidence) |
| lose    | 45–55%       | < 40% (tilting) |
| draw    | 45–55%       | wide gap from others |

If your win-after-loss drops more than 10 points below win-after-win, you are tilting.

`revenge_spiral.sql` is more granular: it shows games 1–5 after a loss. A player who tilts sees a sharp decline from game 1 to game 3, then gradually recovers. A resilient player sees stable win% across all 5 games.

---

### 6. Session & Fatigue Patterns

**Question:** Do I get worse the longer I play in one sitting?

```bash
python main.py query queries/session_fatigue.sql       # win% by game number in a session
python main.py query queries/rest_effect.sql            # win% by break length before session
python main.py query queries/streak_day_performance.sql # multi-day streaks: momentum or burnout?
python main.py query queries/format_switching.sql       # first game of session vs warmed up
```

**Session boundaries:** A new session starts when the gap between games exceeds 60 minutes.

**What to look for in `session_fatigue.sql`:**
- Game 1 win% noticeably lower than game 2–3 → you need a warm-up game
- Game 4–5 win% drops sharply → stop at 3 games per sitting
- Stable across all → good stamina, session length is not a factor

`rest_effect.sql` shows whether longer breaks before playing help or hurt. Most players perform best after a 1–6 hour break (refreshed but not rusty).

---

### 7. Time Management

**Question:** Am I losing because I run out of time? Do I play better with more time on the clock?

```bash
python main.py query queries/time_pressure.sql          # win% by % of clock used
python main.py query queries/time_pressure_monthly.sql  # time pressure trend month by month
.venv/bin/python queries/first_move_speed.py            # first-move response time vs win rate
```

**How to read `time_pressure.sql`:**
- `clock_used_pct` is how much of your initial clock you spent
- 0–50%: you won on time or resigned quickly — not much info
- 50–80%: normal range
- 80–100%: time scramble — if win% drops here, you're losing on time or making blunders under pressure

`first_move_speed.py` reads `[%clk]` annotations directly from PGN. Fast first moves (< 5 seconds) that correlate with losses can indicate impulsive opening play.

---

### 8. Timing & Scheduling

**Question:** When do I play my best chess? Should I avoid Monday mornings?

```bash
python main.py query queries/time_of_day.sql       # morning / afternoon / evening / night (IST)
python main.py query queries/day_of_week.sql        # Mon–Sun win rate
python main.py query queries/day_time_combined.sql  # day × time slot (e.g. Friday evening)
```

All times are in **IST (Asia/Kolkata)**. `day_time_combined.sql` requires ≥ 5 games in a slot to show a row — low-game slots are filtered out automatically.

**Actionable rule:** Find your best 2–3 slots from `day_time_combined.sql`. If rating matters to you, only play rated games during those slots.

---

### 9. Psychological Pressure Points

**Question:** Do I choke near rating milestones? Does playing a titled player rattle me?

```bash
python main.py query queries/rating_anxiety.sql        # win% near round-number milestones (every 50 pts)
python main.py query queries/titled_opponent_effect.sql # win% vs GM/IM/FM/CM/NM vs untitled
python main.py query queries/collapse_recovery.sql     # next game after a long loss vs a quick loss
```

**How to read `rating_anxiety.sql`:**
- `Near milestone (40-49: approaching)` — the 10 points before crossing a milestone (e.g., 990–999 before 1000)
- `Near milestone (0-10: just crossed)` — just past the milestone (e.g., 1000–1010)
- `Away from milestone` — everything else

If win% in the "approaching" zone is significantly lower than "away", you are experiencing rating anxiety.

**How to read `titled_opponent_effect.sql`:**
A drop in win% vs titled players beyond what the rating difference explains is the intimidation factor — you are beaten before the game starts.

---

### 10. Game Length & Style

**Question:** Am I a tactical slugger or a grinder? Do I win more in short games or long games?

```bash
python main.py query queries/game_length_sweet_spot.sql # win% by move count bucket
python main.py query queries/recent_games.sql            # last 30 rapid games with details
```

**How to read `game_length_sweet_spot.sql`:**
- High win% in short games (< 20 moves): tactical strength, opponents blunder early
- High win% in long games (40+ moves): endgame and positional strength
- Drops in the 20–35 move range: middlegame is the weak link — study plans and piece coordination

---

### 11. Win Streaks

**Question:** What's my longest winning run? How does it compare to my losing streaks?

```bash
python main.py query queries/win_streaks.sql    # top 10 longest winning runs
python main.py query queries/losing_streaks.sql # top 10 longest losing runs
```

Compare the two. If your longest win streak is 9 and longest losing streak is 11, the floor and ceiling are roughly balanced. A losing streak ceiling significantly above your win streak ceiling suggests you grind through slumps instead of cutting sessions short.

---

### 12. How Games End

**Question:** Am I resigning too early? Am I flagging? How do I win — checkmate or making them resign?

```bash
python main.py query queries/termination_breakdown.sql
```

**How to read the results:**
- **Resignation win%** typically highest — you only play on when you're better
- **Checkmate win%** typically lower — these are complex fights that can go either way
- **Timeout loss rate** high? You have a clock problem, not a chess problem
- **High abandonment count** — opponent left; these are noise, not real results

---

### 13. Opening Improvement Over Time

**Question:** Is my Scandinavian getting better? Am I actually improving in my core openings?

```bash
python main.py query queries/opening_trend.sql  # win% by 6-month period for top 8 openings
```

Shows each opening split into half-year periods (2025-H1, 2025-H2 etc). An opening trending upward means your preparation is working. A flat or declining trend despite many games means you are repeating the same mistakes — study that opening specifically.

---

### 14. Clock Battle

**Question:** Do I win when I spend more time thinking? Does using less time than my opponent help or hurt?

```bash
python main.py query queries/clock_battle.sql
```

`clock_ratio` is your time used divided by opponent's time used.

**How to read the results:**
- **You used less (0.5–0.8x) → highest win%**: you play sharply and efficiently
- **Even (0.8–1.2x) → low win%**: even time = equal positions = 50/50, so if this is low you're losing drawn positions
- **You used much less (<0.5x)**: either very fast games or opponent flagged — noisy bucket

---

### 15. Volume vs Quality

**Question:** Do I play better when I play more games per month, or fewer?

```bash
python main.py query queries/volume_vs_quality.sql
```

Shows monthly game count alongside win rate for the last 24 months. Look for the pattern:
- If medium-volume months (10–24 games) have noticeably higher win% than very-high-volume months (50+), you are grinding past your optimal stopping point
- If win% is stable across volumes, game count doesn't affect your quality

---

### 16. Fresh vs Repeat Opponents

**Question:** Do I do better against players I've never faced, or ones I've played before?

```bash
python main.py query queries/fresh_vs_repeat.sql
```

**How to read the results:**
- **1st game**: baseline — no information on either side
- **2nd game**: you've seen their style once
- **3rd–4th game**: if win% drops here, opponents are adapting to you faster than you're adapting to them
- **5th+ game**: regular sparring partners — high win% here means you study opponents well; low means they have your number

---

### 17. Missed Mates (Mate in 1 & 2)

**Question:** How often do I have a forced checkmate but don't play it?

This analysis requires a one-time scan of all PGNs using python-chess. Run it once; results are stored in the database and all follow-up queries are instant.

```bash
# First-time scan (takes ~2 minutes for 1600 games)
.venv/bin/python queries/missed_mates.py

# Re-run to pick up newly synced games
.venv/bin/python queries/missed_mates.py

# Force full re-analysis from scratch
.venv/bin/python queries/missed_mates.py --force
```

Once the table is populated, query it:

```bash
# Monthly summary
python main.py query queries/missed_mates_summary.sql

# Which openings produce the most missed mates
python main.py query queries/missed_mates_by_opening.sql

# Recent missed mates with game links
python main.py query queries/missed_mates_recent.sql

# Breakdown by game phase
python main.py query "
SELECT
  CASE WHEN move_number < 15 THEN 'opening (<15)'
       WHEN move_number < 30 THEN 'middlegame (15-29)'
       ELSE 'endgame (30+)' END AS phase,
  SUM(CASE WHEN mate_in = 1 THEN 1 ELSE 0 END) AS missed_m1,
  SUM(CASE WHEN mate_in = 2 THEN 1 ELSE 0 END) AS missed_m2,
  COUNT(*) AS total
FROM missed_mates
GROUP BY phase ORDER BY total DESC
"

# Browse a specific game's misses
python main.py query "SELECT move_number, mate_in, best_move, played_move, fen FROM missed_mates WHERE game_url = '<url>'"
```

**Schema of `missed_mates` table:**
| Column | Description |
|--------|-------------|
| `game_url` | Link to the game on chess.com |
| `end_time` | Unix timestamp of the game |
| `opening` | Opening name |
| `color` | Your color in that game |
| `opponent` | Opponent username |
| `move_number` | Full-move number where the mate was missed |
| `mate_in` | 1 or 2 |
| `fen` | Board position FEN — paste into any chess board viewer |
| `best_move` | The mating move you should have played (SAN) |
| `played_move` | What you actually played (SAN) |

**How to study a missed mate:** Copy the `fen` into [lichess.org/analysis](https://lichess.org/analysis) or the chess.com analysis board. Verify the forced mate, then play through a few lines to understand why it works. One session of 5–10 missed mates is more effective than an hour of tactics puzzles from a random source because these are your own blind spots.

**Limitation:** The script uses pure move generation (no engine), so it reliably finds M1 and M2s that start with checks or forcing moves. Quiet M2 first moves (non-check threats) may occasionally be missed — for 100% coverage, run Stockfish analysis on chess.com for individual games.

---

## Ad-hoc SQL

For anything not covered by a pre-built query, use the `query` subcommand with inline SQL or a custom `.sql` file. `$USERNAME` is substituted automatically.

```bash
# Your longest winning streak this year
python main.py query "
WITH ranked AS (
  SELECT end_time, user_result,
         ROW_NUMBER() OVER (ORDER BY end_time) -
         ROW_NUMBER() OVER (PARTITION BY user_result ORDER BY end_time) AS grp
  FROM games
  WHERE (white = \$USERNAME OR black = \$USERNAME)
    AND time_class = 'rapid'
    AND strftime(to_timestamp(end_time), '%Y') = '2025'
),
streaks AS (
  SELECT COUNT(*) AS len, MIN(end_time) AS s, MAX(end_time) AS e
  FROM ranked WHERE user_result = 'win' GROUP BY grp
)
SELECT len, strftime(to_timestamp(s), '%Y-%m-%d') AS start, strftime(to_timestamp(e), '%Y-%m-%d') AS end
FROM streaks ORDER BY len DESC LIMIT 5
"

# Games against a specific opening
python main.py query "
SELECT user_result, COUNT(*) AS cnt
FROM games
WHERE (white = \$USERNAME OR black = \$USERNAME)
  AND time_class = 'rapid'
  AND opening LIKE '%Sicilian%'
GROUP BY user_result
"
```

For longer queries, save to a `.sql` file and pass the path:

```bash
python main.py query my_query.sql
```

---

## Diagnostic Workflow

Use this sequence when trying to diagnose a rating slump or understand a plateau:

1. `python main.py stats` — get the full picture first
2. `queries/rating_momentum.sql` — find when the slump started
3. `queries/tilt_detection.sql` — is it mental or technical?
4. `queries/openings_worst.sql` — are specific openings dragging the numbers?
5. `queries/session_fatigue.sql` — are you playing too many games in one sitting?
6. `queries/time_pressure.sql` — are you flagging or blundering on the clock?
7. `queries/day_time_combined.sql` — are you playing at your worst times?

Fix one variable at a time. Change your schedule first (cheapest), then openings, then deep tactical issues.

---

## Keeping Data Fresh

```bash
# Sync new games (skips already-cached months, always re-fetches current month)
python main.py sync

# Sync a specific date range
python main.py sync --since 20250101 --until 20250430

# Re-parse all stored PGNs (after updating parsing code)
python main.py backfill

# Analyse a different player
python main.py stats neopaque
CHESS_USERNAME=neopaque python main.py query queries/summary.sql
```
