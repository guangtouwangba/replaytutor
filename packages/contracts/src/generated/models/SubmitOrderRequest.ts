// Generated from Pydantic. Do not edit.

export type CommandId = string;
export type ExpectedRevision = number;
export type LimitPrice = string | null;
export type OrderType = "MARKET" | "LIMIT" | "STOP_MARKET";
export type ProtectiveStopPrice = string | null;
export type Quantity = string;
export type Side = "BUY" | "SELL";
export type StopPrice = string | null;
export type TakeProfitPrice = string | null;

export interface SubmitOrderRequest {
  command_id: CommandId;
  expected_revision: ExpectedRevision;
  limit_price?: LimitPrice;
  order_type: OrderType;
  protective_stop_price?: ProtectiveStopPrice;
  quantity: Quantity;
  side: Side;
  stop_price?: StopPrice;
  take_profit_price?: TakeProfitPrice;
}
