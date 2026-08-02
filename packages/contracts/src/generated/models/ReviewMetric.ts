// Generated from Pydantic. Do not edit.

export type Key =
  | "net_pnl"
  | "realized_pnl"
  | "fees"
  | "ending_equity"
  | "trade_count"
  | "win_rate"
  | "mfe"
  | "mae"
  | "r_multiple"
  | "max_drawdown"
  | "exit_efficiency";
export type Label = string;
export type Unit = string | null;
export type Value = string;

export interface ReviewMetric {
  key: Key;
  label: Label;
  unit?: Unit;
  value: Value;
}
