# DuckDB Integration Design

**Date:** 2026-05-02  
**Status:** Approved

## Goal

Add DuckDB as a persistent store for chess.com games. Primary goals: avoid re-downloading games on every run (caching), and enable SQL-based analytics over game history. PGN export remains available as an output from the store.

## Architecture

Approach: thin store layer. `downloader.py` is unchanged and continues to return `list[dict]`. A new `src/store.py` handles all DuckDB interaction. `src/cli.py` is refactored from a single `main()` into subcommands.

### File Changes

```
src/
  downloader.py     — unchanged
  store.py          — NEW: DuckDB layer
  cli.py            — refactored: subcommands (sync, export, query, stats)
  __main__.py       — unchanged
data/
  {username}.duckdb — default DB location, e.g. rathnakaragn.duckdb (gitignored)
tests/
  test_store.py     — NEW: store unit tests
  test_downloader.py — unchanged
  test_filter.py    — removed (filtering now done in DuckDB)
  test_cli.py       — updated for subcommands
```

### Data Flow

- `sync`: `downloader.download_all_games()` → `store.upsert_games()` → done
- `export`: `store.query_games(filters)` → PGN text → file or stdout
- `query`: `store.raw_sql(sql)` → tab-separated table to stdout
- `stats`: `store.stats(username)` → formatted dashboard to stdout

## Database Schema

Single `games` table in `games.duckdb`:

```sql
CREATE TABLE IF NOT EXISTS games (
    url          TEXT PRIMARY KEY,
    pgn          TEXT,
    time_class   TEXT,
    time_control TEXT,
    end_time     INTEGER,
    white        TEXT,
    black        TEXT,
    white_result TEXT,
    black_result TEXT,
    rated        BOOLEAN,
    fen          TEXT,
    eco          TEXT,
    opening      TEXT
)
```

`url` is the natural primary key from the chess.com API and guarantees deduplication on upsert. Most columns map directly from the raw game dict. Transformations: flatten `game["white"]["username"]` and `game["white"]["result"]`; parse `eco` and `opening` from PGN header lines (e.g. `[ECO "B20"]`, `[Opening "Sicilian Defense"]`) during `upsert_games()`.

## store.py Public Interface

```python
def init_db(db_path: str) -> duckdb.DuckDBPyConnection
def upsert_games(conn, games: list[dict]) -> int        # returns count inserted
def query_games(conn, time_class, since, until, n) -> list[dict]
def raw_sql(conn, sql: str) -> list[tuple]
def stats(conn, username: str) -> dict
```

## CLI Subcommands

All subcommands share `--db PATH` (default: `./data/{username}.duckdb`, e.g. `./data/rathnakaragn.duckdb`). `username` defaults to `rathnakaragn`.

```
python -m src sync [username] [--db PATH] [--since YYYYMMDD] [--until YYYYMMDD]
python -m src export [--db PATH] [--time-class rapid|blitz|bullet|daily] [--since YYYYMMDD] [--until YYYYMMDD] [-n N] [-o FILE]
python -m src query "<SQL>" [--db PATH]
python -m src stats [username] [--db PATH]
```

### Subcommand Behaviours

- **sync**: Skips fully-cached months by comparing archive URLs against data already in the DB (always re-fetches the current month). Inserts new games via `upsert_games()`.
- **export**: Pure DB query, no network access. Outputs PGN to `-o FILE` or stdout.
- **query**: Executes raw SQL, prints results as tab-separated rows to stdout.
- **stats**: Prints a fixed dashboard — total games, win/loss/draw rate by time class, top 5 openings by ECO, current and longest win streak.

## Error Handling

| Scenario | Behaviour |
|---|---|
| DB directory missing on `sync` | Auto-created via `Path(db_path).parent.mkdir(parents=True, exist_ok=True)` |
| Network error during `sync` | Propagated from `downloader.py` (existing retry/backoff logic) |
| Invalid SQL in `query` | `duckdb.Error` caught, printed to stderr, exit 1 |
| No matching games in `export` | Warning to stderr, exit 0 |
| DB file missing on `export`/`query`/`stats` | Clear error message, exit 1 |

## Testing

- **`test_store.py`**: All tests use in-memory DuckDB (`duckdb.connect(":memory:")`). Covers: upsert deduplication, query filtering by time class and date range, stats output correctness, raw SQL passthrough.
- **`test_cli.py`**: Tests each subcommand via argparse + mocked `store` and `downloader`. Updated from current single-command tests.
- **`test_downloader.py`**: Unchanged.
- **`test_filter.py`**: Removed — filtering is now done in DuckDB via `query_games()`.

## Dependencies

- `duckdb` — single pip install, embedded binary, no system-level requirements.
- Add to `requirements.txt` (create if not present).
