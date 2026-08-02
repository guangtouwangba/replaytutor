// Generated from Pydantic. Do not edit.

export type ContentHash = string;
export type CoverageEnd = string;
export type CoverageStart = string;
export type CreatedAt = string;
export type DerivedTimeframes = ("1m" | "5m" | "15m" | "1h" | "2h" | "4h" | "1d")[];
export type Immutable = true;
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
export type SchemaVersion = "1.0";
export type TickSize = string;
export type Timezone = string;
export type Venue = string;
export type ManifestHash = string;
export type DuplicateCount = number;
export type Flags = string[];
export type GapCount = number;
export type InvalidOhlcCount = number;
export type RowCount = number;
export type Status = "passed" | "warning" | "failed";
export type SchemaVersion1 = "1.0";
export type SnapshotId = string;
export type SourceId = string;
export type SourceKind = "golden" | "binance_public" | "binance_usdm" | "file_import";
export type Timeframe = "1m" | "5m" | "15m" | "1h" | "2h" | "4h" | "1d";

export interface DataSnapshot {
  content_hash: ContentHash;
  coverage_end: CoverageEnd;
  coverage_start: CoverageStart;
  created_at: CreatedAt;
  derived_timeframes?: DerivedTimeframes;
  immutable?: Immutable;
  instrument: Instrument;
  manifest_hash: ManifestHash;
  quality: DataQuality;
  schema_version?: SchemaVersion1;
  snapshot_id: SnapshotId;
  source_id: SourceId;
  source_kind: SourceKind;
  timeframe: Timeframe;
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
  schema_version?: SchemaVersion;
  tick_size: TickSize;
  timezone: Timezone;
  venue: Venue;
}
export interface DataQuality {
  duplicate_count: DuplicateCount;
  flags?: Flags;
  gap_count: GapCount;
  invalid_ohlc_count: InvalidOhlcCount;
  row_count: RowCount;
  status: Status;
}
