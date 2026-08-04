from __future__ import annotations

from fastapi import APIRouter, Request

from replaytutor.config import Settings
from replaytutor.contracts import CompanionResponse
from replaytutor.modules.companion import CompanionFacade

router = APIRouter(prefix="/api/v1", tags=["chrome-companion"])


@router.post("/companion", response_model=CompanionResponse)
def companion(request: Request, payload: dict[str, object]) -> CompanionResponse:
    settings: Settings = request.app.state.settings
    return CompanionFacade(settings).dispatch(payload)
