from __future__ import annotations

from fastapi import APIRouter, Request

from replaytutor.config import Settings
from replaytutor.contracts import (
    AnnotationActionRequest,
    AnnotationDisposition,
    AnnotationDispositionListResponse,
    CancelOrderRequest,
    ChartAnnotation,
    CompletedSession,
    CreateAnnotationRequest,
    CreateSessionSpec,
    EvidenceTarget,
    FinishSessionRequest,
    LockTradePlanRequest,
    OrderResult,
    PlaybookEvaluation,
    SessionCommand,
    SessionDelta,
    SessionListResponse,
    SubmitOrderRequest,
    TradePlanResult,
    TrainingReview,
    TrainingReviewListResponse,
)
from replaytutor.errors import ApiError
from replaytutor.modules.annotations import AnnotationService
from replaytutor.modules.evidence_review import EvidenceResolver, EvidenceReviewService
from replaytutor.modules.execution.service import ExecutionService
from replaytutor.modules.market_data.service import MarketDataError
from replaytutor.modules.market_rules import RuleViolation
from replaytutor.modules.playbook import PlaybookEvaluator
from replaytutor.modules.training_session.service import (
    InvalidSessionStateError,
    SessionConflictError,
    SessionNotFoundError,
    TrainingSessionError,
    TrainingSessionService,
)

router = APIRouter(prefix="/api/v1", tags=["training-sessions"])


def service(request: Request) -> TrainingSessionService:
    settings: Settings = request.app.state.settings
    return TrainingSessionService(settings)


def translate(error: Exception) -> ApiError:
    if isinstance(error, SessionConflictError):
        return ApiError(
            "session_revision_conflict",
            str(error),
            status_code=409,
            retryable=True,
            details={"current_revision": error.current_revision},
        )
    if isinstance(error, SessionNotFoundError):
        return ApiError("session_not_found", str(error), status_code=404)
    if isinstance(error, InvalidSessionStateError):
        return ApiError("invalid_session_state", str(error), status_code=409)
    return ApiError("training_session_error", str(error), status_code=422)


@router.post("/sessions", response_model=SessionDelta)
def create_session(request: Request, payload: CreateSessionSpec) -> SessionDelta:
    try:
        return service(request).create(payload)
    except (TrainingSessionError, MarketDataError) as error:
        raise translate(error) from error


@router.get("/sessions", response_model=SessionListResponse)
def list_sessions(request: Request) -> SessionListResponse:
    try:
        return service(request).list()
    except (TrainingSessionError, MarketDataError) as error:
        raise translate(error) from error


@router.get("/sessions/{session_id}", response_model=SessionDelta)
def get_session(request: Request, session_id: str) -> SessionDelta:
    try:
        return service(request).get(session_id)
    except (TrainingSessionError, MarketDataError) as error:
        raise translate(error) from error


@router.post("/sessions/{session_id}/commands", response_model=SessionDelta)
def apply_command(
    request: Request,
    session_id: str,
    payload: SessionCommand,
) -> SessionDelta:
    try:
        return service(request).apply(session_id, payload)
    except (TrainingSessionError, MarketDataError) as error:
        raise translate(error) from error


@router.post("/sessions/{session_id}/finish", response_model=CompletedSession)
def finish_session(
    request: Request,
    session_id: str,
    payload: FinishSessionRequest,
) -> CompletedSession:
    try:
        return service(request).finish(session_id, payload)
    except (TrainingSessionError, MarketDataError) as error:
        raise translate(error) from error


@router.post("/sessions/{session_id}/plan", response_model=TradePlanResult)
def lock_trade_plan(
    request: Request,
    session_id: str,
    payload: LockTradePlanRequest,
) -> TradePlanResult:
    try:
        return ExecutionService(service(request)).lock_plan(session_id, payload)
    except (TrainingSessionError, MarketDataError, RuleViolation) as error:
        raise translate(error) from error


@router.post("/sessions/{session_id}/orders", response_model=OrderResult)
def submit_order(
    request: Request,
    session_id: str,
    payload: SubmitOrderRequest,
) -> OrderResult:
    try:
        return ExecutionService(service(request)).submit_order(session_id, payload)
    except (TrainingSessionError, MarketDataError, RuleViolation) as error:
        raise translate(error) from error


@router.post("/sessions/{session_id}/orders/cancel", response_model=OrderResult)
def cancel_order(
    request: Request,
    session_id: str,
    payload: CancelOrderRequest,
) -> OrderResult:
    try:
        return ExecutionService(service(request)).cancel_order(session_id, payload)
    except (TrainingSessionError, MarketDataError, RuleViolation) as error:
        raise translate(error) from error


@router.post(
    "/sessions/{session_id}/annotations",
    response_model=ChartAnnotation,
)
def create_annotation(
    request: Request,
    session_id: str,
    payload: CreateAnnotationRequest,
) -> ChartAnnotation:
    try:
        settings: Settings = request.app.state.settings
        return AnnotationService(settings).create(session_id, payload)
    except (TrainingSessionError, MarketDataError) as error:
        raise translate(error) from error


@router.get(
    "/sessions/{session_id}/annotations/dispositions",
    response_model=AnnotationDispositionListResponse,
)
def list_annotation_dispositions(
    request: Request,
    session_id: str,
) -> AnnotationDispositionListResponse:
    try:
        settings: Settings = request.app.state.settings
        dispositions = AnnotationService(settings).list_dispositions(session_id)
        return AnnotationDispositionListResponse(dispositions=dispositions)
    except (TrainingSessionError, MarketDataError) as error:
        raise translate(error) from error


@router.post(
    "/sessions/{session_id}/annotations/{annotation_id}/actions",
    response_model=AnnotationDisposition,
)
def act_on_annotation(
    request: Request,
    session_id: str,
    annotation_id: str,
    payload: AnnotationActionRequest,
) -> AnnotationDisposition:
    try:
        settings: Settings = request.app.state.settings
        return AnnotationService(settings).act(session_id, annotation_id, payload)
    except (TrainingSessionError, MarketDataError) as error:
        raise translate(error) from error


@router.get("/sessions/{session_id}/review", response_model=TrainingReview)
def get_training_review(request: Request, session_id: str) -> TrainingReview:
    try:
        settings: Settings = request.app.state.settings
        return EvidenceReviewService(settings).get(session_id)
    except (TrainingSessionError, MarketDataError) as error:
        raise translate(error) from error


@router.get(
    "/sessions/{session_id}/evidence/{evidence_id}",
    response_model=EvidenceTarget,
)
def resolve_evidence(
    request: Request,
    session_id: str,
    evidence_id: str,
) -> EvidenceTarget:
    try:
        settings: Settings = request.app.state.settings
        return EvidenceResolver(settings).resolve(session_id, evidence_id)
    except (TrainingSessionError, MarketDataError) as error:
        raise translate(error) from error


@router.get(
    "/sessions/{session_id}/playbook-checks",
    response_model=PlaybookEvaluation,
)
def evaluate_playbook(
    request: Request,
    session_id: str,
) -> PlaybookEvaluation:
    try:
        settings: Settings = request.app.state.settings
        return PlaybookEvaluator(settings).evaluate(session_id)
    except (TrainingSessionError, MarketDataError) as error:
        raise translate(error) from error


@router.get("/training-reviews", response_model=TrainingReviewListResponse)
def list_training_reviews(request: Request) -> TrainingReviewListResponse:
    try:
        settings: Settings = request.app.state.settings
        return EvidenceReviewService(settings).list()
    except (TrainingSessionError, MarketDataError) as error:
        raise translate(error) from error
