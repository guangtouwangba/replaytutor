// Generated from Pydantic. Do not edit.

export type EvidenceIds = string[];
export type Reason = string;
export type RuleId = string;
export type Status = "passed" | "failed" | "unknown";

export interface TutorRuleCheck {
  evidence_ids?: EvidenceIds;
  reason: Reason;
  rule_id: RuleId;
  status: Status;
}
