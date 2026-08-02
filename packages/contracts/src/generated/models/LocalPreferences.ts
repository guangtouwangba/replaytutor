// Generated from Pydantic. Do not edit.

export type AiMode = "codex" | "off";
export type ConfirmBeforeFinish = boolean;
export type DefaultPlaybookId = string | null;
export type Locale = "system" | "en-US" | "zh-CN";
export type PrivacyMode = "local_only";
export type RetainAgentRunsDays = number;
export type SchemaVersion = "1.0";
export type UpdatedAt = string | null;

export interface LocalPreferences {
  ai_mode?: AiMode;
  confirm_before_finish?: ConfirmBeforeFinish;
  default_playbook_id?: DefaultPlaybookId;
  locale?: Locale;
  privacy_mode?: PrivacyMode;
  retain_agent_runs_days?: RetainAgentRunsDays;
  schema_version?: SchemaVersion;
  updated_at?: UpdatedAt;
}
