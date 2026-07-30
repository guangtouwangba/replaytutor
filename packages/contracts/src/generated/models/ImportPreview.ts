// Generated from Pydantic. Do not edit.

export type Error = string | null;
export type Filename = string;
export type ImportId = string;
export type DuplicateCount = number;
export type Flags = string[];
export type GapCount = number;
export type InvalidOhlcCount = number;
export type RowCount = number;
export type Status = "passed" | "warning" | "failed";
export type SampleRows = {
  [k: string]: string;
}[];
export type SchemaVersion = "1.0";
export type Status1 = "preview_ready" | "failed" | "committed";

export interface ImportPreview {
  detected_columns: DetectedColumns;
  error?: Error;
  filename: Filename;
  import_id: ImportId;
  quality: DataQuality;
  sample_rows: SampleRows;
  schema_version?: SchemaVersion;
  status: Status1;
}
export interface DetectedColumns {
  [k: string]: string;
}
export interface DataQuality {
  duplicate_count: DuplicateCount;
  flags?: Flags;
  gap_count: GapCount;
  invalid_ohlc_count: InvalidOhlcCount;
  row_count: RowCount;
  status: Status;
}
