// Generated from Pydantic. Do not edit.

export type DuplicateCount = number;
export type Flags = string[];
export type GapCount = number;
export type InvalidOhlcCount = number;
export type RowCount = number;
export type Status = "passed" | "warning" | "failed";

export interface DataQuality {
  duplicate_count: DuplicateCount;
  flags?: Flags;
  gap_count: GapCount;
  invalid_ohlc_count: InvalidOhlcCount;
  row_count: RowCount;
  status: Status;
}
