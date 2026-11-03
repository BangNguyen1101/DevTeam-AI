import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.ai_core.orchestrator import registry
from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.exceptions import AppError, app_error_handler
from app.core.logging import setup_logging
from app.realtime.hub import hub
from app.realtime.routes import router as ws_router


@asynccontextmanager
async def lifespan(_: FastAPI):
    hub.bind_loop(asyncio.get_running_loop())
    get_settings().workspaces_path.mkdir(parents=True, exist_ok=True)
    registry.mark_interrupted_runs()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    setup_logging(settings.log_level)

    app = FastAPI(title="DevTeam AI", version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_exception_handler(AppError, app_error_handler)
    app.include_router(api_router)
    app.include_router(ws_router)
    return app


app = create_app()
