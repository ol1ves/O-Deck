from __future__ import annotations

import time
from unittest.mock import MagicMock

import httpx
import pytest
import respx
from google.transit import gtfs_realtime_pb2

from cyberdeck.cache import Cache
from cyberdeck.config import AppConfig, Settings, StationConfig, TransitConfig
from cyberdeck.integrations.transit import TransitIntegration, _feeds_for_lines, _parse_arrivals
from cyberdeck.ws import WSManager


MTA_FEEDS_URL = "https://api-endpoint.mta.info/Feeds"


def make_stop(
    feed: gtfs_realtime_pb2.FeedMessage,
    *,
    route_id: str,
    stop_id: str,
    arrival_time: int | None = None,
    departure_time: int | None = None,
) -> None:
    entity = feed.entity.add()
    entity.id = f"{route_id}-{stop_id}-{arrival_time or departure_time}"
    entity.trip_update.trip.route_id = route_id
    stop = entity.trip_update.stop_time_update.add()
    stop.stop_id = stop_id
    if arrival_time is not None:
        stop.arrival.time = arrival_time
    if departure_time is not None:
        stop.departure.time = departure_time


def make_alert(feed: gtfs_realtime_pb2.FeedMessage, text: str, language: str = "en") -> None:
    entity = feed.entity.add()
    entity.id = f"alert-{text}"
    translation = entity.alert.header_text.translation.add()
    translation.text = text
    translation.language = language


def feed_bytes(*, stops: list[dict] | None = None, alerts: list[tuple[str, str]] | None = None) -> bytes:
    feed = gtfs_realtime_pb2.FeedMessage()
    feed.header.gtfs_realtime_version = "2.0"
    for stop in stops or []:
        make_stop(feed, **stop)
    for text, language in alerts or []:
        make_alert(feed, text, language)
    return feed.SerializeToString()


def make_config(
    *,
    api_key: str | None = None,
    primary: list[StationConfig] | None = None,
    secondary: list[StationConfig] | None = None,
) -> Settings:
    return Settings(
        mta_api_key=api_key,
        app=AppConfig(
            transit=TransitConfig(
                primary_stations=primary
                or [StationConfig(station="Hoyt-Schermerhorn", stop_id="A42", lines=["A", "C"])],
                secondary_stations=secondary
                or [StationConfig(station="DeKalb Av", stop_id="R30", lines=["B", "Q", "R"])],
            )
        ),
    )


def make_integration(config: Settings | None = None, cache=None, ws=None) -> TransitIntegration:
    return TransitIntegration(
        cache=cache or MagicMock(),
        ws_manager=ws or MagicMock(),
        config=config or make_config(),
    )


def test_feeds_for_lines_maps_known_lines_and_ignores_unknown_lines():
    assert _feeds_for_lines(["A", "C", "Q", "7", "X"]) == {"16", "26", "1"}


def test_parse_arrivals_sorts_by_arrival_and_infers_direction():
    now = 1_000
    parsed = _parse_arrivals(
        feed_bytes(
            stops=[
                {"route_id": "A", "stop_id": "A42S", "arrival_time": now + 600},
                {"route_id": "C", "stop_id": "A42N", "arrival_time": now + 120},
            ]
        ),
        now=now,
    )

    assert parsed["A42N"][0]["line"] == "C"
    assert parsed["A42N"][0]["mins"] == 2
    assert parsed["A42N"][0]["dest"] == "Uptown"
    assert parsed["A42S"][0]["dest"] == "Downtown"


def test_parse_arrivals_uses_departure_time_and_excludes_past_and_far_future_trains():
    now = 1_000
    parsed = _parse_arrivals(
        feed_bytes(
            stops=[
                {"route_id": "A", "stop_id": "A42N", "departure_time": now + 180},
                {"route_id": "A", "stop_id": "A42N", "arrival_time": now - 60},
                {"route_id": "A", "stop_id": "A42N", "arrival_time": now + 3_660},
            ]
        ),
        now=now,
    )

    assert [train["mins"] for train in parsed["A42N"]] == [3]


@pytest.mark.asyncio
@respx.mock
async def test_fetch_returns_sorted_station_trains_filtered_to_configured_lines():
    now = int(time.time())
    respx.get(f"{MTA_FEEDS_URL}/16").mock(
        return_value=httpx.Response(
            200,
            content=feed_bytes(
                stops=[
                    {"route_id": "A", "stop_id": "A42N", "arrival_time": now + 600},
                    {"route_id": "C", "stop_id": "A42S", "arrival_time": now + 120},
                    {"route_id": "E", "stop_id": "A42N", "arrival_time": now + 60},
                    {"route_id": "A", "stop_id": "A42N", "arrival_time": now + 240},
                    {"route_id": "C", "stop_id": "A42N", "arrival_time": now + 300},
                    {"route_id": "A", "stop_id": "A42N", "arrival_time": now + 360},
                    {"route_id": "C", "stop_id": "A42N", "arrival_time": now + 420},
                ]
            ),
        )
    )
    respx.get(f"{MTA_FEEDS_URL}/21").mock(return_value=httpx.Response(200, content=feed_bytes()))
    respx.get(f"{MTA_FEEDS_URL}/26").mock(return_value=httpx.Response(200, content=feed_bytes()))

    result = await make_integration().fetch()

    primary = result["stations"][0]
    assert primary == {
        "name": "Hoyt-Schermerhorn",
        "stop_id": "A42",
        "lines": ["A", "C"],
        "primary": True,
        "trains": [
            {"line": "C", "mins": 2, "dest": "Downtown", "status": "on time", "delay": 0},
            {"line": "A", "mins": 4, "dest": "Uptown", "status": "on time", "delay": 0},
            {"line": "C", "mins": 5, "dest": "Uptown", "status": "on time", "delay": 0},
            {"line": "A", "mins": 6, "dest": "Uptown", "status": "on time", "delay": 0},
        ],
    }
    assert all(train["line"] in {"A", "C"} for train in primary["trains"])
    assert all("_arrival_time" not in train for train in primary["trains"])


@pytest.mark.asyncio
@respx.mock
async def test_fetch_includes_secondary_stations_api_key_header_and_english_alerts():
    now = int(time.time())
    route_16 = respx.get(f"{MTA_FEEDS_URL}/16").mock(
        return_value=httpx.Response(
            200,
            content=feed_bytes(
                stops=[{"route_id": "A", "stop_id": "A42N", "arrival_time": now + 120}],
                alerts=[
                    ("Signal delays on A line", "en"),
                    ("Retards sur la ligne A", "fr"),
                    ("Boarding change", "en-US"),
                    ("Extra alert", "en"),
                    ("Fourth alert", "en"),
                ],
            ),
        )
    )
    route_21 = respx.get(f"{MTA_FEEDS_URL}/21").mock(return_value=httpx.Response(200, content=feed_bytes()))
    route_26 = respx.get(f"{MTA_FEEDS_URL}/26").mock(return_value=httpx.Response(200, content=feed_bytes()))

    result = await make_integration(config=make_config(api_key="secret-key")).fetch()

    assert route_16.calls[0].request.headers["x-api-key"] == "secret-key"
    assert route_21.called
    assert route_26.called
    assert result["secondary"][0]["name"] == "DeKalb Av"
    assert result["secondary"][0]["primary"] is False
    assert result["alerts"] == ["Signal delays on A line", "Boarding change", "Extra alert"]


@pytest.mark.asyncio
@respx.mock
async def test_run_swallows_http_error_and_increments_error_count(tmp_path):
    respx.get(f"{MTA_FEEDS_URL}/16").mock(return_value=httpx.Response(503))
    respx.get(f"{MTA_FEEDS_URL}/21").mock(return_value=httpx.Response(200, content=feed_bytes()))
    respx.get(f"{MTA_FEEDS_URL}/26").mock(return_value=httpx.Response(200, content=feed_bytes()))

    integration = make_integration(cache=Cache(db_path=tmp_path / "c.db"), ws=WSManager())
    await integration.run()

    assert integration.status["error_count"] == 1
