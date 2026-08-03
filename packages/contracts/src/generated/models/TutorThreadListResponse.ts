// Generated from Pydantic. Do not edit.

export type SchemaVersion = "1.0";
export type CreatedAt = string;
export type LastQuestion = string | null;
export type LastStatus = ("running" | "completed" | "failed" | "cancelled" | "timed_out") | null;
export type RunCount = number;
export type SchemaVersion1 = "1.0";
export type SessionId = string;
export type ThreadId = string;
export type Title = string;
export type UpdatedAt = string;
export type Threads = TutorThreadSummary[];

export interface TutorThreadListResponse {
  schema_version?: SchemaVersion;
  threads?: Threads;
}
export interface TutorThreadSummary {
  created_at: CreatedAt;
  last_question?: LastQuestion;
  last_status?: LastStatus;
  run_count: RunCount;
  schema_version?: SchemaVersion1;
  session_id: SessionId;
  thread_id: ThreadId;
  title: Title;
  updated_at: UpdatedAt;
}
