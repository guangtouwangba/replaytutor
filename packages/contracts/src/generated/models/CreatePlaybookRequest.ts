// Generated from Pydantic. Do not edit.

export type Description = string;
export type Name = string;
/**
 * @minItems 1
 * @maxItems 30
 */
export type Rules = [string, ...string[]];
export type Slug = string;

export interface CreatePlaybookRequest {
  description: Description;
  name: Name;
  rules: Rules;
  slug: Slug;
}
