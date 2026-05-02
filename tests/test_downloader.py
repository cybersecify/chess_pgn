"""Unit tests for src.downloader."""

import io
import json
import urllib.error
from unittest.mock import MagicMock, patch

import pytest

from src.downloader import _api_get, download_all_games


def _mock_response(data: dict):
    """Create a mock urlopen response returning JSON data."""
    body = json.dumps(data).encode()
    resp = MagicMock()
    resp.read.return_value = body
    resp.__enter__ = lambda s: s
    resp.__exit__ = MagicMock(return_value=False)
    return resp


class TestApiGet:
    @patch("src.downloader.urllib.request.urlopen")
    def test_success(self, mock_urlopen):
        mock_urlopen.return_value = _mock_response({"ok": True})
        result = _api_get("https://example.com/api")
        assert result == {"ok": True}

    @patch("src.downloader.time.sleep")
    @patch("src.downloader.urllib.request.urlopen")
    def test_429_retry(self, mock_urlopen, mock_sleep):
        err = urllib.error.HTTPError(
            "url", 429, "Too Many Requests", {}, io.BytesIO(b"")
        )
        mock_urlopen.side_effect = [err, _mock_response({"ok": True})]
        result = _api_get("https://example.com/api", retries=3)
        assert result == {"ok": True}
        mock_sleep.assert_called_once_with(2)  # 2**(0+1) = 2

    @patch("src.downloader.urllib.request.urlopen")
    def test_404_raises(self, mock_urlopen):
        err = urllib.error.HTTPError("url", 404, "Not Found", {}, io.BytesIO(b""))
        mock_urlopen.side_effect = err
        with pytest.raises(urllib.error.HTTPError) as exc_info:
            _api_get("https://example.com/api")
        assert exc_info.value.code == 404

    @patch("src.downloader.time.sleep")
    @patch("src.downloader.urllib.request.urlopen")
    def test_exhausted_retries(self, mock_urlopen, mock_sleep):
        err = urllib.error.HTTPError(
            "url", 500, "Server Error", {}, io.BytesIO(b"")
        )
        mock_urlopen.side_effect = [err, err, err]
        with pytest.raises(RuntimeError, match="Failed to fetch"):
            _api_get("https://example.com/api", retries=3)


class TestDownloadAllGames:
    @patch("src.downloader.time.sleep")
    @patch("src.downloader._api_get")
    def test_happy_path(self, mock_api, mock_sleep):
        mock_api.side_effect = [
            {"archives": [
                "https://api.chess.com/pub/player/u/games/2025/01",
                "https://api.chess.com/pub/player/u/games/2025/02",
            ]},
            {"games": [{"pgn": "1. e4 e5 *"}]},
            {"games": [{"pgn": "1. d4 d5 *"}, {"pgn": "1. c4 *"}]},
        ]
        result = download_all_games("testuser")
        assert len(result) == 3

    @patch("src.downloader._api_get")
    def test_player_not_found(self, mock_api):
        err = urllib.error.HTTPError("url", 404, "Not Found", {}, io.BytesIO(b""))
        mock_api.side_effect = err
        with pytest.raises(RuntimeError, match="not found"):
            download_all_games("nobody")

    @patch("src.downloader._api_get")
    def test_no_archives(self, mock_api):
        mock_api.return_value = {"archives": []}
        with pytest.raises(RuntimeError, match="No games found"):
            download_all_games("emptyplayer")
