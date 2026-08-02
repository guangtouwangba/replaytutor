// Generated from Pydantic. Do not edit.

export type EvaluatedCount = number;
export type Key = "environment" | "plan" | "risk" | "execution" | "management";
export type Label = string;
export type PassedCount = number;
export type SampleCount = number;
export type Score = string | null;
export type SessionIds = string[];
export type Status = "insufficient" | "ready";

export interface CapabilityDimension {
  evaluated_count?: EvaluatedCount;
  key: Key;
  label: Label;
  passed_count?: PassedCount;
  sample_count: SampleCount;
  score?: Score;
  session_ids?: SessionIds;
  status: Status;
}
