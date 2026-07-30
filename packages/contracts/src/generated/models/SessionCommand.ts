// Generated from Pydantic. Do not edit.

export type Bars = number;
export type CommandId = string;
export type ExpectedRevision = number;
export type Kind = "advance";

export interface SessionCommand {
  bars?: Bars;
  command_id: CommandId;
  expected_revision: ExpectedRevision;
  kind: Kind;
}
