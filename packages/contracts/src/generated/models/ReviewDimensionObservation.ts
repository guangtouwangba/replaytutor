// Generated from Pydantic. Do not edit.

export type EvaluatedCount = number;
export type EvidenceIds = string[];
export type Key = "environment" | "plan" | "risk" | "execution" | "management";
export type PassedCount = number;

export interface ReviewDimensionObservation {
  evaluated_count: EvaluatedCount;
  evidence_ids?: EvidenceIds;
  key: Key;
  passed_count: PassedCount;
}
