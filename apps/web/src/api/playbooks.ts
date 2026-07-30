import type {
  CreatePlaybookRequest,
  PlaybookListResponse,
  PlaybookVersion,
} from "@replaytutor/contracts";
import { validateContract } from "@replaytutor/contracts";
import { API_BASE_URL, ApiResponseError } from "./health";

async function checked<T>(
  response: Response,
  contract: Parameters<typeof validateContract>[0],
): Promise<T> {
  if (!response.ok) throw new ApiResponseError(`Playbook request failed: ${response.status}`, response.status);
  const value: unknown = await response.json();
  if (!validateContract<T>(contract, value)) throw new ApiResponseError(`Invalid ${contract} response`, 502);
  return value;
}

export async function fetchPlaybooks(): Promise<PlaybookListResponse> {
  return checked(await fetch(`${API_BASE_URL}/api/v1/playbooks`), "PlaybookListResponse");
}

export async function createPlaybook(payload: CreatePlaybookRequest): Promise<PlaybookVersion> {
  return checked(
    await fetch(`${API_BASE_URL}/api/v1/playbooks`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
    "PlaybookVersion",
  );
}
