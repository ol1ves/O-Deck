import json
from unittest.mock import AsyncMock

import pytest

from cyberdeck.ws import WSManager


@pytest.mark.asyncio
async def test_connect_accepts_websocket_and_increments_client_count():
    manager = WSManager()
    ws = AsyncMock()

    await manager.connect(ws)

    ws.accept.assert_awaited_once()
    assert manager.client_count == 1


@pytest.mark.asyncio
async def test_disconnect_removes_client():
    manager = WSManager()
    ws = AsyncMock()
    await manager.connect(ws)

    await manager.disconnect(ws)

    assert manager.client_count == 0


@pytest.mark.asyncio
async def test_disconnect_unknown_client_is_safe():
    manager = WSManager()
    ws = AsyncMock()

    await manager.disconnect(ws)

    assert manager.client_count == 0


@pytest.mark.asyncio
async def test_broadcast_sends_typed_event_json_to_all_clients():
    manager = WSManager()
    ws1 = AsyncMock()
    ws2 = AsyncMock()
    await manager.connect(ws1)
    await manager.connect(ws2)

    payload = {"temp": 72, "unit": "F"}
    await manager.broadcast("weather:update", payload)

    expected = json.dumps({"event": "weather:update", "data": payload})
    ws1.send_text.assert_awaited_once_with(expected)
    ws2.send_text.assert_awaited_once_with(expected)
    assert manager.client_count == 2


@pytest.mark.asyncio
async def test_broadcast_removes_dead_client_on_send_failure():
    manager = WSManager()
    alive = AsyncMock()
    dead = AsyncMock()
    dead.send_text.side_effect = RuntimeError("socket closed")
    await manager.connect(alive)
    await manager.connect(dead)

    await manager.broadcast("ping", {"ok": True})

    assert manager.client_count == 1
    assert alive.send_text.await_count == 1


@pytest.mark.asyncio
async def test_broadcast_empty_manager_is_safe():
    manager = WSManager()

    await manager.broadcast("noop", {"x": 1})

    assert manager.client_count == 0
