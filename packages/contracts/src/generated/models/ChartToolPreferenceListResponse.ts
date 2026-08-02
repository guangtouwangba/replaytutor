// Generated from Pydantic. Do not edit.

export type Continuous = boolean;
export type DefaultTemplateId = string | null;
export type Favorite = boolean;
export type RecentRank = number | null;
export type Tool =
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
export type UpdatedAt = string;
export type Preferences = ChartToolPreference[];
export type SchemaVersion = "1.0";

export interface ChartToolPreferenceListResponse {
  preferences: Preferences;
  schema_version?: SchemaVersion;
}
export interface ChartToolPreference {
  continuous?: Continuous;
  default_template_id?: DefaultTemplateId;
  favorite?: Favorite;
  recent_rank?: RecentRank;
  tool: Tool;
  updated_at: UpdatedAt;
}
