// Generated from Pydantic. Do not edit.

export type BackupId = string;
export type CreatedAt = string;
export type Sha256 = string;
export type SizeBytes = number;

export interface BackupArtifact {
  backup_id: BackupId;
  created_at: CreatedAt;
  sha256: Sha256;
  size_bytes: SizeBytes;
}
