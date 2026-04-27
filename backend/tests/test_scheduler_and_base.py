from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from cyberdeck.integrations.base import Integration
from cyberdeck.scheduler import IntegrationScheduler


class DummyIntegration(Integration):
    name = "dummy"

    async def fetch(self) -> dict[str, int]:
        return {"value": 1}

    def event_name(self) -> str:
        return "dummy:update"


@pytest.mark.asyncio
async def test_integration_run_success_path_broadcasts_and_updates_status():
    cache = Mock()
    cache.set.return_value = True
    ws = SimpleNamespace(broadcast=AsyncMock())
    integration = DummyIntegration(cache=cache, ws_manager=ws, config=object())

    await integration.run()

    cache.set.assert_called_once_with("dummy", {"value": 1})
    ws.broadcast.assert_awaited_once_with("dummy:update", {"value": 1})
    assert integration.status["error_count"] == 0
    assert integration.status["last_success"] is not None


@pytest.mark.asyncio
async def test_integration_run_no_change_path_skips_broadcast():
    cache = Mock()
    cache.set.return_value = False
    ws = SimpleNamespace(broadcast=AsyncMock())
    integration = DummyIntegration(cache=cache, ws_manager=ws, config=object())

    await integration.run()

    cache.set.assert_called_once_with("dummy", {"value": 1})
    ws.broadcast.assert_not_awaited()


@pytest.mark.asyncio
async def test_integration_run_error_path_does_not_raise_and_tracks_errors():
    cache = Mock()
    ws = SimpleNamespace(broadcast=AsyncMock())
    integration = DummyIntegration(cache=cache, ws_manager=ws, config=object())
    integration.fetch = AsyncMock(side_effect=RuntimeError("boom"))  # type: ignore[method-assign]

    await integration.run()

    assert integration.status["error_count"] == 1
    assert integration.status["last_success"] is None


def test_scheduler_register_adds_integration_and_job():
    scheduler = IntegrationScheduler()
    integration = SimpleNamespace(name="weather", run=AsyncMock())

    scheduler.register(integration=integration, interval_seconds=30)

    assert integration in scheduler._integrations
    assert scheduler._scheduler.get_job("weather") is not None
    scheduler.shutdown()


@pytest.mark.asyncio
async def test_scheduler_start_runs_initial_gather_once():
    scheduler = IntegrationScheduler()
    integration = SimpleNamespace(name="weather", run=AsyncMock())
    scheduler.register(integration=integration, interval_seconds=30)

    try:
        await scheduler.start()
    finally:
        scheduler.shutdown()

    assert integration.run.await_count >= 1


def test_scheduler_shutdown_safe_when_not_running():
    scheduler = IntegrationScheduler()

    scheduler.shutdown()


class _BoomIntegration(Integration):
    name = "boom"

    def event_name(self) -> str:
        return "boom.update"

    async def fetch(self) -> dict:
        raise RuntimeError("kaboom: 401 unauthorized")


@pytest.mark.asyncio
async def test_integration_status_includes_last_error_after_failure():
    integration = _BoomIntegration(cache=Mock(), ws_manager=Mock(), config=Mock())

    await integration.run()

    status = integration.status
    assert status["error_count"] == 1
    assert status["last_error"] is not None
    assert "kaboom" in status["last_error"]
    assert "401" in status["last_error"]


@pytest.mark.asyncio
async def test_integration_status_clears_last_error_after_success():
    cache = Mock()
    cache.set = Mock(return_value=False)
    ws = Mock()
    ws.broadcast = AsyncMock()

    class _FlipFlop(Integration):
        name = "flipflop"
        calls = 0

        def event_name(self) -> str:
            return "flipflop.update"

        async def fetch(self) -> dict:
            _FlipFlop.calls += 1
            if _FlipFlop.calls == 1:
                raise RuntimeError("first call fails")
            return {"ok": True}

    integration = _FlipFlop(cache=cache, ws_manager=ws, config=Mock())

    await integration.run()
    assert integration.status["last_error"] is not None

    await integration.run()
    assert integration.status["last_error"] is None
    assert integration.status["error_count"] == 0
