// Generated from Pydantic. Do not edit.

export type Code =
  | "native_host_not_found"
  | "local_service_stopped"
  | "origin_not_allowed"
  | "protocol_incompatible"
  | "method_not_allowed"
  | "payload_invalid"
  | "payload_too_large"
  | "session_not_found"
  | "tutor_disabled"
  | "codex_unavailable"
  | "run_conflict"
  | "run_failed"
  | "evidence_not_found"
  | "internal_error";
export type Message = string;
export type Retryable = boolean;

export interface CompanionError {
  code: Code;
  message: Message;
  retryable?: Retryable;
}
