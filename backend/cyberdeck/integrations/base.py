from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any

from cyberdeck.cache import Cache
from cyberdeck.config import Settings
from cyberdeck.ws import WSManager

logger = logging.getLogger(__name__)


class Integration(ABC):
    name: str

    def __init__(self, cache: Cache, ws_manager: WSManager, config: Settings) -> None:
        self.cache = cache
        self.ws_manager = ws_manager
        self.config = config
        self.error_count = 0
        self.last_success: datetime | None = None

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
                await self.ws_manager.broadcast(self.event_name(), data)
            self.error_count = 0
            self.last_success = datetime.now(timezone.utc)
        except Exception:
            self.error_count += 1
            logger.exception("integration run failed: %s", self.name, exc_info=True)

    @property
    def status(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "error_count": self.error_count,
            "last_success": self.last_success,
        }
