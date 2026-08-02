// Generated from Pydantic. Do not edit.

export type CumulativeNotional = string;
export type CumulativeQuantity = string;
export type Notional = string;
export type Price = string;
export type Quantity = string;
export type Asks = MarketDepthLevel[];
export type BestAsk = string;
export type BestBid = string;
export type Bids = MarketDepthLevel[];
export type CapturedAt = string;
export type DepthId = string;
export type InstrumentId = string;
export type LastUpdateId = number | null;
export type Midpoint = string;
export type SchemaVersion = "1.0";
export type SnapshotId = string;
export type SourceKind = "binance_rest" | "file_import";
export type Spread = string;

export interface MarketDepthSnapshot {
  asks: Asks;
  best_ask: BestAsk;
  best_bid: BestBid;
  bids: Bids;
  captured_at: CapturedAt;
  depth_id: DepthId;
  instrument_id: InstrumentId;
  last_update_id?: LastUpdateId;
  midpoint: Midpoint;
  schema_version?: SchemaVersion;
  snapshot_id: SnapshotId;
  source_kind: SourceKind;
  spread: Spread;
}
export interface MarketDepthLevel {
  cumulative_notional: CumulativeNotional;
  cumulative_quantity: CumulativeQuantity;
  notional: Notional;
  price: Price;
  quantity: Quantity;
}
