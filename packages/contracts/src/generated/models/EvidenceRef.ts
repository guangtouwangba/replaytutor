// Generated from Pydantic. Do not edit.

export type EvidenceId = string;
export type FrameId = string | null;
export type Kind = "plan" | "order" | "fill" | "bar" | "metric";
export type OccurredAt = string | null;
export type Price = string | null;
export type Summary = string;

export interface EvidenceRef {
  evidence_id: EvidenceId;
  frame_id?: FrameId;
  kind: Kind;
  occurred_at?: OccurredAt;
  price?: Price;
  summary: Summary;
}
