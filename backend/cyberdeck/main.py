from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.websockets import WebSocketDisconnect

from cyberdeck.cache import Cache
from cyberdeck.config import load_config
from cyberdeck.integrations.calendar import CalendarIntegration
from cyberdeck.integrations.github import GitHubIntegration
from cyberdeck.integrations.photos import PhotosIntegration
from cyberdeck.integrations.rss import RSSIntegration
from cyberdeck.integrations.spotify import SpotifyIntegration
from cyberdeck.integrations.transit import TransitIntegration
from cyberdeck.integrations.weather import WeatherIntegration
from cyberdeck.pomodoro import PomodoroState, make_router
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
pomodoro_state = PomodoroState(ws_manager=ws_manager)

_INTEGRATIONS: list[tuple[type, int]] = [
    (WeatherIntegration, 600),
    (TransitIntegration, settings.app.transit.refresh_seconds),
    (SpotifyIntegration, 5),
    (GitHubIntegration, 300),
    (RSSIntegration, settings.app.rss.refresh_seconds),
    (PhotosIntegration, settings.app.photos.rotation_seconds),
    (CalendarIntegration, 300),
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    cache.load_from_db()
    existing_integration_names = {integration.name for integration in scheduler._integrations}
    for integration_cls, interval_seconds in _INTEGRATIONS:
        if integration_cls.name in existing_integration_names:
            continue
        integration = integration_cls(cache=cache, ws_manager=ws_manager, config=settings)
        scheduler.register(integration, interval_seconds=interval_seconds)

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
app.include_router(make_router(pomodoro_state), prefix="/api/pomodoro")


@app.get("/api/state")
async def api_state() -> dict[str, Any]:
    """Full cached state for frontend initial hydration."""
    return {
        "weather": cache.get("weather"),
        "transit": cache.get("transit"),
        "spotify": cache.get("spotify"),
        "github": cache.get("github"),
        "rss": cache.get("rss"),
        "photos": cache.get("photos"),
        "calendar": cache.get("calendar"),
        "pomodoro": pomodoro_state.get_status(),
    }


@app.get("/api/config")
async def api_config() -> dict[str, Any]:
    """Safe (no secrets) device + home config subset."""
    cfg = settings.app
    return {
        "device": cfg.device.model_dump(),
        "home": cfg.home.model_dump(),
        "pomodoro": {"presets": [preset.model_dump() for preset in cfg.pomodoro.presets]},
    }


@app.get("/api/status")
async def api_status() -> dict[str, Any]:
    """Diagnostics: WS client count + integration statuses."""
    return {
        "ws_clients": ws_manager.client_count,
        "integrations": [i.status for i in scheduler._integrations],
    }


@app.get("/api/photos/file/{filename}")
async def photos_file(filename: str) -> FileResponse:
    folder = Path(settings.app.photos.local_folder).expanduser().resolve()
    file_path = (folder / filename).resolve()
    if folder not in file_path.parents or not file_path.is_file():
        raise HTTPException(status_code=404, detail="Photo not found")
    return FileResponse(str(file_path))


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
