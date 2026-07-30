// Generated from Pydantic. Do not edit.

export type AnnotationId = string;
export type CreatedAt = string;
export type FrameId = string;
export type Label = string;
export type Layer = "user" | "ai";
/**
 * @minItems 1
 * @maxItems 4
 */
export type Points =
  | [AnnotationPoint]
  | [AnnotationPoint, AnnotationPoint]
  | [AnnotationPoint, AnnotationPoint, AnnotationPoint]
  | [AnnotationPoint, AnnotationPoint, AnnotationPoint, AnnotationPoint];
export type Price = string;
export type Time = string;
export type ProvenanceRunId = string | null;
export type SchemaVersion = "1.0";
export type SessionId = string;
export type Shape = "line" | "zone" | "marker" | "label";

export interface ChartAnnotation {
  annotation_id: AnnotationId;
  created_at: CreatedAt;
  frame_id: FrameId;
  label: Label;
  layer: Layer;
  points: Points;
  provenance_run_id?: ProvenanceRunId;
  schema_version?: SchemaVersion;
  session_id: SessionId;
  shape: Shape;
}
export interface AnnotationPoint {
  price: Price;
  time: Time;
}
