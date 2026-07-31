// Generated from Pydantic. Do not edit.

export type EvidenceIds = string[];
export type ReasonCode = string;
export type RuleId = string;
export type Status = "passed" | "failed" | "unknown";
export type Summary = string;

export interface PlaybookRuleCheck {
  evidence_ids?: EvidenceIds;
  reason_code: ReasonCode;
  rule_id: RuleId;
  status: Status;
  summary: Summary;
}
