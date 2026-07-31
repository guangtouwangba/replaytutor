// Generated from Pydantic. Do not edit.

export type AnnotationId = string;
export type EffectiveLabel = string;
/**
 * @minItems 1
 * @maxItems 4
 */
export type EffectivePoints =
  | [AnnotationPoint]
  | [AnnotationPoint, AnnotationPoint]
  | [AnnotationPoint, AnnotationPoint, AnnotationPoint]
  | [AnnotationPoint, AnnotationPoint, AnnotationPoint, AnnotationPoint];
export type Price = string;
export type Time = string;
export type LatestEventId = string | null;
export type AnnotationId1 = string;
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
export type ProvenanceRunId = string | null;
export type SchemaVersion = "1.0";
export type SessionId = string;
export type Shape = "line" | "zone" | "marker" | "label";
export type SchemaVersion1 = "1.0";
export type State = "active" | "proposed" | "accepted" | "rejected" | "deleted";

export interface AnnotationDisposition {
  annotation_id: AnnotationId;
  effective_label: EffectiveLabel;
  effective_points: EffectivePoints;
  latest_event_id?: LatestEventId;
  original_annotation: ChartAnnotation;
  schema_version?: SchemaVersion1;
  state: State;
}
export interface AnnotationPoint {
  price: Price;
  time: Time;
}
export interface ChartAnnotation {
  annotation_id: AnnotationId1;
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
