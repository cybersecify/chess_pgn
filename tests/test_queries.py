"""Smoke tests — every .sql file in queries/ must execute without error."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from src.store import init_db, upsert_games

USERNAME = "rathnakaragn"

QUERIES_DIR = Path(__file__).parent.parent / "queries"

SQL_FILES = sorted(QUERIES_DIR.rglob("*.sql"))

# Rich sample game that satisfies most query filters:
# - WQ trap (2. Qh5), Icelandic Gambit (3... e5), Scandinavian opening
# - clock annotations, ELO headers, termination, time control
SAMPLE_GAMES = [
    {
        "url": "https://chess.com/game/wq1",
        "pgn": (
            '[ECO "C20"]\n'
            '[ECOUrl "https://www.chess.com/openings/Scandinavian-Defense"]\n'
            '[Opening "Scandinavian Defense"]\n'
            '[WhiteElo "1300"]\n'
            '[BlackElo "1250"]\n'
            '[UTCDate "2025.07.15"]\n'
            '[StartTime "10:00:00"]\n'
            '[EndDate "2025.07.15"]\n'
            '[EndTime "10:15:00"]\n'
            '[Termination "rathnakaragn won by resignation"]\n'
            '[TimeControl "600"]\n'
            '\n'
            '1. e4 {[%clk 0:09:50]} 1... d5 {[%clk 0:09:45]} '
            '2. Qh5 {[%clk 0:09:40]} 2... Nc6 {[%clk 0:09:35]} '
            '3. Bc4 {[%clk 0:09:30]} 3... e5 {[%clk 0:09:25]} '
            '4. Qxf7# {[%clk 0:09:20]} *'
        ),
        "time_class": "rapid",
        "time_control": "600",
        "end_time": 1752566400,
        "white": {"username": USERNAME, "result": "win"},
        "black": {"username": "opponent1", "result": "checkmated"},
        "rated": True,
        "fen": "",
    },
    {
        "url": "https://chess.com/game/wq2",
        "pgn": (
            '[ECO "C20"]\n'
            '[ECOUrl "https://www.chess.com/openings/Scandinavian-Defense"]\n'
            '[Opening "Scandinavian Defense"]\n'
            '[WhiteElo "1280"]\n'
            '[BlackElo "1310"]\n'
            '[UTCDate "2025.08.10"]\n'
            '[StartTime "20:00:00"]\n'
            '[EndDate "2025.08.10"]\n'
            '[EndTime "20:20:00"]\n'
            '[Termination "opponent2 won by checkmate"]\n'
            '[TimeControl "600"]\n'
            '\n'
            '1. e4 {[%clk 0:09:50]} 1... e5 {[%clk 0:09:45]} '
            '2. Qh5 {[%clk 0:09:40]} 2... Nc6 {[%clk 0:09:35]} '
            '3. Bc4 {[%clk 0:09:30]} 3... g6 {[%clk 0:09:25]} '
            '4. Qf3 {[%clk 0:09:20]} 4... Nf6 {[%clk 0:09:15]} '
            '5. Ne2 {[%clk 0:09:10]} 5... d6 {[%clk 0:09:05]} '
            '6. d3 {[%clk 0:09:00]} *'
        ),
        "time_class": "rapid",
        "time_control": "600",
        "end_time": 1754784000,
        "white": {"username": USERNAME, "result": "lose"},
        "black": {"username": "opponent2", "result": "win"},
        "rated": True,
        "fen": "",
    },
    {
        "url": "https://chess.com/game/blitz1",
        "pgn": (
            '[ECO "B20"]\n'
            '[ECOUrl "https://www.chess.com/openings/Sicilian-Defense"]\n'
            '[Opening "Sicilian Defense: Smith-Morra Gambit"]\n'
            '[WhiteElo "1290"]\n'
            '[BlackElo "1260"]\n'
            '[UTCDate "2025.09.01"]\n'
            '[StartTime "15:00:00"]\n'
            '[EndDate "2025.09.01"]\n'
            '[EndTime "15:05:00"]\n'
            '[Termination "rathnakaragn won by resignation"]\n'
            '[TimeControl "180"]\n'
            '\n'
            '1. e4 {[%clk 0:02:55]} 1... c5 {[%clk 0:02:50]} '
            '2. d4 {[%clk 0:02:50]} 2... cxd4 {[%clk 0:02:45]} '
            '3. c3 {[%clk 0:02:45]} *'
        ),
        "time_class": "blitz",
        "time_control": "180",
        "end_time": 1756684800,
        "white": {"username": USERNAME, "result": "win"},
        "black": {"username": "opponent3", "result": "lose"},
        "rated": True,
        "fen": "",
    },
    {
        "url": "https://chess.com/game/black1",
        "pgn": (
            '[ECO "B01"]\n'
            '[ECOUrl "https://www.chess.com/openings/Scandinavian-Defense-Modern-Icelandic-Palme-Gambit"]\n'
            '[Opening "Scandinavian Defense: Modern Icelandic Palme Gambit"]\n'
            '[WhiteElo "1320"]\n'
            '[BlackElo "1295"]\n'
            '[UTCDate "2025.10.05"]\n'
            '[StartTime "09:00:00"]\n'
            '[EndDate "2025.10.05"]\n'
            '[EndTime "09:12:00"]\n'
            '[Termination "rathnakaragn won by resignation"]\n'
            '[TimeControl "600"]\n'
            '\n'
            '1. e4 {[%clk 0:09:50]} 1... d5 {[%clk 0:09:48]} '
            '2. exd5 {[%clk 0:09:45]} 2... Nf6 {[%clk 0:09:43]} '
            '3. d4 {[%clk 0:09:40]} 3... e5 {[%clk 0:09:38]} '
            '4. dxe6 {[%clk 0:09:35]} *'
        ),
        "time_class": "rapid",
        "time_control": "600",
        "end_time": 1759622400,
        "white": {"username": "opponent4", "result": "lose"},
        "black": {"username": USERNAME, "result": "win"},
        "rated": True,
        "fen": "",
    },
    {
        "url": "https://chess.com/game/bdg1",
        "pgn": (
            '[ECO "D00"]\n'
            '[ECOUrl "https://www.chess.com/openings/Queens-Pawn-Opening-Blackmar-Diemer-Gambit"]\n'
            '[Opening "Queens Pawn Opening: Blackmar-Diemer Gambit"]\n'
            '[WhiteElo "1300"]\n'
            '[BlackElo "1280"]\n'
            '[UTCDate "2025.11.01"]\n'
            '[StartTime "14:00:00"]\n'
            '[EndDate "2025.11.01"]\n'
            '[EndTime "14:10:00"]\n'
            '[Termination "rathnakaragn won by resignation"]\n'
            '[TimeControl "600"]\n'
            '\n'
            '1. e4 {[%clk 0:09:50]} 1... d5 {[%clk 0:09:48]} '
            '2. d4 {[%clk 0:09:45]} 2... dxe4 {[%clk 0:09:43]} '
            '3. Nc3 {[%clk 0:09:40]} *'
        ),
        "time_class": "rapid",
        "time_control": "600",
        "end_time": 1762387200,
        "white": {"username": USERNAME, "result": "win"},
        "black": {"username": "opponent5", "result": "lose"},
        "rated": True,
        "fen": "",
    },
]


@pytest.fixture(scope="module")
def conn():
    c = init_db(":memory:")
    upsert_games(c, SAMPLE_GAMES)
    # missed_mates table is created by the scanner script — seed an empty one
    c.execute("""
        CREATE TABLE IF NOT EXISTS missed_mates (
            game_url    TEXT,
            end_time    INTEGER,
            opening     TEXT,
            color       TEXT,
            opponent    TEXT,
            move_number INTEGER,
            mate_in     INTEGER,
            fen         TEXT,
            best_move   TEXT,
            played_move TEXT
        )
    """)
    yield c
    c.close()


TIME_CLASS = "rapid"


def substitute_placeholders(sql: str) -> str:
    sql = sql.replace("$USERNAME", f"'{USERNAME}'")
    sql = sql.replace("$TIME_CLASS", f"'{TIME_CLASS}'")
    return sql


@pytest.mark.parametrize("sql_file", SQL_FILES, ids=lambda p: str(p.relative_to(QUERIES_DIR)))
def test_query_executes(conn, sql_file):
    sql = substitute_placeholders(sql_file.read_text())
    # Queries with HAVING COUNT(*) >= N may return empty results — that is fine.
    # We only assert no exception is raised.
    conn.execute(sql).fetchall()
