// Generated from Pydantic. Do not edit.

export type CommandId = string;
export type EntryPrice = string | null;
export type ExpectedRevision = number;
export type Invalidation = string;
export type RiskAmount = string;
export type Side = "BUY" | "SELL";
export type StopPrice = string | null;
export type TargetPrice = string | null;
export type Thesis = string;

export interface LockTradePlanRequest {
  command_id: CommandId;
  entry_price?: EntryPrice;
  expected_revision: ExpectedRevision;
  invalidation: Invalidation;
  risk_amount: RiskAmount;
  side: Side;
  stop_price?: StopPrice;
  target_price?: TargetPrice;
  thesis: Thesis;
}
