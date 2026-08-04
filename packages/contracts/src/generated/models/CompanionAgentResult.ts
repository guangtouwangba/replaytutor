// Generated from Pydantic. Do not edit.

export type AgentId = "codex-local";
export type Authentication = "unknown" | "verified" | "failed";
export type Available = boolean;
export type Diagnostics = string[];
export type Installed = boolean;
export type SchemaVersion = "1.0";
export type Version = string | null;

export interface CompanionAgentResult {
  agent_id?: AgentId;
  authentication: Authentication;
  available: Available;
  diagnostics?: Diagnostics;
  installed: Installed;
  schema_version?: SchemaVersion;
  version?: Version;
}
