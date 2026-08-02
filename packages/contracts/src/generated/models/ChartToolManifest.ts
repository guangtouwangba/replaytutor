// Generated from Pydantic. Do not edit.

export type AlgorithmVersion = string;
export type GeometryKind =
  | "point"
  | "line"
  | "channel"
  | "region"
  | "polyline"
  | "levels"
  | "measurement"
  | "risk_reward"
  | "anchored_series"
  | "pattern";
export type Group = "analysis" | "fibonacci" | "measure" | "shapes" | "notes" | "trade" | "position";
export type MaxAnchors = number;
export type MinAnchors = number;
export type ToolId =
  | "trend_line"
  | "trend_ray"
  | "extended_line"
  | "price_line"
  | "horizontal_ray"
  | "vertical_line"
  | "parallel_channel"
  | "price_channel"
  | "info_line"
  | "trend_angle"
  | "cross_line"
  | "regression_trend"
  | "flat_top_bottom"
  | "disjoint_channel"
  | "anchored_vwap"
  | "fibonacci_retracement"
  | "fibonacci_extension"
  | "fibonacci_channel"
  | "fibonacci_time_zone"
  | "pitchfork"
  | "measure"
  | "price_range"
  | "date_range"
  | "horizontal_line"
  | "zone"
  | "brush"
  | "polyline"
  | "head_shoulders"
  | "triangle_pattern"
  | "text"
  | "note_marker"
  | "planned_entry"
  | "add_position"
  | "reduce_position"
  | "planned_exit"
  | "stop_loss"
  | "take_profit"
  | "long_position"
  | "short_position"
  | "risk_reward"
  | "ai_suggestion";
export type ToolVersion = number;
export type TutorSemantic = string;

export interface ChartToolManifest {
  algorithm_version?: AlgorithmVersion;
  geometry_kind: GeometryKind;
  group: Group;
  max_anchors: MaxAnchors;
  min_anchors: MinAnchors;
  tool_id: ToolId;
  tool_version?: ToolVersion;
  tutor_semantic: TutorSemantic;
}
