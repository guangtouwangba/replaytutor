// Generated from Pydantic. Do not edit.

export type AgentId = "codex-local";
export type Authentication = "not_checked";
export type Executable = string | null;
export type Installed = boolean;
export type Agents = AgentExecutableHealth[];
export type Detail = string | null;
export type Status = "healthy" | "degraded" | "unavailable";
export type Version = string | null;
export type Detail1 = string | null;
export type Path = string;
export type Status1 = "healthy" | "degraded" | "unavailable";
export type Version1 = string | null;
export type Writable = boolean;
export type Detail2 = string | null;
export type ForeignKeys = boolean;
export type JournalMode = string;
export type MigrationCurrent = string | null;
export type MigrationHead = string | null;
export type Path1 = string;
export type Status2 = "healthy" | "degraded" | "unavailable";
export type Version2 = string | null;
export type RequestId = string;
export type SchemaVersion = "1.0";
export type Status3 = "healthy" | "degraded";

export interface HealthResponse {
  agents: Agents;
  api: HealthService;
  data: DataHealth;
  database: DatabaseHealth;
  request_id: RequestId;
  schema_version?: SchemaVersion;
  status: Status3;
}
export interface AgentExecutableHealth {
  agent_id: AgentId;
  authentication?: Authentication;
  executable: Executable;
  installed: Installed;
}
export interface HealthService {
  detail?: Detail;
  status: Status;
  version?: Version;
}
export interface DataHealth {
  detail?: Detail1;
  path: Path;
  status: Status1;
  version?: Version1;
  writable: Writable;
}
export interface DatabaseHealth {
  detail?: Detail2;
  foreign_keys: ForeignKeys;
  journal_mode: JournalMode;
  migration_current: MigrationCurrent;
  migration_head: MigrationHead;
  path: Path1;
  status: Status2;
  version?: Version2;
}
