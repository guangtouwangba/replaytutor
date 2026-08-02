// Generated from Pydantic. Do not edit.

export type EndTime = string;
export type MarketType = "SPOT" | "USDT_PERPETUAL";
export type StartTime = string;
export type Symbol = string;
export type Timeframe = "1m";

export interface BinanceDownloadRequest {
  end_time: EndTime;
  market_type?: MarketType;
  start_time: StartTime;
  symbol: Symbol;
  timeframe?: Timeframe;
}
