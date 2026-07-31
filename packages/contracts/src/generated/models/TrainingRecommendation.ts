// Generated from Pydantic. Do not edit.

export type Dimension = ("environment" | "plan" | "risk" | "execution" | "management") | null;
export type PlaybookId = string | null;
export type Reason = string;
export type SampleCount = number;
export type Score = string | null;
export type SetupPath = string;
export type Status = "insufficient" | "ready";

export interface TrainingRecommendation {
  dimension?: Dimension;
  playbook_id?: PlaybookId;
  reason: Reason;
  sample_count: SampleCount;
  score?: Score;
  setup_path?: SetupPath;
  status: Status;
}
