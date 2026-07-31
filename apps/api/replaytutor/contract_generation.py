from __future__ import annotations

import json
from pathlib import Path

from replaytutor.contracts import (
    AgentCapability,
    AnnotationActionRequest,
    AnnotationDisposition,
    AnnotationDispositionListResponse,
    AnnotationPoint,
    Bar,
    BarListResponse,
    BinanceConnectionStatus,
    BinanceDownloadRequest,
    CancelOrderRequest,
    CapabilityDimension,
    ChartAnnotation,
    CommitImportRequest,
    CompletedSession,
    CreateAnnotationRequest,
    CreatePlaybookRequest,
    CreateSessionSpec,
    DataQuality,
    DatasetListResponse,
    DataSnapshot,
    EpisodeReview,
    ErrorEnvelope,
    EvidenceRef,
    ExecutionFill,
    ExecutionSnapshot,
    FinishSessionRequest,
    GoldenDatasetRequest,
    HealthResponse,
    ImportPreview,
    Instrument,
    LockTradePlanRequest,
    OrderResult,
    PaperFill,
    PaperOrder,
    PlaybookListResponse,
    PlaybookVersion,
    PortfolioState,
    PriceActionAnnotation,
    PriceValues,
    ReplayFrame,
    ReplaySession,
    ReviewArtifact,
    ReviewDimension,
    ReviewListResponse,
    ReviewMetric,
    ReviewRequest,
    SessionCommand,
    SessionDelta,
    SessionEvent,
    SessionListResponse,
    SubmitOrderRequest,
    TradeEpisode,
    TradePlan,
    TradePlanResult,
    TradeSyncResult,
    TrainingReview,
    TrainingReviewListResponse,
    TutorChartInstruction,
    TutorInference,
    TutorObservation,
    TutorRequest,
    TutorResponse,
    TutorRuleCheck,
    TutorRun,
)


def contract_path() -> Path:
    return (
        Path(__file__).resolve().parents[3] / "packages" / "contracts" / "schema" / "contracts.json"
    )


def render_contracts() -> str:
    models = (
        ErrorEnvelope,
        HealthResponse,
        PriceValues,
        Instrument,
        Bar,
        DataQuality,
        DataSnapshot,
        DatasetListResponse,
        BarListResponse,
        GoldenDatasetRequest,
        BinanceDownloadRequest,
        ImportPreview,
        CommitImportRequest,
        CreateSessionSpec,
        ReplayFrame,
        ReplaySession,
        TradePlan,
        LockTradePlanRequest,
        PaperOrder,
        SubmitOrderRequest,
        CancelOrderRequest,
        PaperFill,
        PortfolioState,
        ExecutionSnapshot,
        TradePlanResult,
        OrderResult,
        SessionCommand,
        SessionEvent,
        SessionDelta,
        SessionListResponse,
        FinishSessionRequest,
        CompletedSession,
        ChartAnnotation,
        CreateAnnotationRequest,
        AnnotationActionRequest,
        AnnotationDisposition,
        AnnotationDispositionListResponse,
        ReviewMetric,
        EvidenceRef,
        TrainingReview,
        CapabilityDimension,
        TrainingReviewListResponse,
        AgentCapability,
        TutorRequest,
        TutorObservation,
        TutorInference,
        TutorRuleCheck,
        TutorChartInstruction,
        TutorResponse,
        TutorRun,
        PlaybookVersion,
        CreatePlaybookRequest,
        PlaybookListResponse,
        BinanceConnectionStatus,
        TradeSyncResult,
        ExecutionFill,
        TradeEpisode,
        AnnotationPoint,
        PriceActionAnnotation,
        ReviewDimension,
        EpisodeReview,
        ReviewArtifact,
        ReviewRequest,
        ReviewListResponse,
    )
    schemas = {
        "schema_version": "1.0",
        "models": {model.__name__: model.model_json_schema() for model in models},
    }
    return json.dumps(schemas, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def export_contracts() -> Path:
    path = contract_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_contracts(), encoding="utf-8")
    return path


def check_contracts() -> bool:
    path = contract_path()
    return path.is_file() and path.read_text(encoding="utf-8") == render_contracts()
