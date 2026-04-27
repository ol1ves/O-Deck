import httpx
import pytest
import respx
import re
from unittest.mock import AsyncMock, MagicMock
from urllib.parse import parse_qs, urlparse

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


# -- Unit tests (no network) ---------------------------------------


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


# -- Integration tests (mocked HTTP) --------------------------------


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
    # 35C = 95F, above default threshold of 90F
    fixture = {
        **OPEN_METEO_FIXTURE,
        "current": {**OPEN_METEO_FIXTURE["current"], "temperature_2m": 35.0, "weather_code": 0},
    }
    respx.get(METEO_URL).mock(return_value=httpx.Response(200, json=fixture))

    result = await make_integration().fetch()

    assert any(a["type"] == "heat" for a in result["alerts"])


@pytest.mark.asyncio
@respx.mock
async def test_fetch_generates_snow_alert():
    fixture = {**OPEN_METEO_FIXTURE, "current": {**OPEN_METEO_FIXTURE["current"], "weather_code": 73}}
    respx.get(METEO_URL).mock(return_value=httpx.Response(200, json=fixture))

    result = await make_integration().fetch()

    assert any(a["type"] == "snow" for a in result["alerts"])


@pytest.mark.asyncio
@respx.mock
async def test_fetch_generates_cold_alert():
    # -5C = 23F, below default threshold of 25F
    fixture = {
        **OPEN_METEO_FIXTURE,
        "current": {**OPEN_METEO_FIXTURE["current"], "temperature_2m": -5.0, "weather_code": 0},
    }
    respx.get(METEO_URL).mock(return_value=httpx.Response(200, json=fixture))

    result = await make_integration().fetch()

    assert any(a["type"] == "cold" for a in result["alerts"])


@pytest.mark.asyncio
@respx.mock
async def test_fetch_suppresses_thunder_when_severe_disabled():
    fixture = {**OPEN_METEO_FIXTURE, "current": {**OPEN_METEO_FIXTURE["current"], "weather_code": 95}}
    respx.get(METEO_URL).mock(return_value=httpx.Response(200, json=fixture))

    result = await make_integration(config=make_config(severe=False)).fetch()

    assert not any(a["type"] == "thunder" for a in result["alerts"])


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("fixture", "expected_path"),
    [
        ({k: v for k, v in OPEN_METEO_FIXTURE.items() if k != "current"}, "current"),
        ({k: v for k, v in OPEN_METEO_FIXTURE.items() if k != "daily"}, "daily"),
        ({**OPEN_METEO_FIXTURE, "hourly": {}}, "hourly.temperature_2m"),
        (
            {**OPEN_METEO_FIXTURE, "daily": {**OPEN_METEO_FIXTURE["daily"], "temperature_2m_max": []}},
            "daily.temperature_2m_max[0]",
        ),
        (
            {**OPEN_METEO_FIXTURE, "daily": {**OPEN_METEO_FIXTURE["daily"], "temperature_2m_min": []}},
            "daily.temperature_2m_min[0]",
        ),
    ],
)
@respx.mock
async def test_fetch_raises_value_error_on_missing_payload_fields(fixture, expected_path):
    respx.get(METEO_URL).mock(return_value=httpx.Response(200, json=fixture))

    with pytest.raises(ValueError, match=re.escape(expected_path)):
        await make_integration().fetch()


@pytest.mark.asyncio
@respx.mock
async def test_fetch_raises_value_error_on_non_list_hourly_temperature():
    fixture = {**OPEN_METEO_FIXTURE, "hourly": {"temperature_2m": 10.0}}
    respx.get(METEO_URL).mock(return_value=httpx.Response(200, json=fixture))

    with pytest.raises(ValueError, match=re.escape("hourly.temperature_2m")):
        await make_integration().fetch()


@pytest.mark.asyncio
@respx.mock
async def test_fetch_raises_value_error_on_non_numeric_current_temperature():
    fixture = {**OPEN_METEO_FIXTURE, "current": {**OPEN_METEO_FIXTURE["current"], "temperature_2m": "warm"}}
    respx.get(METEO_URL).mock(return_value=httpx.Response(200, json=fixture))

    with pytest.raises(ValueError, match=re.escape("current.temperature_2m")):
        await make_integration().fetch()


@pytest.mark.asyncio
@respx.mock
async def test_fetch_raises_value_error_on_non_numeric_hourly_temperature_value():
    fixture = {
        **OPEN_METEO_FIXTURE,
        "hourly": {"temperature_2m": [10.0, "bad", 12.0, 13.0, 14.0, 15.0]},
    }
    respx.get(METEO_URL).mock(return_value=httpx.Response(200, json=fixture))

    with pytest.raises(ValueError, match=re.escape("hourly.temperature_2m[1]")):
        await make_integration().fetch()


@pytest.mark.asyncio
@respx.mock
async def test_fetch_requests_required_query_fields():
    route = respx.get(METEO_URL).mock(return_value=httpx.Response(200, json=OPEN_METEO_FIXTURE))

    await make_integration().fetch()

    assert route.called
    request = route.calls[0].request
    query = parse_qs(urlparse(str(request.url)).query)
    assert query["current"] == ["temperature_2m,apparent_temperature,weather_code"]
    assert query["daily"] == ["temperature_2m_max,temperature_2m_min"]
    assert query["hourly"] == ["temperature_2m"]


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

    await integration.run()  # first run - data changes -> broadcast
    await integration.run()  # second run - same data -> no broadcast

    assert ws.broadcast.call_count == 1


@pytest.mark.asyncio
@respx.mock
async def test_run_swallows_http_error_and_increments_error_count():
    respx.get(METEO_URL).mock(return_value=httpx.Response(503))

    integration = make_integration()
    await integration.run()  # must not raise

    assert integration.status["error_count"] == 1
