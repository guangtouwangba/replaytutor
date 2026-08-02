// Generated from Pydantic. Do not edit.

export type EvaluatedCount = number;
export type Key = "environment" | "plan" | "risk" | "execution" | "management";
export type Label = string;
export type PassedCount = number;
export type SampleCount = number;
export type Score = string | null;
export type SessionIds = string[];
export type Status = "insufficient" | "ready";
export type Dimensions = CapabilityDimension[];
export type Dimension = ("environment" | "plan" | "risk" | "execution" | "management") | null;
export type PlaybookId = string | null;
export type Reason = string;
export type SampleCount1 = number;
export type Score1 = string | null;
export type SetupPath = string;
export type Status1 = "insufficient" | "ready";
export type CreatedAt = string;
export type EvaluatedCount1 = number;
export type EvidenceIds = string[];
export type Key1 = "environment" | "plan" | "risk" | "execution" | "management";
export type PassedCount1 = number;
export type DimensionObservations = ReviewDimensionObservation[];
export type Equity = string;
export type OccurredAt = string;
export type EquityCurve = EquityCurvePoint[];
export type EvidenceId = string;
export type FrameId = string | null;
export type Kind = "plan" | "order" | "fill" | "bar" | "metric" | "user_annotation" | "ai_annotation";
export type OccurredAt1 = string | null;
export type Price = string | null;
export type Summary = string;
export type Evidence = EvidenceRef[];
export type Findings = string[];
export type Key2 =
  | "net_pnl"
  | "realized_pnl"
  | "fees"
  | "ending_equity"
  | "trade_count"
  | "win_rate"
  | "mfe"
  | "mae"
  | "r_multiple"
  | "max_drawdown"
  | "exit_efficiency";
export type Label1 = string;
export type Unit = string | null;
export type Value = string;
export type Metrics = ReviewMetric[];
export type PlaybookEvaluatorVersion = string;
export type PlaybookId1 = string | null;
export type ProcessOutcome =
  "good_process_profit" | "good_process_loss" | "bad_process_profit" | "bad_process_loss" | "insufficient_evidence";
export type ReviewHash = string;
export type ReviewId = string;
export type EvidenceIds1 = string[];
export type ReasonCode = string;
export type RuleId = string;
export type Status2 = "passed" | "failed" | "unknown";
export type Summary1 = string;
export type RuleChecks = PlaybookRuleCheck[];
export type SchemaVersion = "1.0";
export type SessionId = string;
export type EvidenceId1 = string | null;
export type Kind1 = "plan" | "order" | "fill" | "user_annotation" | "ai_annotation" | "session_completed";
export type Label2 = string;
export type OccurredAt2 = string;
export type Timeline = ReviewTimelineItem[];
export type Reviews = TrainingReview[];
export type SchemaVersion1 = "1.0";

export interface TrainingReviewListResponse {
  dimensions: Dimensions;
  recommendation: TrainingRecommendation;
  reviews: Reviews;
  schema_version?: SchemaVersion1;
}
export interface CapabilityDimension {
  evaluated_count?: EvaluatedCount;
  key: Key;
  label: Label;
  passed_count?: PassedCount;
  sample_count: SampleCount;
  score?: Score;
  session_ids?: SessionIds;
  status: Status;
}
export interface TrainingRecommendation {
  dimension?: Dimension;
  playbook_id?: PlaybookId;
  reason: Reason;
  sample_count: SampleCount1;
  score?: Score1;
  setup_path?: SetupPath;
  status: Status1;
}
export interface TrainingReview {
  created_at: CreatedAt;
  dimension_observations?: DimensionObservations;
  equity_curve?: EquityCurve;
  evidence: Evidence;
  findings: Findings;
  metrics: Metrics;
  playbook_evaluator_version?: PlaybookEvaluatorVersion;
  playbook_id?: PlaybookId1;
  process_outcome: ProcessOutcome;
  review_hash: ReviewHash;
  review_id: ReviewId;
  rule_checks?: RuleChecks;
  schema_version?: SchemaVersion;
  session_id: SessionId;
  timeline?: Timeline;
}
export interface ReviewDimensionObservation {
  evaluated_count: EvaluatedCount1;
  evidence_ids?: EvidenceIds;
  key: Key1;
  passed_count: PassedCount1;
}
export interface EquityCurvePoint {
  equity: Equity;
  occurred_at: OccurredAt;
}
export interface EvidenceRef {
  evidence_id: EvidenceId;
  frame_id?: FrameId;
  kind: Kind;
  occurred_at?: OccurredAt1;
  price?: Price;
  summary: Summary;
}
export interface ReviewMetric {
  key: Key2;
  label: Label1;
  unit?: Unit;
  value: Value;
}
export interface PlaybookRuleCheck {
  evidence_ids?: EvidenceIds1;
  reason_code: ReasonCode;
  rule_id: RuleId;
  status: Status2;
  summary: Summary1;
}
export interface ReviewTimelineItem {
  evidence_id?: EvidenceId1;
  kind: Kind1;
  label: Label2;
  occurred_at: OccurredAt2;
}
