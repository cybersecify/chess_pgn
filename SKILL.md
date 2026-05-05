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

## Query Folder Structure

```
queries/
├── openings/
│   ├── traps/wayward_queen_attack/     WQ attack deep analysis
│   ├── gambits/icelandic_gambit/       Icelandic Gambit as Black
│   ├── gambits/blackmar_diemer_gambit/ BDG as White vs 1...d5
│   ├── gambits/smith_morra_gambit/     Smith-Morra as White vs 1...c5
│   ├── white_responses/                White 2nd move vs every Black reply
│   ├── black_responses/                Your reply to every White first move
│   └── *.sql                           General opening stats
├── performance/                        Rating, trends, volume, termination
├── psychology/                         Tilt, streaks, fatigue, anxiety
├── time/                               Clock, day/time patterns, time pressure
├── opponents/                          Most played, toughest, rematches
├── checkmates/                         Missed mates, fastest, distribution
└── general/                            Summary, recent games
```

---

## Core Skills

### 1. Overall Performance Picture

**Question:** How am I doing overall? What's my win rate by format?

```bash
python main.py stats                              # full dashboard
python main.py stats --time-class rapid           # rapid only
python main.py query queries/general/summary.sql  # W/L/D + win% per time control
```

---

### 2. Rating Trajectory

**Question:** Is my rating going up, down, or flat? When was I at my best?

```bash
python main.py rating
python main.py query queries/performance/rating_history.sql   # monthly high/low (rapid)
python main.py query queries/performance/rating_momentum.sql  # rolling 10-game win%
python main.py query queries/performance/monthly_trend.sql    # monthly win rate, last 12 months
```

`rating_momentum.sql` is the best signal for identifying hot and cold patches — look for stretches where rolling win% stays above 55% or drops below 40%.

---

### 3. Opening Repertoire

**Question:** Which openings win for me? Which am I wasting time on?

```bash
python main.py query queries/openings/openings_best.sql      # top 10 by win% (min 10 games)
python main.py query queries/openings/openings_worst.sql     # worst 10 by win%
python main.py query queries/openings/openings_by_color.sql  # win% split by white/black
python main.py query queries/openings/opening_loyalty.sql    # core repertoire vs experiments
python main.py query queries/openings/draw_by_opening.sql    # openings that end in draws most
python main.py query queries/openings/eco_family.sql         # performance by ECO family (A/B/C/D/E)
python main.py query queries/openings/opening_trend.sql      # win% by 6-month period per opening
```

**How to read `opening_loyalty.sql`:**
- **Core** (10+ games): your actual repertoire — invest here
- **Regular** (4–9 games): developing — worth continuing if win% is good
- **One-off** (1–3 games): experiments — commit or drop

---

### 4. White Responses — Your Plan vs Every Black First Move

**Question:** What do I play as White against each reply? Where am I inconsistent?

```bash
python main.py query queries/openings/white_responses/white_first_move_summary.sql  # full overview
python main.py query queries/openings/white_responses/vs_e5_wayward_queen.sql        # WQ monthly trend
python main.py query queries/openings/white_responses/vs_d5_gap.sql                  # biggest gap (41%)
python main.py query queries/openings/white_responses/vs_c5_sicilian.sql             # Sicilian responses
python main.py query queries/openings/white_responses/vs_nc6_gap.sql                 # 5-move chaos (39%)
python main.py query queries/openings/white_responses/vs_c6_e6.sql                   # consistent d4 system
python main.py query queries/openings/white_responses/white_move_sequence_wins_vs_losses.sql  # WQ moves 3-8
```

**Known gaps as White (rapid):**
| Black plays | Issue | Fix |
|-------------|-------|-----|
| 1...d5 | Qf3/e5/Bd3 randomly | Always 2.Qh5 (57.9%) |
| 1...Nc6 | 5 different moves | Always 2.Bc4 (66.7% rapid) |
| 1...c5 | 4 different moves in blitz | 2.Bc4 in rapid (57.9%) |

---

### 5. Black Responses — Your Plan vs Every White First Move

**Question:** What do I play as Black? Where do I have no weapon?

```bash
python main.py query queries/openings/black_responses/black_first_move_summary.sql            # full overview
python main.py query queries/openings/black_responses/vs_e4_scandinavian.sql                  # Scandinavian trend
python main.py query queries/openings/black_responses/vs_d4_replies.sql                       # vs 1.d4 breakdown
python main.py query queries/openings/black_responses/vs_nf3_gap.sql                          # worst gap (26%)
python main.py query queries/openings/black_responses/vs_nc3_gap.sql                          # second gap (~22%)
python main.py query queries/openings/black_responses/vs_c4_strong.sql                        # strongest area (71%)
python main.py query queries/openings/black_responses/black_move_sequence_wins_vs_losses.sql  # Scandinavian moves 2-6
```

**Known gaps as Black (rapid):**
| White plays | Win% | Issue |
|-------------|------|-------|
| 1.Nf3 | 26.4% | No weapon — lose 3 in 4 |
| 1.Nc3 | ~22% | No weapon |
| 1.d4 | ~44% | Below 50% with both c5 and d5 |

**Strong area:** vs 1.c4 → 71% win rate with 1...d5.

---

### 6. Wayward Queen Attack (Trap)

**Question:** How is my WQ attack performing? Where am I losing in the move sequence?

```bash
python main.py query queries/openings/traps/wayward_queen_attack/wayward_queen.sql            # summary by format
python main.py query queries/openings/traps/wayward_queen_attack/wayward_queen_monthly.sql    # monthly trend
python main.py query queries/openings/traps/wayward_queen_attack/wayward_queen_responses.sql  # Black's 2nd move
python main.py query queries/openings/traps/wayward_queen_attack/wayward_queen_opp_rating.sql # win% by ELO bucket
python main.py query queries/openings/traps/wayward_queen_attack/wayward_queen_length.sql     # win% by game length
python main.py query queries/openings/traps/wayward_queen_attack/wayward_queen_termination.sql
python main.py query queries/openings/traps/wayward_queen_attack/wayward_queen_posttrap.sql   # post-trap conversion
python main.py query queries/openings/traps/wayward_queen_attack/wayward_queen_recent.sql     # 20 most recent
python main.py query queries/openings/traps/wayward_queen_attack/wayward_queen_top_wins.sql   # highest ELO beaten
```

**Key mistakes to avoid (from data):**
| Move | Bad habit | Win% | Better option | Win% |
|------|-----------|------|---------------|------|
| Move 5 | 5.c3 | 41% | **5.Ne2** | 63% |
| Move 6 | 6.Bxf7+ | 16% | **6.d3** | 56% |
| Move 7 | 7.d3 | 35% | **7.h3 / 7.Nf3** | 58-61% |

---

### 7. Icelandic Gambit (Gambit as Black)

**Question:** How is my Icelandic Gambit performing?

```bash
python main.py query queries/openings/gambits/icelandic_gambit/icelandic_gambit.sql            # summary
python main.py query queries/openings/gambits/icelandic_gambit/icelandic_gambit_monthly.sql    # monthly trend
python main.py query queries/openings/gambits/icelandic_gambit/icelandic_gambit_responses.sql  # White's 4th move
python main.py query queries/openings/gambits/icelandic_gambit/icelandic_gambit_opp_rating.sql
python main.py query queries/openings/gambits/icelandic_gambit/icelandic_gambit_length.sql
python main.py query queries/openings/gambits/icelandic_gambit/icelandic_gambit_termination.sql
python main.py query queries/openings/gambits/icelandic_gambit/icelandic_gambit_recent.sql
python main.py query queries/openings/gambits/icelandic_gambit/icelandic_gambit_top_wins.sql
```

---

### 8. Blackmar-Diemer Gambit (Gambit as White vs 1...d5)

**Question:** How is my BDG performing?

```bash
python main.py query queries/openings/gambits/blackmar_diemer_gambit/blackmar_diemer.sql
python main.py query queries/openings/gambits/blackmar_diemer_gambit/blackmar_diemer_monthly.sql
python main.py query queries/openings/gambits/blackmar_diemer_gambit/blackmar_diemer_responses.sql
python main.py query queries/openings/gambits/blackmar_diemer_gambit/blackmar_diemer_opp_rating.sql
python main.py query queries/openings/gambits/blackmar_diemer_gambit/blackmar_diemer_length.sql
python main.py query queries/openings/gambits/blackmar_diemer_gambit/blackmar_diemer_termination.sql
python main.py query queries/openings/gambits/blackmar_diemer_gambit/blackmar_diemer_recent.sql
python main.py query queries/openings/gambits/blackmar_diemer_gambit/blackmar_diemer_top_wins.sql
```

---

### 9. Smith-Morra Gambit (Gambit as White vs 1...c5)

**Question:** How is my Smith-Morra performing?

```bash
python main.py query queries/openings/gambits/smith_morra_gambit/smith_morra.sql
python main.py query queries/openings/gambits/smith_morra_gambit/smith_morra_monthly.sql
python main.py query queries/openings/gambits/smith_morra_gambit/smith_morra_responses.sql
python main.py query queries/openings/gambits/smith_morra_gambit/smith_morra_length.sql
python main.py query queries/openings/gambits/smith_morra_gambit/smith_morra_termination.sql
python main.py query queries/openings/gambits/smith_morra_gambit/smith_morra_recent.sql
python main.py query queries/openings/gambits/smith_morra_gambit/smith_morra_top_wins.sql
```

---

### 10. Opponent Analysis

**Question:** Who beats me the most? How do I do against stronger players?

```bash
python main.py opponent <username>
python main.py query queries/opponents/opponents_most_played.sql
python main.py query queries/opponents/opponents_toughest.sql
python main.py query queries/opponents/biggest_upsets.sql
python main.py query queries/opponents/rematch_record.sql
python main.py query queries/opponents/rating_vs_opponent.sql
python main.py query queries/opponents/fresh_vs_repeat.sql
python main.py query queries/opponents/titled_opponent_effect.sql
```

---

### 11. Tilt & Emotional Patterns

**Question:** Do I lose it after a bad game? Am I tilting?

```bash
python main.py query queries/psychology/tilt_detection.sql
python main.py query queries/psychology/revenge_spiral.sql
python main.py query queries/psychology/losing_streaks.sql
python main.py query queries/psychology/win_streaks.sql
python main.py query queries/psychology/color_gap_after_loss.sql
python main.py query queries/psychology/collapse_recovery.sql
python main.py query queries/psychology/rating_anxiety.sql
```

**How to read `tilt_detection.sql`:**
| after_a | Healthy range | Red flag |
|---------|--------------|----------|
| win     | 50–60%       | < 45% (overconfidence) |
| lose    | 45–55%       | < 40% (tilting) |

If your win-after-loss drops more than 10 points below win-after-win, you are tilting.

---

### 12. Session & Fatigue Patterns

**Question:** Do I get worse the longer I play in one sitting?

```bash
python main.py query queries/psychology/session_fatigue.sql
python main.py query queries/psychology/rest_effect.sql
python main.py query queries/psychology/streak_day_performance.sql
python main.py query queries/performance/format_switching.sql
```

**Session boundaries:** A new session starts when the gap between games exceeds 60 minutes.

---

### 13. Time Management

**Question:** Am I losing because I run out of time?

```bash
python main.py query queries/time/time_pressure.sql
python main.py query queries/time/time_pressure_monthly.sql
python main.py query queries/time/clock_battle.sql
.venv/bin/python queries/time/first_move_speed.py
```

---

### 14. Timing & Scheduling

**Question:** When do I play my best chess?

```bash
python main.py query queries/time/time_of_day.sql
python main.py query queries/time/day_of_week.sql
python main.py query queries/time/day_time_combined.sql
```

All times are in **IST (Asia/Kolkata)**.

**Actionable rule:** Find your best 2–3 slots from `day_time_combined.sql`. Only play rated games during those slots.

---

### 15. Game Length & Style

**Question:** Do I win more in short games or long games?

```bash
python main.py query queries/performance/game_length_sweet_spot.sql
python main.py query queries/general/recent_games.sql
```

---

### 16. How Games End

**Question:** Am I resigning too early? Am I flagging?

```bash
python main.py query queries/performance/termination_breakdown.sql
```

---

### 17. Volume vs Quality

**Question:** Do I play better when I play more games per month, or fewer?

```bash
python main.py query queries/performance/volume_vs_quality.sql
```

---

### 18. Missed Mates (Mate in 1 & 2)

**Question:** How often do I have a forced checkmate but don't play it?

```bash
# First-time scan (takes ~2 minutes)
.venv/bin/python queries/checkmates/missed_mates.py

# Force full re-analysis
.venv/bin/python queries/checkmates/missed_mates.py --force

# Query results
python main.py query queries/checkmates/missed_mates_summary.sql
python main.py query queries/checkmates/missed_mates_by_opening.sql
python main.py query queries/checkmates/missed_mates_recent.sql
```

**Schema of `missed_mates` table:**
| Column | Description |
|--------|-------------|
| `game_url` | Link to the game on chess.com |
| `color` | Your color in that game |
| `move_number` | Full-move number where mate was missed |
| `mate_in` | 1 or 2 |
| `fen` | Board position — paste into lichess.org/analysis |
| `best_move` | The mating move you should have played |
| `played_move` | What you actually played |

---

### 19. Checkmate Patterns

```bash
python main.py query queries/checkmates/checkmate_distribution.sql
python main.py query queries/checkmates/checkmate_openings.sql
python main.py query queries/checkmates/fastest_checkmates.sql
python main.py query queries/checkmates/fastest_mated.sql
```

---

## Ad-hoc SQL

```bash
python main.py query "SELECT ... FROM games WHERE white = \$USERNAME ..."
python main.py query my_query.sql
```

`$USERNAME` is substituted automatically from `CHESS_USERNAME`.

---

## Diagnostic Workflow

Use this sequence when diagnosing a rating slump:

1. `python main.py stats` — get the full picture
2. `queries/performance/rating_momentum.sql` — find when the slump started
3. `queries/psychology/tilt_detection.sql` — is it mental or technical?
4. `queries/openings/openings_worst.sql` — specific openings dragging numbers?
5. `queries/psychology/session_fatigue.sql` — playing too long per session?
6. `queries/time/time_pressure.sql` — flagging or blundering on the clock?
7. `queries/time/day_time_combined.sql` — playing at your worst times?

Fix one variable at a time. Schedule first (cheapest), then openings, then tactics.

---

## Keeping Data Fresh

```bash
python main.py sync                                    # sync new games
python main.py sync --since 20250101 --until 20250430  # specific range
python main.py backfill                                # re-parse all PGNs

# Analyse a different player
CHESS_USERNAME=neopaque python main.py query queries/general/summary.sql
```
