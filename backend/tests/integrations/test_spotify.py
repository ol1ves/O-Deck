from __future__ import annotations

import base64
from unittest.mock import MagicMock

import httpx
import pytest
import respx

from cyberdeck.cache import Cache
from cyberdeck.config import AppConfig, Settings, SpotifyConfig
from cyberdeck.integrations.spotify import SpotifyIntegration
from cyberdeck.ws import WSManager


TOKEN_URL = "https://accounts.spotify.com/api/token"
NOW_PLAYING_URL = "https://api.spotify.com/v1/me/player/currently-playing"

EMPTY_STATE = {
    "is_playing": False,
    "track": None,
    "artist": None,
    "album": None,
    "progress": 0.0,
    "elapsed": "0:00",
    "total": "0:00",
    "art_url": None,
}

PLAYING_FIXTURE = {
    "is_playing": True,
    "progress_ms": 125_000,
    "item": {
        "name": "Digital Love",
        "duration_ms": 301_000,
        "artists": [{"name": "Daft Punk"}, {"name": "Discovery Bot"}],
        "album": {
            "name": "Discovery",
            "images": [{"url": "https://example.test/cover.jpg"}],
        },
    },
}


def make_config(
    *,
    enabled: bool = True,
    client_id: str | None = "client-id",
    client_secret: str | None = "client-secret",
    refresh_token: str | None = "refresh-token",
) -> Settings:
    return Settings(
        spotify_client_id=client_id,
        spotify_client_secret=client_secret,
        spotify_refresh_token=refresh_token,
        app=AppConfig(spotify=SpotifyConfig(enabled=enabled)),
    )


def make_integration(config: Settings | None = None, cache=None, ws=None) -> SpotifyIntegration:
    return SpotifyIntegration(
        cache=cache or MagicMock(),
        ws_manager=ws or MagicMock(),
        config=config or make_config(),
    )


def token_response(access_token: str = "access-token") -> httpx.Response:
    return httpx.Response(200, json={"access_token": access_token, "token_type": "Bearer"})


def test_integration_event_contract():
    integration = make_integration()

    assert integration.name == "spotify"
    assert integration.event_name() == "spotify.update"


@pytest.mark.asyncio
@respx.mock
async def test_fetch_maps_currently_playing_fields():
    respx.post(TOKEN_URL).mock(return_value=token_response())
    respx.get(NOW_PLAYING_URL).mock(return_value=httpx.Response(200, json=PLAYING_FIXTURE))

    result = await make_integration().fetch()

    assert result == {
        "is_playing": True,
        "track": "Digital Love",
        "artist": "Daft Punk, Discovery Bot",
        "album": "Discovery",
        "progress": 0.42,
        "elapsed": "2:05",
        "total": "5:01",
        "art_url": "https://example.test/cover.jpg",
    }


@pytest.mark.asyncio
@respx.mock
async def test_fetch_maps_paused_track_state():
    paused_fixture = {**PLAYING_FIXTURE, "is_playing": False}
    respx.post(TOKEN_URL).mock(return_value=token_response())
    respx.get(NOW_PLAYING_URL).mock(return_value=httpx.Response(200, json=paused_fixture))

    result = await make_integration().fetch()

    assert result["is_playing"] is False
    assert result["track"] == "Digital Love"
    assert result["progress"] == 0.42


@pytest.mark.asyncio
@respx.mock
async def test_fetch_returns_empty_state_for_idle_204():
    respx.post(TOKEN_URL).mock(return_value=token_response())
    respx.get(NOW_PLAYING_URL).mock(return_value=httpx.Response(204))

    result = await make_integration().fetch()

    assert result == EMPTY_STATE


@pytest.mark.asyncio
@respx.mock
async def test_fetch_disabled_skips_token_call():
    token_route = respx.post(TOKEN_URL).mock(return_value=token_response())

    result = await make_integration(config=make_config(enabled=False)).fetch()

    assert result == EMPTY_STATE
    assert not token_route.called


@pytest.mark.asyncio
@respx.mock
@pytest.mark.parametrize(
    "missing",
    ["client_id", "client_secret", "refresh_token"],
)
async def test_fetch_missing_credentials_skip_token_call(missing):
    kwargs = {
        "client_id": "client-id",
        "client_secret": "client-secret",
        "refresh_token": "refresh-token",
    }
    kwargs[missing] = None
    token_route = respx.post(TOKEN_URL).mock(return_value=token_response())

    result = await make_integration(config=make_config(**kwargs)).fetch()

    assert result == EMPTY_STATE
    assert not token_route.called


@pytest.mark.asyncio
@respx.mock
async def test_fetch_sends_refresh_token_request_with_basic_auth_header():
    token_route = respx.post(TOKEN_URL).mock(return_value=token_response())
    respx.get(NOW_PLAYING_URL).mock(return_value=httpx.Response(204))

    await make_integration().fetch()

    request = token_route.calls[0].request
    expected_auth = base64.b64encode(b"client-id:client-secret").decode("ascii")
    assert request.headers["authorization"] == f"Basic {expected_auth}"
    assert request.headers["content-type"] == "application/x-www-form-urlencoded"
    assert request.content == b"grant_type=refresh_token&refresh_token=refresh-token"


@pytest.mark.asyncio
@respx.mock
async def test_fetch_requests_now_playing_with_bearer_token():
    respx.post(TOKEN_URL).mock(return_value=token_response("fresh-token"))
    now_playing_route = respx.get(NOW_PLAYING_URL).mock(return_value=httpx.Response(204))

    await make_integration().fetch()

    assert now_playing_route.calls[0].request.headers["authorization"] == "Bearer fresh-token"


@pytest.mark.asyncio
@respx.mock
async def test_run_swallows_http_error_and_increments_error_count(tmp_path):
    respx.post(TOKEN_URL).mock(return_value=httpx.Response(503))

    integration = make_integration(cache=Cache(db_path=tmp_path / "c.db"), ws=WSManager())
    await integration.run()

    assert integration.status["error_count"] == 1


@pytest.mark.asyncio
@respx.mock
@pytest.mark.parametrize("status_code", [401, 500])
async def test_run_treats_empty_now_playing_error_response_as_error(tmp_path, status_code):
    respx.post(TOKEN_URL).mock(return_value=token_response())
    respx.get(NOW_PLAYING_URL).mock(return_value=httpx.Response(status_code))

    integration = make_integration(cache=Cache(db_path=tmp_path / "c.db"), ws=WSManager())
    await integration.run()

    assert integration.status["error_count"] == 1
