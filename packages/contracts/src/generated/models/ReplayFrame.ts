// Generated from Pydantic. Do not edit.

export type CurrentIndex = number;
export type FrameId = string;
export type Progress = number;
export type Revision = number;
export type SchemaVersion = "1.0";
export type SessionId = string;
export type TotalBars = number;
export type VisibleAt = string;

export interface ReplayFrame {
  current_index: CurrentIndex;
  frame_id: FrameId;
  progress: Progress;
  revision: Revision;
  schema_version?: SchemaVersion;
  session_id: SessionId;
  total_bars: TotalBars;
  visible_at: VisibleAt;
}
