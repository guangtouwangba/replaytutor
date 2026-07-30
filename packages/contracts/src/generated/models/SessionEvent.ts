// Generated from Pydantic. Do not edit.

export type EventId = string;
export type EventType = "session_created" | "replay_advanced" | "session_completed";
export type OccurredAt = string;
export type Revision = number;
export type Sequence = number;
export type SessionId = string;

export interface SessionEvent {
  event_id: EventId;
  event_type: EventType;
  occurred_at: OccurredAt;
  payload?: Payload;
  revision: Revision;
  sequence: Sequence;
  session_id: SessionId;
}
export interface Payload {
  [k: string]: unknown;
}
