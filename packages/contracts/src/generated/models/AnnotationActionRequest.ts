// Generated from Pydantic. Do not edit.

export type Action = "accepted" | "rejected" | "revised" | "deleted";
export type CommandId = string;
export type ExpectedRevision = number;
export type Label = string | null;
export type Points =
  | [AnnotationPoint]
  | [AnnotationPoint, AnnotationPoint]
  | [AnnotationPoint, AnnotationPoint, AnnotationPoint]
  | [AnnotationPoint, AnnotationPoint, AnnotationPoint, AnnotationPoint]
  | null;
export type Price = string;
export type Time = string;

export interface AnnotationActionRequest {
  action: Action;
  command_id: CommandId;
  expected_revision: ExpectedRevision;
  label?: Label;
  points?: Points;
}
export interface AnnotationPoint {
  price: Price;
  time: Time;
}
