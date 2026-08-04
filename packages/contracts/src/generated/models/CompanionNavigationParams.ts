// Generated from Pydantic. Do not edit.

export type EvidenceId = string | null;
export type Mode = "replay" | "review";
export type SessionId = string;

export interface CompanionNavigationParams {
  evidence_id?: EvidenceId;
  mode?: Mode;
  session_id: SessionId;
}
