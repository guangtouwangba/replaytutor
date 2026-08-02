// Generated from Pydantic. Do not edit.

export type ClosedAt = string | null;
export type Commission = string;
export type Direction = "long" | "short";
export type EntryPrice = string;
export type EpisodeId = string;
export type ExitPrice = string | null;
export type FillCount = number;
export type OpenedAt = string;
export type PeakQty = string;
export type PositionSide = "BOTH" | "LONG" | "SHORT";
export type RealizedPnl = string;
export type SchemaVersion = "1.0";
export type Status = "open" | "closed";
export type Symbol = string;

export interface TradeEpisode {
  closed_at: ClosedAt;
  commission: Commission;
  direction: Direction;
  entry_price: EntryPrice;
  episode_id: EpisodeId;
  exit_price: ExitPrice;
  fill_count: FillCount;
  opened_at: OpenedAt;
  peak_qty: PeakQty;
  position_side: PositionSide;
  realized_pnl: RealizedPnl;
  schema_version?: SchemaVersion;
  status: Status;
  symbol: Symbol;
}
