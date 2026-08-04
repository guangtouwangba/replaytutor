// Generated from Pydantic. Do not edit.

export type Title = string | null;
export type SessionId = string;

export interface CompanionThreadCreateParams {
  request?: CreateTutorThreadRequest;
  session_id: SessionId;
}
export interface CreateTutorThreadRequest {
  title?: Title;
}
