// Generated from Pydantic. Do not edit.

export type DeletedAt = string;
export type SchemaVersion = "1.0";
export type SnapshotId = string;
export type TrashPath = string | null;

export interface SnapshotDeleteResponse {
  deleted_at: DeletedAt;
  schema_version?: SchemaVersion;
  snapshot_id: SnapshotId;
  trash_path?: TrashPath;
}
