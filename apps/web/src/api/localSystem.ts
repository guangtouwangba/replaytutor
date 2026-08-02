import type {
  BackupArtifact,
  CleanupResult,
  LocalPreferences,
  MaintenanceStatus,
} from "@replaytutor/contracts";
import { validateContract } from "@replaytutor/contracts";
import { API_BASE_URL, ApiResponseError, apiFetch } from "./health";
import { localeHeaders } from "./locale";

async function checked<T>(
  response: Response,
  contract: Parameters<typeof validateContract>[0],
): Promise<T> {
  if (!response.ok) {
    throw new ApiResponseError(`Local system request failed: ${response.status}`, response.status);
  }
  const value: unknown = await response.json();
  if (!validateContract<T>(contract, value)) {
    throw new ApiResponseError(`Invalid ${contract} response`, 502);
  }
  return value;
}

export async function fetchPreferences(): Promise<LocalPreferences> {
  return checked(
    await apiFetch(`${API_BASE_URL}/api/v1/settings/preferences`, { headers: localeHeaders() }),
    "LocalPreferences",
  );
}

export async function savePreferences(
  payload: LocalPreferences,
): Promise<LocalPreferences> {
  return checked(
    await apiFetch(`${API_BASE_URL}/api/v1/settings/preferences`, {
      method: "PUT",
      headers: localeHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify(payload),
    }),
    "LocalPreferences",
  );
}

export async function fetchMaintenance(): Promise<MaintenanceStatus> {
  return checked(
    await apiFetch(`${API_BASE_URL}/api/v1/maintenance`),
    "MaintenanceStatus",
  );
}

export async function createBackup(): Promise<BackupArtifact> {
  return checked(
    await apiFetch(`${API_BASE_URL}/api/v1/maintenance/backups`, { method: "POST" }),
    "BackupArtifact",
  );
}

export async function restoreBackup(backupId: string): Promise<BackupArtifact> {
  return checked(
    await apiFetch(`${API_BASE_URL}/api/v1/maintenance/backups/${backupId}/restore`, {
      method: "POST",
    }),
    "BackupArtifact",
  );
}

export async function cleanupAgentRuns(): Promise<CleanupResult> {
  return checked(
    await apiFetch(`${API_BASE_URL}/api/v1/maintenance/cleanup-agent-runs`, {
      method: "POST",
    }),
    "CleanupResult",
  );
}
