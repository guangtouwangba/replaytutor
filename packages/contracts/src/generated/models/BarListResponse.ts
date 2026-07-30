// Generated from Pydantic. Do not edit.

export type Close = string;
export type High = string;
export type Low = string;
export type Open = string;
export type Volume = string;
export type BarId = string;
export type CloseTime = string;
export type InstrumentId = string;
export type OpenTime = string;
export type QualityFlags = string[];
export type SchemaVersion = "1.0";
export type Timeframe = "1m" | "5m" | "15m" | "1h" | "2h" | "4h" | "1d";
export type Bars = Bar[];
export type HasMore = boolean;
export type SchemaVersion1 = "1.0";
export type SnapshotId = string;
export type Timeframe1 = "1m" | "5m" | "15m" | "1h" | "2h" | "4h" | "1d";

export interface BarListResponse {
  bars: Bars;
  has_more: HasMore;
  schema_version?: SchemaVersion1;
  snapshot_id: SnapshotId;
  timeframe: Timeframe1;
}
export interface Bar {
  adjusted?: PriceValues | null;
  bar_id: BarId;
  close_time: CloseTime;
  instrument_id: InstrumentId;
  open_time: OpenTime;
  quality_flags?: QualityFlags;
  raw: PriceValues;
  schema_version?: SchemaVersion;
  timeframe: Timeframe;
}
export interface PriceValues {
  close: Close;
  high: High;
  low: Low;
  open: Open;
  volume: Volume;
}
