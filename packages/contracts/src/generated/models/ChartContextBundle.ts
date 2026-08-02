// Generated from Pydantic. Do not edit.

export type ContextBundleId = string;
export type CreatedAt = string;
export type EvidenceIds = string[];
export type FrameId = string;
/**
 * @minItems 1
 * @maxItems 32
 */
export type Objects = [ChartContextObject, ...ChartContextObject[]];
export type AlgorithmVersion = string;
/**
 * @minItems 1
 * @maxItems 16
 */
export type Anchors =
  | [AnnotationPoint]
  | [AnnotationPoint, AnnotationPoint]
  | [AnnotationPoint, AnnotationPoint, AnnotationPoint]
  | [AnnotationPoint, AnnotationPoint, AnnotationPoint, AnnotationPoint]
  | [AnnotationPoint, AnnotationPoint, AnnotationPoint, AnnotationPoint, AnnotationPoint]
  | [AnnotationPoint, AnnotationPoint, AnnotationPoint, AnnotationPoint, AnnotationPoint, AnnotationPoint]
  | [
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint
    ]
  | [
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint
    ]
  | [
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint
    ]
  | [
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint
    ]
  | [
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint
    ]
  | [
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint
    ]
  | [
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint
    ]
  | [
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint
    ]
  | [
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint
    ]
  | [
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint
    ];
export type Price = string;
export type Time = string;
export type Kind =
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
export type Label = string;
export type Layer = "user" | "ai";
export type ObjectId = string;
/**
 * @minItems 1
 * @maxItems 16
 */
export type Points =
  | [AnnotationPoint]
  | [AnnotationPoint, AnnotationPoint]
  | [AnnotationPoint, AnnotationPoint, AnnotationPoint]
  | [AnnotationPoint, AnnotationPoint, AnnotationPoint, AnnotationPoint]
  | [AnnotationPoint, AnnotationPoint, AnnotationPoint, AnnotationPoint, AnnotationPoint]
  | [AnnotationPoint, AnnotationPoint, AnnotationPoint, AnnotationPoint, AnnotationPoint, AnnotationPoint]
  | [
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint
    ]
  | [
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint
    ]
  | [
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint
    ]
  | [
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint
    ]
  | [
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint
    ]
  | [
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint
    ]
  | [
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint
    ]
  | [
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint
    ]
  | [
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint
    ]
  | [
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint,
      AnnotationPoint
    ];
export type RevisionId = string | null;
export type SemanticRole =
  | "analysis"
  | "note"
  | "entry"
  | "add_position"
  | "reduce_position"
  | "exit"
  | "stop_loss"
  | "take_profit"
  | "risk_reward";
export type Shape = "line" | "zone" | "marker" | "label";
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
export type SchemaVersion = "1.0";
export type SelectionMode = "selected";
export type SessionId = string;
export type VisibleAt = string;

export interface ChartContextBundle {
  context_bundle_id: ContextBundleId;
  created_at: CreatedAt;
  derived_facts?: DerivedFacts;
  evidence_ids?: EvidenceIds;
  frame_id: FrameId;
  objects: Objects;
  schema_version?: SchemaVersion;
  selection_mode?: SelectionMode;
  session_id: SessionId;
  visible_at: VisibleAt;
}
export interface DerivedFacts {
  [k: string]: string;
}
export interface ChartContextObject {
  algorithm_version?: AlgorithmVersion;
  derived_facts?: DerivedFacts1;
  geometry?: ChartGeometry | null;
  label: Label;
  layer: Layer;
  metadata?: Metadata;
  object_id: ObjectId;
  points: Points;
  properties?: Properties;
  revision_id?: RevisionId;
  semantic_role: SemanticRole;
  shape: Shape;
  style?: ChartObjectStyle;
  tool: Tool;
  tool_version?: ToolVersion;
}
export interface DerivedFacts1 {
  [k: string]: unknown;
}
export interface ChartGeometry {
  anchors: Anchors;
  kind: Kind;
}
export interface AnnotationPoint {
  price: Price;
  time: Time;
}
export interface Metadata {
  [k: string]: string;
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
