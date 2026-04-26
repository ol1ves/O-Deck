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
from cyberdeck.config import load_config
from cyberdeck.integrations.weather import WeatherIntegration
from cyberdeck.scheduler import IntegrationScheduler
from cyberdeck.ws import WSManager

logging.basicConfig(
    level=logging.INFO,
    format='{"t":"%(asctime)s","lvl":"%(levelname)s","name":"%(name)s","msg":%(message)r}',
)
logger = logging.getLogger("cyberdeck")


settings = load_config()
cache = Cache()
ws_manager = WSManager()
scheduler = IntegrationScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    cache.load_from_db()
    existing_integration_names = {integration.name for integration in scheduler._integrations}
    if "weather" not in existing_integration_names:
        weather = WeatherIntegration(cache=cache, ws_manager=ws_manager, config=settings)
        scheduler.register(weather, interval_seconds=600)

    await scheduler.start()
    logger.info("O-Deck backend online")
    yield
    scheduler.shutdown()
    logger.info("O-Deck backend shutdown complete")


app = FastAPI(title="O-Deck", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/state")
async def api_state() -> dict[str, Any]:
    """Full cached state for frontend initial hydration."""
    return {
        "weather": cache.get("weather"),
    }


@app.get("/api/config")
async def api_config() -> dict[str, Any]:
    """Safe (no secrets) device + home config subset."""
    cfg = settings.app
    return {
        "device": cfg.device.model_dump(),
        "home": cfg.home.model_dump(),
    }


@app.get("/api/status")
async def api_status() -> dict[str, Any]:
    """Diagnostics: WS client count + integration statuses."""
    return {
        "ws_clients": ws_manager.client_count,
        "integrations": [i.status for i in scheduler._integrations],
    }


@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await ws_manager.connect(ws)
    logger.info("ws connect; clients=%d", ws_manager.client_count)
    try:
        while True:
            await ws.receive_text()  # keep-alive; client sends pings
    except WebSocketDisconnect:
        pass
    finally:
        await ws_manager.disconnect(ws)
        logger.info("ws disconnect; clients=%d", ws_manager.client_count)


_static_dir = Path(__file__).parent.parent.parent / "frontend" / "build"
if _static_dir.exists():
    app.mount("/", StaticFiles(directory=str(_static_dir), html=True), name="static")
