"""Chess.com Game Downloader — subcommand CLI."""

from __future__ import annotations

import argparse
import datetime
import re
import sys
import time
import urllib.error
from pathlib import Path

import duckdb

from src.downloader import _api_get, API_BASE
from src import store

DEFAULT_USERNAME = "rathnakaragn"


def _default_db(username: str) -> str:
    return f"./data/{username}.duckdb"


def _validate_date(value: str) -> str:
    if not re.fullmatch(r"\d{8}", value):
        raise argparse.ArgumentTypeError(
            f"invalid date '{value}': expected YYYYMMDD format"
        )
    try:
        datetime.datetime.strptime(value, "%Y%m%d")
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"invalid date '{value}': not a valid calendar date"
        )
    return value


def _open_existing_db(db_path: str) -> duckdb.DuckDBPyConnection:
    if not Path(db_path).exists():
        print(f"Error: database not found at {db_path}. Run 'sync' first.",
              file=sys.stderr)
        sys.exit(1)
    return store.init_db(db_path)


def _archive_ym(url: str) -> str:
    parts = url.rstrip("/").split("/")
    return parts[-2] + parts[-1]  # e.g. "202401"


def cmd_sync(args: argparse.Namespace) -> None:
    username = args.username
    db_path = args.db or _default_db(username)
    conn = store.init_db(db_path)
    try:
        try:
            archives_data = _api_get(f"{API_BASE}/{username}/games/archives")
        except urllib.error.HTTPError as e:
            if e.code == 404:
                print(f"Error: Player '{username}' not found on chess.com",
                      file=sys.stderr)
                sys.exit(1)
            raise

        archive_urls = archives_data.get("archives", [])
        synced = store.get_synced_archives(conn)

        t = time.gmtime()
        current_ym = f"{t.tm_year}{t.tm_mon:02d}"

        since_ym = args.since[:6] if args.since else None
        until_ym = args.until[:6] if args.until else None

        to_fetch = []
        for url in archive_urls:
            ym = _archive_ym(url)
            if since_ym and ym < since_ym:
                continue
            if until_ym and ym > until_ym:
                continue
            if url in synced and ym != current_ym:
                continue
            to_fetch.append(url)

        skip_count = len(archive_urls) - len(to_fetch)
        print(f"Syncing {len(to_fetch)} archives (skipping {skip_count} cached)...",
              file=sys.stderr)

        total_new = 0
        for i, url in enumerate(to_fetch, 1):
            ym = _archive_ym(url)
            data = _api_get(url)
            games = data.get("games", [])
            new = store.upsert_games(conn, games)
            total_new += new
            if ym != current_ym:
                store.mark_archive_synced(conn, url)
            print(f"  [{i}/{len(to_fetch)}] {ym[:4]}/{ym[4:]}: {len(games)} games ({new} new)",
                  file=sys.stderr)

        print(f"Sync complete. {total_new} new games added.", file=sys.stderr)
    finally:
        conn.close()


def cmd_export(args: argparse.Namespace) -> None:
    username = args.username
    db_path = args.db or _default_db(username)
    conn = _open_existing_db(db_path)
    try:
        games = store.query_games(conn, args.time_class, args.since, args.until, args.n)
        if not games:
            print("No games match the given filters.", file=sys.stderr)
            return

        pgn_parts = [g["pgn"].strip() for g in games if g.get("pgn")]
        pgn_text = "\n\n".join(pgn_parts) + "\n"

        if args.output:
            with open(args.output, "w") as f:
                f.write(pgn_text)
            print(f"{len(pgn_parts)} games written to {args.output}", file=sys.stderr)
        else:
            print(pgn_text)
    finally:
        conn.close()


def cmd_query(args: argparse.Namespace) -> None:
    conn = _open_existing_db(args.db)
    try:
        try:
            rows = store.raw_sql(conn, args.sql)
        except duckdb.Error as e:
            print(f"Query error: {e}", file=sys.stderr)
            sys.exit(1)
        for row in rows:
            print("\t".join(str(v) for v in row))
    finally:
        conn.close()


def cmd_stats(args: argparse.Namespace) -> None:
    username = args.username
    db_path = args.db or _default_db(username)
    conn = _open_existing_db(db_path)
    try:
        result = store.stats(conn, username)

        print(f"\n=== Stats for {username} ===")
        print(f"Total games: {result['total']}\n")
        for tc, counts in sorted(result["by_time_class"].items()):
            total_tc = sum(counts.values())
            win_pct = counts["win"] / total_tc * 100 if total_tc else 0
            print(f"{tc:10s}  W:{counts['win']}  L:{counts['lose']}  "
                  f"D:{counts['draw']}  ({win_pct:.0f}% win)")
        if result["top_openings"]:
            print("\nTop openings:")
            for opening, cnt in result["top_openings"]:
                print(f"  {opening}: {cnt}")
        print(f"\nCurrent win streak : {result['current_streak']}")
        print(f"Longest win streak : {result['longest_streak']}")
    finally:
        conn.close()


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Chess.com game downloader and analyzer."
    )
    sub = ap.add_subparsers(dest="command", required=True)

    # sync
    p_sync = sub.add_parser("sync", help="Download and store games from chess.com")
    p_sync.add_argument("username", nargs="?", default=DEFAULT_USERNAME)
    p_sync.add_argument("--db", help="Path to DuckDB file (default: ./data/{username}.duckdb)")
    p_sync.add_argument("--since", type=_validate_date,
                        help="Only sync archives on or after YYYYMMDD")
    p_sync.add_argument("--until", type=_validate_date,
                        help="Only sync archives on or before YYYYMMDD")
    p_sync.set_defaults(func=cmd_sync)

    # export
    p_export = sub.add_parser("export", help="Export games from DB as PGN")
    p_export.add_argument("username", nargs="?", default=DEFAULT_USERNAME)
    p_export.add_argument("--db", help="Path to DuckDB file")
    p_export.add_argument("--time-class", dest="time_class",
                          choices=["bullet", "blitz", "rapid", "daily"])
    p_export.add_argument("--since", type=_validate_date)
    p_export.add_argument("--until", type=_validate_date)
    p_export.add_argument("-n", type=int, metavar="N",
                          help="Only export last N games")
    p_export.add_argument("-o", "--output", help="Write PGN to file instead of stdout")
    p_export.set_defaults(func=cmd_export)

    # query
    p_query = sub.add_parser("query", help="Run raw SQL against the DB")
    p_query.add_argument("sql", help="SQL query string")
    p_query.add_argument("--db", required=True, help="Path to DuckDB file")
    p_query.set_defaults(func=cmd_query)

    # stats
    p_stats = sub.add_parser("stats", help="Show game statistics dashboard")
    p_stats.add_argument("username", nargs="?", default=DEFAULT_USERNAME)
    p_stats.add_argument("--db", help="Path to DuckDB file")
    p_stats.set_defaults(func=cmd_stats)

    args = ap.parse_args()
    args.func(args)
