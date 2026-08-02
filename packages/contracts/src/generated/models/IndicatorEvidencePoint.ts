// Generated from Pydantic. Do not edit.

export type BarId = string;
export type Time = string;

export interface IndicatorEvidencePoint {
  bar_id: BarId;
  time: Time;
  values?: Values;
}
export interface Values {
  [k: string]: string;
}
