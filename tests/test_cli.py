"""Integration tests for CLI subcommands."""

from __future__ import annotations

import sys
from unittest.mock import patch

import pytest

from src.store import init_db, upsert_games


ARCHIVE_URL = "https://api.chess.com/pub/player/rathnakaragn/games/2024/01"

SAMPLE_GAME = {
    "url": "https://chess.com/game/1",
    "pgn": '[ECO "B20"]\n[Opening "Sicilian Defense"]\n\n1. e4 c5 *',
    "time_class": "rapid",
    "time_control": "600",
    "end_time": 1704067200,
    "white": {"username": "rathnakaragn", "result": "win"},
    "black": {"username": "opponent", "result": "lose"},
    "rated": True,
    "fen": "",
}

DEFAULT_DB = "data/rathnakaragn.duckdb"


def run_cli(*args):
    with patch("sys.argv", ["prog"] + list(args)):
        from src.cli import main
        main()


def seed_db(tmp_path, games=None):
    """Create data/ dir and seed the default DB in tmp_path."""
    (tmp_path / "data").mkdir(exist_ok=True)
    db_path = str(tmp_path / DEFAULT_DB)
    conn = init_db(db_path)
    upsert_games(conn, games or [SAMPLE_GAME])
    conn.close()
    return db_path


class TestSync:
    def test_creates_db_and_inserts_games(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        with patch("src.cli._api_get", side_effect=[
            {"archives": [ARCHIVE_URL]},
            {"games": [SAMPLE_GAME]},
        ]):
            run_cli("sync", "rathnakaragn")

        conn = init_db(str(tmp_path / DEFAULT_DB))
        count = conn.execute("SELECT COUNT(*) FROM games").fetchone()[0]
        assert count == 1

    def test_skips_already_synced_archive(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        api_calls = []

        def fake_api(url, retries=3):
            api_calls.append(url)
            if "archives" in url:
                return {"archives": [ARCHIVE_URL]}
            return {"games": [SAMPLE_GAME]}

        with patch("src.cli._api_get", side_effect=fake_api):
            run_cli("sync", "rathnakaragn")

        api_calls.clear()

        with patch("src.cli._api_get", side_effect=fake_api):
            run_cli("sync", "rathnakaragn")

        assert ARCHIVE_URL not in api_calls

    def test_default_db_path_uses_username(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        with patch("src.cli._api_get", side_effect=[
            {"archives": [ARCHIVE_URL]},
            {"games": [SAMPLE_GAME]},
        ]):
            run_cli("sync", "rathnakaragn")

        assert (tmp_path / DEFAULT_DB).exists()


class TestExport:
    def test_export_to_file(self, tmp_path, monkeypatch):
        monkeypatch.setenv("CHESS_USERNAME", "rathnakaragn")
        monkeypatch.chdir(tmp_path)
        seed_db(tmp_path)
        out = tmp_path / "out.pgn"
        run_cli("export", "-o", str(out))
        assert "Sicilian Defense" in out.read_text()

    def test_export_to_stdout(self, tmp_path, monkeypatch, capsys):
        monkeypatch.setenv("CHESS_USERNAME", "rathnakaragn")
        monkeypatch.chdir(tmp_path)
        seed_db(tmp_path)
        run_cli("export")
        assert "Sicilian Defense" in capsys.readouterr().out

    def test_export_filter_time_class(self, tmp_path, monkeypatch):
        monkeypatch.setenv("CHESS_USERNAME", "rathnakaragn")
        monkeypatch.chdir(tmp_path)
        seed_db(tmp_path, games=[
            SAMPLE_GAME,
            {**SAMPLE_GAME, "url": "u2", "time_class": "blitz",
             "pgn": '[ECO "C60"]\n[Opening "Ruy Lopez"]\n\n1. e4 e5 2. Nf3 Nc6 3. Bb5 *'},
        ])
        out = tmp_path / "blitz.pgn"
        run_cli("export", "--time-class", "blitz", "-o", str(out))
        content = out.read_text()
        assert "Ruy Lopez" in content
        assert "Sicilian Defense" not in content

    def test_export_missing_db_exits(self, tmp_path, monkeypatch):
        monkeypatch.setenv("CHESS_USERNAME", "rathnakaragn")
        monkeypatch.chdir(tmp_path)
        with pytest.raises(SystemExit) as exc:
            run_cli("export")
        assert exc.value.code == 1


class TestQuery:
    def test_query_prints_rows(self, tmp_path, monkeypatch, capsys):
        monkeypatch.setenv("CHESS_USERNAME", "rathnakaragn")
        monkeypatch.chdir(tmp_path)
        seed_db(tmp_path)
        run_cli("query", "SELECT url FROM games")
        assert "https://chess.com/game/1" in capsys.readouterr().out

    def test_query_malformed_sql_exits(self, tmp_path, monkeypatch):
        monkeypatch.setenv("CHESS_USERNAME", "rathnakaragn")
        monkeypatch.chdir(tmp_path)
        seed_db(tmp_path)
        with pytest.raises(SystemExit) as exc:
            run_cli("query", "SELEC * FORM games")
        assert exc.value.code == 1


class TestStats:
    def test_stats_prints_total(self, tmp_path, monkeypatch, capsys):
        monkeypatch.chdir(tmp_path)
        seed_db(tmp_path)
        run_cli("stats", "rathnakaragn")
        assert "Total games: 1" in capsys.readouterr().out

    def test_stats_missing_db_exits(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        with pytest.raises(SystemExit) as exc:
            run_cli("stats", "rathnakaragn")
        assert exc.value.code == 1


class TestBackfill:
    def test_backfill_updates_rows(self, tmp_path, monkeypatch, capsys):
        monkeypatch.chdir(tmp_path)
        seed_db(tmp_path)
        run_cli("backfill", "rathnakaragn")
        assert "rows updated" in capsys.readouterr().err

    def test_backfill_missing_db_exits(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        with pytest.raises(SystemExit) as exc:
            run_cli("backfill", "rathnakaragn")
        assert exc.value.code == 1


class TestRating:
    def test_rating_prints_current(self, tmp_path, monkeypatch, capsys):
        monkeypatch.chdir(tmp_path)
        seed_db(tmp_path, games=[{
            **SAMPLE_GAME,
            "pgn": '[WhiteElo "1200"]\n[BlackElo "1100"]\n\n1. e4 c5 *',
        }])
        run_cli("backfill", "rathnakaragn")
        capsys.readouterr()
        run_cli("rating", "rathnakaragn")
        out = capsys.readouterr().out
        assert "Rating for rathnakaragn" in out

    def test_rating_missing_db_exits(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        with pytest.raises(SystemExit) as exc:
            run_cli("rating", "rathnakaragn")
        assert exc.value.code == 1


class TestOpponent:
    def test_opponent_happy_path(self, tmp_path, monkeypatch, capsys):
        monkeypatch.setenv("CHESS_USERNAME", "rathnakaragn")
        monkeypatch.chdir(tmp_path)
        seed_db(tmp_path, games=[
            SAMPLE_GAME,
            {**SAMPLE_GAME, "url": "u2",
             "white": {"username": "fischer", "result": "win"},
             "black": {"username": "rathnakaragn", "result": "lose"}},
        ])
        run_cli("opponent", "fischer")
        out = capsys.readouterr().out
        assert "fischer" in out
        assert "W:" in out
        assert "L:" in out
        assert "D:" in out

    def test_opponent_missing_db_exits(self, tmp_path, monkeypatch):
        monkeypatch.setenv("CHESS_USERNAME", "rathnakaragn")
        monkeypatch.chdir(tmp_path)
        with pytest.raises(SystemExit) as exc:
            run_cli("opponent", "fischer")
        assert exc.value.code == 1


class TestDerivedColumns:
    def test_sync_populates_derived_columns(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        games = [
            {
                "url": "https://chess.com/game/1",
                "pgn": '[ECO "B20"]\n[ECOUrl "https://www.chess.com/openings/Sicilian-Defense"]\n[WhiteElo "1200"]\n[BlackElo "1100"]\n[UTCDate "2024.01.01"]\n[StartTime "00:00:00"]\n[EndDate "2024.01.01"]\n[EndTime "00:15:00"]\n[Termination "rathnakaragn won by resignation"]\n\n1. e4 c5 2. Nf3 *',
                "time_class": "rapid", "time_control": "600", "end_time": 1704067200,
                "white": {"username": "rathnakaragn", "result": "win"},
                "black": {"username": "fischer", "result": "lose"},
                "rated": True, "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
            }
        ]
        with patch("src.cli._api_get") as mock_api:
            mock_api.side_effect = [
                {"archives": ["https://api.chess.com/pub/player/rathnakaragn/games/2024/01"]},
                {"games": games},
            ]
            run_cli("sync", "rathnakaragn")

        import duckdb
        conn = duckdb.connect(str(tmp_path / DEFAULT_DB), read_only=True)
        row = conn.execute("SELECT color, opponent, user_result FROM games").fetchone()
        conn.close()
        assert row[0] == "white"
        assert row[1] == "fischer"
        assert row[2] == "win"
