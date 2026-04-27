from __future__ import annotations

import base64
from typing import Any

import httpx

from cyberdeck.integrations.base import Integration

_TOKEN_URL = "https://accounts.spotify.com/api/token"
_NOW_PLAYING_URL = "https://api.spotify.com/v1/me/player/currently-playing"

EMPTY_STATE: dict[str, Any] = {
    "is_playing": False,
    "track": None,
    "artist": None,
    "album": None,
    "progress": 0.0,
    "elapsed": "0:00",
    "total": "0:00",
    "art_url": None,
}


class SpotifyIntegration(Integration):
    name = "spotify"

    def event_name(self) -> str:
        return "spotify.update"

    async def fetch(self) -> dict[str, Any]:
        if not self.config.app.spotify.enabled or not self._has_credentials:
            return dict(EMPTY_STATE)

        async with httpx.AsyncClient(timeout=10.0) as client:
            access_token = await self._refresh_access_token(client)
            response = await client.get(
                _NOW_PLAYING_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            if response.status_code == 204:
                return dict(EMPTY_STATE)
            response.raise_for_status()
            if not response.content:
                return dict(EMPTY_STATE)
            return _playing_state(response.json())

    @property
    def _has_credentials(self) -> bool:
        return bool(
            self.config.spotify_client_id
            and self.config.spotify_client_secret
            and self.config.spotify_refresh_token
        )

    async def _refresh_access_token(self, client: httpx.AsyncClient) -> str:
        auth_raw = f"{self.config.spotify_client_id}:{self.config.spotify_client_secret}".encode()
        auth = base64.b64encode(auth_raw).decode("ascii")
        response = await client.post(
            _TOKEN_URL,
            headers={"Authorization": f"Basic {auth}"},
            data={
                "grant_type": "refresh_token",
                "refresh_token": self.config.spotify_refresh_token,
            },
        )
        response.raise_for_status()
        return str(response.json()["access_token"])


def _playing_state(payload: dict[str, Any]) -> dict[str, Any]:
    item = payload.get("item")
    if not isinstance(item, dict):
        return dict(EMPTY_STATE)

    duration_ms = _int_value(item.get("duration_ms"))
    progress_ms = _int_value(payload.get("progress_ms"))
    artists = item.get("artists")
    album = item.get("album") if isinstance(item.get("album"), dict) else {}

    return {
        "is_playing": bool(payload.get("is_playing")),
        "track": item.get("name"),
        "artist": _artists(artists),
        "album": album.get("name"),
        "progress": _progress(progress_ms, duration_ms),
        "elapsed": _duration(progress_ms),
        "total": _duration(duration_ms),
        "art_url": _art_url(album.get("images")),
    }


def _artists(artists: Any) -> str | None:
    if not isinstance(artists, list):
        return None
    names = [artist.get("name") for artist in artists if isinstance(artist, dict) and artist.get("name")]
    return ", ".join(names) if names else None


def _art_url(images: Any) -> str | None:
    if not isinstance(images, list) or not images:
        return None
    first = images[0]
    if not isinstance(first, dict):
        return None
    url = first.get("url")
    return str(url) if url else None


def _progress(progress_ms: int, duration_ms: int) -> float:
    if duration_ms <= 0:
        return 0.0
    return round(progress_ms / duration_ms, 2)


def _duration(ms: int) -> str:
    seconds = max(0, ms) // 1000
    minutes, remainder = divmod(seconds, 60)
    return f"{minutes}:{remainder:02d}"


def _int_value(value: Any) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) else 0
