import type {
  AgentCapability,
  TutorRequest,
  TutorRun,
} from "@replaytutor/contracts";
import { validateContract } from "@replaytutor/contracts";
import { API_BASE_URL, ApiResponseError } from "./health";

async function validated<T>(
  response: Response,
  contract: Parameters<typeof validateContract>[0],
): Promise<T> {
  if (!response.ok) {
    const payload = await response.json().catch(() => ({})) as {
      error?: { message?: string };
    };
    throw new ApiResponseError(
      payload.error?.message ?? `Tutor request failed: ${response.status}`,
      response.status,
    );
  }
  const value: unknown = await response.json();
  if (!validateContract<T>(contract, value)) {
    throw new ApiResponseError(`Invalid ${contract} response`, 502);
  }
  return value;
}

export async function discoverCodex(): Promise<AgentCapability> {
  return validated(await fetch(`${API_BASE_URL}/api/v1/agents/codex`), "AgentCapability");
}

export async function startTutor(
  sessionId: string,
  request: TutorRequest,
): Promise<TutorRun> {
  return validated(
    await fetch(`${API_BASE_URL}/api/v1/sessions/${sessionId}/tutor`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
    }),
    "TutorRun",
  );
}

export async function fetchTutorRun(runId: string): Promise<TutorRun> {
  return validated(
    await fetch(`${API_BASE_URL}/api/v1/tutor/runs/${runId}`),
    "TutorRun",
  );
}

export async function cancelTutorRun(runId: string): Promise<TutorRun> {
  return validated(
    await fetch(`${API_BASE_URL}/api/v1/tutor/runs/${runId}/cancel`, {
      method: "POST",
    }),
    "TutorRun",
  );
}
