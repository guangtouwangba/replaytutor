// Generated from Pydantic. Do not edit.

export type CalculationVersion = string;
export type DefinitionId = "MA" | "EMA" | "VOL" | "OBV" | "VWAP" | "ATR" | "BAR_COUNT" | "ORDER_BLOCK";
export type EvidenceId = string;
export type FrameId = string;
export type InstanceId = string;
export type Params = number[];
export type BarId = string;
export type Time = string;
/**
 * @maxItems 50
 */
export type Points = IndicatorEvidencePoint[];
export type SchemaVersion = "1.0";
export type Status = "ready" | "insufficient_data";
export type Timeframe = "1m" | "5m" | "15m" | "1h" | "2h" | "4h" | "1d";
export type VisibleAt = string;

export interface IndicatorEvidence {
  calculation_version: CalculationVersion;
  definition_id: DefinitionId;
  evidence_id: EvidenceId;
  frame_id: FrameId;
  instance_id: InstanceId;
  params?: Params;
  points?: Points;
  schema_version?: SchemaVersion;
  status: Status;
  timeframe: Timeframe;
  visible_at: VisibleAt;
}
export interface IndicatorEvidencePoint {
  bar_id: BarId;
  time: Time;
  values?: Values;
}
export interface Values {
  [k: string]: string;
}
