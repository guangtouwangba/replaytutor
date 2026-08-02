// Generated from Pydantic. Do not edit.

export type AccountType = "SPOT" | "USDT_PERPETUAL";
export type FundingIntervalBars = number;
export type FundingRate = string;
export type HiddenRealDate = boolean;
export type InitialCash = string;
export type Leverage = number;
export type MaintenanceMarginRate = string;
export type MakerFeeRate = string;
export type MarginMode = "ISOLATED" | "CROSS";
export type PlaybookId = string | null;
export type PositionMode = "ONEWAY" | "HEDGE";
export type Seed = number;
export type SnapshotId = string;
export type StartMode = "beginning" | "random" | "specific";
export type StartTime = string | null;
export type TakerFeeRate = string;
export type WarmupBars = number;

export interface CreateSessionSpec {
  account_type?: AccountType;
  funding_interval_bars?: FundingIntervalBars;
  funding_rate?: FundingRate;
  hidden_real_date?: HiddenRealDate;
  initial_cash?: InitialCash;
  leverage?: Leverage;
  maintenance_margin_rate?: MaintenanceMarginRate;
  maker_fee_rate?: MakerFeeRate;
  margin_mode?: MarginMode;
  playbook_id?: PlaybookId;
  position_mode?: PositionMode;
  seed?: Seed;
  snapshot_id: SnapshotId;
  start_mode?: StartMode;
  start_time?: StartTime;
  taker_fee_rate?: TakerFeeRate;
  warmup_bars?: WarmupBars;
}
