// Generated from Pydantic. Do not edit.

export type EvidenceIds = string[];
export type ReasonCode = string;
export type RuleId = string;
export type Status = "passed" | "failed" | "unknown";
export type Summary = string;
export type Checks = PlaybookRuleCheck[];
export type EvaluatorVersion = string;
export type PlaybookId = string | null;
export type SchemaVersion = "1.0";

export interface PlaybookEvaluation {
  checks: Checks;
  evaluator_version: EvaluatorVersion;
  playbook_id?: PlaybookId;
  schema_version?: SchemaVersion;
}
export interface PlaybookRuleCheck {
  evidence_ids?: EvidenceIds;
  reason_code: ReasonCode;
  rule_id: RuleId;
  status: Status;
  summary: Summary;
}
