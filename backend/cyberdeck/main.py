from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.websockets import WebSocketDisconnect

from cyberdeck.cache import Cache
from cyberdeck.config import Settings, load_config
from cyberdeck.integrations.base import Integration
from cyberdeck.scheduler import IntegrationScheduler
from cyberdeck.ws import WSManager

APP_VERSION = "0.1.0"


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format=(
            "%(asctime)s level=%(levelname)s logger=%(name)s "
            "event=%(message)s"
        ),
    )


setup_logging()
logger = logging.getLogger(__name__)


class WeatherIntegration(Integration):
    name = "weather"

    async def fetch(self) -> dict[str, Any]:
        location = self.config.app.device.location
        return {
            "provider": self.config.app.weather.provider,
            "lat": location.lat,
            "lon": location.lon,
            "conditions": "unknown",
            "temperature_f": None,
        }

    def event_name(self) -> str:
        return "weather:update"


settings = load_config()
cache = Cache()
ws_manager = WSManager()
scheduler = IntegrationScheduler()


@asynccontextmanager
async def lifespan(_: FastAPI):
    logger.info("starting application lifespan")
    cache.load_from_db()
    scheduler.register(WeatherIntegration(cache, ws_manager, settings), interval_seconds=600)
    await scheduler.start()
    try:
        yield
    finally:
        scheduler.shutdown()
        logger.info("stopped application lifespan")


app = FastAPI(
    title="Cyberdeck API",
    version=APP_VERSION,
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/state")
async def get_state() -> dict[str, Any]:
    return {"weather": cache.get("weather")}


@app.get("/api/config")
async def get_config() -> dict[str, Any]:
    return {
        "device": settings.app.device.model_dump(),
        "home": settings.app.home.model_dump(),
    }


@app.get("/api/status")
async def get_status() -> dict[str, Any]:
    integrations = [integration.status for integration in getattr(scheduler, "_integrations", [])]
    return {"ws_clients": ws_manager.client_count, "integrations": integrations}


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket) -> None:
    await ws_manager.connect(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        logger.info("websocket disconnected")
    finally:
        await ws_manager.disconnect(ws)


frontend_build = Path(__file__).resolve().parents[2] / "frontend" / "build"
if frontend_build.exists():
    app.mount("/", StaticFiles(directory=str(frontend_build), html=True), name="frontend")
