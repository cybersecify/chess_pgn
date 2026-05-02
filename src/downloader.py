"""Chess.com API client for downloading player games."""

from __future__ import annotations

import json
import ssl
import sys
import time
import urllib.error
import urllib.request

API_BASE = "https://api.chess.com/pub/player"
USER_AGENT = "ChessAnalyzer/1.0 (github.com/chess-analyzer)"


def _make_ssl_context() -> ssl.SSLContext:
    """Create SSL context, trying multiple certificate sources."""
    try:
        import certifi

        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        pass

    ctx = ssl.create_default_context()
    if ctx.cert_store_stats()["x509_ca"] > 0:
        return ctx

    for path in [
        "/etc/ssl/cert.pem",
        "/etc/ssl/certs/ca-certificates.crt",
        "/etc/pki/tls/certs/ca-bundle.crt",
    ]:
        try:
            ctx.load_verify_locations(path)
            if ctx.cert_store_stats()["x509_ca"] > 0:
                return ctx
        except (OSError, ssl.SSLError):
            continue

    print(
        "Warning: no CA certificates found; SSL verification disabled.",
        file=sys.stderr,
    )
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


_ssl_ctx: ssl.SSLContext | None = None


def _get_ssl_context() -> ssl.SSLContext:
    global _ssl_ctx
    if _ssl_ctx is None:
        _ssl_ctx = _make_ssl_context()
    return _ssl_ctx


def _api_get(url: str, retries: int = 3) -> dict:
    """Fetch JSON from chess.com API with backoff.

    Raises urllib.error.HTTPError directly for 404 (not found).
    Raises RuntimeError for all other failures after retries.
    """
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=30, context=_get_ssl_context()) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait = 2 ** (attempt + 1)
                print(f"  Rate limited, waiting {wait}s...", file=sys.stderr)
                time.sleep(wait)
            elif e.code == 404:
                raise
            else:
                print(f"  HTTP {e.code} for {url}, retrying...", file=sys.stderr)
                time.sleep(1)
        except (ssl.SSLError, urllib.error.URLError):
            time.sleep(1)
    raise RuntimeError(f"Failed to fetch {url} after {retries} retries")


def download_all_games(username: str) -> list[dict]:
    """Download all games for a chess.com user.

    Returns list of raw game dicts from the chess.com API.
    """
    print(f"Fetching game archives for {username}...", file=sys.stderr)

    try:
        archives_data = _api_get(f"{API_BASE}/{username}/games/archives")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise RuntimeError(f"Player '{username}' not found on chess.com")
        raise RuntimeError(f"API error {e.code} fetching archives for '{username}'")

    archive_urls = archives_data.get("archives", [])
    if not archive_urls:
        raise RuntimeError(f"No games found for player '{username}'")

    print(f"Found {len(archive_urls)} monthly archives.", file=sys.stderr)

    all_games: list[dict] = []

    for i, url in enumerate(archive_urls, 1):
        parts = url.rstrip("/").split("/")
        ym = f"{parts[-2]}/{parts[-1]}"

        data = _api_get(url)
        games = data.get("games", [])

        print(
            f"  [{i}/{len(archive_urls)}] {ym}: {len(games)} games",
            file=sys.stderr,
        )

        all_games.extend(games)

    print(f"Total: {len(all_games)} games downloaded.", file=sys.stderr)
    return all_games
