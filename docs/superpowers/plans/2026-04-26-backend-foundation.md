# O-Deck Backend Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up a fully-working FastAPI backend with config, cache, WebSocket pub/sub, APScheduler, and a live weather integration — the foundation every other integration and the frontend depends on.

**Architecture:** FastAPI app with a lifespan context that registers integrations into APScheduler; each integration polls an external API, writes to a SQLite-backed in-memory cache, and broadcasts change events over WebSocket. The frontend (not built yet) will connect on `/ws` and call `/api/state` for initial hydration.

**Tech Stack:** Python 3.11+, FastAPI, uvicorn, APScheduler (asyncio), pydantic v2, pydantic-settings, PyYAML, httpx, respx (test mocking), pytest-asyncio

---

## Plan Series

This is **Plan 1 of 5**:
1. **Backend Foundation** ← you are here
2. Backend Integrations (transit, calendar, spotify, github, rss, photos) → `2026-04-26-backend-integrations.md`
3. Frontend Foundation (SvelteKit, tokens, primitives, home screen) → `2026-04-26-frontend-foundation.md`
4. Fullscreen Apps → `2026-04-26-fullscreen-apps.md`
5. Install & Ops → `2026-04-26-install-ops.md`

---

## File Map

Files created in this plan:

```
cyberdeck/
├── pyproject.toml
├── package.json                           # stub for SvelteKit (Plan 3)
├── config.example.yaml
├── .env.example
└── backend/
    ├── cyberdeck/
    │   ├── __init__.py
    │   ├── main.py                        # FastAPI app + lifespan + REST + /ws
    │   ├── config.py                      # Pydantic config loader (YAML + .env)
    │   ├── cache.py                       # SQLite-backed in-memory cache
    │   ├── scheduler.py                   # APScheduler wrapper
    │   ├── ws.py                          # WebSocket pub/sub manager
    │   └── integrations/
    │       ├── __init__.py
    │       ├── base.py                    # Integration ABC
    │       └── weather.py                 # Open-Meteo weather integration
    └── tests/
        ├── conftest.py                    # (empty — fixtures per-file)
        ├── test_config.py
        ├── test_cache.py
        ├── test_ws.py
        └── integrations/
            ├── __init__.py
            └── test_weather.py
```

---

### Task 1: Repo scaffold

**Files:**
- Create: `pyproject.toml`
- Create: `package.json`
- Create: `config.example.yaml`
- Create: `.env.example`
- Create: `backend/cyberdeck/__init__.py` (empty)
- Create: `backend/cyberdeck/integrations/__init__.py` (empty)
- Create: `backend/tests/conftest.py` (empty)
- Create: `backend/tests/integrations/__init__.py` (empty)

- [ ] **Step 1: Create directory structure**

```bash
mkdir -p backend/cyberdeck/integrations backend/tests/integrations
touch backend/cyberdeck/__init__.py
touch backend/cyberdeck/integrations/__init__.py
touch backend/tests/conftest.py
touch backend/tests/integrations/__init__.py
```

- [ ] **Step 2: Create `pyproject.toml`**

```toml
[project]
name = "cyberdeck"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.110.0",
    "uvicorn[standard]>=0.29.0",
    "httpx>=0.27.0",
    "apscheduler>=3.10.4",
    "pydantic>=2.7.0",
    "pydantic-settings>=2.2.0",
    "pyyaml>=6.0.1",
    "feedparser>=6.0.11",
    "gtfs-realtime-bindings>=1.0.0",
    "google-api-python-client>=2.128.0",
    "google-auth-httplib2>=0.2.0",
    "google-auth-oauthlib>=1.2.0",
    "gcsa>=2.3.0",
    "notion-client>=2.2.1",
    "spotipy>=2.23.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.1.0",
    "pytest-asyncio>=0.23.0",
    "respx>=0.21.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["backend/cyberdeck"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["backend/tests"]
```

- [ ] **Step 3: Create `package.json` (stub)**

```json
{
  "name": "cyberdeck-frontend",
  "private": true,
  "version": "0.0.1",
  "scripts": {
    "dev": "vite dev",
    "build": "vite build",
    "preview": "vite preview"
  }
}
```

- [ ] **Step 4: Create `config.example.yaml`**

```yaml
device:
  name: "O-Deck"
  resolution:
    width: 1024
    height: 600
  timezone: "America/New_York"
  location:
    lat: 40.6926
    lon: -73.9869

home:
  layout: "default"
  hero_tiles: ["now_playing"]
  core_tiles: ["time", "weather", "transit", "calendar", "rss"]

audio:
  enabled: true
  master_volume: 0.6
  chimes:
    pomodoro: true
    weather_alert: true

weather:
  provider: "open-meteo"
  alerts:
    rain: true
    snow: true
    heat_spike_threshold_f: 90
    cold_drop_threshold_f: 25
    severe: true

transit:
  refresh_seconds: 30
  primary_stations:
    - station: "Jay St-MetroTech"
      stop_id: "A41N"
      lines: ["A", "C", "F", "R"]
    - station: "DeKalb Av"
      stop_id: "R30N"
      lines: ["Q"]
  secondary_stations:
    - station: "14 St-Union Sq"
      stop_id: "635S"
      lines: ["4", "5", "6", "R", "Q"]
    - station: "W 4 St-Wash Sq"
      stop_id: "A32S"
      lines: ["F", "A", "C"]
  show_alerts: true

calendar:
  google:
    calendar_ids: ["primary"]
  notion:
    todo_database_ids: []
    join_strategy: "event_link"
  view: "today_at_a_glance"

spotify:
  enabled: true

github:
  username: "<your-github-username>"
  show: ["recent_commits", "open_prs", "assigned_issues"]

rss:
  refresh_seconds: 600
  feeds:
    - name: "TLDR"
      url: "https://kill-the-newsletter.com/feeds/<your-id>.xml"
    - name: "Hacker News"
      url: "https://news.ycombinator.com/rss"
  ticker:
    enabled: true
    speed: "medium"
  headline_stack_size: 3

photos:
  source: "icloud_shared_album"
  icloud_share_url: "https://www.icloud.com/sharedalbum/#..."
  local_folder: "~/cyberdeck-photos"
  rotation_seconds: 30

pomodoro:
  presets:
    - name: "Classic"
      work_min: 25
      break_min: 5
      cycles: 4
      long_break_min: 15
    - name: "Deep"
      work_min: 50
      break_min: 10
      cycles: 3
      long_break_min: 20

doomscroll:
  sources: ["rss"]
  qr_open_on_phone: true

showcase:
  default_mode: "generative"
  music_reactive_when_playing: true
```

- [ ] **Step 5: Create `.env.example`**

```
GOOGLE_CALENDAR_CREDENTIALS_PATH=/home/pi/.config/cyberdeck/google-credentials.json
GOOGLE_CALENDAR_TOKEN_PATH=/home/pi/.config/cyberdeck/google-token.json
NOTION_TOKEN=secret_xxx
SPOTIFY_CLIENT_ID=xxx
SPOTIFY_CLIENT_SECRET=xxx
SPOTIFY_REFRESH_TOKEN=xxx
GITHUB_TOKEN=ghp_xxx
```

- [ ] **Step 6: Create venv and install deps**

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install uv
uv pip install -e ".[dev]"
```

Expected: packages install cleanly. Last line: `Successfully installed cyberdeck-0.1.0 ...`

- [ ] **Step 7: Verify import works**

```bash
python -c "import cyberdeck; print('ok')"
```

Expected: `ok`

- [ ] **Step 8: Commit**

```bash
git add pyproject.toml package.json config.example.yaml .env.example backend/
git commit -m "chore: repo scaffold — dirs, pyproject.toml, config templates"
```

---

### Task 2: Config system

**Files:**
- Create: `backend/cyberdeck/config.py`
- Create: `backend/tests/test_config.py`

- [ ] **Step 1: Write `backend/tests/test_config.py`**

```python
import tempfile
from pathlib import Path

import yaml
import pytest

from cyberdeck.config import AppConfig, load_config


def test_app_config_has_sane_defaults():
    cfg = AppConfig.model_validate({})
    assert cfg.device.resolution.width == 1024
    assert cfg.device.resolution.height == 600
    assert cfg.device.timezone == "America/New_York"
    assert cfg.weather.provider == "open-meteo"
    assert cfg.transit.refresh_seconds == 30
    assert cfg.home.hero_tiles == ["now_playing"]


def test_app_config_overrides_from_dict():
    raw = {
        "device": {"name": "Test-Deck", "resolution": {"width": 800, "height": 480}},
        "weather": {"alerts": {"rain": False}},
    }
    cfg = AppConfig.model_validate(raw)
    assert cfg.device.name == "Test-Deck"
    assert cfg.device.resolution.width == 800
    assert cfg.weather.alerts.rain is False
    assert cfg.weather.alerts.snow is True  # unchanged default


def test_load_config_reads_yaml_file(tmp_path):
    data = {
        "device": {"name": "Pi-Test", "timezone": "America/Chicago"},
        "transit": {"refresh_seconds": 60},
    }
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text(yaml.dump(data))
    env_file = tmp_path / ".env"
    env_file.write_text("")

    settings = load_config(config_path=cfg_file, env_path=env_file)

    assert settings.app.device.name == "Pi-Test"
    assert settings.app.device.timezone == "America/Chicago"
    assert settings.app.transit.refresh_seconds == 60
    assert settings.app.device.resolution.width == 1024  # default preserved


def test_load_config_works_when_yaml_missing(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("")

    settings = load_config(config_path=tmp_path / "nonexistent.yaml", env_path=env_file)

    assert settings.app.device.name == "O-Deck"


def test_station_config_validates():
    raw = {
        "transit": {
            "primary_stations": [
                {"station": "Jay St", "stop_id": "A41N", "lines": ["A", "C", "F"]}
            ]
        }
    }
    cfg = AppConfig.model_validate(raw)
    assert len(cfg.transit.primary_stations) == 1
    st = cfg.transit.primary_stations[0]
    assert st.stop_id == "A41N"
    assert "A" in st.lines


def test_load_config_reads_env_secrets(tmp_path):
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text("")
    env_file = tmp_path / ".env"
    env_file.write_text("GITHUB_TOKEN=ghp_abc123\n")

    settings = load_config(config_path=cfg_file, env_path=env_file)

    assert settings.github_token == "ghp_abc123"
```

- [ ] **Step 2: Run test, verify it fails**

```bash
pytest backend/tests/test_config.py -v
```

Expected: `ModuleNotFoundError: No module named 'cyberdeck.config'`

- [ ] **Step 3: Write `backend/cyberdeck/config.py`**

```python
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

CONFIG_DIR = Path.home() / ".config" / "cyberdeck"
CONFIG_PATH = CONFIG_DIR / "config.yaml"
ENV_PATH = CONFIG_DIR / ".env"


# ── Sub-models ───────────────────────────────────────────────────

class Resolution(BaseModel):
    width: int = 1024
    height: int = 600


class Location(BaseModel):
    lat: float = 40.6926
    lon: float = -73.9869


class DeviceConfig(BaseModel):
    name: str = "O-Deck"
    resolution: Resolution = Field(default_factory=Resolution)
    timezone: str = "America/New_York"
    location: Location = Field(default_factory=Location)


class HomeConfig(BaseModel):
    layout: str = "default"
    hero_tiles: list[str] = Field(default_factory=lambda: ["now_playing"])
    core_tiles: list[str] = Field(
        default_factory=lambda: ["time", "weather", "transit", "calendar", "rss"]
    )


class AudioChimes(BaseModel):
    pomodoro: bool = True
    weather_alert: bool = True


class AudioConfig(BaseModel):
    enabled: bool = True
    master_volume: float = 0.6
    chimes: AudioChimes = Field(default_factory=AudioChimes)


class WeatherAlerts(BaseModel):
    rain: bool = True
    snow: bool = True
    heat_spike_threshold_f: float = 90.0
    cold_drop_threshold_f: float = 25.0
    severe: bool = True


class WeatherConfig(BaseModel):
    provider: str = "open-meteo"
    alerts: WeatherAlerts = Field(default_factory=WeatherAlerts)


class StationConfig(BaseModel):
    station: str
    stop_id: str
    lines: list[str]


class TransitConfig(BaseModel):
    refresh_seconds: int = 30
    primary_stations: list[StationConfig] = Field(default_factory=list)
    secondary_stations: list[StationConfig] = Field(default_factory=list)
    show_alerts: bool = True


class GoogleCalendarConfig(BaseModel):
    calendar_ids: list[str] = Field(default_factory=lambda: ["primary"])


class NotionCalendarConfig(BaseModel):
    todo_database_ids: list[str] = Field(default_factory=list)
    join_strategy: str = "event_link"


class CalendarConfig(BaseModel):
    google: GoogleCalendarConfig = Field(default_factory=GoogleCalendarConfig)
    notion: NotionCalendarConfig = Field(default_factory=NotionCalendarConfig)
    view: str = "today_at_a_glance"


class SpotifyConfig(BaseModel):
    enabled: bool = True


class GitHubConfig(BaseModel):
    username: str = ""
    show: list[str] = Field(
        default_factory=lambda: ["recent_commits", "open_prs", "assigned_issues"]
    )


class RSSTicker(BaseModel):
    enabled: bool = True
    speed: str = "medium"


class RSSFeedConfig(BaseModel):
    name: str
    url: str


class RSSConfig(BaseModel):
    refresh_seconds: int = 600
    feeds: list[RSSFeedConfig] = Field(default_factory=list)
    ticker: RSSTicker = Field(default_factory=RSSTicker)
    headline_stack_size: int = 3


class PhotosConfig(BaseModel):
    source: str = "icloud_shared_album"
    icloud_share_url: str = ""
    local_folder: str = "~/cyberdeck-photos"
    rotation_seconds: int = 30


class PomodoroPreset(BaseModel):
    name: str
    work_min: int
    break_min: int
    cycles: int
    long_break_min: int


class PomodoroConfig(BaseModel):
    presets: list[PomodoroPreset] = Field(
        default_factory=lambda: [
            PomodoroPreset(
                name="Classic", work_min=25, break_min=5, cycles=4, long_break_min=15
            )
        ]
    )


class DoomscrollConfig(BaseModel):
    sources: list[str] = Field(default_factory=lambda: ["rss"])
    qr_open_on_phone: bool = True


class ShowcaseConfig(BaseModel):
    default_mode: str = "generative"
    music_reactive_when_playing: bool = True


class AppConfig(BaseModel):
    device: DeviceConfig = Field(default_factory=DeviceConfig)
    home: HomeConfig = Field(default_factory=HomeConfig)
    audio: AudioConfig = Field(default_factory=AudioConfig)
    weather: WeatherConfig = Field(default_factory=WeatherConfig)
    transit: TransitConfig = Field(default_factory=TransitConfig)
    calendar: CalendarConfig = Field(default_factory=CalendarConfig)
    spotify: SpotifyConfig = Field(default_factory=SpotifyConfig)
    github: GitHubConfig = Field(default_factory=GitHubConfig)
    rss: RSSConfig = Field(default_factory=RSSConfig)
    photos: PhotosConfig = Field(default_factory=PhotosConfig)
    pomodoro: PomodoroConfig = Field(default_factory=PomodoroConfig)
    doomscroll: DoomscrollConfig = Field(default_factory=DoomscrollConfig)
    showcase: ShowcaseConfig = Field(default_factory=ShowcaseConfig)


# ── Settings (YAML app config + .env secrets) ────────────────────

class Settings(BaseSettings):
    """Secrets from .env; app config injected after YAML parse."""

    model_config = SettingsConfigDict(extra="ignore")

    google_calendar_credentials_path: Path | None = None
    google_calendar_token_path: Path | None = None
    notion_token: str | None = None
    spotify_client_id: str | None = None
    spotify_client_secret: str | None = None
    spotify_refresh_token: str | None = None
    github_token: str | None = None

    app: AppConfig = Field(default_factory=AppConfig)


def load_config(
    config_path: Path = CONFIG_PATH,
    env_path: Path = ENV_PATH,
) -> Settings:
    """Load config.yaml into AppConfig, merge with .env secrets."""
    raw: dict[str, Any] = {}
    if config_path.exists():
        with open(config_path) as f:
            raw = yaml.safe_load(f) or {}

    app = AppConfig.model_validate(raw)

    # Subclass to inject env_file at construction time (pydantic-settings pattern)
    class _S(Settings):
        model_config = SettingsConfigDict(
            env_file=str(env_path),
            env_file_encoding="utf-8",
            extra="ignore",
        )

    return _S(app=app)
```

- [ ] **Step 4: Run tests, verify they pass**

```bash
pytest backend/tests/test_config.py -v
```

Expected:
```
PASSED test_app_config_has_sane_defaults
PASSED test_app_config_overrides_from_dict
PASSED test_load_config_reads_yaml_file
PASSED test_load_config_works_when_yaml_missing
PASSED test_station_config_validates
PASSED test_load_config_reads_env_secrets
6 passed
```

- [ ] **Step 5: Commit**

```bash
git add backend/cyberdeck/config.py backend/tests/test_config.py
git commit -m "feat: pydantic config system with YAML + .env loading"
```

---

### Task 3: Cache layer

**Files:**
- Create: `backend/cyberdeck/cache.py`
- Create: `backend/tests/test_cache.py`

- [ ] **Step 1: Write `backend/tests/test_cache.py`**

```python
import time
import pytest

from cyberdeck.cache import Cache


@pytest.fixture
def cache(tmp_path):
    return Cache(db_path=tmp_path / "test.db")


def test_get_missing_key_returns_none(cache):
    assert cache.get("missing") is None


def test_set_and_get_roundtrip(cache):
    cache.set("weather", {"tempF": 58.0, "cond": "Partly cloudy"})
    result = cache.get("weather")
    assert result["tempF"] == 58.0
    assert result["cond"] == "Partly cloudy"


def test_set_returns_true_on_new_key(cache):
    assert cache.set("k", {"v": 1}) is True


def test_set_returns_false_when_value_unchanged(cache):
    cache.set("k", {"v": 1})
    assert cache.set("k", {"v": 1}) is False


def test_set_returns_true_when_value_changes(cache):
    cache.set("k", {"v": 1})
    assert cache.set("k", {"v": 2}) is True


def test_get_entry_has_fetched_at_timestamp(cache):
    before = time.time()
    cache.set("k", {"v": 1})
    entry = cache.get_entry("k")
    assert entry is not None
    assert entry.fetched_at >= before


def test_value_persists_across_cache_instances(tmp_path):
    db = tmp_path / "shared.db"
    c1 = Cache(db_path=db)
    c1.set("weather", {"tempF": 72.0})

    c2 = Cache(db_path=db)
    c2.load_from_db()

    assert c2.get("weather") == {"tempF": 72.0}


def test_load_from_db_restores_timestamp(tmp_path):
    db = tmp_path / "ts.db"
    c1 = Cache(db_path=db)
    c1.set("k", {"v": 1})
    original_ts = c1.get_entry("k").fetched_at

    c2 = Cache(db_path=db)
    c2.load_from_db()

    assert c2.get_entry("k").fetched_at == pytest.approx(original_ts, abs=0.001)
```

- [ ] **Step 2: Run test, verify it fails**

```bash
pytest backend/tests/test_cache.py -v
```

Expected: `ModuleNotFoundError: No module named 'cyberdeck.cache'`

- [ ] **Step 3: Write `backend/cyberdeck/cache.py`**

```python
from __future__ import annotations

import json
import sqlite3
import time
from dataclasses import dataclass, field
from pathlib import Path
from threading import Lock
from typing import Any

DEFAULT_DB = Path.home() / ".config" / "cyberdeck" / "cache.db"


@dataclass
class CacheEntry:
    payload: Any
    fetched_at: float = field(default_factory=time.time)


class Cache:
    def __init__(self, db_path: Path = DEFAULT_DB) -> None:
        self._db_path = db_path
        self._mem: dict[str, CacheEntry] = {}
        self._lock = Lock()
        self._init_db()

    def _init_db(self) -> None:
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                """CREATE TABLE IF NOT EXISTS cache (
                    key TEXT PRIMARY KEY,
                    payload TEXT NOT NULL,
                    fetched_at REAL NOT NULL
                )"""
            )
            conn.commit()

    def get(self, key: str) -> Any | None:
        with self._lock:
            entry = self._mem.get(key)
            return entry.payload if entry else None

    def get_entry(self, key: str) -> CacheEntry | None:
        with self._lock:
            return self._mem.get(key)

    def set(self, key: str, payload: Any) -> bool:
        """Persist payload. Returns True if value changed, False if identical."""
        serialized = json.dumps(payload, sort_keys=True, default=str)
        with self._lock:
            existing = self._mem.get(key)
            if existing is not None:
                if json.dumps(existing.payload, sort_keys=True, default=str) == serialized:
                    return False
            entry = CacheEntry(payload=payload)
            self._mem[key] = entry
        self._persist(key, serialized, entry.fetched_at)
        return True

    def _persist(self, key: str, serialized: str, fetched_at: float) -> None:
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO cache (key, payload, fetched_at) VALUES (?,?,?)",
                (key, serialized, fetched_at),
            )
            conn.commit()

    def load_from_db(self) -> None:
        """Restore in-memory state from SQLite on process start."""
        with self._lock:
            with sqlite3.connect(self._db_path) as conn:
                for key, payload_str, fetched_at in conn.execute(
                    "SELECT key, payload, fetched_at FROM cache"
                ):
                    self._mem[key] = CacheEntry(
                        payload=json.loads(payload_str),
                        fetched_at=fetched_at,
                    )
```

- [ ] **Step 4: Run tests, verify they pass**

```bash
pytest backend/tests/test_cache.py -v
```

Expected: `8 passed`

- [ ] **Step 5: Commit**

```bash
git add backend/cyberdeck/cache.py backend/tests/test_cache.py
git commit -m "feat: SQLite-backed in-memory cache with change detection"
```

---

### Task 4: WebSocket pub/sub manager

**Files:**
- Create: `backend/cyberdeck/ws.py`
- Create: `backend/tests/test_ws.py`

- [ ] **Step 1: Write `backend/tests/test_ws.py`**

```python
import json
import pytest
from unittest.mock import AsyncMock

from cyberdeck.ws import WSManager


@pytest.fixture
def manager():
    return WSManager()


def make_ws():
    ws = AsyncMock()
    ws.send_text = AsyncMock()
    return ws


@pytest.mark.asyncio
async def test_connect_accepts_websocket(manager):
    ws = make_ws()
    await manager.connect(ws)
    ws.accept.assert_called_once()
    assert manager.client_count == 1


@pytest.mark.asyncio
async def test_disconnect_removes_client(manager):
    ws = make_ws()
    await manager.connect(ws)
    await manager.disconnect(ws)
    assert manager.client_count == 0


@pytest.mark.asyncio
async def test_disconnect_unknown_client_is_safe(manager):
    ws = make_ws()
    await manager.disconnect(ws)  # no error raised
    assert manager.client_count == 0


@pytest.mark.asyncio
async def test_broadcast_sends_typed_event_to_all_clients(manager):
    ws1 = make_ws()
    ws2 = make_ws()
    await manager.connect(ws1)
    await manager.connect(ws2)

    await manager.broadcast("weather.update", {"tempF": 58})

    ws1.send_text.assert_called_once()
    ws2.send_text.assert_called_once()
    msg = json.loads(ws1.send_text.call_args[0][0])
    assert msg["event"] == "weather.update"
    assert msg["data"]["tempF"] == 58


@pytest.mark.asyncio
async def test_broadcast_removes_dead_client(manager):
    ws = make_ws()
    ws.send_text.side_effect = RuntimeError("connection closed")
    await manager.connect(ws)

    await manager.broadcast("test.event", {})

    assert manager.client_count == 0


@pytest.mark.asyncio
async def test_broadcast_to_empty_manager_is_safe(manager):
    await manager.broadcast("test.event", {"x": 1})  # no error
```

- [ ] **Step 2: Run test, verify it fails**

```bash
pytest backend/tests/test_ws.py -v
```

Expected: `ModuleNotFoundError: No module named 'cyberdeck.ws'`

- [ ] **Step 3: Write `backend/cyberdeck/ws.py`**

```python
from __future__ import annotations

import asyncio
import json
from typing import Any

from fastapi import WebSocket


class WSManager:
    """Fan-out WebSocket pub/sub for the asyncio event loop."""

    def __init__(self) -> None:
        self._clients: set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        async with self._lock:
            self._clients.add(ws)

    async def disconnect(self, ws: WebSocket) -> None:
        async with self._lock:
            self._clients.discard(ws)

    async def broadcast(self, event: str, data: dict[str, Any]) -> None:
        message = json.dumps({"event": event, "data": data})
        async with self._lock:
            dead: set[WebSocket] = set()
            for ws in self._clients:
                try:
                    await ws.send_text(message)
                except Exception:
                    dead.add(ws)
            self._clients -= dead

    @property
    def client_count(self) -> int:
        return len(self._clients)
```

- [ ] **Step 4: Run tests, verify they pass**

```bash
pytest backend/tests/test_ws.py -v
```

Expected: `6 passed`

- [ ] **Step 5: Commit**

```bash
git add backend/cyberdeck/ws.py backend/tests/test_ws.py
git commit -m "feat: WebSocket pub/sub manager with dead-client cleanup"
```

---

### Task 5: Integration ABC + scheduler

**Files:**
- Create: `backend/cyberdeck/integrations/base.py`
- Create: `backend/cyberdeck/scheduler.py`

These have no isolated unit tests — both are tested end-to-end via the weather integration in Task 7.

- [ ] **Step 1: Write `backend/cyberdeck/integrations/base.py`**

```python
from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from cyberdeck.cache import Cache
    from cyberdeck.config import Settings
    from cyberdeck.ws import WSManager

logger = logging.getLogger(__name__)


class Integration(ABC):
    """Base class for all O-Deck data integrations.

    Subclasses define:
      name: str            — cache key and log label
      event_name() -> str  — WebSocket event emitted on data change
      fetch() -> dict      — pull fresh data; raise on unrecoverable error
    """

    name: str  # set as a class attribute in each subclass

    def __init__(
        self,
        cache: "Cache",
        ws_manager: "WSManager",
        config: "Settings",
    ) -> None:
        self.cache = cache
        self.ws = ws_manager
        self.config = config
        self._error_count = 0
        self._last_success: float | None = None

    @abstractmethod
    async def fetch(self) -> dict[str, Any]:
        """Fetch fresh data from external source. Raise on failure."""
        ...

    @abstractmethod
    def event_name(self) -> str:
        """WebSocket event type, e.g. 'weather.update'."""
        ...

    async def run(self) -> None:
        """One poll cycle: fetch → cache → broadcast if changed."""
        try:
            data = await self.fetch()
            changed = self.cache.set(self.name, data)
            if changed:
                await self.ws.broadcast(self.event_name(), data)
            self._error_count = 0
            self._last_success = time.time()
        except Exception as exc:
            self._error_count += 1
            logger.error(
                "integration %s failed (error #%d): %s",
                self.name,
                self._error_count,
                exc,
                exc_info=True,
            )

    @property
    def status(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "error_count": self._error_count,
            "last_success": self._last_success,
        }
```

- [ ] **Step 2: Write `backend/cyberdeck/scheduler.py`**

```python
from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

if TYPE_CHECKING:
    from cyberdeck.integrations.base import Integration

logger = logging.getLogger(__name__)


class IntegrationScheduler:
    """Thin wrapper around APScheduler (asyncio) for integration polling."""

    def __init__(self) -> None:
        self._scheduler = AsyncIOScheduler()
        self._integrations: list[Integration] = []

    def register(self, integration: "Integration", interval_seconds: int) -> None:
        self._integrations.append(integration)
        self._scheduler.add_job(
            integration.run,
            trigger=IntervalTrigger(seconds=interval_seconds),
            id=integration.name,
            replace_existing=True,
            misfire_grace_time=30,
        )
        logger.info(
            "registered integration %s every %ds", integration.name, interval_seconds
        )

    async def start(self) -> None:
        """Start scheduler then run all integrations immediately once."""
        self._scheduler.start()
        logger.info("scheduler started with %d integrations", len(self._integrations))
        await asyncio.gather(*[i.run() for i in self._integrations])

    def shutdown(self) -> None:
        if self._scheduler.running:
            self._scheduler.shutdown(wait=False)
```

- [ ] **Step 3: Verify imports are clean**

```bash
python -c "
from cyberdeck.integrations.base import Integration
from cyberdeck.scheduler import IntegrationScheduler
print('ok')
"
```

Expected: `ok`

- [ ] **Step 4: Commit**

```bash
git add backend/cyberdeck/integrations/base.py backend/cyberdeck/scheduler.py
git commit -m "feat: integration ABC and APScheduler wrapper"
```

---

### Task 6: FastAPI app

**Files:**
- Create: `backend/cyberdeck/main.py`

No isolated unit tests — tested via the E2E smoke test in Task 8.

- [ ] **Step 1: Write `backend/cyberdeck/main.py`**

```python
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from cyberdeck.cache import Cache
from cyberdeck.config import load_config
from cyberdeck.integrations.weather import WeatherIntegration
from cyberdeck.scheduler import IntegrationScheduler
from cyberdeck.ws import WSManager

logging.basicConfig(
    level=logging.INFO,
    format='{"t":"%(asctime)s","lvl":"%(levelname)s","name":"%(name)s","msg":%(message)r}',
)
logger = logging.getLogger("cyberdeck")

# Module-level singletons (one per process)
settings = load_config()
cache = Cache()
ws_manager = WSManager()
scheduler = IntegrationScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    cache.load_from_db()

    weather = WeatherIntegration(cache=cache, ws_manager=ws_manager, config=settings)
    scheduler.register(weather, interval_seconds=600)

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


@app.get("/api/state")
async def api_state() -> dict[str, Any]:
    """Full cached state for frontend initial hydration."""
    return {
        "weather": cache.get("weather"),
    }


@app.get("/api/config")
async def api_config() -> dict[str, Any]:
    """Safe (no secrets) device + home config subset."""
    cfg = settings.app
    return {
        "device": cfg.device.model_dump(),
        "home": cfg.home.model_dump(),
    }


@app.get("/api/status")
async def api_status() -> dict[str, Any]:
    """Diagnostics: WS client count + integration statuses."""
    return {
        "ws_clients": ws_manager.client_count,
        "integrations": [i.status for i in scheduler._integrations],
    }


@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await ws_manager.connect(ws)
    logger.info("ws connect; clients=%d", ws_manager.client_count)
    try:
        while True:
            await ws.receive_text()  # keep-alive; client sends pings
    except WebSocketDisconnect:
        pass
    finally:
        await ws_manager.disconnect(ws)
        logger.info("ws disconnect; clients=%d", ws_manager.client_count)


# Serve SvelteKit static build when present (Plan 3)
_static_dir = Path(__file__).parent.parent.parent / "frontend" / "build"
if _static_dir.exists():
    app.mount("/", StaticFiles(directory=str(_static_dir), html=True), name="static")
```

- [ ] **Step 2: Verify import is clean**

```bash
python -c "from cyberdeck.main import app; print('app ok')"
```

Expected: `app ok` (may emit a config-not-found log line — not an error)

- [ ] **Step 3: Commit**

```bash
git add backend/cyberdeck/main.py
git commit -m "feat: FastAPI app with lifespan, REST routes, and WebSocket endpoint"
```

---

### Task 7: Weather integration

**Files:**
- Create: `backend/cyberdeck/integrations/weather.py`
- Create: `backend/tests/integrations/test_weather.py`

- [ ] **Step 1: Write `backend/tests/integrations/test_weather.py`**

```python
import httpx
import pytest
import respx
from unittest.mock import AsyncMock, MagicMock

from cyberdeck.cache import Cache
from cyberdeck.integrations.weather import WeatherIntegration, _c_to_f, _wmo_desc
from cyberdeck.ws import WSManager


# Minimal valid Open-Meteo response (recorded 2026-04-26)
OPEN_METEO_FIXTURE = {
    "current": {
        "temperature_2m": 14.2,
        "apparent_temperature": 12.0,
        "weather_code": 2,
    },
    "daily": {
        "temperature_2m_max": [17.5],
        "temperature_2m_min": [9.1],
    },
    "hourly": {
        "temperature_2m": [10.0, 11.0, 12.0, 13.0, 14.0, 15.0, 14.5, 13.0],
    },
}

METEO_URL = "https://api.open-meteo.com/v1/forecast"


def make_config(
    lat=40.6926,
    lon=-73.9869,
    rain=True,
    snow=True,
    severe=True,
    heat=90.0,
    cold=25.0,
):
    cfg = MagicMock()
    cfg.app.device.location.lat = lat
    cfg.app.device.location.lon = lon
    cfg.app.weather.alerts.rain = rain
    cfg.app.weather.alerts.snow = snow
    cfg.app.weather.alerts.severe = severe
    cfg.app.weather.alerts.heat_spike_threshold_f = heat
    cfg.app.weather.alerts.cold_drop_threshold_f = cold
    return cfg


def make_integration(config=None, cache=None, ws=None):
    return WeatherIntegration(
        cache=cache or MagicMock(),
        ws_manager=ws or MagicMock(),
        config=config or make_config(),
    )


# ── Unit tests (no network) ───────────────────────────────────────

def test_c_to_f_freezing():
    assert _c_to_f(0) == 32.0


def test_c_to_f_boiling():
    assert _c_to_f(100) == 212.0


def test_c_to_f_body_temp():
    assert _c_to_f(37) == pytest.approx(98.6, abs=0.1)


def test_wmo_desc_known_codes():
    assert _wmo_desc(2) == "Partly cloudy"
    assert _wmo_desc(95) == "Thunderstorm"
    assert _wmo_desc(0) == "Clear sky"


def test_wmo_desc_unknown_code():
    assert _wmo_desc(999) == "WMO 999"


# ── Integration tests (mocked HTTP) ──────────────────────────────

@pytest.mark.asyncio
@respx.mock
async def test_fetch_converts_to_fahrenheit():
    respx.get(METEO_URL).mock(return_value=httpx.Response(200, json=OPEN_METEO_FIXTURE))

    result = await make_integration().fetch()

    assert result["tempF"] == pytest.approx(_c_to_f(14.2), abs=0.01)
    assert result["highF"] == pytest.approx(_c_to_f(17.5), abs=0.01)
    assert result["lowF"] == pytest.approx(_c_to_f(9.1), abs=0.01)
    assert result["feelsLikeF"] == pytest.approx(_c_to_f(12.0), abs=0.01)


@pytest.mark.asyncio
@respx.mock
async def test_fetch_includes_condition_string():
    respx.get(METEO_URL).mock(return_value=httpx.Response(200, json=OPEN_METEO_FIXTURE))

    result = await make_integration().fetch()

    assert result["cond"] == "Partly cloudy"


@pytest.mark.asyncio
@respx.mock
async def test_fetch_returns_six_hourly_points():
    respx.get(METEO_URL).mock(return_value=httpx.Response(200, json=OPEN_METEO_FIXTURE))

    result = await make_integration().fetch()

    assert len(result["hourly"]) == 6
    assert all("h" in pt and "t" in pt for pt in result["hourly"])


@pytest.mark.asyncio
@respx.mock
async def test_fetch_no_alerts_for_clear_sky():
    fixture = {**OPEN_METEO_FIXTURE, "current": {**OPEN_METEO_FIXTURE["current"], "weather_code": 0}}
    respx.get(METEO_URL).mock(return_value=httpx.Response(200, json=fixture))

    result = await make_integration().fetch()

    assert result["alerts"] == []


@pytest.mark.asyncio
@respx.mock
async def test_fetch_generates_thunder_alert():
    fixture = {**OPEN_METEO_FIXTURE, "current": {**OPEN_METEO_FIXTURE["current"], "weather_code": 95}}
    respx.get(METEO_URL).mock(return_value=httpx.Response(200, json=fixture))

    result = await make_integration().fetch()

    assert any(a["type"] == "thunder" for a in result["alerts"])


@pytest.mark.asyncio
@respx.mock
async def test_fetch_generates_rain_alert():
    fixture = {**OPEN_METEO_FIXTURE, "current": {**OPEN_METEO_FIXTURE["current"], "weather_code": 63}}
    respx.get(METEO_URL).mock(return_value=httpx.Response(200, json=fixture))

    result = await make_integration().fetch()

    assert any(a["type"] == "rain" for a in result["alerts"])


@pytest.mark.asyncio
@respx.mock
async def test_fetch_generates_heat_alert():
    # 35°C = 95°F, above default threshold of 90°F
    fixture = {
        **OPEN_METEO_FIXTURE,
        "current": {**OPEN_METEO_FIXTURE["current"], "temperature_2m": 35.0, "weather_code": 0},
    }
    respx.get(METEO_URL).mock(return_value=httpx.Response(200, json=fixture))

    result = await make_integration().fetch()

    assert any(a["type"] == "heat" for a in result["alerts"])


@pytest.mark.asyncio
@respx.mock
async def test_run_writes_to_cache(tmp_path):
    respx.get(METEO_URL).mock(return_value=httpx.Response(200, json=OPEN_METEO_FIXTURE))

    cache = Cache(db_path=tmp_path / "c.db")
    ws = WSManager()
    integration = WeatherIntegration(cache=cache, ws_manager=ws, config=make_config())

    await integration.run()

    assert cache.get("weather") is not None
    assert cache.get("weather")["cond"] == "Partly cloudy"


@pytest.mark.asyncio
@respx.mock
async def test_run_broadcasts_only_on_change(tmp_path):
    respx.get(METEO_URL).mock(return_value=httpx.Response(200, json=OPEN_METEO_FIXTURE))

    cache = Cache(db_path=tmp_path / "c.db")
    ws = MagicMock()
    ws.broadcast = AsyncMock()
    integration = WeatherIntegration(cache=cache, ws_manager=ws, config=make_config())

    await integration.run()   # first run — data changes → broadcast
    await integration.run()   # second run — same data → no broadcast

    assert ws.broadcast.call_count == 1


@pytest.mark.asyncio
@respx.mock
async def test_run_swallows_http_error_and_increments_error_count():
    respx.get(METEO_URL).mock(return_value=httpx.Response(503))

    integration = make_integration()
    await integration.run()  # must not raise

    assert integration.status["error_count"] == 1
```

- [ ] **Step 2: Run test, verify it fails**

```bash
pytest backend/tests/integrations/test_weather.py -v
```

Expected: `ModuleNotFoundError: No module named 'cyberdeck.integrations.weather'`

- [ ] **Step 3: Write `backend/cyberdeck/integrations/weather.py`**

```python
from __future__ import annotations

from typing import Any

import httpx

from cyberdeck.integrations.base import Integration

_OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

# WMO Weather Interpretation Code → human-readable label
_WMO: dict[int, str] = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Foggy",
    48: "Icy fog",
    51: "Light drizzle",
    53: "Drizzle",
    55: "Heavy drizzle",
    61: "Slight rain",
    63: "Rain",
    65: "Heavy rain",
    71: "Slight snow",
    73: "Snow",
    75: "Heavy snow",
    80: "Slight showers",
    81: "Showers",
    82: "Heavy showers",
    95: "Thunderstorm",
    96: "Thunderstorm + hail",
    99: "Thunderstorm + heavy hail",
}

_RAIN_CODES: frozenset[int] = frozenset({51, 53, 55, 61, 63, 65, 80, 81, 82})
_SNOW_CODES: frozenset[int] = frozenset({71, 73, 75})
_THUNDER_CODES: frozenset[int] = frozenset({95, 96, 99})


def _wmo_desc(code: int) -> str:
    return _WMO.get(code, f"WMO {code}")


def _c_to_f(c: float) -> float:
    return round(c * 9 / 5 + 32, 1)


class WeatherIntegration(Integration):
    name = "weather"

    def event_name(self) -> str:
        return "weather.update"

    async def fetch(self) -> dict[str, Any]:
        loc = self.config.app.device.location
        params = {
            "latitude": loc.lat,
            "longitude": loc.lon,
            "current": "temperature_2m,apparent_temperature,weather_code",
            "daily": "temperature_2m_max,temperature_2m_min",
            "hourly": "temperature_2m",
            "temperature_unit": "celsius",
            "timezone": "auto",
            "forecast_days": "1",
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(_OPEN_METEO_URL, params=params)
            resp.raise_for_status()
            raw = resp.json()

        current = raw["current"]
        daily = raw["daily"]
        hourly_temps = raw["hourly"]["temperature_2m"]

        temp_c = current["temperature_2m"]
        feels_c = current["apparent_temperature"]
        code = int(current["weather_code"])
        high_c = daily["temperature_2m_max"][0]
        low_c = daily["temperature_2m_min"][0]

        hourly = [
            {"h": str(i), "t": _c_to_f(t)}
            for i, t in enumerate(hourly_temps[:6])
        ]

        alerts_cfg = self.config.app.weather.alerts
        alerts: list[dict[str, str]] = []

        if code in _RAIN_CODES and alerts_cfg.rain:
            alerts.append({"type": "rain", "label": "Rain expected"})
        if code in _SNOW_CODES and alerts_cfg.snow:
            alerts.append({"type": "snow", "label": "Snow expected"})
        if code in _THUNDER_CODES and alerts_cfg.severe:
            alerts.append({"type": "thunder", "label": "Thunderstorm"})

        temp_f = _c_to_f(temp_c)
        if temp_f >= alerts_cfg.heat_spike_threshold_f:
            alerts.append({"type": "heat", "label": f"Heat spike · {temp_f}°F"})
        if temp_f <= alerts_cfg.cold_drop_threshold_f:
            alerts.append({"type": "cold", "label": f"Cold drop · {temp_f}°F"})

        return {
            "tempF": temp_f,
            "feelsLikeF": _c_to_f(feels_c),
            "highF": _c_to_f(high_c),
            "lowF": _c_to_f(low_c),
            "cond": _wmo_desc(code),
            "code": code,
            "hourly": hourly,
            "alerts": alerts,
        }
```

- [ ] **Step 4: Run weather tests, verify they pass**

```bash
pytest backend/tests/integrations/test_weather.py -v
```

Expected: `13 passed`

- [ ] **Step 5: Run full suite**

```bash
pytest backend/tests/ -v
```

Expected: `33 passed` (6 config + 8 cache + 6 ws + 13 weather)

- [ ] **Step 6: Commit**

```bash
git add backend/cyberdeck/integrations/weather.py backend/tests/integrations/test_weather.py
git commit -m "feat: weather integration (open-meteo) with F conversion and WMO alert logic"
```

---

### Task 8: E2E smoke test

No new files. Verify the full data flow end-to-end.

- [ ] **Step 1: Start the dev server**

```bash
uvicorn cyberdeck.main:app --reload --port 8080
```

Expected startup output (JSON lines to stderr):
```
{"t":"...","lvl":"INFO","name":"apscheduler.scheduler","msg":"Scheduler started"}
{"t":"...","lvl":"INFO","name":"cyberdeck","msg":"O-Deck backend online"}
```

Within ~2 seconds, a weather fetch log should appear.

- [ ] **Step 2: Verify `/api/state` returns live weather**

In a second terminal (with venv active):

```bash
curl -s http://localhost:8080/api/state | python -m json.tool
```

Expected shape (values reflect live Brooklyn weather):

```json
{
    "weather": {
        "tempF": 58.0,
        "feelsLikeF": 55.0,
        "highF": 64.0,
        "lowF": 49.0,
        "cond": "Partly cloudy",
        "code": 2,
        "hourly": [
            {"h": "0", "t": 52.0},
            {"h": "1", "t": 53.0},
            {"h": "2", "t": 55.0},
            {"h": "3", "t": 57.0},
            {"h": "4", "t": 58.0},
            {"h": "5", "t": 57.0}
        ],
        "alerts": []
    }
}
```

- [ ] **Step 3: Verify `/api/config` returns device config**

```bash
curl -s http://localhost:8080/api/config | python -m json.tool
```

Expected:

```json
{
    "device": {
        "name": "O-Deck",
        "resolution": {"width": 1024, "height": 600},
        "timezone": "America/New_York",
        "location": {"lat": 40.6926, "lon": -73.9869}
    },
    "home": {
        "layout": "default",
        "hero_tiles": ["now_playing"],
        "core_tiles": ["time", "weather", "transit", "calendar", "rss"]
    }
}
```

- [ ] **Step 4: Verify `/api/status`**

```bash
curl -s http://localhost:8080/api/status | python -m json.tool
```

Expected:

```json
{
    "ws_clients": 0,
    "integrations": [
        {
            "name": "weather",
            "error_count": 0,
            "last_success": 1745699000.0
        }
    ]
}
```

`last_success` is a Unix timestamp. `error_count: 0` confirms the live fetch worked.

- [ ] **Step 5: Verify WebSocket delivers events**

Install wscat if needed: `npm install -g wscat`

```bash
wscat -c ws://localhost:8080/ws
```

In the server terminal, `CTRL+C` the server and restart it. Within ~2 seconds of reconnect, you will see:

```json
{"event":"weather.update","data":{"tempF":58.0,"cond":"Partly cloudy",...}}
```

- [ ] **Step 6: Stop server and commit**

```bash
git commit --allow-empty -m "chore: E2E smoke test passed — backend foundation complete"
```

---

## Self-Review

**Spec coverage:**

| Requirement | Task |
|---|---|
| FastAPI backend — REST + WebSocket | Task 6 `main.py` |
| APScheduler per-integration polling | Task 5 `scheduler.py` |
| In-memory + SQLite cache | Task 3 `cache.py` |
| Cache survives frontend reload | Task 3 `load_from_db()` called in lifespan |
| WebSocket typed events `{"event":…,"data":…}` | Task 4 `ws.py` |
| Per-integration failure isolation (no crash) | Task 5 `base.py run()` catches all exceptions |
| Staleness metadata (`fetched_at`) | Task 3 `CacheEntry.fetched_at` |
| Broadcast only on data change | Task 3 `set()` returns bool; Task 5 `run()` checks it |
| Config from `config.yaml` + `.env` | Task 2 `config.py` |
| Pydantic validates loudly on bad config | Task 2 — model_validate raises `ValidationError` |
| Weather integration (Open-Meteo, no auth) | Task 7 `weather.py` |
| °F conversion | Task 7 `_c_to_f()` |
| Weather alert badges (rain/snow/heat/cold/severe) | Task 7 `fetch()` alert logic |
| Structured JSON logging | Task 6 `logging.basicConfig` |
| Backend reachable at `http://<pi-ip>:8080` | Task 8 — uvicorn binds `0.0.0.0` by default |
| `config.example.yaml` template committed | Task 1 |
| `.env.example` template committed | Task 1 |

**Not in this plan (Plan 2):** transit, calendar, spotify, github, rss, photos integrations — all use the same `Integration` ABC + scheduler established here.

**Placeholder scan:** No TBD/TODO/placeholder text found.

**Type consistency:** `AppConfig.device.location` is a `Location` model with `.lat`/`.lon` attributes. `WeatherIntegration.fetch()` accesses `self.config.app.device.location.lat` — consistent. Test `make_config()` sets `cfg.app.device.location.lat` on a MagicMock — consistent.
