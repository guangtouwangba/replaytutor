// Generated from Pydantic. Do not edit.

export type SchemaVersion = "1.0";
export type CreatedAt = string;
export type Fingerprint = string;
export type CurrentIndex = number;
export type FrameId = string;
export type Progress = number;
export type Revision = number;
export type SchemaVersion1 = "1.0";
export type SessionId = string;
export type TotalBars = number;
export type VisibleAt = string;
export type HiddenRealDate = boolean;
export type InitialCash = string;
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
export type SchemaVersion2 = "1.0";
export type TickSize = string;
export type Timezone = string;
export type Venue = string;
export type PlaybookId = string | null;
export type Revision1 = number;
export type SchemaVersion3 = "1.0";
export type Seed = number;
export type SessionId1 = string;
export type SnapshotId = string;
export type StartIndex = number;
export type Status = "ready" | "paused" | "completed" | "stopped";
export type Timeframe = "1m";
export type UpdatedAt = string;
export type WarmupBars = number;
export type Sessions = ReplaySession[];

export interface SessionListResponse {
  schema_version?: SchemaVersion;
  sessions: Sessions;
}
export interface ReplaySession {
  created_at: CreatedAt;
  fingerprint: Fingerprint;
  frame: ReplayFrame;
  hidden_real_date: HiddenRealDate;
  initial_cash: InitialCash;
  instrument: Instrument;
  playbook_id?: PlaybookId;
  revision: Revision1;
  schema_version?: SchemaVersion3;
  seed: Seed;
  session_id: SessionId1;
  snapshot_id: SnapshotId;
  start_index: StartIndex;
  status: Status;
  timeframe?: Timeframe;
  updated_at: UpdatedAt;
  warmup_bars: WarmupBars;
}
export interface ReplayFrame {
  current_index: CurrentIndex;
  frame_id: FrameId;
  progress: Progress;
  revision: Revision;
  schema_version?: SchemaVersion1;
  session_id: SessionId;
  total_bars: TotalBars;
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
  schema_version?: SchemaVersion2;
  tick_size: TickSize;
  timezone: Timezone;
  venue: Venue;
}
