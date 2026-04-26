from __future__ import annotations

import asyncio
import logging

from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from cyberdeck.integrations.base import Integration

logger = logging.getLogger(__name__)


class IntegrationScheduler:
    def __init__(self) -> None:
        self._scheduler = AsyncIOScheduler()
        self._integrations: list[Integration] = []

    def register(self, integration: Integration, interval_seconds: int) -> None:
        self._integrations.append(integration)
        self._scheduler.add_job(
            integration.run,
            trigger=IntervalTrigger(seconds=interval_seconds),
            id=integration.name,
            replace_existing=True,
            misfire_grace_time=30,
        )
        logger.info("registered integration %s every %ds", integration.name, interval_seconds)

    async def start(self) -> None:
        self._scheduler.start()
        logger.info("integration scheduler started with %d integrations", len(self._integrations))
        await asyncio.gather(*[integration.run() for integration in self._integrations])

    def shutdown(self) -> None:
        if self._scheduler.running:
            self._scheduler.shutdown(wait=False)
