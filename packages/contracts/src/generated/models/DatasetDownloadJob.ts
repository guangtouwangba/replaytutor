// Generated from Pydantic. Do not edit.

export type CompletedBars = number;
export type CreatedAt = string;
export type EndTime = string;
export type Error = string | null;
export type FinishedAt = string | null;
export type JobId = string;
export type Kind = "binance_market_data";
export type MarketType = "SPOT" | "USDT_PERPETUAL";
export type Progress = number;
export type SchemaVersion = "1.0";
export type SnapshotId = string | null;
export type StartTime = string;
export type StartedAt = string | null;
export type Status = "queued" | "running" | "succeeded" | "failed";
export type Symbol = string;
export type Timeframe = "1m";
export type TotalBars = number;

export interface DatasetDownloadJob {
  completed_bars: CompletedBars;
  created_at: CreatedAt;
  end_time: EndTime;
  error?: Error;
  finished_at?: FinishedAt;
  job_id: JobId;
  kind?: Kind;
  market_type: MarketType;
  progress: Progress;
  schema_version?: SchemaVersion;
  snapshot_id?: SnapshotId;
  start_time: StartTime;
  started_at?: StartedAt;
  status: Status;
  symbol: Symbol;
  timeframe?: Timeframe;
  total_bars: TotalBars;
}
