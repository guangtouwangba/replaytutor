// Generated from Pydantic. Do not edit.

export type EndTime = string;
export type StartTime = string;
export type Symbol = string;
export type Timeframe = "1m";

export interface BinanceDownloadRequest {
  end_time: EndTime;
  start_time: StartTime;
  symbol: Symbol;
  timeframe?: Timeframe;
}
