from __future__ import annotations

import asyncio

from fastapi import APIRouter, Request, Response
from fastapi.responses import StreamingResponse

from replaytutor.config import Settings
from replaytutor.contracts import (
    AgentCapability,
    CreateTutorThreadRequest,
    TutorRequest,
    TutorRun,
    TutorThreadDetail,
    TutorThreadListResponse,
    UpdateTutorThreadRequest,
)
from replaytutor.errors import ApiError
from replaytutor.modules.tutor import TutorRuntime
from replaytutor.modules.tutor.capabilities import discover_codex_capability
from replaytutor.modules.tutor.runtime import TutorRunNotFoundError, TutorThreadNotFoundError

router = APIRouter(prefix="/api/v1", tags=["codex-tutor"])


def runtime(request: Request) -> TutorRuntime:
    settings: Settings = request.app.state.settings
    return TutorRuntime(settings)


@router.get("/agents/codex", response_model=AgentCapability)
def discover_codex(request: Request) -> AgentCapability:
    settings: Settings = request.app.state.settings
    return discover_codex_capability(settings)


@router.post("/sessions/{session_id}/tutor", response_model=TutorRun)
def start_tutor(
    request: Request,
    session_id: str,
    payload: TutorRequest,
) -> TutorRun:
    try:
        return runtime(request).start(session_id, payload)
    except (TutorThreadNotFoundError, ValueError) as error:
        raise ApiError("tutor_request_invalid", str(error), status_code=409) from error


@router.get(
    "/sessions/{session_id}/tutor/threads",
    response_model=TutorThreadListResponse,
)
def list_tutor_threads(request: Request, session_id: str) -> TutorThreadListResponse:
    return runtime(request).list_threads(session_id)


@router.post(
    "/sessions/{session_id}/tutor/threads",
    response_model=TutorThreadDetail,
)
def create_tutor_thread(
    request: Request,
    session_id: str,
    payload: CreateTutorThreadRequest,
) -> TutorThreadDetail:
    return runtime(request).create_thread(session_id, payload)


@router.get("/tutor/threads/{thread_id}", response_model=TutorThreadDetail)
def get_tutor_thread(request: Request, thread_id: str) -> TutorThreadDetail:
    try:
        return runtime(request).get_thread(thread_id)
    except TutorThreadNotFoundError as error:
        raise ApiError("tutor_thread_not_found", str(error), status_code=404) from error


@router.patch("/tutor/threads/{thread_id}", response_model=TutorThreadDetail)
def update_tutor_thread(
    request: Request,
    thread_id: str,
    payload: UpdateTutorThreadRequest,
) -> TutorThreadDetail:
    try:
        return runtime(request).update_thread(thread_id, payload)
    except TutorThreadNotFoundError as error:
        raise ApiError("tutor_thread_not_found", str(error), status_code=404) from error
    except ValueError as error:
        raise ApiError("tutor_thread_invalid", str(error), status_code=409) from error


@router.delete("/tutor/threads/{thread_id}", status_code=204)
def delete_tutor_thread(request: Request, thread_id: str) -> Response:
    try:
        runtime(request).delete_thread(thread_id)
    except TutorThreadNotFoundError as error:
        raise ApiError("tutor_thread_not_found", str(error), status_code=404) from error
    except ValueError as error:
        raise ApiError("tutor_thread_busy", str(error), status_code=409) from error
    return Response(status_code=204)


@router.get("/tutor/runs/{run_id}", response_model=TutorRun)
def get_tutor_run(request: Request, run_id: str) -> TutorRun:
    try:
        return runtime(request).get(run_id)
    except TutorRunNotFoundError as error:
        raise ApiError("tutor_run_not_found", str(error), status_code=404) from error


@router.post("/tutor/runs/{run_id}/cancel", response_model=TutorRun)
def cancel_tutor_run(request: Request, run_id: str) -> TutorRun:
    try:
        return runtime(request).cancel(run_id)
    except TutorRunNotFoundError as error:
        raise ApiError("tutor_run_not_found", str(error), status_code=404) from error


@router.get("/tutor/runs/{run_id}/events")
async def tutor_events(request: Request, run_id: str) -> StreamingResponse:
    async def events():
        previous = ""
        while True:
            run = runtime(request).get(run_id)
            payload = run.model_dump_json()
            if payload != previous:
                yield f"event: status\ndata: {payload}\n\n"
                previous = payload
            if run.status != "running":
                break
            await asyncio.sleep(0.25)

    try:
        runtime(request).get(run_id)
    except TutorRunNotFoundError as error:
        raise ApiError("tutor_run_not_found", str(error), status_code=404) from error
    return StreamingResponse(events(), media_type="text/event-stream")
