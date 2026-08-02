// Generated from Pydantic. Do not edit.

export type ActivateIndex = number;
export type ActivationPrice = string | null;
export type AverageFillPrice = string;
export type CallbackRate = string | null;
export type ClosePosition = boolean;
export type FilledAt = string | null;
export type FilledQuantity = string;
export type GoodTillIndex = number | null;
export type LimitPrice = string | null;
export type OcoGroupId = string | null;
export type OrderId = string;
export type OrderType =
  | "MARKET"
  | "LIMIT"
  | "STOP_MARKET"
  | "STOP_LIMIT"
  | "TAKE_PROFIT_MARKET"
  | "TAKE_PROFIT_LIMIT"
  | "TRAILING_STOP_MARKET";
export type ParentOrderId = string | null;
export type PlanId = string;
export type PositionSide = "BOTH" | "LONG" | "SHORT";
export type PostOnly = boolean;
export type Quantity = string;
export type ReduceOnly = boolean;
export type SchemaVersion = "1.0";
export type SessionId = string;
export type Side = "BUY" | "SELL";
export type Status = "PENDING" | "TRIGGERED" | "PARTIALLY_FILLED" | "FILLED" | "CANCELLED" | "EXPIRED" | "REJECTED";
export type StopPrice = string | null;
export type SubmittedAt = string;
export type SubmittedFrameId = string;
export type TimeInForce = "GTC" | "IOC" | "FOK" | "GTD";
export type TrailAnchorPrice = string | null;
export type TriggeredAtIndex = number | null;

export interface PaperOrder {
  activate_index: ActivateIndex;
  activation_price?: ActivationPrice;
  average_fill_price?: AverageFillPrice;
  callback_rate?: CallbackRate;
  close_position?: ClosePosition;
  filled_at?: FilledAt;
  filled_quantity?: FilledQuantity;
  good_till_index?: GoodTillIndex;
  limit_price?: LimitPrice;
  oco_group_id?: OcoGroupId;
  order_id: OrderId;
  order_type: OrderType;
  parent_order_id?: ParentOrderId;
  plan_id: PlanId;
  position_side?: PositionSide;
  post_only?: PostOnly;
  quantity: Quantity;
  reduce_only?: ReduceOnly;
  schema_version?: SchemaVersion;
  session_id: SessionId;
  side: Side;
  status: Status;
  stop_price?: StopPrice;
  submitted_at: SubmittedAt;
  submitted_frame_id: SubmittedFrameId;
  time_in_force?: TimeInForce;
  trail_anchor_price?: TrailAnchorPrice;
  triggered_at_index?: TriggeredAtIndex;
}
