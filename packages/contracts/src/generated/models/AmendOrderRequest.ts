// Generated from Pydantic. Do not edit.

export type ActivationPrice = string | null;
export type CallbackRate = string | null;
export type CommandId = string;
export type ExpectedRevision = number;
export type GoodTillIndex = number | null;
export type LimitPrice = string | null;
export type OrderId = string;
export type Quantity = string | null;
export type StopPrice = string | null;

export interface AmendOrderRequest {
  activation_price?: ActivationPrice;
  callback_rate?: CallbackRate;
  command_id: CommandId;
  expected_revision: ExpectedRevision;
  good_till_index?: GoodTillIndex;
  limit_price?: LimitPrice;
  order_id: OrderId;
  quantity?: Quantity;
  stop_price?: StopPrice;
}
