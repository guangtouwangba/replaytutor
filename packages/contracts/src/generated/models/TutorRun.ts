// Generated from Pydantic. Do not edit.

export type AgentId = "codex-local";
export type CompletedAt = string | null;
export type ContextBundleId = string | null;
export type CreatedAt = string;
export type Error = string | null;
export type FrameId = string;
export type Question = string;
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
export type Shape = "line" | "zone" | "marker" | "label";
export type Annotations = TutorChartInstruction[];
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
export type RunId = string;
export type SchemaVersion1 = "1.0";
export type SessionId = string;
export type Stage = "environment" | "plan" | "position" | "exit" | "after_action";
export type Status1 = "running" | "completed" | "failed" | "cancelled" | "timed_out";

export interface TutorRun {
  agent_id?: AgentId;
  completed_at?: CompletedAt;
  context_bundle_id?: ContextBundleId;
  created_at: CreatedAt;
  error?: Error;
  frame_id: FrameId;
  question: Question;
  response?: TutorResponse | null;
  run_id: RunId;
  schema_version?: SchemaVersion1;
  session_id: SessionId;
  stage: Stage;
  status: Status1;
}
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
  evidence_ids: EvidenceIds;
  label: Label;
  points: Points;
  shape: Shape;
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
