// Generated from Pydantic. Do not edit.

export type ActivateIndex = number;
export type FilledAt = string | null;
export type LimitPrice = string | null;
export type OcoGroupId = string | null;
export type OrderId = string;
export type OrderType = "MARKET" | "LIMIT" | "STOP_MARKET";
export type ParentOrderId = string | null;
export type PlanId = string;
export type Quantity = string;
export type SchemaVersion = "1.0";
export type SessionId = string;
export type Side = "BUY" | "SELL";
export type Status = "PENDING" | "FILLED" | "CANCELLED" | "REJECTED";
export type StopPrice = string | null;
export type SubmittedAt = string;
export type SubmittedFrameId = string;

export interface PaperOrder {
  activate_index: ActivateIndex;
  filled_at?: FilledAt;
  limit_price?: LimitPrice;
  oco_group_id?: OcoGroupId;
  order_id: OrderId;
  order_type: OrderType;
  parent_order_id?: ParentOrderId;
  plan_id: PlanId;
  quantity: Quantity;
  schema_version?: SchemaVersion;
  session_id: SessionId;
  side: Side;
  status: Status;
  stop_price?: StopPrice;
  submitted_at: SubmittedAt;
  submitted_frame_id: SubmittedFrameId;
}
