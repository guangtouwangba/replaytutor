// Generated from Pydantic. Do not edit.

export type CoverageEnd = string;
export type CoverageStart = string;
export type CoverageStatus = "complete" | "partial" | "quota_blocked" | "failed";
export type Diagnostics = string[];
export type EpisodeCount = number;
export type FillCount = number;
export type IncomeCount = number;
export type OrderCount = number;
export type SchemaVersion = "1.0";
export type SyncId = string;

export interface TradeSyncResult {
  coverage_end: CoverageEnd;
  coverage_start: CoverageStart;
  coverage_status: CoverageStatus;
  diagnostics?: Diagnostics;
  episode_count: EpisodeCount;
  fill_count: FillCount;
  income_count: IncomeCount;
  order_count: OrderCount;
  schema_version?: SchemaVersion;
  sync_id: SyncId;
}
