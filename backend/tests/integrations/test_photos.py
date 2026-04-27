from unittest.mock import MagicMock, patch

import httpx
import pytest
import respx

from cyberdeck.integrations.photos import (
    PhotosIntegration,
    _list_local_photos,
    _parse_share_token,
)


def _make_config(source="local", local_folder=None, icloud_url="", rotation=30):
    cfg = MagicMock()
    cfg.app.photos.source = source
    cfg.app.photos.local_folder = str(local_folder or "~/cyberdeck-photos")
    cfg.app.photos.icloud_share_url = icloud_url
    cfg.app.photos.rotation_seconds = rotation
    return cfg


def _make_integration(config=None):
    return PhotosIntegration(
        cache=MagicMock(),
        ws_manager=MagicMock(),
        config=config or _make_config(),
    )


def test_parse_share_token_extracts_fragment():
    url = "https://www.icloud.com/sharedalbum/#B0TGPfq4JFwQAVq"
    assert _parse_share_token(url) == "B0TGPfq4JFwQAVq"


def test_parse_share_token_returns_none_for_invalid():
    assert _parse_share_token("https://example.com") is None


def test_list_local_photos_finds_image_files(tmp_path):
    (tmp_path / "a.jpg").write_bytes(b"")
    (tmp_path / "b.png").write_bytes(b"")
    (tmp_path / "c.txt").write_bytes(b"")

    found = _list_local_photos(str(tmp_path))

    assert len(found) == 2
    assert all(path.endswith((".jpg", ".png")) for path in found)


def test_list_local_photos_returns_empty_for_missing_folder():
    assert _list_local_photos("/nonexistent/path/xyz") == []


@pytest.mark.asyncio
async def test_fetch_local_returns_first_photo(tmp_path):
    (tmp_path / "img1.jpg").write_bytes(b"")
    (tmp_path / "img2.jpg").write_bytes(b"")

    result = await _make_integration(
        _make_config(source="local", local_folder=str(tmp_path))
    ).fetch()

    assert result["source"] == "local"
    assert result["total"] == 2
    assert result["index"] == 0
    assert "/api/photos/file/" in result["url"]


@pytest.mark.asyncio
async def test_fetch_local_advances_index(tmp_path):
    (tmp_path / "img1.jpg").write_bytes(b"")
    (tmp_path / "img2.jpg").write_bytes(b"")
    integration = _make_integration(_make_config(source="local", local_folder=str(tmp_path)))

    await integration.fetch()
    result = await integration.fetch()

    assert result["index"] == 1


@pytest.mark.asyncio
async def test_fetch_local_wraps_index(tmp_path):
    (tmp_path / "img1.jpg").write_bytes(b"")
    integration = _make_integration(_make_config(source="local", local_folder=str(tmp_path)))

    await integration.fetch()
    result = await integration.fetch()

    assert result["index"] == 0


@pytest.mark.asyncio
async def test_fetch_local_returns_empty_when_no_files(tmp_path):
    result = await _make_integration(
        _make_config(source="local", local_folder=str(tmp_path))
    ).fetch()

    assert result["total"] == 0
    assert result["url"] is None


@pytest.mark.asyncio
@respx.mock
async def test_fetch_icloud_returns_cdn_url():
    token = "B0TGPfq4JFwQAVq"
    webstream_resp = {
        "photos": [
            {
                "photoGuid": "guid-1",
                "derivatives": {
                    "3": {"checksum": "cksum1", "width": 3024, "height": 4032},
                },
            }
        ]
    }
    webasset_resp = {
        "items": {
            "cksum1": {"url_expiry": "2099-01-01", "url": "https://cdn.icloud.com/img1.jpg"}
        }
    }
    for partition in range(37, 42):
        respx.post(
            f"https://p{partition}-sharedstreams.icloud.com/{token}/sharedstreams/webstream"
        ).mock(return_value=httpx.Response(200, json=webstream_resp))
        respx.post(
            f"https://p{partition}-sharedstreams.icloud.com/{token}/sharedstreams/webasseturls"
        ).mock(return_value=httpx.Response(200, json=webasset_resp))

    result = await _make_integration(
        _make_config(
            source="icloud_shared_album",
            icloud_url=f"https://www.icloud.com/sharedalbum/#{token}",
        )
    ).fetch()

    assert result["source"] == "icloud_shared_album"
    assert result["url"] == "https://cdn.icloud.com/img1.jpg"


@pytest.mark.asyncio
async def test_run_swallows_error():
    with patch.object(PhotosIntegration, "fetch", side_effect=Exception("oops")):
        integration = _make_integration()
        await integration.run()

    assert integration.status["error_count"] == 1
