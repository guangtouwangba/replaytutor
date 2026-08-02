// Generated from Pydantic. Do not edit.

export type Adjustment = "raw" | "forward" | "backward";
export type LotSize = string;
export type Market = "CRYPTO" | "CN";
export type QuoteCurrency = string;
export type Symbol = string;
export type TickSize = string;
export type Timezone = string;
export type Venue = string;

export interface CommitImportRequest {
  adjustment: Adjustment;
  lot_size: LotSize;
  market: Market;
  quote_currency: QuoteCurrency;
  symbol: Symbol;
  tick_size: TickSize;
  timezone: Timezone;
  venue: Venue;
}
