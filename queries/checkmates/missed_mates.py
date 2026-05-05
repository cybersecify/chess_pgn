"""
Detect missed mate-in-1 and mate-in-2 opportunities in your games.

Reads PGNs from the user's DuckDB, scans every position where it's the
user's turn, and records cases where a forced mate existed but was not played.

Results are stored in a `missed_mates` table inside the same database so
you can query them with `python main.py query`.

Usage:
    .venv/bin/python queries/missed_mates.py
    .venv/bin/python queries/missed_mates.py --user neopaque
    .venv/bin/python queries/missed_mates.py --time-class blitz --limit 200
    .venv/bin/python queries/missed_mates.py --force   # re-run from scratch
"""

from __future__ import annotations

import argparse
import io
import os
import sys
from pathlib import Path

try:
    import chess
    import chess.pgn
except ImportError:
    print("Error: python-chess not installed. Run: pip install chess", file=sys.stderr)
    sys.exit(1)

try:
    import duckdb
except ImportError:
    print("Error: duckdb not installed. Run: pip install duckdb", file=sys.stderr)
    sys.exit(1)


CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS missed_mates (
    game_url     TEXT,
    end_time     INTEGER,
    opening      TEXT,
    color        TEXT,
    opponent     TEXT,
    move_number  INTEGER,
    mate_in      INTEGER,
    fen          TEXT,
    best_move    TEXT,
    played_move  TEXT
)
"""

INSERT_ROW = """
INSERT INTO missed_mates
    (game_url, end_time, opening, color, opponent,
     move_number, mate_in, fen, best_move, played_move)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
"""


def find_mate_in_1(board: chess.Board) -> chess.Move | None:
    for move in board.legal_moves:
        board.push(move)
        if board.is_checkmate():
            board.pop()
            return move
        board.pop()
    return None


def find_mate_in_2(board: chess.Board) -> chess.Move | None:
    """Return the first move of a mate-in-2, or None.

    A mate-in-2 exists when there is a move such that every legal opponent
    response leaves a position where find_mate_in_1 succeeds.
    """
    for move1 in board.legal_moves:
        board.push(move1)
        opponent_moves = list(board.legal_moves)
        if not opponent_moves:
            board.pop()
            continue
        all_lose = True
        for move2 in opponent_moves:
            board.push(move2)
            m1 = find_mate_in_1(board)
            board.pop()
            if m1 is None:
                all_lose = False
                break
        board.pop()
        if all_lose:
            return move1
    return None


def analyse_game(pgn_text: str, username_lower: str) -> list[dict]:
    missed = []
    try:
        game = chess.pgn.read_game(io.StringIO(pgn_text))
    except Exception:
        return missed
    if game is None:
        return missed

    headers = game.headers
    white = headers.get("White", "").lower()
    black = headers.get("Black", "").lower()
    if username_lower not in (white, black):
        return missed
    user_color = chess.WHITE if white == username_lower else chess.BLACK

    board = game.board()
    for node in game.mainline():
        if board.turn == user_color:
            m1 = find_mate_in_1(board)
            if m1 is not None:
                played = node.move
                if played != m1:
                    missed.append({
                        "mate_in": 1,
                        "fen": board.fen(),
                        "best_move": board.san(m1),
                        "played_move": board.san(played),
                        "move_number": board.fullmove_number,
                    })
            else:
                m2 = find_mate_in_2(board)
                if m2 is not None:
                    played = node.move
                    if played != m2:
                        missed.append({
                            "mate_in": 2,
                            "fen": board.fen(),
                            "best_move": board.san(m2),
                            "played_move": board.san(played),
                            "move_number": board.fullmove_number,
                        })
        try:
            board.push(node.move)
        except Exception:
            break

    return missed


def main() -> None:
    parser = argparse.ArgumentParser(description="Find missed mate-in-1 and mate-in-2 opportunities")
    parser.add_argument("--user", default=os.environ.get("CHESS_USERNAME", ""),
                        help="Chess.com username (default: $CHESS_USERNAME)")
    parser.add_argument("--time-class", default="rapid",
                        help="Time class to analyse (default: rapid)")
    parser.add_argument("--limit", type=int, default=None,
                        help="Only analyse the most recent N games")
    parser.add_argument("--force", action="store_true",
                        help="Drop existing missed_mates table and re-run")
    args = parser.parse_args()

    username = args.user
    if not username:
        parser.error("No username. Pass --user or set CHESS_USERNAME.")

    db_path = Path("data") / f"{username}.duckdb"
    if not db_path.exists():
        print(f"Error: database not found at {db_path}", file=sys.stderr)
        sys.exit(1)

    conn = duckdb.connect(str(db_path))

    if args.force:
        conn.execute("DROP TABLE IF EXISTS missed_mates")
        print("Dropped existing missed_mates table.", file=sys.stderr)

    conn.execute(CREATE_TABLE)

    # Skip games already analysed
    analysed_urls: set[str] = set()
    try:
        rows = conn.execute("SELECT DISTINCT game_url FROM missed_mates").fetchall()
        analysed_urls = {r[0] for r in rows}
    except duckdb.Error:
        pass

    query = f"""
    SELECT url, pgn, end_time, opening, color, opponent
    FROM games
    WHERE (white = '{username}' OR black = '{username}')
      AND time_class = '{args.time_class}'
      AND pgn IS NOT NULL
    ORDER BY end_time DESC
    """
    if args.limit:
        query += f" LIMIT {args.limit}"

    games = conn.execute(query).fetchall()
    to_do = [(url, pgn, et, op, col, opp) for url, pgn, et, op, col, opp in games
             if url not in analysed_urls]

    print(f"Games to analyse: {len(to_do)}  (already done: {len(analysed_urls)})",
          file=sys.stderr)

    username_lower = username.lower()
    total_missed = 0
    batch: list[tuple] = []

    for i, (url, pgn_text, end_time, opening, color, opponent) in enumerate(to_do):
        results = analyse_game(pgn_text, username_lower)
        for r in results:
            batch.append((
                url, end_time, opening, color, opponent,
                r["move_number"], r["mate_in"],
                r["fen"], r["best_move"], r["played_move"],
            ))
            total_missed += 1

        # Flush every 100 games
        if len(batch) >= 100 or (i + 1) == len(to_do):
            if batch:
                conn.executemany(INSERT_ROW, batch)
                batch = []

        if (i + 1) % 100 == 0 or (i + 1) == len(to_do):
            print(f"  {i + 1}/{len(to_do)} games analysed — {total_missed} missed mates so far",
                  file=sys.stderr, flush=True)

    conn.close()
    print(f"\nDone. {total_missed} missed mates stored in missed_mates table.", file=sys.stderr)
    print(f"Query them: python main.py query \"SELECT * FROM missed_mates ORDER BY end_time DESC LIMIT 20\"")


if __name__ == "__main__":
    main()
