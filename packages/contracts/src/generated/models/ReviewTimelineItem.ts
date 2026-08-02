// Generated from Pydantic. Do not edit.

export type EvidenceId = string | null;
export type Kind = "plan" | "order" | "fill" | "user_annotation" | "ai_annotation" | "session_completed";
export type Label = string;
export type OccurredAt = string;

export interface ReviewTimelineItem {
  evidence_id?: EvidenceId;
  kind: Kind;
  label: Label;
  occurred_at: OccurredAt;
}
