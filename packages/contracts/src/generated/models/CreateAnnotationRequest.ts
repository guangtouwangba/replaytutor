// Generated from Pydantic. Do not edit.

export type CommandId = string;
export type ExpectedRevision = number;
export type Label = string;
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
export type Shape = "line" | "zone" | "marker" | "label";

export interface CreateAnnotationRequest {
  command_id: CommandId;
  expected_revision: ExpectedRevision;
  label: Label;
  points: Points;
  shape: Shape;
}
export interface AnnotationPoint {
  price: Price;
  time: Time;
}
