// Generated from Pydantic. Do not edit.

export type MovedAgentRuns = number;
export type SchemaVersion = "1.0";
export type TrashPath = string;

export interface CleanupResult {
  moved_agent_runs: MovedAgentRuns;
  schema_version?: SchemaVersion;
  trash_path: TrashPath;
}
