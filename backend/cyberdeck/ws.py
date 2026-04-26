import asyncio
import json
from typing import Any

from fastapi import WebSocket


class WSManager:
    def __init__(self) -> None:
        self._clients: set[WebSocket] = set()
        self._lock = asyncio.Lock()

    @property
    def client_count(self) -> int:
        return len(self._clients)

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        async with self._lock:
            self._clients.add(ws)

    async def disconnect(self, ws: WebSocket) -> None:
        async with self._lock:
            self._clients.discard(ws)

    async def broadcast(self, event: str, data: Any) -> None:
        message = json.dumps({"event": event, "data": data})

        async with self._lock:
            clients = list(self._clients)

        dead_clients: list[WebSocket] = []
        for client in clients:
            try:
                await client.send_text(message)
            except Exception:
                dead_clients.append(client)

        if dead_clients:
            async with self._lock:
                for client in dead_clients:
                    self._clients.discard(client)
