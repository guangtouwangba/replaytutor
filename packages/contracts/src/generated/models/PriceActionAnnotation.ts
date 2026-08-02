// Generated from Pydantic. Do not edit.

export type AnnotationId = string;
export type Confidence = number;
export type Evidence = string;
export type Label = string;
export type Layer = "background" | "location" | "setup" | "trigger" | "execution" | "management";
export type Perspective = "decision_time" | "after_action";
export type Price = string;
export type Time = string;
export type Points = AnnotationPoint[];
export type RuleId = string;
export type SchemaVersion = "1.0";
export type Shape = "line" | "zone" | "marker" | "label" | "path";
export type Timeframe = "1m" | "5m" | "15m" | "1h" | "2h" | "4h" | "1d";
export type Verdict = "correct" | "improve" | "neutral" | "unknown";

export interface PriceActionAnnotation {
  annotation_id: AnnotationId;
  confidence: Confidence;
  evidence: Evidence;
  label: Label;
  layer: Layer;
  perspective: Perspective;
  points: Points;
  rule_id: RuleId;
  schema_version?: SchemaVersion;
  shape: Shape;
  timeframe: Timeframe;
  verdict: Verdict;
}
export interface AnnotationPoint {
  price: Price;
  time: Time;
}
