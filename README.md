# Chess PGN Downloader

Download all your chess.com games as PGN. Zero dependencies — stdlib only.

## Requirements

- Python 3.11+

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
```

## Usage

```bash
# Download all games (defaults to rathnakaragn)
python main.py

# Download games for a specific user
python main.py username

# Filter by time control
python main.py --time-class rapid

# Filter by date range (YYYYMMDD)
python main.py --since 20250101 --until 20250630

# Save to file instead of stdout
python main.py -o games.pgn

# Last 100 games only
python main.py -n 100

# Combine filters
python main.py username --time-class rapid --since 20250101 -n 50 -o rapid_2025.pgn
```

### Options

| Flag | Description |
|------|-------------|
| `username` | Chess.com username (default: `rathnakaragn`) |
| `--time-class` | Filter by time control: `bullet`, `blitz`, `rapid`, `daily` |
| `--since` | Only include games on or after this date (`YYYYMMDD`) |
| `--until` | Only include games on or before this date (`YYYYMMDD`) |
| `-n` | Only include the last N games (most recent) |
| `-o, --output` | Write PGN to file (default: stdout) |

## Running Tests

```bash
pip install pytest
python -m pytest tests/ -v
```

## Project Structure

```
src/
  downloader.py   — chess.com API client with retry/backoff
  cli.py          — CLI entry point, filtering, PGN output
tests/
  conftest.py     — shared test helpers and fixtures
  test_downloader.py  — unit tests for API client
  test_filter.py      — unit tests for game filtering
  test_cli.py         — integration tests for CLI
```
