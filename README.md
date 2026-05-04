# Chess PGN Downloader & Analyzer

Download, store, and analyze your chess.com games using a local DuckDB database.

## Requirements

- Python 3.11+
- `duckdb` (installed via pip)

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Commands

All commands use `python main.py <subcommand>`. The default username is `rathnakaragn`.

### `sync` — Download games from chess.com

```bash
python main.py sync [username] [--db PATH] [--since YYYYMMDD] [--until YYYYMMDD] [--force]
```

Downloads and stores games into a local DuckDB file (`./data/{username}.duckdb`). Already-cached months are skipped; only the current month is always re-fetched.

| Flag | Description |
|------|-------------|
| `username` | Chess.com username (default: `rathnakaragn`) |
| `--db` | Path to DuckDB file (default: `./data/{username}.duckdb`) |
| `--since` | Only sync archives on or after this date (`YYYYMMDD`) |
| `--until` | Only sync archives on or before this date (`YYYYMMDD`) |
| `--force` | Re-fetch all archives, ignoring the cache |

### `export` — Export games as PGN

```bash
python main.py export [username] [--db PATH] [--time-class TYPE] [--since YYYYMMDD] [--until YYYYMMDD] [-n N] [-o FILE]
```

| Flag | Description |
|------|-------------|
| `--time-class` | Filter by `bullet`, `blitz`, `rapid`, or `daily` |
| `--since` / `--until` | Date range filter (`YYYYMMDD`) |
| `-n` | Only the last N games |
| `-o, --output` | Write PGN to file (default: stdout) |

### `stats` — Game statistics dashboard

```bash
python main.py stats [username] [--db PATH] [--time-class TYPE]
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
python main.py rating [username] [--db PATH]
```

### `opponent` — Record against a specific player

```bash
python main.py opponent <opponent_username> [--username YOUR_USERNAME] [--db PATH]
```

### `backfill` — Re-parse PGNs for derived columns

```bash
python main.py backfill [username] [--db PATH]
```

Useful after updating the code to populate new derived columns from already-stored PGNs.

### `query` — Run raw SQL

```bash
python main.py query "<SQL>" --db PATH
```

## Examples

```bash
# Sync all games
python main.py sync

# Sync only rapid games from 2025
python main.py sync --since 20250101 --time-class rapid

# Show rapid stats
python main.py stats --time-class rapid

# Export last 50 rapid games to file
python main.py export --time-class rapid -n 50 -o recent_rapid.pgn

# Record against a specific opponent
python main.py opponent MagnusCarlsen

# Raw SQL query
python main.py query "SELECT opening, COUNT(*) FROM games GROUP BY 1 ORDER BY 2 DESC LIMIT 10" --db data/rathnakaragn.duckdb
```

## Project Structure

```
src/
  downloader.py   — chess.com API client with retry/backoff
  store.py        — DuckDB layer: schema, upsert, queries, stats
  cli.py          — CLI subcommands
main.py           — entry point
data/
  {username}.duckdb  — local game database (gitignored)
tests/
  test_store.py      — store unit tests (in-memory DuckDB)
  test_cli.py        — CLI integration tests
  test_downloader.py — API client unit tests
```

## Running Tests

```bash
.venv/bin/python -m pytest tests/ -v
```
