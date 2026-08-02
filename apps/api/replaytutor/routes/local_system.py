from __future__ import annotations

from fastapi import APIRouter, Request

from replaytutor.config import Settings
from replaytutor.contracts import (
    BackupArtifact,
    CleanupResult,
    LocalPreferences,
    MaintenanceStatus,
)
from replaytutor.errors import ApiError
from replaytutor.modules.local_system import LocalSystemService

router = APIRouter(prefix="/api/v1", tags=["local-system"])


def service(request: Request) -> LocalSystemService:
    settings: Settings = request.app.state.settings
    return LocalSystemService(settings)


@router.get("/settings/preferences", response_model=LocalPreferences)
def get_preferences(request: Request) -> LocalPreferences:
    return service(request).get_preferences()


@router.put("/settings/preferences", response_model=LocalPreferences)
def save_preferences(
    request: Request,
    payload: LocalPreferences,
) -> LocalPreferences:
    return service(request).save_preferences(payload)


@router.get("/maintenance", response_model=MaintenanceStatus)
def maintenance_status(request: Request) -> MaintenanceStatus:
    return service(request).status()


@router.post("/maintenance/backups", response_model=BackupArtifact)
def create_backup(request: Request) -> BackupArtifact:
    return service(request).create_backup()


@router.post(
    "/maintenance/backups/{backup_id}/restore",
    response_model=BackupArtifact,
)
def restore_backup(request: Request, backup_id: str) -> BackupArtifact:
    try:
        return service(request).restore_backup(backup_id)
    except ValueError as error:
        raise ApiError(
            "invalid_backup",
            str(error),
            status_code=400,
        ) from error


@router.post("/maintenance/cleanup-agent-runs", response_model=CleanupResult)
def cleanup_agent_runs(request: Request) -> CleanupResult:
    local = service(request)
    preferences = local.get_preferences()
    return local.cleanup_agent_runs(preferences.retain_agent_runs_days)
