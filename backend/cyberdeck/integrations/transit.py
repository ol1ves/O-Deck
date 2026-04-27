from __future__ import annotations

import asyncio
import time
from typing import Any

import httpx
from google.transit import gtfs_realtime_pb2

from cyberdeck.config import StationConfig
from cyberdeck.integrations.base import Integration

_MTA_FEEDS_URL = "https://api-endpoint.mta.info/Feeds"
_MAX_ARRIVAL_SECONDS = 60 * 60

_FEED_LINES: dict[str, frozenset[str]] = {
    "1": frozenset({"1", "2", "3", "4", "5", "6", "7"}),
    "16": frozenset({"A", "C", "E", "H"}),
    "21": frozenset({"B", "D", "F", "M"}),
    "26": frozenset({"N", "Q", "R", "W"}),
    "31": frozenset({"L"}),
    "36": frozenset({"G"}),
    "51": frozenset({"J", "Z"}),
}


def _feeds_for_lines(lines: list[str]) -> set[str]:
    requested = {line.upper() for line in lines}
    return {feed_id for feed_id, feed_lines in _FEED_LINES.items() if requested & feed_lines}


def _parse_arrivals(feed_bytes: bytes, now: float | None = None) -> dict[str, list[dict[str, Any]]]:
    current_time = time.time() if now is None else now
    feed = gtfs_realtime_pb2.FeedMessage()
    feed.ParseFromString(feed_bytes)

    arrivals: dict[str, list[dict[str, Any]]] = {}
    for entity in feed.entity:
        if not entity.HasField("trip_update"):
            continue
        line = entity.trip_update.trip.route_id
        if not line:
            continue
        for stop_update in entity.trip_update.stop_time_update:
            arrival_time = _arrival_timestamp(stop_update)
            if arrival_time is None:
                continue
            seconds_until = arrival_time - current_time
            if seconds_until < 0 or seconds_until > _MAX_ARRIVAL_SECONDS:
                continue

            stop_id = stop_update.stop_id
            if not stop_id:
                continue
            arrivals.setdefault(stop_id, []).append(
                {
                    "line": line,
                    "mins": int(round(seconds_until / 60)),
                    "dest": "Uptown" if stop_id.endswith("N") else "Downtown",
                    "status": "on time",
                    "delay": 0,
                    "_arrival_time": arrival_time,
                }
            )

    for trains in arrivals.values():
        trains.sort(key=lambda train: train["_arrival_time"])
    return arrivals


def _parse_alerts(feed_bytes: bytes) -> list[str]:
    feed = gtfs_realtime_pb2.FeedMessage()
    feed.ParseFromString(feed_bytes)

    alerts: list[str] = []
    for entity in feed.entity:
        if not entity.HasField("alert"):
            continue
        for translation in entity.alert.header_text.translation:
            language = translation.language.lower()
            if language == "en" or language.startswith("en-"):
                alerts.append(translation.text)
                break
    return alerts


def _arrival_timestamp(stop_update: gtfs_realtime_pb2.TripUpdate.StopTimeUpdate) -> int | None:
    if stop_update.HasField("arrival") and stop_update.arrival.time:
        return stop_update.arrival.time
    if stop_update.HasField("departure") and stop_update.departure.time:
        return stop_update.departure.time
    return None


class TransitIntegration(Integration):
    name = "transit"

    def event_name(self) -> str:
        return "transit.update"

    async def fetch(self) -> dict[str, Any]:
        transit_cfg = self.config.app.transit
        stations = list(transit_cfg.primary_stations)
        secondary = list(transit_cfg.secondary_stations)
        feed_ids = _feeds_for_lines([line for station in stations + secondary for line in station.lines])

        headers = {}
        if self.config.mta_api_key:
            headers["x-api-key"] = self.config.mta_api_key

        async with httpx.AsyncClient(timeout=10.0, headers=headers) as client:
            responses = await asyncio.gather(
                *[client.get(f"{_MTA_FEEDS_URL}/{feed_id}") for feed_id in sorted(feed_ids)]
            )

        feed_payloads: list[bytes] = []
        for response in responses:
            response.raise_for_status()
            feed_payloads.append(response.content)

        arrivals_by_stop: dict[str, list[dict[str, Any]]] = {}
        alerts: list[str] = []
        for payload in feed_payloads:
            for stop_id, trains in _parse_arrivals(payload).items():
                arrivals_by_stop.setdefault(stop_id, []).extend(trains)
            if transit_cfg.show_alerts:
                alerts.extend(_parse_alerts(payload))

        return {
            "stations": [
                _station_payload(station, primary=True, arrivals_by_stop=arrivals_by_stop)
                for station in stations
            ],
            "secondary": [
                _station_payload(station, primary=False, arrivals_by_stop=arrivals_by_stop)
                for station in secondary
            ],
            "alerts": alerts[:3],
        }


def _station_payload(
    station: StationConfig,
    *,
    primary: bool,
    arrivals_by_stop: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    lines = {line.upper() for line in station.lines}
    trains = [
        train
        for stop_id, stop_trains in arrivals_by_stop.items()
        if stop_id == station.stop_id or stop_id.startswith(station.stop_id)
        for train in stop_trains
        if train["line"].upper() in lines
    ]
    trains.sort(key=lambda train: train["_arrival_time"])

    public_trains = []
    for train in trains[:4]:
        public_train = dict(train)
        public_train.pop("_arrival_time", None)
        public_trains.append(public_train)

    return {
        "name": station.station,
        "stop_id": station.stop_id,
        "lines": station.lines,
        "primary": primary,
        "trains": public_trains,
    }
