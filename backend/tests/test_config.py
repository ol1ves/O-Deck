import tempfile
from pathlib import Path

import pytest
import yaml

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


def test_settings_accepts_mta_api_key(monkeypatch):
    monkeypatch.setenv("MTA_API_KEY", "test-key")

    from cyberdeck.config import Settings

    settings = Settings()

    assert settings.mta_api_key == "test-key"
