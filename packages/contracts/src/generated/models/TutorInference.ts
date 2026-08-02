// Generated from Pydantic. Do not edit.

export type Confidence = "low" | "medium" | "high";
export type EvidenceIds = string[];
export type Text = string;

export interface TutorInference {
  confidence: Confidence;
  evidence_ids?: EvidenceIds;
  text: Text;
}
