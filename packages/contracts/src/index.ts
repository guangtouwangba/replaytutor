export interface ErrorDetail {
  readonly code: string;
  readonly message: string;
  readonly retryable: boolean;
  readonly request_id: string;
  readonly details: Readonly<Record<string, unknown>>;
}

export interface ErrorEnvelope {
  readonly error: ErrorDetail;
}

export type ServiceState = "healthy" | "degraded" | "unavailable";

export interface HealthService {
  readonly status: ServiceState;
  readonly version?: string;
  readonly detail?: string;
}

export interface DatabaseHealth extends HealthService {
  readonly path: string;
  readonly journal_mode: string;
  readonly foreign_keys: boolean;
  readonly migration_current: string | null;
  readonly migration_head: string | null;
}

export interface AgentExecutableHealth {
  readonly agent_id: "codex-local" | "claude-local";
  readonly installed: boolean;
  readonly executable: string | null;
  readonly authentication: "not_checked";
}

export interface HealthResponse {
  readonly schema_version: "1.0";
  readonly status: "healthy" | "degraded";
  readonly request_id: string;
  readonly api: HealthService;
  readonly database: DatabaseHealth;
  readonly data: HealthService & { readonly path: string; readonly writable: boolean };
  readonly agents: readonly AgentExecutableHealth[];
}
