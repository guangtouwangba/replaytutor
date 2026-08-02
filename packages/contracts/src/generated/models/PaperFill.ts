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
