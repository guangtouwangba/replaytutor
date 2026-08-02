// Generated from Pydantic. Do not edit.

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

export interface PlaybookRuleDefinition {
  evaluator_kind: EvaluatorKind;
  label: Label;
  params?: Params;
  rule_id: RuleId;
}
export interface Params {
  [k: string]: string;
}
