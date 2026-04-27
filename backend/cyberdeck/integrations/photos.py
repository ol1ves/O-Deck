from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import httpx

from cyberdeck.integrations.base import Integration

_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".JPG", ".JPEG", ".PNG", ".WEBP"}
_ICLOUD_PARTITIONS = range(37, 42)


def _parse_share_token(url: str) -> str | None:
    if "#" not in url:
        return None
    token = url.split("#", 1)[1].strip()
    return token or None


def _list_local_photos(folder_str: str) -> list[str]:
    folder = Path(folder_str).expanduser()
    if not folder.exists():
        return []
    return sorted(str(path) for path in folder.iterdir() if path.suffix in _IMAGE_SUFFIXES)


class PhotosIntegration(Integration):
    name = "photos"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._index = 0
        self._photo_list: list[str] = []
        self._last_list_refresh = 0.0
        self._is_first_fetch = True

    def event_name(self) -> str:
        return "photos.update"

    async def fetch(self) -> dict[str, Any]:
        cfg = self.config.app.photos
        now = time.time()
        list_stale = (now - self._last_list_refresh) > 300

        if list_stale or self._is_first_fetch:
            if cfg.source == "icloud_shared_album":
                self._photo_list = await self._fetch_icloud_urls(cfg.icloud_share_url)
            else:
                self._photo_list = _list_local_photos(cfg.local_folder)
            self._last_list_refresh = now
            if self._is_first_fetch:
                self._is_first_fetch = False
            else:
                self._index = (self._index + 1) % max(len(self._photo_list), 1)
        else:
            self._index = (self._index + 1) % max(len(self._photo_list), 1)

        if not self._photo_list:
            return {
                "source": cfg.source,
                "url": None,
                "index": 0,
                "total": 0,
                "rotation_seconds": cfg.rotation_seconds,
            }

        current = self._photo_list[self._index % len(self._photo_list)]
        url = (
            f"/api/photos/file/{Path(current).name}"
            if cfg.source == "local"
            else current
        )

        return {
            "source": cfg.source,
            "url": url,
            "index": self._index,
            "total": len(self._photo_list),
            "rotation_seconds": cfg.rotation_seconds,
        }

    async def _fetch_icloud_urls(self, share_url: str) -> list[str]:
        token = _parse_share_token(share_url)
        if not token:
            return []

        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            webstream_data: dict[str, Any] | None = None
            for partition in _ICLOUD_PARTITIONS:
                try:
                    resp = await client.post(
                        f"https://p{partition}-sharedstreams.icloud.com/{token}/sharedstreams/webstream",
                        json={"streamCtag": None},
                    )
                    if resp.status_code == 200:
                        webstream_data = resp.json()
                        break
                except httpx.RequestError:
                    continue

            if not webstream_data:
                return []

            photos = webstream_data.get("photos", [])
            checksums: list[str] = []
            for photo in photos:
                derivatives = photo.get("derivatives", {})
                best = max(
                    derivatives.values(),
                    key=lambda derivative: derivative.get("width", 0),
                    default=None,
                )
                if best:
                    checksums.append(best["checksum"])

            if not checksums:
                return []

            for partition in _ICLOUD_PARTITIONS:
                try:
                    resp = await client.post(
                        f"https://p{partition}-sharedstreams.icloud.com/{token}/sharedstreams/webasseturls",
                        json={"photoGuids": [photo["photoGuid"] for photo in photos]},
                    )
                    if resp.status_code == 200:
                        items = resp.json().get("items", {})
                        return [items[checksum]["url"] for checksum in checksums if checksum in items]
                except httpx.RequestError:
                    continue

        return []
