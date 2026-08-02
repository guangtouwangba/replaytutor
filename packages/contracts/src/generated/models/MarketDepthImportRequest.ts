// Generated from Pydantic. Do not edit.

/**
 * @minItems 1
 * @maxItems 5000
 */
export type Asks = [MarketDepthInputLevel, ...MarketDepthInputLevel[]];
export type Price = string;
export type Quantity = string;
/**
 * @minItems 1
 * @maxItems 5000
 */
export type Bids = [MarketDepthInputLevel, ...MarketDepthInputLevel[]];
export type CapturedAt = string;
export type LastUpdateId = number | null;

export interface MarketDepthImportRequest {
  asks: Asks;
  bids: Bids;
  captured_at: CapturedAt;
  last_update_id?: LastUpdateId;
}
export interface MarketDepthInputLevel {
  price: Price;
  quantity: Quantity;
}
