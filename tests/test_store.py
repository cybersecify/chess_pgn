"""Unit tests for src.store — all use in-memory DuckDB."""

import pytest

from src.store import init_db, upsert_games


def make_game(**overrides):
    g = {
        "url": "https://chess.com/game/1",
        "pgn": '[ECO "B20"]\n[Opening "Sicilian Defense"]\n\n1. e4 c5 *',
        "time_class": "rapid",
        "time_control": "600",
        "end_time": 1704067200,  # 2024-01-01 00:00:00 UTC
        "white": {"username": "rathnakaragn", "result": "win"},
        "black": {"username": "opponent", "result": "lose"},
        "rated": True,
        "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
    }
    g.update(overrides)
    return g


@pytest.fixture
def conn():
    c = init_db(":memory:")
    yield c
    c.close()


class TestInitDb:
    def test_creates_games_table(self, conn):
        tables = {r[0] for r in conn.execute("SHOW TABLES").fetchall()}
        assert "games" in tables

    def test_creates_synced_archives_table(self, conn):
        tables = {r[0] for r in conn.execute("SHOW TABLES").fetchall()}
        assert "synced_archives" in tables


class TestUpsertGames:
    def test_inserts_game(self, conn):
        count = upsert_games(conn, [make_game()])
        assert count == 1
        row = conn.execute("SELECT url, white, eco, opening FROM games").fetchone()
        assert row[0] == "https://chess.com/game/1"
        assert row[1] == "rathnakaragn"
        assert row[2] == "B20"
        assert row[3] == "Sicilian Defense"

    def test_deduplicates_on_url(self, conn):
        upsert_games(conn, [make_game()])
        second = upsert_games(conn, [make_game()])
        assert second == 0
        assert conn.execute("SELECT COUNT(*) FROM games").fetchone()[0] == 1

    def test_inserts_multiple(self, conn):
        games = [make_game(url="https://chess.com/game/1"),
                 make_game(url="https://chess.com/game/2")]
        count = upsert_games(conn, games)
        assert count == 2

    def test_empty_list(self, conn):
        assert upsert_games(conn, []) == 0

    def test_flattens_white_black(self, conn):
        upsert_games(conn, [make_game(
            white={"username": "alice", "result": "win"},
            black={"username": "bob", "result": "lose"},
        )])
        row = conn.execute("SELECT white, black, white_result, black_result FROM games").fetchone()
        assert row == ("alice", "bob", "win", "lose")

    def test_eco_missing_from_pgn(self, conn):
        upsert_games(conn, [make_game(pgn="1. e4 e5 *")])
        row = conn.execute("SELECT eco, opening FROM games").fetchone()
        assert row[0] is None
        assert row[1] is None
