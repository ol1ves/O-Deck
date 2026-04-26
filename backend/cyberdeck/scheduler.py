from __future__ import annotations

import asyncio

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from cyberdeck.integrations.base import Integration


class IntegrationScheduler:
    def __init__(self) -> None:
        self.scheduler = AsyncIOScheduler()
        self.integrations: list[Integration] = []

    def register(self, integration: Integration, interval_seconds: int) -> None:
        self.integrations.append(integration)
        self.scheduler.add_job(
            integration.run,
            trigger="interval",
            seconds=interval_seconds,
            id=integration.name,
            replace_existing=True,
            misfire_grace_time=30,
        )

    async def start(self) -> None:
        if not self.scheduler.running:
            self.scheduler.start()
        await asyncio.gather(*(integration.run() for integration in self.integrations))

    async def shutdown(self) -> None:
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
