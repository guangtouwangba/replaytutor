from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from replaytutor import __version__
from replaytutor.config import Settings, get_settings
from replaytutor.errors import install_exception_handlers
from replaytutor.middleware import RequestIdMiddleware
from replaytutor.modules.local_system import LocalSystemService
from replaytutor.modules.market_data.download_jobs import DatasetDownloadJobService
from replaytutor.routes.chart_tools import router as chart_tools_router
from replaytutor.routes.datasets import router as datasets_router
from replaytutor.routes.health import router as health_router
from replaytutor.routes.local_system import router as local_system_router
from replaytutor.routes.playbooks import router as playbooks_router
from replaytutor.routes.reviews import router as reviews_router
from replaytutor.routes.sessions import router as sessions_router
from replaytutor.routes.tutor import router as tutor_router
from replaytutor.runtime import ensure_runtime_directories
from replaytutor.storage.database import connect_database, upgrade_database


def create_app(settings: Settings | None = None) -> FastAPI:
    configured_settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        ensure_runtime_directories(configured_settings)
        upgrade_database(configured_settings)
        LocalSystemService(configured_settings).recover_orphaned_tutor_runs()
        background_tasks: set[asyncio.Task[None]] = set()
        app.state.background_tasks = background_tasks
        downloads = DatasetDownloadJobService(configured_settings)
        for job_id in downloads.recover_pending():
            task = asyncio.create_task(downloads.run(job_id), name=job_id)
            background_tasks.add(task)
            task.add_done_callback(background_tasks.discard)
        connection = connect_database(configured_settings.database_path)
        app.state.database_connection = connection
        try:
            yield
        finally:
            pending_tasks = tuple(background_tasks)
            for task in pending_tasks:
                task.cancel()
            if pending_tasks:
                await asyncio.gather(*pending_tasks, return_exceptions=True)
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
        allow_headers=["Accept", "Accept-Language", "Content-Type", "X-Request-ID"],
    )
    app.add_middleware(RequestIdMiddleware)
    install_exception_handlers(app)
    app.include_router(health_router)
    app.include_router(local_system_router)
    app.include_router(playbooks_router)
    app.include_router(datasets_router)
    app.include_router(chart_tools_router)
    app.include_router(reviews_router)
    app.include_router(sessions_router)
    app.include_router(tutor_router)
    return app


app = create_app()
