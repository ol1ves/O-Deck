import asyncio
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
async def test_broadcast_reraises_unexpected_send_exceptions():
    manager = WSManager()
    ws = AsyncMock()
    ws.send_text.side_effect = ValueError("unexpected send error")
    await manager.connect(ws)

    with pytest.raises(ValueError, match="unexpected send error"):
        await manager.broadcast("ping", {"ok": True})


@pytest.mark.asyncio
async def test_broadcast_safe_during_concurrent_disconnect_and_connect():
    manager = WSManager()
    stable = AsyncMock()
    leaving = AsyncMock()
    joining = AsyncMock()

    gate = asyncio.Event()

    async def delayed_send_text(message: str) -> None:
        await gate.wait()
        return None

    stable.send_text.side_effect = delayed_send_text
    leaving.send_text.side_effect = delayed_send_text

    await manager.connect(stable)
    await manager.connect(leaving)

    payload = {"ok": True}
    expected = json.dumps({"event": "tick", "data": payload})
    broadcast_task = asyncio.create_task(manager.broadcast("tick", payload))

    await asyncio.sleep(0)
    await manager.disconnect(leaving)
    await manager.connect(joining)
    gate.set()
    await broadcast_task

    stable.send_text.assert_awaited_once_with(expected)
    leaving.send_text.assert_awaited_once_with(expected)
    assert joining.send_text.await_count == 0
    assert manager.client_count == 2


@pytest.mark.asyncio
async def test_concurrent_broadcasts_deliver_sane_counts():
    manager = WSManager()
    ws1 = AsyncMock()
    ws2 = AsyncMock()
    await manager.connect(ws1)
    await manager.connect(ws2)

    await asyncio.gather(
        manager.broadcast("a", {"n": 1}),
        manager.broadcast("b", {"n": 2}),
    )

    assert ws1.send_text.await_count == 2
    assert ws2.send_text.await_count == 2
    delivered_ws1 = [json.loads(call.args[0])["event"] for call in ws1.send_text.await_args_list]
    delivered_ws2 = [json.loads(call.args[0])["event"] for call in ws2.send_text.await_args_list]
    assert sorted(delivered_ws1) == ["a", "b"]
    assert sorted(delivered_ws2) == ["a", "b"]
    assert manager.client_count == 2


@pytest.mark.asyncio
async def test_broadcast_empty_manager_is_safe():
    manager = WSManager()

    await manager.broadcast("noop", {"x": 1})

    assert manager.client_count == 0
