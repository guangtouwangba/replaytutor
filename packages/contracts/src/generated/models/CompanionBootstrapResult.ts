// Generated from Pydantic. Do not edit.

export type Capabilities = ("session.read" | "tutor.run" | "evidence.resolve" | "navigation.local")[];
export type CompatibleProtocols = "1.0"[];
export type ConnectorVersion = string;
export type ReplaytutorVersion = string;
export type SchemaVersion = "1.0";

export interface CompanionBootstrapResult {
  capabilities: Capabilities;
  compatible_protocols?: CompatibleProtocols;
  connector_version: ConnectorVersion;
  replaytutor_version: ReplaytutorVersion;
  schema_version?: SchemaVersion;
}
