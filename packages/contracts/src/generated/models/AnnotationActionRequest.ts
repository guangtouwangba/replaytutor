// Generated from Pydantic. Do not edit.

export type Action = "accepted" | "rejected" | "revised" | "deleted";
export type CommandId = string;
export type ExpectedRevision = number;
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
export type Label = string | null;
export type Metadata = {
  [k: string]: string;
} | null;
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
    ]
  | null;
export type Properties = {
  [k: string]: unknown;
} | null;
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

export interface AnnotationActionRequest {
  action: Action;
  command_id: CommandId;
  expected_revision: ExpectedRevision;
  geometry?: ChartGeometry | null;
  label?: Label;
  metadata?: Metadata;
  points?: Points;
  properties?: Properties;
  style?: ChartObjectStyle | null;
}
export interface ChartGeometry {
  anchors: Anchors;
  kind: Kind;
}
export interface AnnotationPoint {
  price: Price;
  time: Time;
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
