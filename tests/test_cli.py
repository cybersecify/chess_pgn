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


def run_cli(*args):
    with patch("sys.argv", ["prog"] + list(args)):
        from src.cli import main
        main()


class TestSync:
    def test_creates_db_and_inserts_games(self, tmp_path):
        db_path = str(tmp_path / "test.duckdb")
        with patch("src.cli._api_get", side_effect=[
            {"archives": [ARCHIVE_URL]},
            {"games": [SAMPLE_GAME]},
        ]):
            run_cli("sync", "rathnakaragn", "--db", db_path)

        conn = init_db(db_path)
        count = conn.execute("SELECT COUNT(*) FROM games").fetchone()[0]
        assert count == 1

    def test_skips_already_synced_archive(self, tmp_path):
        db_path = str(tmp_path / "test.duckdb")
        api_calls = []

        def fake_api(url, retries=3):
            api_calls.append(url)
            if "archives" in url:
                return {"archives": [ARCHIVE_URL]}
            return {"games": [SAMPLE_GAME]}

        # First sync
        with patch("src.cli._api_get", side_effect=fake_api):
            run_cli("sync", "rathnakaragn", "--db", db_path)

        api_calls.clear()

        # Second sync — archive already cached, only archive list fetched
        with patch("src.cli._api_get", side_effect=fake_api):
            run_cli("sync", "rathnakaragn", "--db", db_path)

        assert ARCHIVE_URL not in api_calls

    def test_default_db_path_uses_username(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        with patch("src.cli._api_get", side_effect=[
            {"archives": [ARCHIVE_URL]},
            {"games": [SAMPLE_GAME]},
        ]):
            run_cli("sync", "rathnakaragn")

        assert (tmp_path / "data" / "rathnakaragn.duckdb").exists()


class TestExport:
    def _seed_db(self, db_path):
        conn = init_db(db_path)
        upsert_games(conn, [SAMPLE_GAME])
        conn.close()

    def test_export_to_file(self, tmp_path):
        db_path = str(tmp_path / "test.duckdb")
        self._seed_db(db_path)
        out = tmp_path / "out.pgn"
        run_cli("export", "--db", db_path, "-o", str(out))
        assert "Sicilian Defense" in out.read_text()

    def test_export_to_stdout(self, tmp_path, capsys):
        db_path = str(tmp_path / "test.duckdb")
        self._seed_db(db_path)
        run_cli("export", "--db", db_path)
        assert "Sicilian Defense" in capsys.readouterr().out

    def test_export_filter_time_class(self, tmp_path):
        db_path = str(tmp_path / "test.duckdb")
        conn = init_db(db_path)
        upsert_games(conn, [
            SAMPLE_GAME,  # rapid, Opening "Sicilian Defense"
            {**SAMPLE_GAME, "url": "u2", "time_class": "blitz",
             "pgn": '[ECO "C60"]\n[Opening "Ruy Lopez"]\n\n1. e4 e5 2. Nf3 Nc6 3. Bb5 *'},
        ])
        conn.close()
        out = tmp_path / "blitz.pgn"
        run_cli("export", "--db", db_path, "--time-class", "blitz", "-o", str(out))
        content = out.read_text()
        assert "Ruy Lopez" in content
        assert "Sicilian Defense" not in content

    def test_export_missing_db_exits(self, tmp_path):
        with pytest.raises(SystemExit) as exc:
            run_cli("export", "--db", str(tmp_path / "missing.duckdb"))
        assert exc.value.code == 1


class TestQuery:
    def test_query_prints_rows(self, tmp_path, capsys):
        db_path = str(tmp_path / "test.duckdb")
        conn = init_db(db_path)
        upsert_games(conn, [SAMPLE_GAME])
        conn.close()
        run_cli("query", "SELECT url FROM games", "--db", db_path)
        out = capsys.readouterr().out
        assert "https://chess.com/game/1" in out

    def test_query_invalid_sql_exits(self, tmp_path):
        db_path = str(tmp_path / "test.duckdb")
        conn = init_db(db_path)
        conn.close()
        with pytest.raises(SystemExit) as exc:
            run_cli("query", "SELECT FROM NOWHERE", "--db", db_path)
        assert exc.value.code == 1


class TestStats:
    def test_stats_prints_total(self, tmp_path, capsys):
        db_path = str(tmp_path / "test.duckdb")
        conn = init_db(db_path)
        upsert_games(conn, [SAMPLE_GAME])
        conn.close()
        run_cli("stats", "rathnakaragn", "--db", db_path)
        out = capsys.readouterr().out
        assert "Total games: 1" in out

    def test_stats_missing_db_exits(self, tmp_path):
        with pytest.raises(SystemExit) as exc:
            run_cli("stats", "rathnakaragn", "--db", str(tmp_path / "missing.duckdb"))
        assert exc.value.code == 1


class TestBackfill:
    def test_backfill_updates_rows(self, tmp_path, capsys):
        db_path = str(tmp_path / "test.duckdb")
        conn = init_db(db_path)
        upsert_games(conn, [SAMPLE_GAME])
        conn.close()
        run_cli("backfill", "rathnakaragn", "--db", db_path)
        err = capsys.readouterr().err
        assert "rows updated" in err

    def test_backfill_missing_db_exits(self, tmp_path):
        with pytest.raises(SystemExit) as exc:
            run_cli("backfill", "rathnakaragn", "--db", str(tmp_path / "missing.duckdb"))
        assert exc.value.code == 1


class TestOpponent:
    def test_opponent_happy_path(self, tmp_path, capsys):
        db_path = str(tmp_path / "test.duckdb")
        conn = init_db(db_path)
        # Two games against opponent "fischer"
        upsert_games(conn, [
            SAMPLE_GAME,  # white: rathnakaragn (win), black: opponent (lose)
            {**SAMPLE_GAME, "url": "u2",
             "white": {"username": "fischer", "result": "win"},
             "black": {"username": "rathnakaragn", "result": "lose"}},
        ])
        conn.close()
        run_cli("opponent", "fischer", "--db", db_path)
        out = capsys.readouterr().out
        assert "fischer" in out
        assert "W:" in out
        assert "L:" in out
        assert "D:" in out

    def test_opponent_missing_db_exits(self, tmp_path):
        with pytest.raises(SystemExit) as exc:
            run_cli("opponent", "fischer", "--db", str(tmp_path / "missing.duckdb"))
        assert exc.value.code == 1
