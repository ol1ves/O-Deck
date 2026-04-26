from __future__ import annotations

from typing import Any

import httpx

from cyberdeck.integrations.base import Integration

_OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

# WMO Weather Interpretation Code -> human-readable label
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

        current = _required_mapping(raw, "current")
        daily = _required_mapping(raw, "daily")
        hourly_data = _required_mapping(raw, "hourly")
        hourly_temps = _required_value(hourly_data, "temperature_2m", "hourly.temperature_2m")

        temp_c = _required_value(current, "temperature_2m", "current.temperature_2m")
        feels_c = _required_value(current, "apparent_temperature", "current.apparent_temperature")
        code_raw = _required_value(current, "weather_code", "current.weather_code")
        try:
            code = int(code_raw)
        except (TypeError, ValueError) as exc:
            raise ValueError("Invalid weather payload: invalid 'current.weather_code'") from exc

        high_c = _required_first(daily, "temperature_2m_max", "daily.temperature_2m_max")
        low_c = _required_first(daily, "temperature_2m_min", "daily.temperature_2m_min")


        hourly = [{"h": str(i), "t": _c_to_f(t)} for i, t in enumerate(hourly_temps[:6])]

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


def _required_mapping(payload: dict[str, Any], key: str) -> dict[str, Any]:
    value = payload.get(key)
    if value is None:
        raise ValueError(f"Invalid weather payload: missing '{key}'")
    if not isinstance(value, dict):
        raise ValueError(f"Invalid weather payload: invalid '{key}'")
    return value


def _required_value(mapping: dict[str, Any], key: str, path: str) -> Any:
    if key not in mapping:
        raise ValueError(f"Invalid weather payload: missing '{path}'")
    return mapping[key]


def _required_first(mapping: dict[str, Any], key: str, path: str) -> Any:
    value = _required_value(mapping, key, path)
    if not isinstance(value, list) or not value:
        raise ValueError(f"Invalid weather payload: missing '{path}[0]'")
    return value[0]
