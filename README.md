# Chess PGN Downloader & Analyzer

Download, store, and analyze your chess.com games using a local DuckDB database.

## Requirements

- Python 3.11+
- `uv` (recommended) or `pip`

## Setup

```bash
# Using uv (recommended)
uv sync

# Or with pip
python -m venv .venv
source .venv/bin/activate
pip install duckdb
```

Set your chess.com username once:

```bash
# Add to your shell profile or .envrc
export CHESS_USERNAME=your_username
```

## Commands

All commands use `python main.py <subcommand>`. The username is read from `CHESS_USERNAME` or passed as a positional argument. The database is always at `./data/{username}.duckdb`.

### `sync` — Download games from chess.com

```bash
python main.py sync [username] [--since YYYYMMDD] [--until YYYYMMDD] [--force]
```

Downloads and stores games into `./data/{username}.duckdb`. Already-cached months are skipped; only the current month is always re-fetched.

| Flag | Description |
|------|-------------|
| `username` | Chess.com username (default: `$CHESS_USERNAME`) |
| `--since` | Only sync archives on or after this date (`YYYYMMDD`) |
| `--until` | Only sync archives on or before this date (`YYYYMMDD`) |
| `--force` | Re-fetch all archives, ignoring the cache |

### `export` — Export games as PGN

```bash
python main.py export [username] [--time-class TYPE] [--since YYYYMMDD] [--until YYYYMMDD] [-n N] [-o FILE]
```

| Flag | Description |
|------|-------------|
| `--time-class` | Filter by `bullet`, `blitz`, `rapid`, or `daily` |
| `--since` / `--until` | Date range filter (`YYYYMMDD`) |
| `-n` | Only the last N games |
| `-o, --output` | Write PGN to file (default: stdout) |

### `stats` — Game statistics dashboard

```bash
python main.py stats [username] [--time-class TYPE]
```

Displays a full analysis dashboard:
- Win/loss/draw breakdown by time control
- Top openings by frequency
- Current and longest win streak
- Monthly trend (this month vs last)
- Win rate by time of day (IST)
- Losses by game phase (opening / middlegame / endgame)
- Win rate by color (white / black)
- Best and worst openings by win rate (min 5 games)
- Time pressure performance (% of clock used)
- Performance vs opponent rating range
- Win rate by day of week

### `rating` — Current rating and monthly delta

```bash
python main.py rating [username]
```

### `opponent` — Record against a specific player

```bash
python main.py opponent <opponent_username> [--username YOUR_USERNAME]
```

### `backfill` — Re-parse PGNs for derived columns

```bash
python main.py backfill [username]
```

Useful after updating the code to populate new derived columns from already-stored PGNs.

### `query` — Run raw SQL or a query file

```bash
python main.py query "<SQL>"
python main.py query queries/summary.sql
```

SQL files in `queries/` use `$USERNAME` as a placeholder which is automatically substituted with the active username.

## Examples

```bash
# Sync all games
python main.py sync

# Show rapid stats
python main.py stats --time-class rapid

# Export last 50 rapid games to file
python main.py export --time-class rapid -n 50 -o recent_rapid.pgn

# Record against a specific opponent
python main.py opponent MagnusCarlsen

# Run a built-in analysis query
python main.py query queries/psychology/tilt_detection.sql

# Raw SQL
python main.py query "SELECT opening, COUNT(*) FROM games GROUP BY 1 ORDER BY 2 DESC LIMIT 10"

# Analyse a different user
python main.py stats neopaque
CHESS_USERNAME=neopaque python main.py query queries/general/summary.sql
```

## Project Structure

```
src/
  downloader.py   — chess.com API client with retry/backoff
  store.py        — DuckDB layer: schema, upsert, queries, stats
  cli.py          — CLI subcommands
main.py           — entry point
queries/          — 94 SQL analysis files organised by category
  openings/       — traps, gambits, white/black responses, opening stats
  performance/    — rating, trends, volume, termination
  psychology/     — tilt, streaks, fatigue, anxiety
  time/           — clock, day/time patterns, time pressure
  opponents/      — most played, toughest, rematches
  checkmates/     — missed mates, fastest, distribution
  general/        — summary, recent games
data/
  {username}.duckdb  — local game database (gitignored)
tests/
  test_store.py      — store unit tests (in-memory DuckDB)
  test_cli.py        — CLI integration tests
  test_downloader.py — API client unit tests
```

See `SKILL.md` for a full guide on which queries to run and how to interpret results.

## Running Tests

```bash
.venv/bin/python -m pytest tests/ -v
```
