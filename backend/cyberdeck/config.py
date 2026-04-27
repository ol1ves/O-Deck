from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

CONFIG_DIR = Path.home() / ".config" / "cyberdeck"
CONFIG_PATH = CONFIG_DIR / "config.yaml"
ENV_PATH = CONFIG_DIR / ".env"


class Resolution(BaseModel):
    width: int = 800
    height: int = 480


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


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    google_calendar_credentials_path: Path | None = None
    google_calendar_token_path: Path | None = None
    notion_token: str | None = None
    spotify_client_id: str | None = None
    spotify_client_secret: str | None = None
    spotify_refresh_token: str | None = None
    github_token: str | None = None
    mta_api_key: str | None = None

    app: AppConfig = Field(default_factory=AppConfig)


def load_config(
    config_path: Path = CONFIG_PATH,
    env_path: Path = ENV_PATH,
) -> Settings:
    raw: dict[str, Any] = {}
    if config_path.exists():
        with open(config_path) as f:
            raw = yaml.safe_load(f) or {}

    app = AppConfig.model_validate(raw)

    class _S(Settings):
        model_config = SettingsConfigDict(
            env_file=str(env_path),
            env_file_encoding="utf-8",
            extra="ignore",
        )

    return _S(app=app)
