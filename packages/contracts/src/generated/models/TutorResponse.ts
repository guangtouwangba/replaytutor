// Generated from Pydantic. Do not edit.

/**
 * @maxItems 8
 */
export type Annotations =
  | []
  | [TutorChartInstruction]
  | [TutorChartInstruction, TutorChartInstruction]
  | [TutorChartInstruction, TutorChartInstruction, TutorChartInstruction]
  | [TutorChartInstruction, TutorChartInstruction, TutorChartInstruction, TutorChartInstruction]
  | [TutorChartInstruction, TutorChartInstruction, TutorChartInstruction, TutorChartInstruction, TutorChartInstruction]
  | [
      TutorChartInstruction,
      TutorChartInstruction,
      TutorChartInstruction,
      TutorChartInstruction,
      TutorChartInstruction,
      TutorChartInstruction
    ]
  | [
      TutorChartInstruction,
      TutorChartInstruction,
      TutorChartInstruction,
      TutorChartInstruction,
      TutorChartInstruction,
      TutorChartInstruction,
      TutorChartInstruction
    ]
  | [
      TutorChartInstruction,
      TutorChartInstruction,
      TutorChartInstruction,
      TutorChartInstruction,
      TutorChartInstruction,
      TutorChartInstruction,
      TutorChartInstruction,
      TutorChartInstruction
    ];
export type AnnotationId = string | null;
export type EvidenceIds = string[];
export type Label = string;
/**
 * @minItems 1
 * @maxItems 16
 */
export type Points =
  | [AnnotationPoint]
  | [AnnotationPoint, AnnotationPoint]
  | [AnnotationPoint, AnnotationPoint, AnnotationPoint]
  | [AnnotationPoint, AnnotationPoint, AnnotationPoint, AnnotationPoint]
  | [AnnotationPoint, AnnotationPoint, AnnotationPoint, AnnotationPoint, AnnotationPoint]
  | [AnnotationPoint, AnnotationPoint, AnnotationPoint, AnnotationPoint, AnnotationPoint, AnnotationPoint]
  | [
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint
    ]
  | [
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint
    ]
  | [
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint
    ]
  | [
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint
    ]
  | [
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint
    ]
  | [
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint
    ]
  | [
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint
    ]
  | [
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint
    ]
  | [
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint
    ]
  | [
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint
    ];
export type Price = string;
export type Time = string;
export type Purpose = "trend" | "support" | "resistance" | "channel";
export type Shape = "line" | "zone" | "marker" | "label";
export type Timeframe = "1m" | "5m" | "15m" | "1h" | "2h" | "4h" | "1d";
export type Tool = "trend_line" | "horizontal_line" | "parallel_channel" | "zone";
export type Disclaimer = string;
export type Confidence = "low" | "medium" | "high";
export type EvidenceIds1 = string[];
export type Text = string;
export type Inferences = TutorInference[];
export type NextQuestions = string[];
export type EvidenceIds2 = string[];
export type Text1 = string;
export type Observations = TutorObservation[];
export type RisksAndUnknowns = string[];
export type EvidenceIds3 = string[];
export type Reason = string;
export type RuleId = string;
export type Status = "passed" | "failed" | "unknown";
export type RuleChecks = TutorRuleCheck[];
export type SchemaVersion = "1.0";
export type Summary = string;

export interface TutorResponse {
  annotations?: Annotations;
  disclaimer: Disclaimer;
  inferences?: Inferences;
  next_questions?: NextQuestions;
  observations?: Observations;
  risks_and_unknowns?: RisksAndUnknowns;
  rule_checks?: RuleChecks;
  schema_version?: SchemaVersion;
  summary: Summary;
}
export interface TutorChartInstruction {
  annotation_id?: AnnotationId;
  evidence_ids: EvidenceIds;
  label: Label;
  points: Points;
  purpose: Purpose;
  shape: Shape;
  timeframe: Timeframe;
  tool: Tool;
}
export interface AnnotationPoint {
  price: Price;
  time: Time;
}
export interface TutorInference {
  confidence: Confidence;
  evidence_ids?: EvidenceIds1;
  text: Text;
}
export interface TutorObservation {
  evidence_ids?: EvidenceIds2;
  text: Text1;
}
export interface TutorRuleCheck {
  evidence_ids?: EvidenceIds3;
  reason: Reason;
  rule_id: RuleId;
  status: Status;
}
