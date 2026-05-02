"""Unit tests for src.store — all use in-memory DuckDB."""

import pytest

from src.store import init_db, upsert_games, get_synced_archives, mark_archive_synced, query_games, raw_sql, stats


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


class TestArchiveTracking:
    def test_empty_initially(self, conn):
        assert get_synced_archives(conn) == set()

    def test_mark_and_retrieve(self, conn):
        url = "https://api.chess.com/pub/player/rathnakaragn/games/2024/01"
        mark_archive_synced(conn, url)
        assert url in get_synced_archives(conn)

    def test_mark_idempotent(self, conn):
        url = "https://api.chess.com/pub/player/rathnakaragn/games/2024/01"
        mark_archive_synced(conn, url)
        mark_archive_synced(conn, url)  # should not raise
        assert len(get_synced_archives(conn)) == 1


class TestQueryGames:
    def test_returns_all(self, conn):
        upsert_games(conn, [make_game(url="u1"), make_game(url="u2")])
        assert len(query_games(conn)) == 2

    def test_filter_time_class(self, conn):
        upsert_games(conn, [
            make_game(url="u1", time_class="rapid"),
            make_game(url="u2", time_class="blitz"),
        ])
        results = query_games(conn, time_class="rapid")
        assert len(results) == 1
        assert results[0]["time_class"] == "rapid"

    def test_filter_since(self, conn):
        upsert_games(conn, [
            make_game(url="u1", end_time=1704067200),  # 2024-01-01
            make_game(url="u2", end_time=1706745600),  # 2024-02-01
        ])
        results = query_games(conn, since="20240201")
        assert len(results) == 1
        assert results[0]["url"] == "u2"

    def test_filter_until(self, conn):
        upsert_games(conn, [
            make_game(url="u1", end_time=1704067200),  # 2024-01-01
            make_game(url="u2", end_time=1706745600),  # 2024-02-01
        ])
        results = query_games(conn, until="20240131")
        assert len(results) == 1
        assert results[0]["url"] == "u1"

    def test_filter_n_last(self, conn):
        games = [
            make_game(url=f"u{i}", end_time=1704067200 + i * 86400)
            for i in range(5)
        ]
        upsert_games(conn, games)
        results = query_games(conn, n=2)
        assert len(results) == 2
        assert results[0]["url"] == "u3"
        assert results[1]["url"] == "u4"

    def test_returns_dicts(self, conn):
        upsert_games(conn, [make_game()])
        results = query_games(conn)
        assert isinstance(results[0], dict)
        assert "url" in results[0]
        assert "pgn" in results[0]


class TestRawSql:
    def test_returns_rows(self, conn):
        upsert_games(conn, [make_game()])
        rows = raw_sql(conn, "SELECT url FROM games")
        assert len(rows) == 1
        assert rows[0][0] == "https://chess.com/game/1"

    def test_empty_result(self, conn):
        assert raw_sql(conn, "SELECT url FROM games") == []


class TestStats:
    def test_total(self, conn):
        upsert_games(conn, [make_game(url="u1"), make_game(url="u2")])
        result = stats(conn, "rathnakaragn")
        assert result["total"] == 2

    def test_win_loss_count(self, conn):
        upsert_games(conn, [
            make_game(url="u1",
                      white={"username": "rathnakaragn", "result": "win"},
                      black={"username": "opp", "result": "lose"}),
            make_game(url="u2",
                      white={"username": "opp", "result": "win"},
                      black={"username": "rathnakaragn", "result": "lose"}),
        ])
        result = stats(conn, "rathnakaragn")
        rapid = result["by_time_class"]["rapid"]
        assert rapid["win"] == 1
        assert rapid["lose"] == 1
        assert rapid["draw"] == 0

    def test_longest_streak(self, conn):
        # 3 wins then 2 losses
        games = [
            make_game(
                url=f"u{i}",
                end_time=1704067200 + i * 86400,
                white={"username": "rathnakaragn",
                       "result": "win" if i < 3 else "lose"},
                black={"username": "opp",
                       "result": "lose" if i < 3 else "win"},
            )
            for i in range(5)
        ]
        upsert_games(conn, games)
        result = stats(conn, "rathnakaragn")
        assert result["longest_streak"] == 3
        assert result["current_streak"] == 0

    def test_current_streak(self, conn):
        # 1 loss then 2 wins (current streak = 2)
        games = [
            make_game(
                url=f"u{i}",
                end_time=1704067200 + i * 86400,
                white={"username": "rathnakaragn",
                       "result": "lose" if i == 0 else "win"},
                black={"username": "opp",
                       "result": "win" if i == 0 else "lose"},
            )
            for i in range(3)
        ]
        upsert_games(conn, games)
        result = stats(conn, "rathnakaragn")
        assert result["current_streak"] == 2

    def test_top_openings(self, conn):
        upsert_games(conn, [
            make_game(url=f"u{i}",
                      pgn=f'[Opening "Sicilian Defense"]\n\n1. e4 c5 *')
            for i in range(3)
        ] + [
            make_game(url="u99",
                      pgn='[Opening "Ruy Lopez"]\n\n1. e4 e5 *')
        ])
        result = stats(conn, "rathnakaragn")
        openings = [o for o, _ in result["top_openings"]]
        assert openings[0] == "Sicilian Defense"
