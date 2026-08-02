// Generated from Pydantic. Do not edit.

export type ActivationPrice = string | null;
export type CallbackRate = string | null;
export type ClosePosition = boolean;
export type CommandId = string;
export type ExpectedRevision = number;
export type GoodTillIndex = number | null;
export type LimitPrice = string | null;
export type OrderType =
  | "MARKET"
  | "LIMIT"
  | "STOP_MARKET"
  | "STOP_LIMIT"
  | "TAKE_PROFIT_MARKET"
  | "TAKE_PROFIT_LIMIT"
  | "TRAILING_STOP_MARKET";
export type PositionSide = "BOTH" | "LONG" | "SHORT";
export type PostOnly = boolean;
export type ProtectiveStopPrice = string | null;
export type Quantity = string;
export type ReduceOnly = boolean;
export type Side = "BUY" | "SELL";
export type StopPrice = string | null;
export type TakeProfitPrice = string | null;
export type TimeInForce = "GTC" | "IOC" | "FOK" | "GTD";

export interface SubmitOrderRequest {
  activation_price?: ActivationPrice;
  callback_rate?: CallbackRate;
  close_position?: ClosePosition;
  command_id: CommandId;
  expected_revision: ExpectedRevision;
  good_till_index?: GoodTillIndex;
  limit_price?: LimitPrice;
  order_type: OrderType;
  position_side?: PositionSide;
  post_only?: PostOnly;
  protective_stop_price?: ProtectiveStopPrice;
  quantity: Quantity;
  reduce_only?: ReduceOnly;
  side: Side;
  stop_price?: StopPrice;
  take_profit_price?: TakeProfitPrice;
  time_in_force?: TimeInForce;
}
