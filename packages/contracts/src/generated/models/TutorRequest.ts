// Generated from Pydantic. Do not edit.

/**
 * @maxItems 32
 */
export type ContextAnnotationIds = string[];
/**
 * @maxItems 8
 */
export type ContextIndicators =
  | []
  | [IndicatorSpec]
  | [IndicatorSpec, IndicatorSpec]
  | [IndicatorSpec, IndicatorSpec, IndicatorSpec]
  | [IndicatorSpec, IndicatorSpec, IndicatorSpec, IndicatorSpec]
  | [IndicatorSpec, IndicatorSpec, IndicatorSpec, IndicatorSpec, IndicatorSpec]
  | [IndicatorSpec, IndicatorSpec, IndicatorSpec, IndicatorSpec, IndicatorSpec, IndicatorSpec]
  | [IndicatorSpec, IndicatorSpec, IndicatorSpec, IndicatorSpec, IndicatorSpec, IndicatorSpec, IndicatorSpec]
  | [
      IndicatorSpec,
      IndicatorSpec,
      IndicatorSpec,
      IndicatorSpec,
      IndicatorSpec,
      IndicatorSpec,
      IndicatorSpec,
      IndicatorSpec
    ];
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
export type Locale = "en-US" | "zh-CN";
export type Question = string;
export type Stage = "environment" | "plan" | "position" | "exit" | "after_action";

export interface TutorRequest {
  context_annotation_ids?: ContextAnnotationIds;
  context_indicators?: ContextIndicators;
  locale?: Locale;
  question: Question;
  stage?: Stage;
}
export interface IndicatorSpec {
  definition_id: DefinitionId;
  instance_id: InstanceId;
  params?: Params;
  timeframe?: Timeframe;
}
