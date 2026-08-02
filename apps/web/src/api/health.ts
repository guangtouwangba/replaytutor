import type { HealthResponse } from "@replaytutor/contracts";
import { localeHeaders } from "./locale";

export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8788";

export class ApiResponseError extends Error {
  constructor(
    message: string,
    public readonly status: number,
  ) {
    super(message);
    this.name = "ApiResponseError";
  }
}

export function apiFetch(input: RequestInfo | URL, init: RequestInit = {}): Promise<Response> {
  return fetch(input, { ...init, headers: localeHeaders(init.headers) });
}

export async function fetchHealth(
  signal?: AbortSignal,
): Promise<HealthResponse> {
  const response = await apiFetch(`${API_BASE_URL}/api/v1/health`, { signal });
  if (!response.ok) {
    throw new ApiResponseError(`Health request failed: ${response.status}`, response.status);
  }
  return (await response.json()) as HealthResponse;
}
