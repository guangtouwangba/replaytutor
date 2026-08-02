// Generated from Pydantic. Do not edit.

export type AnnotationId = string | null;
export type EvidenceId = string;
export type FillId = string | null;
export type FrameId = string | null;
export type Kind = "plan" | "order" | "fill" | "bar" | "metric" | "user_annotation" | "ai_annotation";
export type Layer = ("user" | "ai") | null;
export type OccurredAt = string | null;
export type OrderId = string | null;
export type Price = string | null;
export type SchemaVersion = "1.0";
export type SessionId = string;

export interface EvidenceTarget {
  annotation_id?: AnnotationId;
  evidence_id: EvidenceId;
  fill_id?: FillId;
  frame_id?: FrameId;
  kind: Kind;
  layer?: Layer;
  occurred_at?: OccurredAt;
  order_id?: OrderId;
  price?: Price;
  schema_version?: SchemaVersion;
  session_id: SessionId;
}
