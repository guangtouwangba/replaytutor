from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ErrorDetail(ContractModel):
    code: str
    message: str
    retryable: bool = False
    request_id: str
    details: dict[str, object] = Field(default_factory=dict)


class ErrorEnvelope(ContractModel):
    error: ErrorDetail


class HealthService(ContractModel):
    status: Literal["healthy", "degraded", "unavailable"]
    version: str | None = None
    detail: str | None = None


class DatabaseHealth(HealthService):
    path: str
    journal_mode: str
    foreign_keys: bool
    migration_current: str | None
    migration_head: str | None


class DataHealth(HealthService):
    path: str
    writable: bool


class AgentExecutableHealth(ContractModel):
    agent_id: Literal["codex-local"]
    installed: bool
    executable: str | None
    authentication: Literal["not_checked"] = "not_checked"


class HealthResponse(ContractModel):
    schema_version: Literal["1.0"] = "1.0"
    status: Literal["healthy", "degraded"]
    request_id: str
    api: HealthService
    database: DatabaseHealth
    data: DataHealth
    agents: list[AgentExecutableHealth]


Identifier = Annotated[str, Field(pattern=r"^[a-z]{3}_[0-9a-f-]{36}$")]
DecimalString = Annotated[str, Field(pattern=r"^-?(0|[1-9][0-9]*)(\.[0-9]+)?$")]
Timeframe = Literal["1m", "5m", "15m", "1h", "2h", "4h", "1d"]
Market = Literal["CRYPTO", "CN"]


class PriceValues(ContractModel):
    open: DecimalString
    high: DecimalString
    low: DecimalString
    close: DecimalString
    volume: DecimalString


class Instrument(ContractModel):
    schema_version: Literal["1.0"] = "1.0"
    instrument_id: Identifier
    asset_class: Literal["crypto_spot", "crypto_perpetual", "equity"]
    market: Market
    venue: str
    canonical_symbol: str
    display_name: str
    base_currency: str
    quote_currency: str
    timezone: str
    tick_size: DecimalString
    lot_size: DecimalString
    price_scale: int = Field(ge=0, le=18)
    market_rule_set_id: str


class Bar(ContractModel):
    schema_version: Literal["1.0"] = "1.0"
    bar_id: Identifier
    instrument_id: Identifier
    timeframe: Timeframe
    open_time: datetime
    close_time: datetime
    raw: PriceValues
    adjusted: PriceValues | None = None
    quality_flags: list[str] = Field(default_factory=list)


class DataQuality(ContractModel):
    status: Literal["passed", "warning", "failed"]
    row_count: int = Field(ge=0)
    duplicate_count: int = Field(ge=0)
    gap_count: int = Field(ge=0)
    invalid_ohlc_count: int = Field(ge=0)
    flags: list[str] = Field(default_factory=list)


class DataSnapshot(ContractModel):
    schema_version: Literal["1.0"] = "1.0"
    snapshot_id: Identifier
    instrument: Instrument
    timeframe: Timeframe
    source_id: str
    source_kind: Literal["golden", "binance_public", "binance_usdm", "file_import"]
    coverage_start: datetime
    coverage_end: datetime
    created_at: datetime
    content_hash: str
    manifest_hash: str
    immutable: Literal[True] = True
    quality: DataQuality
    derived_timeframes: list[Timeframe] = Field(default_factory=list)


class DatasetListResponse(ContractModel):
    schema_version: Literal["1.0"] = "1.0"
    datasets: list[DataSnapshot]


class BarListResponse(ContractModel):
    schema_version: Literal["1.0"] = "1.0"
    snapshot_id: Identifier
    timeframe: Timeframe
    bars: list[Bar]
    has_more: bool


class GoldenDatasetRequest(ContractModel):
    dataset_id: Literal["btcusdt-1m-2025-01"] = "btcusdt-1m-2025-01"


class BinanceDownloadRequest(ContractModel):
    symbol: str = Field(pattern=r"^[A-Z0-9]{5,20}$")
    start_time: datetime
    end_time: datetime
    timeframe: Literal["1m"] = "1m"


class ImportPreview(ContractModel):
    schema_version: Literal["1.0"] = "1.0"
    import_id: Identifier
    filename: str
    status: Literal["preview_ready", "failed", "committed"]
    detected_columns: dict[str, str]
    sample_rows: list[dict[str, str]]
    quality: DataQuality
    error: str | None = None


class CommitImportRequest(ContractModel):
    symbol: str
    market: Market
    venue: str
    timezone: str
    quote_currency: str
    adjustment: Literal["raw", "forward", "backward"]
    tick_size: DecimalString
    lot_size: DecimalString


class CreateSessionSpec(ContractModel):
    snapshot_id: Identifier
    start_mode: Literal["beginning", "random"] = "beginning"
    seed: int = Field(default=1, ge=0, le=2_147_483_647)
    warmup_bars: int = Field(default=120, ge=20, le=500)
    initial_cash: DecimalString = "100000"
    hidden_real_date: bool = True
    playbook_id: Identifier | None = None


class ReplayFrame(ContractModel):
    schema_version: Literal["1.0"] = "1.0"
    frame_id: Identifier
    session_id: Identifier
    revision: int = Field(ge=0)
    current_index: int = Field(ge=0)
    total_bars: int = Field(ge=1)
    visible_at: datetime
    progress: float = Field(ge=0, le=1)


class ReplaySession(ContractModel):
    schema_version: Literal["1.0"] = "1.0"
    session_id: Identifier
    snapshot_id: Identifier
    instrument: Instrument
    timeframe: Literal["1m"] = "1m"
    status: Literal["ready", "paused", "completed", "stopped"]
    revision: int = Field(ge=0)
    frame: ReplayFrame
    start_index: int = Field(ge=0)
    warmup_bars: int = Field(ge=20, le=500)
    seed: int = Field(ge=0)
    initial_cash: DecimalString
    hidden_real_date: bool
    playbook_id: Identifier | None = None
    fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    created_at: datetime
    updated_at: datetime


class TradePlan(ContractModel):
    schema_version: Literal["1.0"] = "1.0"
    plan_id: Identifier
    session_id: Identifier
    frame_id: Identifier
    status: Literal["locked"]
    side: Literal["BUY", "SELL"]
    thesis: str = Field(min_length=3, max_length=1000)
    invalidation: str = Field(min_length=3, max_length=1000)
    entry_price: DecimalString | None = None
    stop_price: DecimalString | None = None
    target_price: DecimalString | None = None
    risk_amount: DecimalString
    created_at: datetime


class LockTradePlanRequest(ContractModel):
    command_id: Identifier
    expected_revision: int = Field(ge=0)
    side: Literal["BUY", "SELL"]
    thesis: str = Field(min_length=3, max_length=1000)
    invalidation: str = Field(min_length=3, max_length=1000)
    entry_price: DecimalString | None = None
    stop_price: DecimalString | None = None
    target_price: DecimalString | None = None
    risk_amount: DecimalString


class PaperOrder(ContractModel):
    schema_version: Literal["1.0"] = "1.0"
    order_id: Identifier
    session_id: Identifier
    plan_id: Identifier
    submitted_frame_id: Identifier
    side: Literal["BUY", "SELL"]
    order_type: Literal["MARKET", "LIMIT", "STOP_MARKET"]
    status: Literal["PENDING", "FILLED", "CANCELLED", "REJECTED"]
    quantity: DecimalString
    limit_price: DecimalString | None = None
    stop_price: DecimalString | None = None
    parent_order_id: Identifier | None = None
    oco_group_id: str | None = None
    activate_index: int = Field(ge=0)
    submitted_at: datetime
    filled_at: datetime | None = None


class SubmitOrderRequest(ContractModel):
    command_id: Identifier
    expected_revision: int = Field(ge=0)
    side: Literal["BUY", "SELL"]
    order_type: Literal["MARKET", "LIMIT", "STOP_MARKET"]
    quantity: DecimalString
    limit_price: DecimalString | None = None
    stop_price: DecimalString | None = None
    take_profit_price: DecimalString | None = None
    protective_stop_price: DecimalString | None = None


class CancelOrderRequest(ContractModel):
    command_id: Identifier
    expected_revision: int = Field(ge=0)
    order_id: Identifier


class PaperFill(ContractModel):
    schema_version: Literal["1.0"] = "1.0"
    fill_id: Identifier
    order_id: Identifier
    session_id: Identifier
    frame_id: Identifier
    side: Literal["BUY", "SELL"]
    price: DecimalString
    quantity: DecimalString
    quote_amount: DecimalString
    fee: DecimalString
    executed_at: datetime


class PortfolioState(ContractModel):
    schema_version: Literal["1.0"] = "1.0"
    cash: DecimalString
    position_quantity: DecimalString
    average_entry_price: DecimalString
    realized_pnl: DecimalString
    fees_paid: DecimalString


class ExecutionSnapshot(ContractModel):
    schema_version: Literal["1.0"] = "1.0"
    plan: TradePlan | None = None
    orders: list[PaperOrder] = Field(default_factory=list)
    fills: list[PaperFill] = Field(default_factory=list)
    portfolio: PortfolioState


class TradePlanResult(ContractModel):
    schema_version: Literal["1.0"] = "1.0"
    session: ReplaySession
    execution: ExecutionSnapshot
    idempotent_replay: bool = False


class OrderResult(ContractModel):
    schema_version: Literal["1.0"] = "1.0"
    session: ReplaySession
    order: PaperOrder
    execution: ExecutionSnapshot
    idempotent_replay: bool = False


class SessionCommand(ContractModel):
    command_id: Identifier
    expected_revision: int = Field(ge=0)
    kind: Literal["advance"]
    bars: int = Field(default=1, ge=1, le=500)


class SessionEvent(ContractModel):
    event_id: Identifier
    session_id: Identifier
    sequence: int = Field(ge=1)
    revision: int = Field(ge=0)
    event_type: Literal["session_created", "replay_advanced", "session_completed"]
    occurred_at: datetime
    payload: dict[str, object] = Field(default_factory=dict)


class SessionDelta(ContractModel):
    schema_version: Literal["1.0"] = "1.0"
    session: ReplaySession
    bars: list[Bar]
    events: list[SessionEvent]
    execution: ExecutionSnapshot | None = None
    annotations: list[ChartAnnotation] = Field(default_factory=list)
    idempotent_replay: bool = False


class SessionListResponse(ContractModel):
    schema_version: Literal["1.0"] = "1.0"
    sessions: list[ReplaySession]


class FinishSessionRequest(ContractModel):
    command_id: Identifier
    expected_revision: int = Field(ge=0)


class CompletedSession(ContractModel):
    schema_version: Literal["1.0"] = "1.0"
    session: ReplaySession
    finished_at: datetime
    revealed_coverage_start: datetime
    revealed_coverage_end: datetime
    idempotent_replay: bool = False


class ReviewMetric(ContractModel):
    key: Literal[
        "net_pnl",
        "realized_pnl",
        "fees",
        "ending_equity",
        "trade_count",
        "win_rate",
        "mfe",
        "mae",
        "r_multiple",
        "max_drawdown",
        "exit_efficiency",
    ]
    label: str
    value: str
    unit: str | None = None


class EvidenceRef(ContractModel):
    evidence_id: str
    kind: Literal[
        "plan",
        "order",
        "fill",
        "bar",
        "metric",
        "user_annotation",
        "ai_annotation",
    ]
    summary: str
    frame_id: Identifier | None = None
    occurred_at: datetime | None = None
    price: DecimalString | None = None


class EvidenceTarget(ContractModel):
    schema_version: Literal["1.0"] = "1.0"
    evidence_id: Identifier
    session_id: Identifier
    kind: Literal[
        "plan",
        "order",
        "fill",
        "bar",
        "metric",
        "user_annotation",
        "ai_annotation",
    ]
    frame_id: Identifier | None = None
    occurred_at: datetime | None = None
    price: DecimalString | None = None
    layer: Literal["user", "ai"] | None = None
    annotation_id: Identifier | None = None
    order_id: Identifier | None = None
    fill_id: Identifier | None = None


class TrainingReview(ContractModel):
    schema_version: Literal["1.0"] = "1.0"
    review_id: Identifier
    session_id: Identifier
    review_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    process_outcome: Literal[
        "good_process_profit",
        "good_process_loss",
        "bad_process_profit",
        "bad_process_loss",
        "insufficient_evidence",
    ]
    metrics: list[ReviewMetric]
    evidence: list[EvidenceRef]
    findings: list[str]
    created_at: datetime


class CapabilityDimension(ContractModel):
    key: Literal["environment", "plan", "risk", "execution", "management"]
    label: str
    sample_count: int = Field(ge=0)
    status: Literal["insufficient", "ready"]
    score: DecimalString | None = None


class TrainingReviewListResponse(ContractModel):
    schema_version: Literal["1.0"] = "1.0"
    reviews: list[TrainingReview]
    dimensions: list[CapabilityDimension]


class AgentCapability(ContractModel):
    schema_version: Literal["1.0"] = "1.0"
    agent_id: Literal["codex-local"] = "codex-local"
    installed: bool
    executable: str | None = None
    version: str | None = None
    available: bool
    authentication: Literal["unknown", "verified", "failed"]
    diagnostics: list[str] = Field(default_factory=list)


class TutorRequest(ContractModel):
    question: str = Field(min_length=2, max_length=2000)
    stage: Literal["environment", "plan", "position", "exit", "after_action"] = "environment"


class TutorObservation(ContractModel):
    text: str
    evidence_ids: list[str] = Field(default_factory=list)


class TutorInference(ContractModel):
    text: str
    confidence: Literal["low", "medium", "high"]
    evidence_ids: list[str] = Field(default_factory=list)


class TutorRuleCheck(ContractModel):
    rule_id: str
    status: Literal["passed", "failed", "unknown"]
    reason: str
    evidence_ids: list[str] = Field(default_factory=list)


class TutorChartInstruction(ContractModel):
    shape: Literal["line", "zone", "marker", "label"]
    label: str
    evidence_ids: list[str]
    points: list[AnnotationPoint] = Field(min_length=1, max_length=4)


class TutorResponse(ContractModel):
    schema_version: Literal["1.0"] = "1.0"
    summary: str
    observations: list[TutorObservation] = Field(default_factory=list)
    inferences: list[TutorInference] = Field(default_factory=list)
    risks_and_unknowns: list[str] = Field(default_factory=list)
    rule_checks: list[TutorRuleCheck] = Field(default_factory=list)
    next_questions: list[str] = Field(default_factory=list)
    annotations: list[TutorChartInstruction] = Field(default_factory=list)
    disclaimer: str


class TutorRun(ContractModel):
    schema_version: Literal["1.0"] = "1.0"
    run_id: Identifier
    session_id: Identifier
    frame_id: Identifier
    agent_id: Literal["codex-local"] = "codex-local"
    status: Literal["running", "completed", "failed", "cancelled", "timed_out"]
    question: str
    stage: Literal["environment", "plan", "position", "exit", "after_action"]
    response: TutorResponse | None = None
    error: str | None = None
    created_at: datetime
    completed_at: datetime | None = None


class PlaybookVersion(ContractModel):
    schema_version: Literal["1.0"] = "1.0"
    playbook_id: Identifier
    slug: str = Field(pattern=r"^[a-z0-9-]{3,64}$")
    name: str = Field(min_length=2, max_length=100)
    version: int = Field(ge=1)
    description: str
    rules: list[str] = Field(min_length=1)
    official: bool = False
    created_at: datetime


class CreatePlaybookRequest(ContractModel):
    slug: str = Field(pattern=r"^[a-z0-9-]{3,64}$")
    name: str = Field(min_length=2, max_length=100)
    description: str = Field(max_length=1000)
    rules: list[str] = Field(min_length=1, max_length=30)


class PlaybookListResponse(ContractModel):
    schema_version: Literal["1.0"] = "1.0"
    playbooks: list[PlaybookVersion]


class ChartAnnotation(ContractModel):
    schema_version: Literal["1.0"] = "1.0"
    annotation_id: Identifier
    session_id: Identifier
    frame_id: Identifier
    layer: Literal["user", "ai"]
    shape: Literal["line", "zone", "marker", "label"]
    label: str
    points: list[AnnotationPoint] = Field(min_length=1, max_length=4)
    provenance_run_id: Identifier | None = None
    created_at: datetime


class CreateAnnotationRequest(ContractModel):
    command_id: Identifier
    expected_revision: int = Field(ge=0)
    shape: Literal["line", "zone", "marker", "label"]
    label: str = Field(min_length=1, max_length=200)
    points: list[AnnotationPoint] = Field(min_length=1, max_length=4)


class AnnotationActionRequest(ContractModel):
    command_id: Identifier
    expected_revision: int = Field(ge=0)
    action: Literal["accepted", "rejected", "revised", "deleted"]
    label: str | None = Field(default=None, min_length=1, max_length=200)
    points: list[AnnotationPoint] | None = Field(default=None, min_length=1, max_length=4)


class AnnotationDisposition(ContractModel):
    schema_version: Literal["1.0"] = "1.0"
    annotation_id: Identifier
    state: Literal["active", "proposed", "accepted", "rejected", "deleted"]
    effective_label: str
    effective_points: list[AnnotationPoint] = Field(min_length=1, max_length=4)
    original_annotation: ChartAnnotation
    latest_event_id: Identifier | None = None


class AnnotationDispositionListResponse(ContractModel):
    schema_version: Literal["1.0"] = "1.0"
    dispositions: list[AnnotationDisposition]


class BinanceConnectionStatus(ContractModel):
    schema_version: Literal["1.0"] = "1.0"
    readable: bool
    mainnet: bool
    read_enabled: bool
    futures_trade_enabled: bool
    withdrawals_enabled: bool
    ip_restricted: bool
    diagnostics: list[str] = Field(default_factory=list)


class TradeSyncResult(ContractModel):
    schema_version: Literal["1.0"] = "1.0"
    sync_id: Identifier
    coverage_start: datetime
    coverage_end: datetime
    coverage_status: Literal["complete", "partial", "quota_blocked", "failed"]
    fill_count: int = Field(ge=0)
    order_count: int = Field(ge=0)
    income_count: int = Field(ge=0)
    episode_count: int = Field(ge=0)
    diagnostics: list[str] = Field(default_factory=list)


class ExecutionFill(ContractModel):
    schema_version: Literal["1.0"] = "1.0"
    fill_id: Identifier
    symbol: str
    trade_id: str
    order_id: str
    side: Literal["BUY", "SELL"]
    position_side: Literal["BOTH", "LONG", "SHORT"]
    price: DecimalString
    qty: DecimalString
    quote_qty: DecimalString
    commission: DecimalString
    commission_asset: str
    realized_pnl: DecimalString
    executed_at: datetime
    is_maker: bool


class TradeEpisode(ContractModel):
    schema_version: Literal["1.0"] = "1.0"
    episode_id: Identifier
    symbol: str
    direction: Literal["long", "short"]
    position_side: Literal["BOTH", "LONG", "SHORT"]
    status: Literal["open", "closed"]
    opened_at: datetime
    closed_at: datetime | None
    entry_price: DecimalString
    exit_price: DecimalString | None
    peak_qty: DecimalString
    realized_pnl: DecimalString
    commission: DecimalString
    fill_count: int = Field(ge=1)


class AnnotationPoint(ContractModel):
    time: datetime
    price: DecimalString


class PriceActionAnnotation(ContractModel):
    schema_version: Literal["1.0"] = "1.0"
    annotation_id: str
    timeframe: Timeframe
    layer: Literal["background", "location", "setup", "trigger", "execution", "management"]
    shape: Literal["line", "zone", "marker", "label", "path"]
    label: str
    evidence: str
    rule_id: str
    confidence: float = Field(ge=0, le=1)
    perspective: Literal["decision_time", "after_action"]
    points: list[AnnotationPoint]
    verdict: Literal["correct", "improve", "neutral", "unknown"]


class ReviewDimension(ContractModel):
    dimension: Literal[
        "background",
        "location",
        "setup",
        "trigger",
        "execution",
        "management",
        "outcome",
    ]
    verdict: Literal["correct", "improve", "unknown"]
    title: str
    evidence: list[str]


class EpisodeReview(ContractModel):
    episode: TradeEpisode
    process_outcome: Literal[
        "good_trade_profit",
        "good_trade_loss",
        "bad_trade_profit",
        "bad_trade_loss",
        "insufficient_evidence",
        "open_trade",
    ]
    dimensions: list[ReviewDimension]
    annotations: list[PriceActionAnnotation]
    positives: list[str]
    improvements: list[str]
    missing_context: list[str]


class ReviewArtifact(ContractModel):
    schema_version: Literal["1.0"] = "1.0"
    review_id: Identifier
    scope_kind: Literal["today", "recent", "trade"]
    scope_value: str
    created_at: datetime
    episode_count: int = Field(ge=0)
    total_realized_pnl: DecimalString
    total_commission: DecimalString
    reviews: list[EpisodeReview]
    top_positives: list[str]
    top_improvements: list[str]
    recurring_patterns: list[str]
    report_url: str


class ReviewRequest(ContractModel):
    scope_kind: Literal["today", "recent", "trade"]
    count: int = Field(default=10, ge=1, le=100)
    episode_id: Identifier | None = None
    symbol: str | None = Field(default=None, pattern=r"^[A-Z0-9]{5,20}$")
    direction: Literal["long", "short"] | None = None
    sync_first: bool = True


class ReviewListResponse(ContractModel):
    schema_version: Literal["1.0"] = "1.0"
    reviews: list[ReviewArtifact]
