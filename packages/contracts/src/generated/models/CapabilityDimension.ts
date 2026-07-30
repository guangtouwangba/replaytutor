// Generated from Pydantic. Do not edit.

export type Key = "environment" | "plan" | "risk" | "execution" | "management";
export type Label = string;
export type SampleCount = number;
export type Score = string | null;
export type Status = "insufficient" | "ready";

export interface CapabilityDimension {
  key: Key;
  label: Label;
  sample_count: SampleCount;
  score?: Score;
  status: Status;
}
