from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from replaytutor import __version__
from replaytutor.config import Settings, get_settings
from replaytutor.errors import install_exception_handlers
from replaytutor.middleware import RequestIdMiddleware
from replaytutor.routes.health import router as health_router
from replaytutor.runtime import ensure_runtime_directories
from replaytutor.storage.database import connect_database


def create_app(settings: Settings | None = None) -> FastAPI:
    configured_settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        ensure_runtime_directories(configured_settings)
        connection = connect_database(configured_settings.database_path)
        app.state.database_connection = connection
        try:
            yield
        finally:
            connection.close()

    app = FastAPI(
        title="ReplayTutor API",
        version=__version__,
        lifespan=lifespan,
    )
    app.state.settings = configured_settings
    app.add_middleware(
        CORSMiddleware,
        allow_origins=configured_settings.allowed_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Accept", "Content-Type", "X-Request-ID"],
    )
    app.add_middleware(RequestIdMiddleware)
    install_exception_handlers(app)
    app.include_router(health_router)
    return app


app = create_app()
