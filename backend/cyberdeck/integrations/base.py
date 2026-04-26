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
    name: str

    def __init__(self, cache: Cache, ws_manager: WSManager, config: Settings) -> None:
        self.cache = cache
        self.ws = ws_manager
        self.config = config
        self._error_count = 0
        self._last_success: float | None = None

    @abstractmethod
    async def fetch(self) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def event_name(self) -> str:
        raise NotImplementedError

    async def run(self) -> None:
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
