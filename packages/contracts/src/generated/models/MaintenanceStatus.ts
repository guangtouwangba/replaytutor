// Generated from Pydantic. Do not edit.

export type BackupId = string;
export type CreatedAt = string;
export type Sha256 = string;
export type SizeBytes = number;
export type Backups = BackupArtifact[];
export type SchemaVersion = "1.0";
export type TrashedAgentRuns = number;

export interface MaintenanceStatus {
  backups: Backups;
  schema_version?: SchemaVersion;
  trashed_agent_runs: TrashedAgentRuns;
}
export interface BackupArtifact {
  backup_id: BackupId;
  created_at: CreatedAt;
  sha256: Sha256;
  size_bytes: SizeBytes;
}
