// Generated from Pydantic. Do not edit.

export type DefinitionId = "MA" | "EMA" | "VOL" | "OBV" | "VWAP" | "ATR" | "BAR_COUNT" | "ORDER_BLOCK";
export type InstanceId = string;
/**
 * @maxItems 8
 */
export type Params =
  | []
  | [number]
  | [number, number]
  | [number, number, number]
  | [number, number, number, number]
  | [number, number, number, number, number]
  | [number, number, number, number, number, number]
  | [number, number, number, number, number, number, number]
  | [number, number, number, number, number, number, number, number];
export type Timeframe = "1m" | "5m" | "15m" | "1h" | "2h" | "4h" | "1d";

export interface IndicatorSpec {
  definition_id: DefinitionId;
  instance_id: InstanceId;
  params?: Params;
  timeframe?: Timeframe;
}
