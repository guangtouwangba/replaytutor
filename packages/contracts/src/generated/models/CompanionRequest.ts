// Generated from Pydantic. Do not edit.

export type Method =
  | "system.bootstrap"
  | "system.health"
  | "agent.codex.discover"
  | "session.list"
  | "session.get"
  | "tutor.thread.list"
  | "tutor.thread.create"
  | "tutor.thread.get"
  | "tutor.run.start"
  | "tutor.run.get"
  | "tutor.run.cancel"
  | "evidence.resolve"
  | "navigation.open_replaytutor";
export type ProtocolVersion = "1.0";
export type RequestId = string;

export interface CompanionRequest {
  method: Method;
  params?: Params;
  protocol_version?: ProtocolVersion;
  request_id: RequestId;
}
export interface Params {
  [k: string]: unknown;
}
