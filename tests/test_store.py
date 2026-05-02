"""Unit tests for src.store — all use in-memory DuckDB."""

import pytest

from src.store import (init_db, upsert_games, get_synced_archives,
                        mark_archive_synced, query_games, raw_sql, stats,
                        _migrate_db, backfill_derived_columns, rating_history)


def make_game(**overrides):
    g = {
        "url": "https://chess.com/game/1",
        "pgn": (
            '[ECO "B20"]\n'
            '[ECOUrl "https://www.chess.com/openings/Sicilian-Defense"]\n'
            '[WhiteElo "1200"]\n'
            '[BlackElo "1100"]\n'
            '[UTCDate "2024.01.01"]\n'
            '[StartTime "00:00:00"]\n'
            '[EndDate "2024.01.01"]\n'
            '[EndTime "00:15:00"]\n'
            '[Termination "rathnakaragn won by resignation"]\n'
            '\n'
            '1. e4 c5 2. Nf3 *'
        ),
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
        assert row[3] == "Sicilian Defense"  # parsed from ECOUrl slug

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

    def test_eco_url_parsed_as_opening(self, conn):
        upsert_games(conn, [make_game(
            pgn='[ECO "C41"]\n[ECOUrl "https://www.chess.com/openings/Philidor-Defense"]\n\n1. e4 e5 *'
        )])
        row = conn.execute("SELECT opening FROM games").fetchone()
        assert row[0] == "Philidor Defense"

    def test_opening_tag_fallback(self, conn):
        upsert_games(conn, [make_game(
            pgn='[ECO "B20"]\n[Opening "Sicilian Defense"]\n\n1. e4 c5 *'
        )])
        row = conn.execute("SELECT opening FROM games").fetchone()
        assert row[0] == "Sicilian Defense"

    def test_new_columns_populated(self, conn):
        upsert_games(conn, [make_game()])
        row = conn.execute(
            "SELECT white_elo, black_elo, move_count, game_duration_secs, termination FROM games"
        ).fetchone()
        assert row[0] == 1200   # white_elo
        assert row[1] == 1100   # black_elo
        assert row[2] == 2      # move_count: last move number is "2. Nf3"
        assert row[3] == 900    # game_duration_secs: 00:00:00 to 00:15:00 = 900s
        assert row[4] == "rathnakaragn won by resignation"


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
                      pgn='[ECOUrl "https://www.chess.com/openings/Sicilian-Defense"]\n\n1. e4 c5 *')
            for i in range(3)
        ] + [
            make_game(url="u99",
                      pgn='[ECOUrl "https://www.chess.com/openings/Ruy-Lopez"]\n\n1. e4 e5 *')
        ])
        result = stats(conn, "rathnakaragn")
        openings = [o for o, _ in result["top_openings"]]
        assert openings[0] == "Sicilian Defense"


class TestMigrateDb:
    def test_adds_missing_columns_to_old_schema(self):
        import duckdb
        conn = duckdb.connect(":memory:")
        conn.execute("""
            CREATE TABLE games (
                url TEXT PRIMARY KEY,
                pgn TEXT,
                opening TEXT
            )
        """)
        _migrate_db(conn)
        cols = {r[0] for r in conn.execute("DESCRIBE games").fetchall()}
        assert "white_elo" in cols
        assert "black_elo" in cols
        assert "move_count" in cols
        assert "game_duration_secs" in cols
        assert "termination" in cols

    def test_idempotent_on_full_schema(self):
        import duckdb
        conn = duckdb.connect(":memory:")
        conn.execute("""
            CREATE TABLE games (
                url TEXT PRIMARY KEY, pgn TEXT, time_class TEXT, time_control TEXT,
                end_time INTEGER, white TEXT, black TEXT, white_result TEXT,
                black_result TEXT, rated BOOLEAN, fen TEXT, eco TEXT, opening TEXT,
                white_elo INTEGER, black_elo INTEGER, move_count INTEGER,
                game_duration_secs INTEGER, termination TEXT
            )
        """)
        _migrate_db(conn)  # should not raise
        cols = {r[0] for r in conn.execute("DESCRIBE games").fetchall()}
        assert len(cols) == 18


class TestBackfill:
    def test_backfills_nulled_columns(self, conn):
        upsert_games(conn, [make_game()])
        # Simulate old rows with NULLs in derived columns
        conn.execute("UPDATE games SET white_elo = NULL, move_count = NULL, termination = NULL")
        updated = backfill_derived_columns(conn)
        assert updated == 1
        row = conn.execute("SELECT white_elo, move_count, termination FROM games").fetchone()
        assert row[0] == 1200
        assert row[1] == 2
        assert row[2] == "rathnakaragn won by resignation"

    def test_skips_complete_rows(self, conn):
        upsert_games(conn, [make_game()])
        # All derived columns already populated — nothing to do
        updated = backfill_derived_columns(conn)
        assert updated == 0

    def test_returns_zero_when_no_games(self, conn):
        updated = backfill_derived_columns(conn)
        assert updated == 0


class TestRatingHistory:
    def test_returns_current_elo_per_format(self, conn):
        upsert_games(conn, [make_game()])  # rapid, white_elo=1200
        result = rating_history(conn, "rathnakaragn")
        assert "rapid" in result
        assert result["rapid"]["current"] == 1200

    def test_delta_is_none_when_no_prior_game_this_month(self, conn):
        # make_game end_time = 2024-01-01, which is not current month (2026-05)
        upsert_games(conn, [make_game()])
        result = rating_history(conn, "rathnakaragn")
        assert result["rapid"]["delta"] is None

    def test_empty_when_no_elo_in_pgn(self, conn):
        upsert_games(conn, [make_game(pgn="1. e4 *")])
        result = rating_history(conn, "rathnakaragn")
        assert result == {}
