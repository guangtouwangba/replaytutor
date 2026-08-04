// Generated from Pydantic. Do not edit.

export type SchemaVersion = "1.0";
export type FrameId = string;
export type AssetClass = "crypto_spot" | "crypto_perpetual" | "equity";
export type BaseCurrency = string;
export type CanonicalSymbol = string;
export type DisplayName = string;
export type InstrumentId = string;
export type LotSize = string;
export type Market = "CRYPTO" | "CN";
export type MarketRuleSetId = string;
export type PriceScale = number;
export type QuoteCurrency = string;
export type SchemaVersion1 = "1.0";
export type TickSize = string;
export type Timezone = string;
export type Venue = string;
export type Revision = number;
export type SchemaVersion2 = "1.0";
export type SessionId = string;
export type SnapshotId = string;
export type Status = "ready" | "paused" | "completed" | "stopped";
export type UpdatedAt = string;
export type VisibleAt = string;

export interface CompanionSessionStateResult {
  schema_version?: SchemaVersion;
  session: CompanionSessionSummary;
}
export interface CompanionSessionSummary {
  frame_id: FrameId;
  instrument: Instrument;
  revision: Revision;
  schema_version?: SchemaVersion2;
  session_id: SessionId;
  snapshot_id: SnapshotId;
  status: Status;
  updated_at: UpdatedAt;
  visible_at: VisibleAt;
}
export interface Instrument {
  asset_class: AssetClass;
  base_currency: BaseCurrency;
  canonical_symbol: CanonicalSymbol;
  display_name: DisplayName;
  instrument_id: InstrumentId;
  lot_size: LotSize;
  market: Market;
  market_rule_set_id: MarketRuleSetId;
  price_scale: PriceScale;
  quote_currency: QuoteCurrency;
  schema_version?: SchemaVersion1;
  tick_size: TickSize;
  timezone: Timezone;
  venue: Venue;
}
