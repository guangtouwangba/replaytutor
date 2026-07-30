// Generated from Pydantic. Do not edit.

export type HiddenRealDate = boolean;
export type InitialCash = string;
export type PlaybookId = string | null;
export type Seed = number;
export type SnapshotId = string;
export type StartMode = "beginning" | "random";
export type WarmupBars = number;

export interface CreateSessionSpec {
  hidden_real_date?: HiddenRealDate;
  initial_cash?: InitialCash;
  playbook_id?: PlaybookId;
  seed?: Seed;
  snapshot_id: SnapshotId;
  start_mode?: StartMode;
  warmup_bars?: WarmupBars;
}
