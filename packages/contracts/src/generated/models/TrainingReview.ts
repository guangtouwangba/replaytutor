// Generated from Pydantic. Do not edit.

export type CreatedAt = string;
export type EvidenceId = string;
export type FrameId = string | null;
export type Kind = "plan" | "order" | "fill" | "bar" | "metric";
export type OccurredAt = string | null;
export type Price = string | null;
export type Summary = string;
export type Evidence = EvidenceRef[];
export type Findings = string[];
export type Key =
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
export type Label = string;
export type Unit = string | null;
export type Value = string;
export type Metrics = ReviewMetric[];
export type ProcessOutcome =
  "good_process_profit" | "good_process_loss" | "bad_process_profit" | "bad_process_loss" | "insufficient_evidence";
export type ReviewHash = string;
export type ReviewId = string;
export type SchemaVersion = "1.0";
export type SessionId = string;

export interface TrainingReview {
  created_at: CreatedAt;
  evidence: Evidence;
  findings: Findings;
  metrics: Metrics;
  process_outcome: ProcessOutcome;
  review_hash: ReviewHash;
  review_id: ReviewId;
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
  key: Key;
  label: Label;
  unit?: Unit;
  value: Value;
}
