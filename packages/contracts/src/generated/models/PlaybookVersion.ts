// Generated from Pydantic. Do not edit.

export type CreatedAt = string;
export type Description = string;
export type Name = string;
export type Official = boolean;
export type PlaybookId = string;
/**
 * @minItems 1
 */
export type Rules = [string, ...string[]];
export type SchemaVersion = "1.0";
export type Slug = string;
export type Version = number;

export interface PlaybookVersion {
  created_at: CreatedAt;
  description: Description;
  name: Name;
  official?: Official;
  playbook_id: PlaybookId;
  rules: Rules;
  schema_version?: SchemaVersion;
  slug: Slug;
  version: Version;
}
