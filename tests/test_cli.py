"""Integration tests for CLI subcommands."""

from __future__ import annotations

import sys
from unittest.mock import patch

import pytest

from src.store import init_db


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
        from src.store import upsert_games
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
        from src.store import upsert_games
        upsert_games(conn, [
            SAMPLE_GAME,
            {**SAMPLE_GAME, "url": "u2", "time_class": "blitz"},
        ])
        conn.close()
        out = tmp_path / "rapid.pgn"
        run_cli("export", "--db", db_path, "--time-class", "blitz", "-o", str(out))
        content = out.read_text()
        assert content.count("Sicilian Defense") == 1

    def test_export_missing_db_exits(self, tmp_path):
        with pytest.raises(SystemExit) as exc:
            run_cli("export", "--db", str(tmp_path / "missing.duckdb"))
        assert exc.value.code == 1
