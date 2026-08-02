// Generated from Pydantic. Do not edit.

export type CreatedAt = string;
export type Description = string;
export type EvaluatorVersion = string;
export type Name = string;
export type Official = boolean;
export type PlaybookId = string;
export type EvaluatorKind =
  | "plan_locked_before_first_order"
  | "order_activated_on_next_bar"
  | "risk_amount_within_limit"
  | "protective_stop_present"
  | "no_order_after_session_complete"
  | "entry_side_matches_locked_plan"
  | "free_text";
export type Label = string;
export type RuleId = string;
export type RuleDefinitions = PlaybookRuleDefinition[];
/**
 * @minItems 1
 */
export type Rules = [string, ...string[]];
export type SchemaVersion = "1.0";
export type Slug = string;
export type Version = number;

export interface PlaybookVersion {
  created_at: CreatedAt;
  description: Description;
  evaluator_version: EvaluatorVersion;
  name: Name;
  official?: Official;
  playbook_id: PlaybookId;
  rule_definitions?: RuleDefinitions;
  rules: Rules;
  schema_version?: SchemaVersion;
  slug: Slug;
  version: Version;
}
export interface PlaybookRuleDefinition {
  evaluator_kind: EvaluatorKind;
  label: Label;
  params?: Params;
  rule_id: RuleId;
}
export interface Params {
  [k: string]: string;
}
