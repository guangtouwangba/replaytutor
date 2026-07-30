// Generated from Pydantic. Do not edit.

export type Commission = string;
export type CommissionAsset = string;
export type ExecutedAt = string;
export type FillId = string;
export type IsMaker = boolean;
export type OrderId = string;
export type PositionSide = "BOTH" | "LONG" | "SHORT";
export type Price = string;
export type Qty = string;
export type QuoteQty = string;
export type RealizedPnl = string;
export type SchemaVersion = "1.0";
export type Side = "BUY" | "SELL";
export type Symbol = string;
export type TradeId = string;

export interface ExecutionFill {
  commission: Commission;
  commission_asset: CommissionAsset;
  executed_at: ExecutedAt;
  fill_id: FillId;
  is_maker: IsMaker;
  order_id: OrderId;
  position_side: PositionSide;
  price: Price;
  qty: Qty;
  quote_qty: QuoteQty;
  realized_pnl: RealizedPnl;
  schema_version?: SchemaVersion;
  side: Side;
  symbol: Symbol;
  trade_id: TradeId;
}
