from __future__ import annotations

import shutil

from fastapi import APIRouter, Request

from replaytutor import __version__
from replaytutor.config import Settings
from replaytutor.contracts import (
    AgentExecutableHealth,
    DatabaseHealth,
    DataHealth,
    HealthResponse,
    HealthService,
)
from replaytutor.runtime import is_writable
from replaytutor.storage.database import inspect_database

router = APIRouter(prefix="/api/v1", tags=["system"])


def executable_probe(agent_id: str, executable_name: str) -> AgentExecutableHealth:
    executable = shutil.which(executable_name)
    return AgentExecutableHealth(
        agent_id=agent_id,  # type: ignore[arg-type]
        installed=executable is not None,
        executable=executable,
    )


@router.get("/health", response_model=HealthResponse)
def health(request: Request) -> HealthResponse:
    settings: Settings = request.app.state.settings
    database = inspect_database(settings)
    database_healthy = (
        database.journal_mode == "wal"
        and database.foreign_keys
        and database.busy_timeout_ms == 5000
        and database.migration_current == database.migration_head
        and database.migration_head is not None
    )
    data_writable = is_writable(settings.resolved_data_dir)
    status = "healthy" if database_healthy and data_writable else "degraded"

    return HealthResponse(
        status=status,
        request_id=str(request.state.request_id),
        api=HealthService(status="healthy", version=__version__),
        database=DatabaseHealth(
            status="healthy" if database_healthy else "degraded",
            path=str(database.path),
            journal_mode=database.journal_mode,
            foreign_keys=database.foreign_keys,
            migration_current=database.migration_current,
            migration_head=database.migration_head,
        ),
        data=DataHealth(
            status="healthy" if data_writable else "unavailable",
            path=str(settings.resolved_data_dir),
            writable=data_writable,
        ),
        agents=[
            executable_probe("codex-local", "codex"),
        ],
    )
