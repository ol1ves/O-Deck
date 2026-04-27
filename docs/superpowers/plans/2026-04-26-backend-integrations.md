# Backend Integrations Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement all six data integrations (transit, calendar, spotify, github, rss, photos) plus backend Pomodoro state, wiring them into the FastAPI app so every integration polls, caches, and broadcasts typed WebSocket events.

**Architecture:** Each integration extends the `Integration` ABC from Plan 1. They are registered in `main.py`'s lifespan with their polling intervals. A separate `PomodoroState` class manages timer state and exposes REST endpoints; it is not an `Integration` subclass because it is event-driven, not polled. The `/api/state` endpoint is extended to include all integration payloads.

**Tech Stack:** Python 3.11+, FastAPI, httpx + respx (tests), gtfs-realtime-bindings, google-auth, notion-client, feedparser, MagicMock/patch (unit tests), pytest-asyncio

**Dependency:** Plan 1 (Backend Foundation) must be complete. Work in the `feature/backend-integrations` branch, branched from `feature/backend-foundation`.

---

## Plan Series

1. Backend Foundation ✅ done
2. **Backend Integrations** ← you are here
3. Frontend Foundation → `2026-04-26-frontend-foundation.md`
4. Fullscreen Apps → `2026-04-26-fullscreen-apps.md`
5. Install & Ops → `2026-04-26-install-ops.md`

---

## File Map

```
backend/cyberdeck/
├── main.py                          # MODIFY: register all integrations + add /api/pomodoro + /api/photos/file
├── config.py                        # MODIFY: add mta_api_key field to Settings
├── pomodoro.py                      # CREATE: PomodoroState + REST router
└── integrations/
    ├── transit.py                   # CREATE
    ├── calendar.py                  # CREATE (Google + Notion join)
    ├── spotify.py                   # CREATE
    ├── github.py                    # CREATE
    ├── rss.py                       # CREATE
    └── photos.py                    # CREATE (local + iCloud)

backend/tests/
├── test_pomodoro.py                 # CREATE
└── integrations/
    ├── test_transit.py              # CREATE
    ├── test_calendar.py             # CREATE
    ├── test_spotify.py              # CREATE
    ├── test_github.py               # CREATE
    ├── test_rss.py                  # CREATE
    └── test_photos.py               # CREATE
```

---

## Setup

Before starting, create and enter the worktree:

```bash
cd ~/cyberdeck
git worktree add .worktrees/backend-integrations feature/backend-integrations 2>/dev/null \
  || git worktree add .worktrees/backend-integrations -b feature/backend-integrations feature/backend-foundation
cd .worktrees/backend-integrations
source .venv/bin/activate  # or: uv venv && uv pip install -e ".[dev]"
```

Run baseline tests to confirm clean state:

```bash
pytest backend/tests/ -v
```

Expected: all tests pass.

---

## Task 1: Config — add mta_api_key + transit helpers

**Files:**
- Modify: `backend/cyberdeck/config.py` — add `mta_api_key` to `Settings`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_config.py  (add to existing file)
def test_settings_accepts_mta_api_key(monkeypatch):
    monkeypatch.setenv("MTA_API_KEY", "test-key")
    from cyberdeck.config import load_config
    # reload after monkeypatch
    import importlib, cyberdeck.config
    importlib.reload(cyberdeck.config)
    from cyberdeck.config import Settings
    s = Settings()
    assert s.mta_api_key == "test-key"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest backend/tests/test_config.py::test_settings_accepts_mta_api_key -v
```

Expected: `AttributeError: 'Settings' object has no attribute 'mta_api_key'`

- [ ] **Step 3: Add `mta_api_key` field to `Settings` in `config.py`**

Add after `github_token` field:

```python
mta_api_key: str | None = None
```

Also add `MTA_API_KEY=` to `.env.example`:

```bash
echo "MTA_API_KEY=" >> .env.example
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest backend/tests/test_config.py -v
```

Expected: all config tests pass.

- [ ] **Step 5: Commit**

```bash
git add backend/cyberdeck/config.py .env.example backend/tests/test_config.py
git commit -m "feat(config): add optional mta_api_key field"
```

---

## Task 2: Transit Integration

**Files:**
- Create: `backend/cyberdeck/integrations/transit.py`
- Create: `backend/tests/integrations/test_transit.py`

The MTA GTFS-RT feeds are protobuf-encoded binary payloads. Each feed covers specific subway lines:

| Feed ID | Lines |
|---------|-------|
| 1 | 1 2 3 4 5 6 7 |
| 16 | A C E H |
| 21 | B D F M |
| 26 | N Q R W |
| 31 | L |
| 36 | G |
| 51 | J Z |

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/integrations/test_transit.py
import time
from unittest.mock import MagicMock, patch

import httpx
import pytest
import respx
from google.transit import gtfs_realtime_pb2

from cyberdeck.cache import Cache
from cyberdeck.integrations.transit import TransitIntegration, _feeds_for_lines, _parse_arrivals
from cyberdeck.ws import WSManager


def _build_feed(
    entities: list[dict],
    now: float = 1_714_000_000.0,
) -> bytes:
    """Build a minimal GTFS-RT protobuf binary from simplified dicts.

    Each dict may contain:
      route_id, trip_id, stops=[{stop_id, arrival_offset_s}]
      OR alert_text, route_id (for service alerts)
    """
    feed = gtfs_realtime_pb2.FeedMessage()
    feed.header.gtfs_realtime_version = "2.0"
    feed.header.timestamp = int(now)

    for i, e in enumerate(entities):
        entity = feed.entity.add()
        entity.id = str(i + 1)

        if "route_id" in e and "stops" in e:
            tu = entity.trip_update
            tu.trip.route_id = e["route_id"]
            tu.trip.trip_id = e.get("trip_id", f"trip-{i}")
            for stop in e["stops"]:
                stu = tu.stop_time_update.add()
                stu.stop_id = stop["stop_id"]
                stu.arrival.time = int(now) + stop["arrival_offset_s"]

        elif "alert_text" in e:
            alert = entity.alert
            t = alert.header_text.translation.add()
            t.text = e["alert_text"]
            t.language = "en"

    return feed.SerializeToString()


def _make_config(primary=None, secondary=None):
    cfg = MagicMock()
    cfg.mta_api_key = None
    stations = primary or [
        MagicMock(station="Jay St", stop_id="A41N", lines=["A", "C"]),
    ]
    sec_stations = secondary or []
    cfg.app.transit.primary_stations = stations
    cfg.app.transit.secondary_stations = sec_stations
    cfg.app.transit.show_alerts = True
    return cfg


def _make_integration(config=None):
    cfg = config or _make_config()
    return TransitIntegration(
        cache=MagicMock(),
        ws_manager=MagicMock(),
        config=cfg,
    )


# -- unit tests ----------------------------------------------------------------

def test_feeds_for_lines_ace():
    assert _feeds_for_lines(["A", "C", "E"]) == {16}


def test_feeds_for_lines_mixed():
    assert _feeds_for_lines(["A", "F", "Q"]) == {16, 21, 26}


def test_feeds_for_lines_unknown_line_ignored():
    assert _feeds_for_lines(["X"]) == set()


def test_parse_arrivals_returns_sorted_by_time():
    now = 1_714_000_000.0
    feed_bytes = _build_feed(
        [
            {"route_id": "C", "stops": [{"stop_id": "A41N", "arrival_offset_s": 360}]},
            {"route_id": "A", "stops": [{"stop_id": "A41N", "arrival_offset_s": 120}]},
        ],
        now=now,
    )
    arrivals = _parse_arrivals(feed_bytes, now=now)
    assert arrivals["A41N"][0]["line"] == "A"
    assert arrivals["A41N"][0]["mins"] == 2
    assert arrivals["A41N"][1]["line"] == "C"
    assert arrivals["A41N"][1]["mins"] == 6


def test_parse_arrivals_excludes_past_trains():
    now = 1_714_000_000.0
    feed_bytes = _build_feed(
        [{"route_id": "A", "stops": [{"stop_id": "A41N", "arrival_offset_s": -60}]}],
        now=now,
    )
    arrivals = _parse_arrivals(feed_bytes, now=now)
    assert arrivals.get("A41N", []) == []


def test_parse_arrivals_excludes_far_future_trains():
    now = 1_714_000_000.0
    feed_bytes = _build_feed(
        [{"route_id": "A", "stops": [{"stop_id": "A41N", "arrival_offset_s": 4000}]}],
        now=now,
    )
    arrivals = _parse_arrivals(feed_bytes, now=now)
    assert arrivals.get("A41N", []) == []


def test_parse_arrivals_infers_direction_from_stop_id():
    now = 1_714_000_000.0
    feed_bytes_n = _build_feed(
        [{"route_id": "A", "stops": [{"stop_id": "A41N", "arrival_offset_s": 120}]}],
        now=now,
    )
    feed_bytes_s = _build_feed(
        [{"route_id": "A", "stops": [{"stop_id": "A41S", "arrival_offset_s": 120}]}],
        now=now,
    )
    assert _parse_arrivals(feed_bytes_n, now=now)["A41N"][0]["dest"] == "Uptown"
    assert _parse_arrivals(feed_bytes_s, now=now)["A41S"][0]["dest"] == "Downtown"


# -- integration tests (mocked HTTP) ------------------------------------------

MTA_BASE = "https://api-endpoint.mta.info/Feeds"


@pytest.mark.asyncio
@respx.mock
async def test_fetch_returns_station_with_sorted_trains(tmp_path):
    now = 1_714_000_000.0
    feed_bytes = _build_feed(
        [
            {"route_id": "C", "stops": [{"stop_id": "A41N", "arrival_offset_s": 360}]},
            {"route_id": "A", "stops": [{"stop_id": "A41N", "arrival_offset_s": 120}]},
        ],
        now=now,
    )
    respx.get(f"{MTA_BASE}/16").mock(return_value=httpx.Response(200, content=feed_bytes))

    with patch("cyberdeck.integrations.transit.time") as t:
        t.time.return_value = now
        result = await _make_integration().fetch()

    assert result["stations"][0]["name"] == "Jay St"
    trains = result["stations"][0]["trains"]
    assert trains[0]["line"] == "A"
    assert trains[0]["mins"] == 2
    assert trains[1]["line"] == "C"
    assert trains[1]["mins"] == 6


@pytest.mark.asyncio
@respx.mock
async def test_fetch_filters_to_configured_lines(tmp_path):
    now = 1_714_000_000.0
    feed_bytes = _build_feed(
        [
            # B is NOT in configured lines ["A", "C"]
            {"route_id": "B", "stops": [{"stop_id": "A41N", "arrival_offset_s": 60}]},
            {"route_id": "A", "stops": [{"stop_id": "A41N", "arrival_offset_s": 120}]},
        ],
        now=now,
    )
    respx.get(f"{MTA_BASE}/16").mock(return_value=httpx.Response(200, content=feed_bytes))
    respx.get(f"{MTA_BASE}/21").mock(return_value=httpx.Response(200, content=feed_bytes))

    with patch("cyberdeck.integrations.transit.time") as t:
        t.time.return_value = now
        result = await _make_integration().fetch()

    lines = [tr["line"] for tr in result["stations"][0]["trains"]]
    assert "B" not in lines


@pytest.mark.asyncio
@respx.mock
async def test_fetch_includes_alerts(tmp_path):
    now = 1_714_000_000.0
    feed_bytes = _build_feed(
        [{"alert_text": "F: signal delays at Bergen St"}],
        now=now,
    )
    respx.get(f"{MTA_BASE}/16").mock(return_value=httpx.Response(200, content=feed_bytes))

    with patch("cyberdeck.integrations.transit.time") as t:
        t.time.return_value = now
        result = await _make_integration().fetch()

    assert result["alerts"] == ["F: signal delays at Bergen St"]


@pytest.mark.asyncio
@respx.mock
async def test_run_swallows_http_error():
    respx.get(f"{MTA_BASE}/16").mock(return_value=httpx.Response(503))
    integration = _make_integration()
    await integration.run()
    assert integration.status["error_count"] == 1
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest backend/tests/integrations/test_transit.py -v
```

Expected: `ModuleNotFoundError: No module named 'cyberdeck.integrations.transit'`

- [ ] **Step 3: Implement `transit.py`**

```python
# backend/cyberdeck/integrations/transit.py
from __future__ import annotations

import time
from typing import Any

import httpx
from google.transit import gtfs_realtime_pb2

from cyberdeck.integrations.base import Integration

_MTA_BASE = "https://api-endpoint.mta.info/Feeds"

_LINE_TO_FEED: dict[str, int] = {
    **{line: 1 for line in "1234567"},
    **{line: 16 for line in ["A", "C", "E", "H"]},
    **{line: 21 for line in ["B", "D", "F", "M"]},
    **{line: 26 for line in ["N", "Q", "R", "W"]},
    "L": 31,
    "G": 36,
    **{line: 51 for line in ["J", "Z"]},
}


def _feeds_for_lines(lines: list[str]) -> set[int]:
    return {_LINE_TO_FEED[ln] for ln in lines if ln in _LINE_TO_FEED}


def _parse_arrivals(
    feed_bytes: bytes,
    now: float | None = None,
) -> dict[str, list[dict[str, Any]]]:
    """Parse GTFS-RT protobuf bytes → {stop_id: [arrival_dict, ...]}."""
    if now is None:
        now = time.time()

    feed = gtfs_realtime_pb2.FeedMessage()
    feed.ParseFromString(feed_bytes)

    arrivals: dict[str, list[dict[str, Any]]] = {}

    for entity in feed.entity:
        if not entity.HasField("trip_update"):
            continue
        tu = entity.trip_update
        route_id = tu.trip.route_id

        for stu in tu.stop_time_update:
            arrival_time: float | None = None
            if stu.HasField("arrival") and stu.arrival.time > 0:
                arrival_time = float(stu.arrival.time)
            elif stu.HasField("departure") and stu.departure.time > 0:
                arrival_time = float(stu.departure.time)

            if arrival_time is None:
                continue

            mins = round((arrival_time - now) / 60)
            if mins < 0 or mins > 60:
                continue

            stop_id = stu.stop_id
            dest = "Uptown" if stop_id.endswith("N") else "Downtown"

            arrivals.setdefault(stop_id, []).append(
                {
                    "line": route_id,
                    "mins": mins,
                    "_arrival_time": arrival_time,
                    "dest": dest,
                    "status": "on time",
                    "delay": 0,
                }
            )

    return arrivals


def _parse_alerts(feed_bytes: bytes) -> list[str]:
    feed = gtfs_realtime_pb2.FeedMessage()
    feed.ParseFromString(feed_bytes)
    texts: list[str] = []
    for entity in feed.entity:
        if not entity.HasField("alert"):
            continue
        for tr in entity.alert.header_text.translation:
            if tr.language in ("", "en"):
                texts.append(tr.text)
                break
    return texts


class TransitIntegration(Integration):
    name = "transit"

    def event_name(self) -> str:
        return "transit.update"

    async def fetch(self) -> dict[str, Any]:
        cfg = self.config.app.transit
        now = time.time()

        all_stations = [*cfg.primary_stations, *cfg.secondary_stations]
        all_lines: set[str] = set()
        for stn in all_stations:
            all_lines.update(stn.lines)

        feed_ids = _feeds_for_lines(list(all_lines))

        headers: dict[str, str] = {}
        if self.config.mta_api_key:
            headers["x-api-key"] = self.config.mta_api_key

        arrivals: dict[str, list[dict[str, Any]]] = {}
        alerts: list[str] = []

        async with httpx.AsyncClient(timeout=15.0) as client:
            for feed_id in sorted(feed_ids):
                resp = await client.get(f"{_MTA_BASE}/{feed_id}", headers=headers)
                resp.raise_for_status()
                parsed = _parse_arrivals(resp.content, now=now)
                for stop_id, trains in parsed.items():
                    arrivals.setdefault(stop_id, []).extend(trains)
                alerts.extend(_parse_alerts(resp.content))

        def _build_station(stn_cfg, primary: bool) -> dict[str, Any]:
            trains = arrivals.get(stn_cfg.stop_id, [])
            trains = [t for t in trains if t["line"] in stn_cfg.lines]
            trains.sort(key=lambda x: x["_arrival_time"])
            clean = [{k: v for k, v in t.items() if k != "_arrival_time"} for t in trains[:4]]
            return {
                "name": stn_cfg.station,
                "stop_id": stn_cfg.stop_id,
                "lines": stn_cfg.lines,
                "primary": primary,
                "trains": clean,
            }

        return {
            "stations": [_build_station(s, True) for s in cfg.primary_stations],
            "secondary": [_build_station(s, False) for s in cfg.secondary_stations],
            "alerts": alerts[:3],
        }
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest backend/tests/integrations/test_transit.py -v
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add backend/cyberdeck/integrations/transit.py backend/tests/integrations/test_transit.py
git commit -m "feat(transit): GTFS-RT integration with 4-station support and alerts"
```

---

## Task 3: Spotify Integration

**Files:**
- Create: `backend/cyberdeck/integrations/spotify.py`
- Create: `backend/tests/integrations/test_spotify.py`

Uses httpx directly (no spotipy dependency) with OAuth2 refresh-token flow.

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/integrations/test_spotify.py
import base64
from unittest.mock import MagicMock

import httpx
import pytest
import respx

from cyberdeck.integrations.spotify import SpotifyIntegration

TOKEN_URL = "https://accounts.spotify.com/api/token"
NOW_PLAYING_URL = "https://api.spotify.com/v1/me/player/currently-playing"

PLAYING_FIXTURE = {
    "is_playing": True,
    "progress_ms": 114000,
    "item": {
        "name": "Pyramid Song",
        "duration_ms": 290000,
        "artists": [{"name": "Radiohead"}],
        "album": {
            "name": "Amnesiac",
            "images": [{"url": "https://i.scdn.co/image/abc123", "width": 640}],
        },
    },
}

PAUSED_FIXTURE = {**PLAYING_FIXTURE, "is_playing": False}

TOKEN_FIXTURE = {"access_token": "new-access-token", "expires_in": 3600}


def _make_config(enabled=True, client_id="cid", client_secret="csec", refresh_token="rtok"):
    cfg = MagicMock()
    cfg.app.spotify.enabled = enabled
    cfg.spotify_client_id = client_id
    cfg.spotify_client_secret = client_secret
    cfg.spotify_refresh_token = refresh_token
    return cfg


def _make_integration(config=None):
    return SpotifyIntegration(
        cache=MagicMock(),
        ws_manager=MagicMock(),
        config=config or _make_config(),
    )


@pytest.mark.asyncio
@respx.mock
async def test_fetch_returns_now_playing_fields():
    respx.post(TOKEN_URL).mock(return_value=httpx.Response(200, json=TOKEN_FIXTURE))
    respx.get(NOW_PLAYING_URL).mock(return_value=httpx.Response(200, json=PLAYING_FIXTURE))

    result = await _make_integration().fetch()

    assert result["track"] == "Pyramid Song"
    assert result["artist"] == "Radiohead"
    assert result["album"] == "Amnesiac"
    assert result["is_playing"] is True
    assert 0 < result["progress"] < 1
    assert result["elapsed"] == "1:54"
    assert result["total"] == "4:50"


@pytest.mark.asyncio
@respx.mock
async def test_fetch_returns_paused_state():
    respx.post(TOKEN_URL).mock(return_value=httpx.Response(200, json=TOKEN_FIXTURE))
    respx.get(NOW_PLAYING_URL).mock(return_value=httpx.Response(200, json=PAUSED_FIXTURE))

    result = await _make_integration().fetch()

    assert result["is_playing"] is False


@pytest.mark.asyncio
@respx.mock
async def test_fetch_returns_nothing_when_idle():
    respx.post(TOKEN_URL).mock(return_value=httpx.Response(200, json=TOKEN_FIXTURE))
    respx.get(NOW_PLAYING_URL).mock(return_value=httpx.Response(204))

    result = await _make_integration().fetch()

    assert result == {"is_playing": False, "track": None, "artist": None,
                      "album": None, "progress": 0.0, "elapsed": "0:00",
                      "total": "0:00", "art_url": None}


@pytest.mark.asyncio
@respx.mock
async def test_fetch_skips_when_disabled():
    respx.post(TOKEN_URL).mock(side_effect=Exception("should not call"))
    result = await _make_integration(config=_make_config(enabled=False)).fetch()
    assert result["is_playing"] is False


@pytest.mark.asyncio
@respx.mock
async def test_fetch_sends_correct_auth_header_to_token_endpoint():
    route = respx.post(TOKEN_URL).mock(return_value=httpx.Response(200, json=TOKEN_FIXTURE))
    respx.get(NOW_PLAYING_URL).mock(return_value=httpx.Response(204))

    await _make_integration().fetch()

    auth_header = route.calls[0].request.headers["authorization"]
    expected_b64 = base64.b64encode(b"cid:csec").decode()
    assert auth_header == f"Basic {expected_b64}"


@pytest.mark.asyncio
@respx.mock
async def test_run_swallows_http_error():
    respx.post(TOKEN_URL).mock(return_value=httpx.Response(401))
    integration = _make_integration()
    await integration.run()
    assert integration.status["error_count"] == 1
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest backend/tests/integrations/test_spotify.py -v
```

Expected: `ModuleNotFoundError: No module named 'cyberdeck.integrations.spotify'`

- [ ] **Step 3: Implement `spotify.py`**

```python
# backend/cyberdeck/integrations/spotify.py
from __future__ import annotations

import base64
from typing import Any

import httpx

from cyberdeck.integrations.base import Integration

_TOKEN_URL = "https://accounts.spotify.com/api/token"
_NOW_PLAYING_URL = "https://api.spotify.com/v1/me/player/currently-playing"

_EMPTY = {
    "is_playing": False,
    "track": None,
    "artist": None,
    "album": None,
    "progress": 0.0,
    "elapsed": "0:00",
    "total": "0:00",
    "art_url": None,
}


def _ms_to_str(ms: int) -> str:
    s = ms // 1000
    return f"{s // 60}:{s % 60:02d}"


class SpotifyIntegration(Integration):
    name = "spotify"

    def event_name(self) -> str:
        return "spotify.update"

    async def fetch(self) -> dict[str, Any]:
        if not self.config.app.spotify.enabled:
            return _EMPTY

        client_id = self.config.spotify_client_id
        client_secret = self.config.spotify_client_secret
        refresh_token = self.config.spotify_refresh_token

        if not all([client_id, client_secret, refresh_token]):
            return _EMPTY

        async with httpx.AsyncClient(timeout=10.0) as client:
            creds_b64 = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
            token_resp = await client.post(
                _TOKEN_URL,
                data={"grant_type": "refresh_token", "refresh_token": refresh_token},
                headers={"Authorization": f"Basic {creds_b64}"},
            )
            token_resp.raise_for_status()
            access_token = token_resp.json()["access_token"]

            resp = await client.get(
                _NOW_PLAYING_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            )

        if resp.status_code == 204 or not resp.content:
            return _EMPTY

        resp.raise_for_status()
        data = resp.json()

        item = data.get("item") or {}
        duration_ms = item.get("duration_ms", 0) or 1
        progress_ms = data.get("progress_ms", 0) or 0

        images = (item.get("album") or {}).get("images") or []
        art_url = images[0]["url"] if images else None

        return {
            "is_playing": bool(data.get("is_playing")),
            "track": item.get("name"),
            "artist": ", ".join(a["name"] for a in (item.get("artists") or [])),
            "album": (item.get("album") or {}).get("name"),
            "progress": round(progress_ms / duration_ms, 4),
            "elapsed": _ms_to_str(progress_ms),
            "total": _ms_to_str(duration_ms),
            "art_url": art_url,
        }
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest backend/tests/integrations/test_spotify.py -v
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add backend/cyberdeck/integrations/spotify.py backend/tests/integrations/test_spotify.py
git commit -m "feat(spotify): now-playing integration with OAuth refresh-token flow"
```

---

## Task 4: GitHub Integration

**Files:**
- Create: `backend/cyberdeck/integrations/github.py`
- Create: `backend/tests/integrations/test_github.py`

Calls three GitHub REST endpoints: user events (commits), search PRs, search assigned issues.

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/integrations/test_github.py
from unittest.mock import MagicMock

import httpx
import pytest
import respx

from cyberdeck.integrations.github import GitHubIntegration

EVENTS_URL = "https://api.github.com/users/oliversantana/events"
PR_SEARCH_URL = "https://api.github.com/search/issues"

EVENTS_FIXTURE = [
    {
        "type": "PushEvent",
        "created_at": "2026-04-26T10:00:00Z",
        "repo": {"name": "oliversantana/cyberdeck"},
        "payload": {
            "commits": [
                {"sha": "a3f2c1b", "message": "feat: transit alerts"},
            ]
        },
    },
    {
        "type": "WatchEvent",
        "created_at": "2026-04-26T09:00:00Z",
        "repo": {"name": "oliversantana/dotfiles"},
        "payload": {},
    },
]

PR_FIXTURE = {
    "items": [
        {
            "number": 42,
            "title": "feat: notion calendar join",
            "repository_url": "https://api.github.com/repos/oliversantana/cyberdeck",
            "state": "open",
            "created_at": "2026-04-24T10:00:00Z",
        }
    ]
}

ISSUES_FIXTURE = {
    "items": [
        {
            "number": 12,
            "title": "F train delay banner overflows",
            "repository_url": "https://api.github.com/repos/oliversantana/cyberdeck",
            "state": "open",
            "labels": [{"name": "bug"}],
            "created_at": "2026-04-25T10:00:00Z",
        }
    ]
}


def _make_config(username="oliversantana", token="ghp_test"):
    cfg = MagicMock()
    cfg.app.github.username = username
    cfg.app.github.show = ["recent_commits", "open_prs", "assigned_issues"]
    cfg.github_token = token
    return cfg


def _make_integration(config=None):
    return GitHubIntegration(
        cache=MagicMock(),
        ws_manager=MagicMock(),
        config=config or _make_config(),
    )


@pytest.mark.asyncio
@respx.mock
async def test_fetch_extracts_push_commits():
    respx.get(EVENTS_URL).mock(return_value=httpx.Response(200, json=EVENTS_FIXTURE))
    respx.get(PR_SEARCH_URL).mock(return_value=httpx.Response(200, json=PR_FIXTURE))

    result = await _make_integration().fetch()

    assert len(result["commits"]) == 1
    c = result["commits"][0]
    assert c["msg"] == "feat: transit alerts"
    assert c["repo"] == "oliversantana/cyberdeck"
    assert c["sha"] == "a3f2c1b"[:7]


@pytest.mark.asyncio
@respx.mock
async def test_fetch_ignores_non_push_events():
    respx.get(EVENTS_URL).mock(return_value=httpx.Response(200, json=EVENTS_FIXTURE))
    respx.get(PR_SEARCH_URL).mock(return_value=httpx.Response(200, json=PR_FIXTURE))

    result = await _make_integration().fetch()

    assert all(c["repo"] != "oliversantana/dotfiles" for c in result["commits"]
               if "WatchEvent" in str(c))
    assert len(result["commits"]) == 1


@pytest.mark.asyncio
@respx.mock
async def test_fetch_returns_open_prs():
    respx.get(EVENTS_URL).mock(return_value=httpx.Response(200, json=[]))
    route = respx.get(PR_SEARCH_URL).mock(side_effect=[
        httpx.Response(200, json=PR_FIXTURE),
        httpx.Response(200, json={"items": ISSUES_FIXTURE["items"]}),
    ])

    result = await _make_integration().fetch()

    assert result["prs"][0]["number"] == 42
    assert result["prs"][0]["title"] == "feat: notion calendar join"


@pytest.mark.asyncio
@respx.mock
async def test_fetch_returns_assigned_issues():
    respx.get(EVENTS_URL).mock(return_value=httpx.Response(200, json=[]))
    respx.get(PR_SEARCH_URL).mock(side_effect=[
        httpx.Response(200, json={"items": []}),
        httpx.Response(200, json=ISSUES_FIXTURE),
    ])

    result = await _make_integration().fetch()

    assert result["issues"][0]["number"] == 12
    assert result["issues"][0]["label"] == "bug"


@pytest.mark.asyncio
@respx.mock
async def test_fetch_sends_bearer_token():
    route = respx.get(EVENTS_URL).mock(return_value=httpx.Response(200, json=[]))
    respx.get(PR_SEARCH_URL).mock(return_value=httpx.Response(200, json={"items": []}))

    await _make_integration().fetch()

    assert route.calls[0].request.headers["authorization"] == "Bearer ghp_test"


@pytest.mark.asyncio
@respx.mock
async def test_run_swallows_http_error():
    respx.get(EVENTS_URL).mock(return_value=httpx.Response(503))
    integration = _make_integration()
    await integration.run()
    assert integration.status["error_count"] == 1
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest backend/tests/integrations/test_github.py -v
```

Expected: `ModuleNotFoundError: No module named 'cyberdeck.integrations.github'`

- [ ] **Step 3: Implement `github.py`**

```python
# backend/cyberdeck/integrations/github.py
from __future__ import annotations

from typing import Any

import httpx

from cyberdeck.integrations.base import Integration

_GH_BASE = "https://api.github.com"


class GitHubIntegration(Integration):
    name = "github"

    def event_name(self) -> str:
        return "github.update"

    async def fetch(self) -> dict[str, Any]:
        username = self.config.app.github.username
        token = self.config.github_token

        if not username:
            return {"commits": [], "prs": [], "issues": []}

        headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
        if token:
            headers["Authorization"] = f"Bearer {token}"

        async with httpx.AsyncClient(timeout=15.0, headers=headers) as client:
            events_resp = await client.get(
                f"{_GH_BASE}/users/{username}/events",
                params={"per_page": 100},
            )
            events_resp.raise_for_status()

            pr_resp = await client.get(
                f"{_GH_BASE}/search/issues",
                params={"q": f"author:{username} type:pr state:open", "per_page": 10},
            )
            pr_resp.raise_for_status()

            issues_resp = await client.get(
                f"{_GH_BASE}/search/issues",
                params={"q": f"assignee:{username} state:open is:issue", "per_page": 10},
            )
            issues_resp.raise_for_status()

        commits: list[dict[str, Any]] = []
        for event in events_resp.json():
            if event.get("type") != "PushEvent":
                continue
            repo = event["repo"]["name"]
            for commit in event["payload"].get("commits", []):
                commits.append(
                    {
                        "sha": commit["sha"][:7],
                        "msg": commit["message"].splitlines()[0][:80],
                        "repo": repo,
                        "time": event["created_at"],
                    }
                )
            if len(commits) >= 10:
                break

        def _repo_name(repo_url: str) -> str:
            return "/".join(repo_url.split("/")[-2:])

        prs = [
            {
                "number": item["number"],
                "title": item["title"],
                "repo": _repo_name(item["repository_url"]),
                "status": item["state"],
                "age": item["created_at"],
            }
            for item in pr_resp.json().get("items", [])
        ]

        issues = [
            {
                "number": item["number"],
                "title": item["title"],
                "repo": _repo_name(item["repository_url"]),
                "label": (item.get("labels") or [{}])[0].get("name", ""),
                "age": item["created_at"],
            }
            for item in issues_resp.json().get("items", [])
        ]

        return {"commits": commits, "prs": prs, "issues": issues}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest backend/tests/integrations/test_github.py -v
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add backend/cyberdeck/integrations/github.py backend/tests/integrations/test_github.py
git commit -m "feat(github): commits + open PRs + assigned issues integration"
```

---

## Task 5: RSS Integration

**Files:**
- Create: `backend/cyberdeck/integrations/rss.py`
- Create: `backend/tests/integrations/test_rss.py`

`feedparser` is sync; wrap in executor. Deduplicate items by `id` or `link`.

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/integrations/test_rss.py
import asyncio
from unittest.mock import MagicMock, patch

import pytest

from cyberdeck.integrations.rss import RSSIntegration, _dedupe, _age_str

# Fake feedparser result
def _make_feed(entries):
    feed = MagicMock()
    feed.entries = entries
    feed.bozo = False
    return feed


def _entry(eid, title, link="https://example.com/article", published_parsed=None):
    e = MagicMock()
    e.id = eid
    e.title = title
    e.link = link
    e.published_parsed = published_parsed or (2026, 4, 26, 10, 0, 0, 0, 0, 0)
    return e


def _make_config(feeds=None, headline_size=3, refresh=600):
    cfg = MagicMock()
    cfg.app.rss.feeds = feeds or [
        MagicMock(name="HN", url="https://news.ycombinator.com/rss"),
        MagicMock(name="TLDR", url="https://example.com/tldr.xml"),
    ]
    cfg.app.rss.headline_stack_size = headline_size
    cfg.app.rss.refresh_seconds = refresh
    return cfg


def _make_integration(config=None):
    return RSSIntegration(
        cache=MagicMock(),
        ws_manager=MagicMock(),
        config=config or _make_config(),
    )


def test_dedupe_removes_duplicate_ids():
    items = [
        {"id": "a", "title": "First"},
        {"id": "b", "title": "Second"},
        {"id": "a", "title": "First again"},
    ]
    assert len(_dedupe(items)) == 2


def test_dedupe_removes_duplicate_links():
    items = [
        {"id": "a", "link": "https://x.com/story", "title": "One"},
        {"id": "b", "link": "https://x.com/story", "title": "Two"},
    ]
    assert len(_dedupe(items)) == 1


@pytest.mark.asyncio
async def test_fetch_returns_items_from_multiple_feeds():
    hn_entries = [_entry("hn-1", "HN Story")]
    tldr_entries = [_entry("tldr-1", "TLDR Story")]

    with patch("cyberdeck.integrations.rss.feedparser") as fp:
        fp.parse.side_effect = [
            _make_feed(hn_entries),
            _make_feed(tldr_entries),
        ]
        result = await _make_integration().fetch()

    titles = [item["title"] for item in result["items"]]
    assert "HN Story" in titles
    assert "TLDR Story" in titles


@pytest.mark.asyncio
async def test_fetch_dedupes_across_feeds():
    shared_link = "https://example.com/same"
    entries = [_entry("a", "Same Story", link=shared_link)]

    with patch("cyberdeck.integrations.rss.feedparser") as fp:
        fp.parse.side_effect = [_make_feed(entries), _make_feed(entries)]
        result = await _make_integration().fetch()

    assert len([i for i in result["items"] if i["title"] == "Same Story"]) == 1


@pytest.mark.asyncio
async def test_fetch_limits_headline_stack():
    entries = [_entry(f"id-{i}", f"Story {i}") for i in range(10)]

    with patch("cyberdeck.integrations.rss.feedparser") as fp:
        fp.parse.side_effect = [_make_feed(entries), _make_feed([])]
        cfg = _make_config(headline_size=3)
        result = await RSSIntegration(
            cache=MagicMock(), ws_manager=MagicMock(), config=cfg
        ).fetch()

    assert len(result["headlines"]) == 3


@pytest.mark.asyncio
async def test_fetch_returns_ticker_list():
    entries = [_entry(f"id-{i}", f"Story {i}") for i in range(5)]

    with patch("cyberdeck.integrations.rss.feedparser") as fp:
        fp.parse.side_effect = [_make_feed(entries), _make_feed([])]
        result = await _make_integration().fetch()

    assert isinstance(result["ticker"], list)
    assert len(result["ticker"]) >= 1


@pytest.mark.asyncio
async def test_run_swallows_feedparser_error():
    with patch("cyberdeck.integrations.rss.feedparser") as fp:
        fp.parse.side_effect = Exception("network error")
        integration = _make_integration()
        await integration.run()
    assert integration.status["error_count"] == 1
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest backend/tests/integrations/test_rss.py -v
```

Expected: `ModuleNotFoundError: No module named 'cyberdeck.integrations.rss'`

- [ ] **Step 3: Implement `rss.py`**

```python
# backend/cyberdeck/integrations/rss.py
from __future__ import annotations

import asyncio
import time
from typing import Any

import feedparser

from cyberdeck.integrations.base import Integration


def _age_str(published_parsed: tuple | None) -> str:
    if not published_parsed:
        return ""
    try:
        ts = time.mktime(published_parsed)
        delta = int(time.time() - ts)
        if delta < 3600:
            return f"{delta // 60}m"
        if delta < 86400:
            return f"{delta // 3600}h"
        return f"{delta // 86400}d"
    except Exception:
        return ""


def _dedupe(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen_ids: set[str] = set()
    seen_links: set[str] = set()
    result: list[dict[str, Any]] = []
    for item in items:
        item_id = item.get("id", "")
        link = item.get("link", "")
        if item_id and item_id in seen_ids:
            continue
        if link and link in seen_links:
            continue
        if item_id:
            seen_ids.add(item_id)
        if link:
            seen_links.add(link)
        result.append(item)
    return result


class RSSIntegration(Integration):
    name = "rss"

    def event_name(self) -> str:
        return "rss.update"

    async def fetch(self) -> dict[str, Any]:
        loop = asyncio.get_event_loop()
        cfg = self.config.app.rss
        all_items: list[dict[str, Any]] = []

        for feed_cfg in cfg.feeds:
            parsed = await loop.run_in_executor(None, feedparser.parse, feed_cfg.url)
            for entry in parsed.entries:
                all_items.append(
                    {
                        "id": getattr(entry, "id", entry.get("link", "")),
                        "src": feed_cfg.name,
                        "title": getattr(entry, "title", ""),
                        "link": getattr(entry, "link", ""),
                        "summary": getattr(entry, "summary", "")[:200],
                        "age": _age_str(getattr(entry, "published_parsed", None)),
                    }
                )

        deduped = _dedupe(all_items)
        headline_size = cfg.headline_stack_size

        return {
            "items": deduped,
            "headlines": [
                {"src": i["src"], "title": i["title"], "age": i["age"]}
                for i in deduped[:headline_size]
            ],
            "ticker": [f"{i['src']} · {i['title']}" for i in deduped[:20]],
        }
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest backend/tests/integrations/test_rss.py -v
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add backend/cyberdeck/integrations/rss.py backend/tests/integrations/test_rss.py
git commit -m "feat(rss): multi-feed RSS integration with dedup and ticker"
```

---

## Task 6: Calendar Integration (Google + Notion join)

**Files:**
- Create: `backend/cyberdeck/integrations/calendar.py`
- Create: `backend/tests/integrations/test_calendar.py`

This is the most complex integration. Token loading runs in executor (google-auth is sync). Join logic: match Google events to Notion todos by URL in description → fallback title match.

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/integrations/test_calendar.py
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cyberdeck.integrations.calendar import CalendarIntegration, _join_events, _parse_google_event


TODAY = "2026-04-26"

GOOGLE_EVENTS_FIXTURE = [
    {
        "id": "evt1",
        "summary": "Lunch w/ Maya",
        "start": {"dateTime": f"{TODAY}T12:30:00-04:00"},
        "end": {"dateTime": f"{TODAY}T13:00:00-04:00"},
        "location": "Devoción",
        "description": "",
        "colorId": "2",
    },
    {
        "id": "evt2",
        "summary": "O-Deck install on Pi",
        "start": {"dateTime": f"{TODAY}T14:00:00-04:00"},
        "end": {"dateTime": f"{TODAY}T15:00:00-04:00"},
        "location": "Desk",
        "description": "https://notion.so/oliversantana/page-abc123",
        "colorId": "5",
    },
]

NOTION_TODOS_FIXTURE = [
    {
        "id": "page-abc123",
        "url": "https://notion.so/oliversantana/page-abc123",
        "properties": {
            "Name": {"title": [{"plain_text": "O-Deck install on Pi"}]},
            "Status": {"status": {"name": "In Progress"}},
            "Project": {"select": {"name": "cyberdeck"}},
        },
    }
]


def _make_config(google_creds_path=None, google_token_path=None, notion_token=None):
    cfg = MagicMock()
    cfg.google_calendar_credentials_path = google_creds_path
    cfg.google_calendar_token_path = google_token_path
    cfg.notion_token = notion_token
    cfg.app.calendar.google.calendar_ids = ["primary"]
    cfg.app.calendar.notion.todo_database_ids = ["db-1"]
    cfg.app.calendar.notion.join_strategy = "event_link"
    cfg.app.device.timezone = "America/New_York"
    return cfg


def _make_integration(config=None):
    return CalendarIntegration(
        cache=MagicMock(),
        ws_manager=MagicMock(),
        config=config or _make_config(),
    )


# -- unit tests ----------------------------------------------------------------

def test_parse_google_event_extracts_fields():
    event = GOOGLE_EVENTS_FIXTURE[0]
    parsed = _parse_google_event(event)
    assert parsed["title"] == "Lunch w/ Maya"
    assert parsed["time"] == "12:30"
    assert parsed["location"] == "Devoción"


def test_parse_google_event_computes_duration():
    event = GOOGLE_EVENTS_FIXTURE[0]  # 30-min event
    parsed = _parse_google_event(event)
    assert parsed["duration"] == "30m"


def test_join_events_matches_by_url_in_description():
    google_events = [_parse_google_event(e) for e in GOOGLE_EVENTS_FIXTURE]
    joined = _join_events(google_events, NOTION_TODOS_FIXTURE)
    matched = next(e for e in joined if e["title"] == "O-Deck install on Pi")
    assert matched["notion"]["status"] == "In Progress"
    assert matched["notion"]["project"] == "cyberdeck"


def test_join_events_leaves_unmatched_events_as_plain():
    google_events = [_parse_google_event(e) for e in GOOGLE_EVENTS_FIXTURE]
    joined = _join_events(google_events, NOTION_TODOS_FIXTURE)
    unmatched = next(e for e in joined if e["title"] == "Lunch w/ Maya")
    assert unmatched["notion"] is None


def test_join_events_title_fallback():
    google_event = _parse_google_event({
        **GOOGLE_EVENTS_FIXTURE[1],
        "description": "",  # no URL
    })
    joined = _join_events([google_event], NOTION_TODOS_FIXTURE)
    assert joined[0]["notion"]["status"] == "In Progress"


# -- integration test (mocked dependencies) ------------------------------------

@pytest.mark.asyncio
async def test_fetch_returns_events_with_notion_join(tmp_path):
    # Write fake credentials files
    creds_file = tmp_path / "creds.json"
    token_file = tmp_path / "token.json"
    creds_file.write_text(json.dumps({
        "installed": {"client_id": "cid", "client_secret": "csec",
                      "token_uri": "https://oauth2.googleapis.com/token"}
    }))
    token_file.write_text(json.dumps({
        "token": "access-token",
        "refresh_token": "refresh-token",
        "expiry": "2099-01-01T00:00:00Z",
    }))

    config = _make_config(
        google_creds_path=creds_file,
        google_token_path=token_file,
        notion_token="notion-token",
    )

    with (
        patch("cyberdeck.integrations.calendar._load_google_token", return_value="access-token"),
        patch("cyberdeck.integrations.calendar._fetch_google_events",
              new=AsyncMock(return_value=GOOGLE_EVENTS_FIXTURE)),
        patch("cyberdeck.integrations.calendar._fetch_notion_todos",
              new=AsyncMock(return_value=NOTION_TODOS_FIXTURE)),
    ):
        result = await CalendarIntegration(
            cache=MagicMock(), ws_manager=MagicMock(), config=config
        ).fetch()

    assert len(result["events"]) == 2
    notion_event = next(e for e in result["events"] if e["title"] == "O-Deck install on Pi")
    assert notion_event["notion"]["project"] == "cyberdeck"


@pytest.mark.asyncio
async def test_fetch_returns_empty_when_no_credentials():
    config = _make_config(google_creds_path=None, google_token_path=None)
    result = await _make_integration(config).fetch()
    assert result["events"] == []


@pytest.mark.asyncio
async def test_run_swallows_auth_error():
    with patch("cyberdeck.integrations.calendar._load_google_token", side_effect=Exception("auth")):
        integration = _make_integration(config=_make_config(
            google_creds_path=Path("/fake/creds.json"),
            google_token_path=Path("/fake/token.json"),
        ))
        await integration.run()
    assert integration.status["error_count"] == 1
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest backend/tests/integrations/test_calendar.py -v
```

Expected: `ModuleNotFoundError: No module named 'cyberdeck.integrations.calendar'`

- [ ] **Step 3: Implement `calendar.py`**

```python
# backend/cyberdeck/integrations/calendar.py
from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

from cyberdeck.integrations.base import Integration

_GCAL_EVENTS_URL = "https://www.googleapis.com/calendar/v3/calendars/{cal_id}/events"

_GOOGLE_COLORS: dict[str, str] = {
    "1": "#7986CB", "2": "#33B679", "3": "#8E24AA", "4": "#E67C73",
    "5": "#F6BF26", "6": "#F4511E", "7": "#039BE5", "8": "#616161",
    "9": "#3F51B5", "10": "#0B8043", "11": "#D50000",
}


def _load_google_token(token_path: Path, creds_path: Path) -> str:
    """Load + refresh Google OAuth token; return access_token. Sync (google-auth)."""
    with open(token_path) as f:
        token_data = json.load(f)
    with open(creds_path) as f:
        client_data = json.load(f)

    installed = client_data.get("installed") or client_data.get("web", {})
    creds = Credentials(
        token=token_data.get("token"),
        refresh_token=token_data.get("refresh_token"),
        token_uri=installed.get("token_uri", "https://oauth2.googleapis.com/token"),
        client_id=installed.get("client_id"),
        client_secret=installed.get("client_secret"),
    )
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        token_data["token"] = creds.token
        with open(token_path, "w") as f:
            json.dump(token_data, f)

    return creds.token


async def _fetch_google_events(
    token: str,
    calendar_ids: list[str],
    date_str: str,
) -> list[dict[str, Any]]:
    headers = {"Authorization": f"Bearer {token}"}
    events: list[dict[str, Any]] = []
    async with httpx.AsyncClient(timeout=15.0) as client:
        for cal_id in calendar_ids:
            resp = await client.get(
                _GCAL_EVENTS_URL.format(cal_id=cal_id),
                params={
                    "timeMin": f"{date_str}T00:00:00Z",
                    "timeMax": f"{date_str}T23:59:59Z",
                    "singleEvents": "true",
                    "orderBy": "startTime",
                },
                headers=headers,
            )
            resp.raise_for_status()
            events.extend(resp.json().get("items", []))
    return events


async def _fetch_notion_todos(
    token: str,
    database_ids: list[str],
) -> list[dict[str, Any]]:
    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": "2022-06-28",
    }
    todos: list[dict[str, Any]] = []
    async with httpx.AsyncClient(timeout=15.0) as client:
        for db_id in database_ids:
            resp = await client.post(
                f"https://api.notion.com/v1/databases/{db_id}/query",
                headers=headers,
                json={},
            )
            resp.raise_for_status()
            todos.extend(resp.json().get("results", []))
    return todos


def _parse_google_event(event: dict[str, Any]) -> dict[str, Any]:
    start_raw = event.get("start", {}).get("dateTime") or event["start"].get("date", "")
    end_raw = event.get("end", {}).get("dateTime") or event["end"].get("date", "")

    def _parse_dt(raw: str) -> datetime | None:
        for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%d"):
            try:
                return datetime.strptime(raw[:19] + (raw[19:] or "+00:00"), "%Y-%m-%dT%H:%M:%S%z")
            except ValueError:
                pass
        return None

    start_dt = _parse_dt(start_raw)
    end_dt = _parse_dt(end_raw)

    time_str = start_dt.strftime("%-I:%M") if start_dt else ""
    if start_dt and end_dt:
        delta = end_dt - start_dt
        mins = int(delta.total_seconds() / 60)
        duration = f"{mins // 60}h {mins % 60}m" if mins >= 60 else f"{mins}m"
        if duration.startswith("0m") or duration == "1h 0m":
            duration = "1h" if mins == 60 else duration
    else:
        duration = ""

    return {
        "id": event.get("id", ""),
        "title": event.get("summary", "Untitled"),
        "time": time_str,
        "duration": duration,
        "location": event.get("location", ""),
        "description": event.get("description", ""),
        "color": _GOOGLE_COLORS.get(event.get("colorId", ""), "#a8c19a"),
        "notion": None,
    }


def _join_events(
    google_events: list[dict[str, Any]],
    notion_todos: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    notion_by_url: dict[str, dict[str, Any]] = {}
    notion_by_title: dict[str, dict[str, Any]] = {}

    for todo in notion_todos:
        url = todo.get("url", "")
        title_parts = (
            todo.get("properties", {})
            .get("Name", {})
            .get("title", [])
        )
        title = "".join(p.get("plain_text", "") for p in title_parts).lower().strip()
        status = (
            todo.get("properties", {})
            .get("Status", {})
            .get("status", {})
            .get("name", "")
        )
        project = (
            todo.get("properties", {})
            .get("Project", {})
            .get("select", {})
            .get("name", "")
        )
        notion_meta = {
            "page_id": todo.get("id", ""),
            "status": status,
            "project": project,
        }
        if url:
            notion_by_url[url] = notion_meta
        if title:
            notion_by_title[title] = notion_meta

    result: list[dict[str, Any]] = []
    for event in google_events:
        desc = event.get("description", "") or ""
        matched_notion = None
        for word in desc.split():
            if word.startswith("https://notion.so/") and word in notion_by_url:
                matched_notion = notion_by_url[word]
                break
        if matched_notion is None:
            title_lower = event.get("title", "").lower().strip()
            matched_notion = notion_by_title.get(title_lower)

        result.append({**event, "notion": matched_notion})
    return result


class CalendarIntegration(Integration):
    name = "calendar"

    def event_name(self) -> str:
        return "calendar.update"

    async def fetch(self) -> dict[str, Any]:
        creds_path = self.config.google_calendar_credentials_path
        token_path = self.config.google_calendar_token_path

        if not (creds_path and token_path):
            return {"events": [], "next_in": None}

        loop = asyncio.get_event_loop()
        token = await loop.run_in_executor(
            None, _load_google_token, Path(token_path), Path(creds_path)
        )

        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        google_events_raw = await _fetch_google_events(
            token,
            self.config.app.calendar.google.calendar_ids,
            today,
        )

        notion_todos: list[dict[str, Any]] = []
        if self.config.notion_token and self.config.app.calendar.notion.todo_database_ids:
            notion_todos = await _fetch_notion_todos(
                self.config.notion_token,
                self.config.app.calendar.notion.todo_database_ids,
            )

        google_events = [_parse_google_event(e) for e in google_events_raw]
        events = _join_events(google_events, notion_todos)

        return {"events": events, "next_in": None}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest backend/tests/integrations/test_calendar.py -v
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add backend/cyberdeck/integrations/calendar.py backend/tests/integrations/test_calendar.py
git commit -m "feat(calendar): Google Calendar + Notion join integration"
```

---

## Task 7: Photos Integration

**Files:**
- Create: `backend/cyberdeck/integrations/photos.py`
- Create: `backend/tests/integrations/test_photos.py`

Two sources: local folder (glob) and iCloud shared album (webstream API). Maintains rotation index internally.

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/integrations/test_photos.py
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
import pytest
import respx

from cyberdeck.integrations.photos import PhotosIntegration, _list_local_photos, _parse_share_token


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


# -- unit tests ----------------------------------------------------------------

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
    assert all(p.endswith((".jpg", ".png")) for p in found)


def test_list_local_photos_returns_empty_for_missing_folder():
    found = _list_local_photos("/nonexistent/path/xyz")
    assert found == []


# -- integration tests ---------------------------------------------------------

@pytest.mark.asyncio
async def test_fetch_local_returns_first_photo(tmp_path):
    (tmp_path / "img1.jpg").write_bytes(b"")
    (tmp_path / "img2.jpg").write_bytes(b"")

    integration = PhotosIntegration(
        cache=MagicMock(),
        ws_manager=MagicMock(),
        config=_make_config(source="local", local_folder=str(tmp_path)),
    )
    result = await integration.fetch()

    assert result["source"] == "local"
    assert result["total"] == 2
    assert result["index"] == 0
    assert "/api/photos/file/" in result["url"]


@pytest.mark.asyncio
async def test_fetch_local_advances_index(tmp_path):
    (tmp_path / "img1.jpg").write_bytes(b"")
    (tmp_path / "img2.jpg").write_bytes(b"")

    integration = PhotosIntegration(
        cache=MagicMock(),
        ws_manager=MagicMock(),
        config=_make_config(source="local", local_folder=str(tmp_path)),
    )
    await integration.fetch()  # index 0
    result = await integration.fetch()  # index 1
    assert result["index"] == 1


@pytest.mark.asyncio
async def test_fetch_local_wraps_index(tmp_path):
    (tmp_path / "img1.jpg").write_bytes(b"")

    integration = PhotosIntegration(
        cache=MagicMock(),
        ws_manager=MagicMock(),
        config=_make_config(source="local", local_folder=str(tmp_path)),
    )
    await integration.fetch()  # index 0
    result = await integration.fetch()  # wraps back to 0
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
        respx.post(f"https://p{partition}-sharedstreams.icloud.com/{token}/sharedstreams/webstream").mock(
            return_value=httpx.Response(200, json=webstream_resp)
        )
        respx.post(f"https://p{partition}-sharedstreams.icloud.com/{token}/sharedstreams/webasseturls").mock(
            return_value=httpx.Response(200, json=webasset_resp)
        )

    url = f"https://www.icloud.com/sharedalbum/#{token}"
    integration = PhotosIntegration(
        cache=MagicMock(),
        ws_manager=MagicMock(),
        config=_make_config(source="icloud_shared_album", icloud_url=url),
    )
    result = await integration.fetch()

    assert result["source"] == "icloud_shared_album"
    assert result["url"] == "https://cdn.icloud.com/img1.jpg"


@pytest.mark.asyncio
async def test_run_swallows_error():
    with patch.object(PhotosIntegration, "fetch", side_effect=Exception("oops")):
        integration = _make_integration()
        await integration.run()
    assert integration.status["error_count"] == 1
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest backend/tests/integrations/test_photos.py -v
```

Expected: `ModuleNotFoundError: No module named 'cyberdeck.integrations.photos'`

- [ ] **Step 3: Implement `photos.py`**

```python
# backend/cyberdeck/integrations/photos.py
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
    return sorted(str(f) for f in folder.iterdir() if f.suffix in _IMAGE_SUFFIXES)


class PhotosIntegration(Integration):
    name = "photos"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._index = 0
        self._photo_list: list[str] = []
        self._last_list_refresh: float = 0.0
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

        if cfg.source == "local":
            filename = Path(current).name
            url = f"/api/photos/file/{filename}"
        else:
            url = current

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
                    key=lambda d: d.get("width", 0),
                    default=None,
                )
                if best:
                    checksums.append(best["checksum"])

            if not checksums:
                return []

            for partition in _ICLOUD_PARTITIONS:
                try:
                    asset_resp = await client.post(
                        f"https://p{partition}-sharedstreams.icloud.com/{token}/sharedstreams/webasseturls",
                        json={"photoGuids": [p["photoGuid"] for p in photos]},
                    )
                    if asset_resp.status_code == 200:
                        items = asset_resp.json().get("items", {})
                        return [
                            items[ck]["url"] for ck in checksums if ck in items
                        ]
                except httpx.RequestError:
                    continue

        return []
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest backend/tests/integrations/test_photos.py -v
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add backend/cyberdeck/integrations/photos.py backend/tests/integrations/test_photos.py
git commit -m "feat(photos): local folder + iCloud shared album rotation integration"
```

---

## Task 8: Pomodoro State

**Files:**
- Create: `backend/cyberdeck/pomodoro.py`
- Create: `backend/tests/test_pomodoro.py`

Pomodoro is REST-driven (not polled). `PomodoroState` is a plain object; `main.py` mounts its router.

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_pomodoro.py
import asyncio
import time
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from cyberdeck.pomodoro import PomodoroState, make_router


PRESET_CLASSIC = {
    "name": "Classic",
    "work_min": 25,
    "break_min": 5,
    "cycles": 4,
    "long_break_min": 15,
}


@pytest.fixture
def ws():
    m = MagicMock()
    m.broadcast = AsyncMock()
    return m


@pytest.fixture
def state(ws):
    return PomodoroState(ws_manager=ws)


@pytest.fixture
def client(state):
    app = FastAPI()
    app.include_router(make_router(state), prefix="/api/pomodoro")
    return TestClient(app)


def test_initial_state_is_idle(state):
    s = state.get_status()
    assert s["running"] is False
    assert s["phase"] == "idle"


def test_start_sets_running(state):
    state.start(PRESET_CLASSIC)
    s = state.get_status()
    assert s["running"] is True
    assert s["phase"] == "work"
    assert s["work_min"] == 25


def test_start_resets_cycle_count(state):
    state.start(PRESET_CLASSIC)
    state.start(PRESET_CLASSIC)
    assert state.get_status()["cycle"] == 1


def test_pause_stops_running(state):
    state.start(PRESET_CLASSIC)
    state.pause()
    assert state.get_status()["running"] is False
    assert state.get_status()["phase"] == "work"


def test_resume_restarts_running(state):
    state.start(PRESET_CLASSIC)
    state.pause()
    state.resume()
    assert state.get_status()["running"] is True


def test_stop_resets_to_idle(state):
    state.start(PRESET_CLASSIC)
    state.stop()
    assert state.get_status()["phase"] == "idle"
    assert state.get_status()["running"] is False


def test_remaining_seconds_decreases_with_time(state):
    state.start(PRESET_CLASSIC)
    initial = state.get_status()["remaining_seconds"]
    state._started_at -= 60  # fake 60s passage
    updated = state.get_status()["remaining_seconds"]
    assert updated == pytest.approx(initial - 60, abs=2)


def test_rest_start_returns_200(client):
    resp = client.post("/api/pomodoro/start", json=PRESET_CLASSIC)
    assert resp.status_code == 200
    assert resp.json()["running"] is True


def test_rest_pause_returns_200(client):
    client.post("/api/pomodoro/start", json=PRESET_CLASSIC)
    resp = client.post("/api/pomodoro/pause")
    assert resp.status_code == 200
    assert resp.json()["running"] is False


def test_rest_stop_returns_200(client):
    client.post("/api/pomodoro/start", json=PRESET_CLASSIC)
    resp = client.post("/api/pomodoro/stop")
    assert resp.status_code == 200
    assert resp.json()["phase"] == "idle"


def test_rest_status_returns_current_state(client):
    resp = client.get("/api/pomodoro/status")
    assert resp.status_code == 200
    assert resp.json()["phase"] == "idle"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest backend/tests/test_pomodoro.py -v
```

Expected: `ModuleNotFoundError: No module named 'cyberdeck.pomodoro'`

- [ ] **Step 3: Implement `pomodoro.py`**

```python
# backend/cyberdeck/pomodoro.py
from __future__ import annotations

import asyncio
import time
from typing import Any, TYPE_CHECKING

from fastapi import APIRouter
from pydantic import BaseModel

if TYPE_CHECKING:
    from cyberdeck.ws import WSManager


class PresetIn(BaseModel):
    name: str
    work_min: int
    break_min: int
    cycles: int
    long_break_min: int


class PomodoroState:
    def __init__(self, ws_manager: "WSManager") -> None:
        self._ws = ws_manager
        self._running = False
        self._phase = "idle"
        self._work_min = 25
        self._break_min = 5
        self._long_break_min = 15
        self._cycles = 4
        self._cycle = 0
        self._preset_name = ""
        self._started_at: float | None = None
        self._paused_remaining: float | None = None

    def _phase_total_seconds(self) -> float:
        if self._phase == "work":
            return self._work_min * 60
        if self._phase == "break":
            return self._break_min * 60
        if self._phase == "long_break":
            return self._long_break_min * 60
        return 0.0

    def get_status(self) -> dict[str, Any]:
        if self._phase == "idle" or self._started_at is None:
            remaining = 0.0
        elif not self._running and self._paused_remaining is not None:
            remaining = self._paused_remaining
        else:
            elapsed = time.time() - self._started_at
            remaining = max(0.0, self._phase_total_seconds() - elapsed)

        return {
            "running": self._running,
            "phase": self._phase,
            "remaining_seconds": round(remaining),
            "cycle": self._cycle,
            "cycles_total": self._cycles,
            "work_min": self._work_min,
            "break_min": self._break_min,
            "long_break_min": self._long_break_min,
            "preset_name": self._preset_name,
        }

    def start(self, preset: dict[str, Any] | PresetIn) -> None:
        if isinstance(preset, PresetIn):
            preset = preset.model_dump()
        self._work_min = preset["work_min"]
        self._break_min = preset["break_min"]
        self._long_break_min = preset["long_break_min"]
        self._cycles = preset["cycles"]
        self._preset_name = preset["name"]
        self._phase = "work"
        self._cycle = 1
        self._running = True
        self._started_at = time.time()
        self._paused_remaining = None
        asyncio.create_task(self._broadcast())

    def pause(self) -> None:
        if not self._running:
            return
        self._paused_remaining = (
            self._phase_total_seconds() - (time.time() - (self._started_at or time.time()))
        )
        self._running = False
        asyncio.create_task(self._broadcast())

    def resume(self) -> None:
        if self._running or self._phase == "idle":
            return
        remaining = self._paused_remaining or self._phase_total_seconds()
        self._started_at = time.time() - (self._phase_total_seconds() - remaining)
        self._paused_remaining = None
        self._running = True
        asyncio.create_task(self._broadcast())

    def stop(self) -> None:
        self._running = False
        self._phase = "idle"
        self._started_at = None
        self._paused_remaining = None
        asyncio.create_task(self._broadcast())

    async def _broadcast(self) -> None:
        await self._ws.broadcast("pomodoro.update", self.get_status())


def make_router(state: PomodoroState) -> APIRouter:
    router = APIRouter()

    @router.post("/start")
    async def start(preset: PresetIn) -> dict[str, Any]:
        state.start(preset)
        return state.get_status()

    @router.post("/pause")
    async def pause() -> dict[str, Any]:
        state.pause()
        return state.get_status()

    @router.post("/resume")
    async def resume() -> dict[str, Any]:
        state.resume()
        return state.get_status()

    @router.post("/stop")
    async def stop() -> dict[str, Any]:
        state.stop()
        return state.get_status()

    @router.get("/status")
    async def status() -> dict[str, Any]:
        return state.get_status()

    return router
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest backend/tests/test_pomodoro.py -v
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add backend/cyberdeck/pomodoro.py backend/tests/test_pomodoro.py
git commit -m "feat(pomodoro): timer state machine with REST controls and WS broadcast"
```

---

## Task 9: Wire everything into `main.py` + extend `/api/state`

**Files:**
- Modify: `backend/cyberdeck/main.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_main.py (create if not exists, or append)
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock


def _mock_integrations():
    """Patch all external calls so app starts without real credentials."""
    patches = [
        patch("cyberdeck.integrations.weather.httpx.AsyncClient"),
        patch("cyberdeck.integrations.transit.httpx.AsyncClient"),
        patch("cyberdeck.integrations.spotify.httpx.AsyncClient"),
        patch("cyberdeck.integrations.github.httpx.AsyncClient"),
        patch("cyberdeck.integrations.rss.feedparser"),
        patch("cyberdeck.integrations.calendar._load_google_token", return_value="tok"),
        patch("cyberdeck.integrations.calendar._fetch_google_events", new=AsyncMock(return_value=[])),
        patch("cyberdeck.integrations.calendar._fetch_notion_todos", new=AsyncMock(return_value=[])),
    ]
    return patches


def test_api_state_includes_all_integrations():
    from cyberdeck.cache import Cache
    import tempfile, pathlib

    with tempfile.TemporaryDirectory() as d:
        db = pathlib.Path(d) / "c.db"
        # Pre-populate cache with stubs
        cache = Cache(db_path=db)
        cache.set("weather", {"tempF": 58})
        cache.set("transit", {"stations": []})
        cache.set("spotify", {"is_playing": False})
        cache.set("github", {"commits": []})
        cache.set("rss", {"items": []})
        cache.set("photos", {"url": None})

        with patch("cyberdeck.main.Cache", return_value=cache):
            from cyberdeck import main as m
            import importlib
            importlib.reload(m)
            with TestClient(m.app) as client:
                resp = client.get("/api/state")

    data = resp.json()
    for key in ["weather", "transit", "spotify", "github", "rss", "photos"]:
        assert key in data, f"missing key: {key}"


def test_api_pomodoro_status_returns_idle():
    from cyberdeck import main as m
    import importlib
    importlib.reload(m)
    with TestClient(m.app) as client:
        resp = client.get("/api/pomodoro/status")
    assert resp.status_code == 200
    assert resp.json()["phase"] == "idle"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest backend/tests/test_main.py::test_api_state_includes_all_integrations -v
```

Expected: assertion fails — keys `transit`, `spotify`, etc. missing from state.

- [ ] **Step 3: Update `main.py`**

Replace the entire file:

```python
# backend/cyberdeck/main.py
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.websockets import WebSocketDisconnect

from cyberdeck.cache import Cache
from cyberdeck.config import load_config
from cyberdeck.integrations.calendar import CalendarIntegration
from cyberdeck.integrations.github import GitHubIntegration
from cyberdeck.integrations.photos import PhotosIntegration
from cyberdeck.integrations.rss import RSSIntegration
from cyberdeck.integrations.spotify import SpotifyIntegration
from cyberdeck.integrations.transit import TransitIntegration
from cyberdeck.integrations.weather import WeatherIntegration
from cyberdeck.pomodoro import PomodoroState, make_router
from cyberdeck.scheduler import IntegrationScheduler
from cyberdeck.ws import WSManager

logging.basicConfig(
    level=logging.INFO,
    format='{"t":"%(asctime)s","lvl":"%(levelname)s","name":"%(name)s","msg":%(message)r}',
)
logger = logging.getLogger("cyberdeck")

settings = load_config()
cache = Cache()
ws_manager = WSManager()
scheduler = IntegrationScheduler()
pomodoro_state = PomodoroState(ws_manager=ws_manager)

_INTEGRATIONS: list[tuple[Any, int]] = [
    (WeatherIntegration, 600),
    (TransitIntegration, settings.app.transit.refresh_seconds),
    (SpotifyIntegration, 5),
    (GitHubIntegration, 300),
    (RSSIntegration, settings.app.rss.refresh_seconds),
    (PhotosIntegration, settings.app.photos.rotation_seconds),
    (CalendarIntegration, 300),
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    cache.load_from_db()
    registered = {i.name for i in scheduler._integrations}
    for cls, interval in _INTEGRATIONS:
        name = cls.name  # type: ignore[attr-defined]
        if name not in registered:
            instance = cls(cache=cache, ws_manager=ws_manager, config=settings)
            scheduler.register(instance, interval_seconds=interval)

    await scheduler.start()
    logger.info("O-Deck backend online")
    yield
    scheduler.shutdown()
    logger.info("O-Deck backend shutdown complete")


app = FastAPI(title="O-Deck", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(make_router(pomodoro_state), prefix="/api/pomodoro")


@app.get("/api/state")
async def api_state() -> dict[str, Any]:
    return {
        "weather": cache.get("weather"),
        "transit": cache.get("transit"),
        "spotify": cache.get("spotify"),
        "github": cache.get("github"),
        "rss": cache.get("rss"),
        "photos": cache.get("photos"),
        "calendar": cache.get("calendar"),
        "pomodoro": pomodoro_state.get_status(),
    }


@app.get("/api/config")
async def api_config() -> dict[str, Any]:
    cfg = settings.app
    return {
        "device": cfg.device.model_dump(),
        "home": cfg.home.model_dump(),
        "pomodoro": {"presets": [p.model_dump() for p in cfg.pomodoro.presets]},
    }


@app.get("/api/status")
async def api_status() -> dict[str, Any]:
    return {
        "ws_clients": ws_manager.client_count,
        "integrations": [i.status for i in scheduler._integrations],
    }


@app.get("/api/photos/file/{filename}")
async def photos_file(filename: str) -> FileResponse:
    folder = Path(settings.app.photos.local_folder).expanduser()
    file_path = folder / filename
    if not file_path.exists() or not file_path.is_file():
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Photo not found")
    return FileResponse(str(file_path))


@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await ws_manager.connect(ws)
    logger.info("ws connect; clients=%d", ws_manager.client_count)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        await ws_manager.disconnect(ws)
        logger.info("ws disconnect; clients=%d", ws_manager.client_count)


_static_dir = Path(__file__).parent.parent.parent / "frontend" / "build"
if _static_dir.exists():
    app.mount("/", StaticFiles(directory=str(_static_dir), html=True), name="static")
```

- [ ] **Step 4: Run all tests**

```bash
pytest backend/tests/ -v
```

Expected: all tests pass.

- [ ] **Step 5: Smoke-test the server locally**

```bash
uvicorn cyberdeck.main:app --reload --host 0.0.0.0 --port 8080
# In another terminal:
curl http://localhost:8080/api/state | python3 -m json.tool
curl http://localhost:8080/api/pomodoro/status
```

Expected: JSON with all integration keys, pomodoro phase "idle".

- [ ] **Step 6: Commit**

```bash
git add backend/cyberdeck/main.py
git commit -m "feat(main): register all integrations + extend /api/state + pomodoro routes"
```

---

## Self-Review

**Spec coverage:**
- Transit: ✅ 4 stations (primary + secondary), alerts
- Calendar: ✅ Google + Notion join by event_link + title fallback
- Spotify: ✅ now playing, progress, paused state
- GitHub: ✅ commits, open PRs, assigned issues
- RSS: ✅ multi-feed, dedupe, ticker, headline stack
- Photos: ✅ local folder + iCloud shared album
- Pomodoro: ✅ REST controls, WS broadcast
- Error isolation: ✅ `Integration.run()` catches all exceptions (from Plan 1)
- Stale data: ✅ `fetched_at` in every CacheEntry (from Plan 1)
- `/api/state` extension: ✅ all integration keys

**Placeholder scan:** None found.

**Type consistency:**
- `SpotifyIntegration.fetch()` returns `is_playing: bool` — matches what frontend expects
- `TransitIntegration.fetch()` returns `stations: list, secondary: list, alerts: list` — consistent
- `_parse_google_event()` returns `notion: None` — `_join_events()` overwrites with dict or keeps None — consistent
- `PhotosIntegration.fetch()` returns `url: str | None` — consistent across local/icloud paths

---

## Parallelization Strategy

- **This plan** can run in parallel with Plan 3 (Frontend Foundation) — both depend only on Plan 1 which is done.
- Tasks within this plan are **sequential** (each integration is independent but the final wiring task depends on all of them).
- Recommended: one subagent, tasks 1–9 in order.

---

## New Chat Handoff Prompt

```
You are implementing the O-Deck cyberdeck backend integrations plan.

Repo: /Users/oliversantana/Documents/dev/cyberdeck
Worktree: .worktrees/backend-integrations  (branch: feature/backend-integrations, based on feature/backend-foundation)
Plan: docs/superpowers/plans/2026-04-26-backend-integrations.md

Context:
- Backend foundation is complete: FastAPI app, Cache, WSManager, IntegrationScheduler, WeatherIntegration, all with tests.
- You are adding: transit, calendar (Google+Notion), spotify, github, rss, photos integrations + pomodoro state + wiring into main.py.
- Use superpowers:subagent-driven-development to execute task-by-task with TDD.
- After each task: run pytest, fix failures, commit.
- Do NOT touch frontend/ — that is a separate plan.
- Run all tests before each commit: `pytest backend/tests/ -v`

Start with Task 1 (config — add mta_api_key).
```
