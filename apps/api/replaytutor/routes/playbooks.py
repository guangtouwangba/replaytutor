from fastapi import APIRouter, Request

from replaytutor.config import Settings
from replaytutor.contracts import (
    CreatePlaybookRequest,
    PlaybookListResponse,
    PlaybookVersion,
)
from replaytutor.modules.playbook import PlaybookService

router = APIRouter(prefix="/api/v1/playbooks", tags=["playbooks"])


def service(request: Request) -> PlaybookService:
    settings: Settings = request.app.state.settings
    return PlaybookService(settings)


@router.get("", response_model=PlaybookListResponse)
def list_playbooks(request: Request) -> PlaybookListResponse:
    return service(request).list()


@router.post("", response_model=PlaybookVersion)
def create_playbook(
    request: Request,
    payload: CreatePlaybookRequest,
) -> PlaybookVersion:
    return service(request).create(payload)
