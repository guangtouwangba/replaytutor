// Generated from Pydantic. Do not edit.

export type CreatedAt = string;
export type EntryPrice = string | null;
export type FrameId = string;
export type Invalidation = string;
export type PlanId = string;
export type RiskAmount = string;
export type SchemaVersion = "1.0";
export type SessionId = string;
export type Side = "BUY" | "SELL";
export type Status = "locked";
export type StopPrice = string | null;
export type TargetPrice = string | null;
export type Thesis = string;

export interface TradePlan {
  created_at: CreatedAt;
  entry_price?: EntryPrice;
  frame_id: FrameId;
  invalidation: Invalidation;
  plan_id: PlanId;
  risk_amount: RiskAmount;
  schema_version?: SchemaVersion;
  session_id: SessionId;
  side: Side;
  status: Status;
  stop_price?: StopPrice;
  target_price?: TargetPrice;
  thesis: Thesis;
}
