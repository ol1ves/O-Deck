from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient


def test_api_state_includes_all_integrations_and_pomodoro():
    from cyberdeck import main as m

    for key, value in {
        "weather": {"tempF": 58},
        "transit": {"stations": []},
        "spotify": {"is_playing": False},
        "github": {"commits": []},
        "rss": {"items": []},
        "photos": {"url": None},
        "calendar": {"events": []},
    }.items():
        m.cache.set(key, value)

    resp = TestClient(m.app).get("/api/state")

    assert resp.status_code == 200
    data = resp.json()
    for key in ["weather", "transit", "spotify", "github", "rss", "photos", "calendar"]:
        assert key in data
    assert data["pomodoro"]["phase"] == "idle"


def test_api_status_includes_device_info_and_last_error():
    from cyberdeck import main as m

    resp = TestClient(m.app).get("/api/status")

    assert resp.status_code == 200
    body = resp.json()

    assert "device" in body
    device = body["device"]
    assert device["callsign"] == m.settings.app.device.callsign
    assert device["hostname"]
    assert device["lan_ip"]
    assert isinstance(device["uptime_seconds"], (int, float))
    assert device["uptime_seconds"] >= 0

    assert isinstance(body["integrations"], list)
    for entry in body["integrations"]:
        assert "last_error" in entry


def test_api_config_includes_pomodoro_presets():
    from cyberdeck import main as m

    resp = TestClient(m.app).get("/api/config")

    assert resp.status_code == 200
    assert resp.json()["pomodoro"]["presets"][0]["name"] == "Classic"


def test_api_pomodoro_status_returns_idle():
    from cyberdeck import main as m

    resp = TestClient(m.app).get("/api/pomodoro/status")

    assert resp.status_code == 200
    assert resp.json()["phase"] == "idle"


def test_api_photos_file_serves_local_photo(tmp_path):
    from cyberdeck import main as m

    photo = tmp_path / "desk.jpg"
    photo.write_bytes(b"image-bytes")
    m.settings.app.photos.local_folder = str(tmp_path)

    resp = TestClient(m.app).get("/api/photos/file/desk.jpg")

    assert resp.status_code == 200
    assert resp.content == b"image-bytes"


@pytest.mark.asyncio
async def test_lifespan_registers_all_integrations(monkeypatch, tmp_path):
    from cyberdeck import main as m
    from cyberdeck.cache import Cache
    from cyberdeck.scheduler import IntegrationScheduler

    monkeypatch.setattr(m, "cache", Cache(db_path=tmp_path / "cache.db"))
    monkeypatch.setattr(m, "scheduler", IntegrationScheduler())
    monkeypatch.setattr(m.scheduler, "start", AsyncMock())
    monkeypatch.setattr(m.scheduler, "shutdown", MagicMock())

    async with m.lifespan(m.app):
        names = {integration.name for integration in m.scheduler._integrations}

    assert names == {
        "weather",
        "transit",
        "spotify",
        "github",
        "rss",
        "photos",
        "calendar",
    }
