// Generated from Pydantic. Do not edit.

export type ExecutedAt = string;
export type Fee = string;
export type FillId = string;
export type FrameId = string;
export type OrderId = string;
export type Price = string;
export type Quantity = string;
export type QuoteAmount = string;
export type SchemaVersion = "1.0";
export type SessionId = string;
export type Side = "BUY" | "SELL";
export type Fills = PaperFill[];
export type ActivateIndex = number;
export type FilledAt = string | null;
export type LimitPrice = string | null;
export type OcoGroupId = string | null;
export type OrderId1 = string;
export type OrderType = "MARKET" | "LIMIT" | "STOP_MARKET";
export type ParentOrderId = string | null;
export type PlanId = string;
export type Quantity1 = string;
export type SchemaVersion1 = "1.0";
export type SessionId1 = string;
export type Side1 = "BUY" | "SELL";
export type Status = "PENDING" | "FILLED" | "CANCELLED" | "REJECTED";
export type StopPrice = string | null;
export type SubmittedAt = string;
export type SubmittedFrameId = string;
export type Orders = PaperOrder[];
export type CreatedAt = string;
export type EntryPrice = string | null;
export type FrameId1 = string;
export type Invalidation = string;
export type PlanId1 = string;
export type RiskAmount = string;
export type SchemaVersion2 = "1.0";
export type SessionId2 = string;
export type Side2 = "BUY" | "SELL";
export type Status1 = "locked";
export type StopPrice1 = string | null;
export type TargetPrice = string | null;
export type Thesis = string;
export type AverageEntryPrice = string;
export type Cash = string;
export type FeesPaid = string;
export type PositionQuantity = string;
export type RealizedPnl = string;
export type SchemaVersion3 = "1.0";
export type SchemaVersion4 = "1.0";

export interface ExecutionSnapshot {
  fills?: Fills;
  orders?: Orders;
  plan?: TradePlan | null;
  portfolio: PortfolioState;
  schema_version?: SchemaVersion4;
}
export interface PaperFill {
  executed_at: ExecutedAt;
  fee: Fee;
  fill_id: FillId;
  frame_id: FrameId;
  order_id: OrderId;
  price: Price;
  quantity: Quantity;
  quote_amount: QuoteAmount;
  schema_version?: SchemaVersion;
  session_id: SessionId;
  side: Side;
}
export interface PaperOrder {
  activate_index: ActivateIndex;
  filled_at?: FilledAt;
  limit_price?: LimitPrice;
  oco_group_id?: OcoGroupId;
  order_id: OrderId1;
  order_type: OrderType;
  parent_order_id?: ParentOrderId;
  plan_id: PlanId;
  quantity: Quantity1;
  schema_version?: SchemaVersion1;
  session_id: SessionId1;
  side: Side1;
  status: Status;
  stop_price?: StopPrice;
  submitted_at: SubmittedAt;
  submitted_frame_id: SubmittedFrameId;
}
export interface TradePlan {
  created_at: CreatedAt;
  entry_price?: EntryPrice;
  frame_id: FrameId1;
  invalidation: Invalidation;
  plan_id: PlanId1;
  risk_amount: RiskAmount;
  schema_version?: SchemaVersion2;
  session_id: SessionId2;
  side: Side2;
  status: Status1;
  stop_price?: StopPrice1;
  target_price?: TargetPrice;
  thesis: Thesis;
}
export interface PortfolioState {
  average_entry_price: AverageEntryPrice;
  cash: Cash;
  fees_paid: FeesPaid;
  position_quantity: PositionQuantity;
  realized_pnl: RealizedPnl;
  schema_version?: SchemaVersion3;
}
