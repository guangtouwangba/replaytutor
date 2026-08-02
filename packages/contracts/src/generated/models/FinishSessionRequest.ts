// Generated from Pydantic. Do not edit.

export type CommandId = string;
export type ExpectedRevision = number;

export interface FinishSessionRequest {
  command_id: CommandId;
  expected_revision: ExpectedRevision;
}
