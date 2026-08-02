// Generated from Pydantic. Do not edit.

export type Name = string;
export type EndCap = "none" | "arrow";
export type FillColor = string;
export type FillOpacity = number;
export type FontSize = number;
export type LineColor = string;
export type LineDash = "solid" | "dashed" | "dotted";
export type LineWidth = number;
export type Opacity = number;
export type StartCap = "none" | "arrow";
export type TextColor = string;
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
export type ToolVersion = number;

export interface CreateChartToolTemplateRequest {
  name: Name;
  properties?: Properties;
  style: ChartObjectStyle;
  tool: Tool;
  tool_version?: ToolVersion;
}
export interface Properties {
  [k: string]: unknown;
}
export interface ChartObjectStyle {
  end_cap?: EndCap;
  fill_color?: FillColor;
  fill_opacity?: FillOpacity;
  font_size?: FontSize;
  line_color?: LineColor;
  line_dash?: LineDash;
  line_width?: LineWidth;
  opacity?: Opacity;
  start_cap?: StartCap;
  text_color?: TextColor;
}
