// Generated from Pydantic. Do not edit.

export type ApiVersion = string;
export type DataStatus = "healthy" | "unavailable";
export type DatabaseStatus = "healthy" | "degraded";
export type SchemaVersion = "1.0";
export type Status = "healthy" | "degraded";

export interface CompanionHealthResult {
  api_version: ApiVersion;
  data_status: DataStatus;
  database_status: DatabaseStatus;
  schema_version?: SchemaVersion;
  status: Status;
}
