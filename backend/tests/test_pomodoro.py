import asyncio
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
    manager = MagicMock()
    manager.broadcast = AsyncMock()
    return manager


@pytest.fixture
def state(ws):
    return PomodoroState(ws_manager=ws)


@pytest.fixture
def client(state):
    app = FastAPI()
    app.include_router(make_router(state), prefix="/api/pomodoro")
    return TestClient(app)


def test_initial_state_is_idle(state):
    status = state.get_status()
    assert status["running"] is False
    assert status["phase"] == "idle"


def test_start_sets_running(state):
    state.start(PRESET_CLASSIC)
    status = state.get_status()
    assert status["running"] is True
    assert status["phase"] == "work"
    assert status["work_min"] == 25


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
    state._started_at -= 60
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


@pytest.mark.asyncio
async def test_state_changes_broadcast_ws_event(state, ws):
    state.start(PRESET_CLASSIC)
    await asyncio.sleep(0)

    ws.broadcast.assert_awaited()
    event, payload = ws.broadcast.await_args.args
    assert event == "pomodoro.update"
    assert payload["phase"] == "work"
