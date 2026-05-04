"""Chess.com Game Downloader — subcommand CLI."""

from __future__ import annotations

import argparse
import datetime
import os
import re
import sys
import time
import urllib.error
from pathlib import Path

import duckdb

from src.downloader import _api_get, API_BASE
from src import store

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
    try:
        return store.init_db(db_path)
    except duckdb.Error as e:
        print(f"Error: database file appears corrupt ({e}).", file=sys.stderr)
        sys.exit(1)


def _archive_ym(url: str) -> str:
    parts = url.rstrip("/").split("/")
    return parts[-2] + parts[-1]  # e.g. "202401"


def cmd_sync(args: argparse.Namespace) -> None:
    username = args.username
    db_path = _default_db(username)
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
            if not args.force and url in synced and ym != current_ym:
                continue
            to_fetch.append(url)

        skip_count = len(archive_urls) - len(to_fetch)
        print(f"Syncing {len(to_fetch)} archives (skipping {skip_count} cached)...",
              file=sys.stderr)

        total_new = 0
        for i, url in enumerate(to_fetch, 1):
            ym = _archive_ym(url)
            try:
                data = _api_get(url)
            except RuntimeError as e:
                print(f"  [{i}/{len(to_fetch)}] {ym[:4]}/{ym[4:]}: skipped ({e})",
                      file=sys.stderr)
                continue
            games = data.get("games", [])
            new = store.upsert_games(conn, games, username=username)
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
    db_path = _default_db(username)
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
    sql = args.sql
    if len(sql) <= 255 and not sql.strip().upper().startswith("SELECT"):
        p = Path(sql)
        try:
            if p.exists() and p.is_file():
                sql = p.read_text()
        except OSError:
            pass
    sql = sql.replace("$USERNAME", f"'{args.username}'")
    conn = _open_existing_db(_default_db(args.username))
    try:
        try:
            rows = store.raw_sql(conn, sql)
        except duckdb.Error as e:
            print(f"Query error: {e}", file=sys.stderr)
            sys.exit(1)
        for row in rows:
            print("\t".join(str(v) for v in row))
    finally:
        conn.close()


def cmd_stats(args: argparse.Namespace) -> None:
    username = args.username
    db_path = _default_db(username)
    conn = _open_existing_db(db_path)
    try:
        result = store.stats(conn, username, args.time_class)

        header = f"\n=== Stats for {username}"
        if args.time_class:
            header += f" ({args.time_class})"
        print(header + " ===")
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

        if result["trend"]:
            print("\nTrend (this month vs last):")
            for tc, months in sorted(result["trend"].items()):
                parts = []
                for ym in sorted(months):
                    d = months[ym]
                    parts.append(f"{ym}: {d['win_pct']}% ({d['games']}g)")
                print(f"  {tc:10s}  " + "  →  ".join(parts))

        if result["time_of_day"]:
            print("\nBy time of day (IST):")
            for period in ["morning", "afternoon", "evening", "night"]:
                if period not in result["time_of_day"]:
                    continue
                counts = result["time_of_day"][period]
                total_p = sum(counts.values())
                pct = counts["win"] / total_p * 100 if total_p else 0
                print(f"  {period:12s}  W:{counts['win']}  L:{counts['lose']}  "
                      f"D:{counts['draw']}  ({pct:.0f}%)")

        if result["game_phase_losses"]:
            print("\nLosses by game phase:")
            for phase in ["opening", "middlegame", "endgame"]:
                cnt = result["game_phase_losses"].get(phase, 0)
                print(f"  {phase:12s}  {cnt}")

        if result["by_color"]:
            print("\nBy color:")
            for color_val in ["white", "black"]:
                if color_val not in result["by_color"]:
                    continue
                counts = result["by_color"][color_val]
                total_c = sum(counts.values())
                pct = counts["win"] / total_c * 100 if total_c else 0
                print(f"  {color_val:8s}  W:{counts['win']}  L:{counts['lose']}  "
                      f"D:{counts['draw']}  ({pct:.0f}%)")
        if result["best_openings"]:
            print("\nBest openings (min 5 games):")
            for opening, wins, games in result["best_openings"]:
                pct = wins / games * 100 if games else 0
                print(f"  {opening:35s}  {pct:.0f}%  ({games}g)")
        if result["worst_openings"]:
            print("\nWorst openings (min 5 games):")
            for opening, wins, games in result["worst_openings"]:
                pct = wins / games * 100 if games else 0
                print(f"  {opening:35s}  {pct:.0f}%  ({games}g)")
        if result["time_pressure"]:
            print("\nTime pressure (% of clock used):")
            for bucket in ["< 30%", "30-70%", "> 70%"]:
                counts = result["time_pressure"].get(bucket, {"win": 0, "lose": 0, "draw": 0})
                total_b = sum(counts.values())
                if total_b == 0:
                    continue
                pct = counts["win"] / total_b * 100
                print(f"  {bucket:8s}  W:{counts['win']}  L:{counts['lose']}  "
                      f"D:{counts['draw']}  ({pct:.0f}%)")
        if result["rating_range"]:
            print("\nvs opponent rating:")
            labels = {"much weaker": "< -100", "similar": "  ±100", "much stronger": "> +100"}
            for bucket in ["much weaker", "similar", "much stronger"]:
                counts = result["rating_range"].get(bucket, {"win": 0, "lose": 0, "draw": 0})
                total_b = sum(counts.values())
                if total_b == 0:
                    continue
                pct = counts["win"] / total_b * 100
                print(f"  {bucket:14s} ({labels[bucket]})  W:{counts['win']}  "
                      f"L:{counts['lose']}  D:{counts['draw']}  ({pct:.0f}%)")
        if result["day_of_week"]:
            print("\nBy day of week:")
            parts = []
            for day in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]:
                if day not in result["day_of_week"]:
                    continue
                counts = result["day_of_week"][day]
                total_d = sum(counts.values())
                pct = counts["win"] / total_d * 100 if total_d else 0
                parts.append(f"{day} {pct:.0f}%({total_d}g)")
            print("  " + "  ".join(parts))
    finally:
        conn.close()


def cmd_backfill(args: argparse.Namespace) -> None:
    username = args.username
    db_path = _default_db(username)
    conn = _open_existing_db(db_path)
    try:
        print("Backfilling derived columns from stored PGNs...", file=sys.stderr)
        updated = store.backfill_derived_columns(conn, username=username)
        print(f"Done. {updated} rows updated.", file=sys.stderr)
    finally:
        conn.close()


def cmd_rating(args: argparse.Namespace) -> None:
    username = args.username
    db_path = _default_db(username)
    conn = _open_existing_db(db_path)
    try:
        result = store.rating_history(conn, username)
        if not result:
            print("No rating data found. Run 'backfill' first.", file=sys.stderr)
            return
        print(f"\n=== Rating for {username} ===\n")
        for tc, data in sorted(result.items()):
            delta = data["delta"]
            if delta is not None:
                sign = "+" if delta >= 0 else ""
                delta_str = f"  ({sign}{delta} this month)"
            else:
                delta_str = ""
            print(f"{tc:8s}  {data['current']}{delta_str}")
    finally:
        conn.close()


def cmd_opponent(args: argparse.Namespace) -> None:
    username = args.username
    db_path = _default_db(username)
    conn = _open_existing_db(db_path)
    try:
        result = store.opponent_stats(conn, username, args.opponent)
        if result["total"] == 0:
            print(f"No games found against '{args.opponent}'.", file=sys.stderr)
            return
        print(f"\n=== {username} vs {args.opponent} ===")
        print(f"Total: {result['total']}  W:{result['wins']}  L:{result['losses']}  "
              f"D:{result['draws']}  ({result['win_pct']:.0f}% win)\n")
        if result["by_time_class"]:
            print("By format:")
            for tc, counts in sorted(result["by_time_class"].items()):
                total_tc = sum(counts.values())
                pct = counts["win"] / total_tc * 100 if total_tc else 0
                print(f"  {tc:8s}  W:{counts['win']}  L:{counts['lose']}  "
                      f"D:{counts['draw']}  ({pct:.0f}%)")
        if result["top_openings"]:
            print("\nTop openings played:")
            for opening, cnt in result["top_openings"]:
                print(f"  {opening}: {cnt}")
    finally:
        conn.close()


def main() -> None:
    # Re-read from env each call so monkeypatching works in tests.
    default_user = os.environ.get("CHESS_USERNAME", "")

    ap = argparse.ArgumentParser(
        description="Chess.com game downloader and analyzer."
    )
    sub = ap.add_subparsers(dest="command", required=True)

    # sync
    p_sync = sub.add_parser("sync", help="Download and store games from chess.com")
    p_sync.add_argument("username", nargs="?", default=default_user)
    p_sync.add_argument("--since", type=_validate_date,
                        help="Only sync archives on or after YYYYMMDD")
    p_sync.add_argument("--until", type=_validate_date,
                        help="Only sync archives on or before YYYYMMDD")
    p_sync.add_argument("--force", action="store_true",
                        help="Re-fetch all archives, ignoring the cache")
    p_sync.set_defaults(func=cmd_sync)

    # export
    p_export = sub.add_parser("export", help="Export games from DB as PGN")
    p_export.add_argument("username", nargs="?", default=default_user)
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
    p_query.add_argument("sql", help="SQL query string or path to .sql file")
    p_query.add_argument("--username", default=default_user,
                         help="Chess.com username (sets DB path and $USERNAME substitution)")
    p_query.set_defaults(func=cmd_query)

    # stats
    p_stats = sub.add_parser("stats", help="Show game statistics dashboard")
    p_stats.add_argument("username", nargs="?", default=default_user)
    p_stats.add_argument("--time-class", dest="time_class",
                         choices=["bullet", "blitz", "rapid", "daily"],
                         help="Filter stats and streaks to one time control")
    p_stats.set_defaults(func=cmd_stats)

    # backfill
    p_backfill = sub.add_parser("backfill", help="Re-parse PGNs to fill missing derived columns")
    p_backfill.add_argument("username", nargs="?", default=default_user)
    p_backfill.set_defaults(func=cmd_backfill)

    # rating
    p_rating = sub.add_parser("rating", help="Show current rating and monthly delta per format")
    p_rating.add_argument("username", nargs="?", default=default_user)
    p_rating.set_defaults(func=cmd_rating)

    # opponent
    p_opponent = sub.add_parser("opponent", help="Show record against a specific player")
    p_opponent.add_argument("opponent", help="Opponent username")
    p_opponent.add_argument("--username", default=default_user)
    p_opponent.set_defaults(func=cmd_opponent)

    args = ap.parse_args()

    username = getattr(args, "username", None) or default_user
    if not username:
        ap.error(
            "No username provided. Pass it as an argument or set CHESS_USERNAME:\n"
            "  python main.py stats <username>\n"
            "  export CHESS_USERNAME=<username>"
        )
    if hasattr(args, "username"):
        args.username = username

    args.func(args)
