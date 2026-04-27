from __future__ import annotations

import asyncio
import time
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter
from pydantic import BaseModel

if TYPE_CHECKING:
    from cyberdeck.ws import WSManager


class PresetIn(BaseModel):
    name: str
    work_min: int
    break_min: int
    cycles: int
    long_break_min: int


class PomodoroState:
    def __init__(self, ws_manager: "WSManager") -> None:
        self._ws = ws_manager
        self._running = False
        self._phase = "idle"
        self._work_min = 25
        self._break_min = 5
        self._long_break_min = 15
        self._cycles = 4
        self._cycle = 0
        self._preset_name = ""
        self._started_at: float | None = None
        self._paused_remaining: float | None = None

    def _phase_total_seconds(self) -> float:
        if self._phase == "work":
            return self._work_min * 60
        if self._phase == "break":
            return self._break_min * 60
        if self._phase == "long_break":
            return self._long_break_min * 60
        return 0.0

    def get_status(self) -> dict[str, Any]:
        if self._phase == "idle" or self._started_at is None:
            remaining = 0.0
        elif not self._running and self._paused_remaining is not None:
            remaining = self._paused_remaining
        else:
            elapsed = time.time() - self._started_at
            remaining = max(0.0, self._phase_total_seconds() - elapsed)

        return {
            "running": self._running,
            "phase": self._phase,
            "remaining_seconds": round(remaining),
            "cycle": self._cycle,
            "cycles_total": self._cycles,
            "work_min": self._work_min,
            "break_min": self._break_min,
            "long_break_min": self._long_break_min,
            "preset_name": self._preset_name,
        }

    def start(self, preset: dict[str, Any] | PresetIn) -> None:
        if isinstance(preset, PresetIn):
            preset = preset.model_dump()
        self._work_min = preset["work_min"]
        self._break_min = preset["break_min"]
        self._long_break_min = preset["long_break_min"]
        self._cycles = preset["cycles"]
        self._preset_name = preset["name"]
        self._phase = "work"
        self._cycle = 1
        self._running = True
        self._started_at = time.time()
        self._paused_remaining = None
        self._schedule_broadcast()

    def pause(self) -> None:
        if not self._running:
            return
        self._paused_remaining = max(
            0.0,
            self._phase_total_seconds() - (time.time() - (self._started_at or time.time())),
        )
        self._running = False
        self._schedule_broadcast()

    def resume(self) -> None:
        if self._running or self._phase == "idle":
            return
        remaining = self._paused_remaining or self._phase_total_seconds()
        self._started_at = time.time() - (self._phase_total_seconds() - remaining)
        self._paused_remaining = None
        self._running = True
        self._schedule_broadcast()

    def stop(self) -> None:
        self._running = False
        self._phase = "idle"
        self._started_at = None
        self._paused_remaining = None
        self._schedule_broadcast()

    def _schedule_broadcast(self) -> None:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return
        loop.create_task(self._broadcast())

    async def _broadcast(self) -> None:
        await self._ws.broadcast("pomodoro.update", self.get_status())


def make_router(state: PomodoroState) -> APIRouter:
    router = APIRouter()

    @router.post("/start")
    async def start(preset: PresetIn) -> dict[str, Any]:
        state.start(preset)
        return state.get_status()

    @router.post("/pause")
    async def pause() -> dict[str, Any]:
        state.pause()
        return state.get_status()

    @router.post("/resume")
    async def resume() -> dict[str, Any]:
        state.resume()
        return state.get_status()

    @router.post("/stop")
    async def stop() -> dict[str, Any]:
        state.stop()
        return state.get_status()

    @router.get("/status")
    async def status() -> dict[str, Any]:
        return state.get_status()

    return router
