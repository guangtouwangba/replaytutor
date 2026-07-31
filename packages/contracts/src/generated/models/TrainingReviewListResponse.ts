// Generated from Pydantic. Do not edit.

export type Key = "environment" | "plan" | "risk" | "execution" | "management";
export type Label = string;
export type SampleCount = number;
export type Score = string | null;
export type Status = "insufficient" | "ready";
export type Dimensions = CapabilityDimension[];
export type CreatedAt = string;
export type EvidenceId = string;
export type FrameId = string | null;
export type Kind = "plan" | "order" | "fill" | "bar" | "metric" | "user_annotation" | "ai_annotation";
export type OccurredAt = string | null;
export type Price = string | null;
export type Summary = string;
export type Evidence = EvidenceRef[];
export type Findings = string[];
export type Key1 =
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
export type PlaybookId = string | null;
export type ProcessOutcome =
  "good_process_profit" | "good_process_loss" | "bad_process_profit" | "bad_process_loss" | "insufficient_evidence";
export type ReviewHash = string;
export type ReviewId = string;
export type EvidenceIds = string[];
export type ReasonCode = string;
export type RuleId = string;
export type Status1 = "passed" | "failed" | "unknown";
export type Summary1 = string;
export type RuleChecks = PlaybookRuleCheck[];
export type SchemaVersion = "1.0";
export type SessionId = string;
export type Reviews = TrainingReview[];
export type SchemaVersion1 = "1.0";

export interface TrainingReviewListResponse {
  dimensions: Dimensions;
  reviews: Reviews;
  schema_version?: SchemaVersion1;
}
export interface CapabilityDimension {
  key: Key;
  label: Label;
  sample_count: SampleCount;
  score?: Score;
  status: Status;
}
export interface TrainingReview {
  created_at: CreatedAt;
  evidence: Evidence;
  findings: Findings;
  metrics: Metrics;
  playbook_evaluator_version?: PlaybookEvaluatorVersion;
  playbook_id?: PlaybookId;
  process_outcome: ProcessOutcome;
  review_hash: ReviewHash;
  review_id: ReviewId;
  rule_checks?: RuleChecks;
  schema_version?: SchemaVersion;
  session_id: SessionId;
}
export interface EvidenceRef {
  evidence_id: EvidenceId;
  frame_id?: FrameId;
  kind: Kind;
  occurred_at?: OccurredAt;
  price?: Price;
  summary: Summary;
}
export interface ReviewMetric {
  key: Key1;
  label: Label1;
  unit?: Unit;
  value: Value;
}
export interface PlaybookRuleCheck {
  evidence_ids?: EvidenceIds;
  reason_code: ReasonCode;
  rule_id: RuleId;
  status: Status1;
  summary: Summary1;
}
