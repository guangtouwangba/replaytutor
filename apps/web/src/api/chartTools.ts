import type {
  ChartAnnotation,
  ChartToolManifestListResponse,
  ChartToolPreference,
  ChartToolPreferenceListResponse,
  ChartToolTemplate,
  ChartToolTemplateListResponse,
  CreateChartToolTemplateRequest,
  UpdateChartToolPreferenceRequest,
} from "@replaytutor/contracts";
import { validateContract } from "@replaytutor/contracts";
import { API_BASE_URL, ApiResponseError, apiFetch } from "./health";

async function contractJson<T>(response: Response, contract: Parameters<typeof validateContract>[0]): Promise<T> {
  if (!response.ok) throw new ApiResponseError(`Chart tool request failed: ${response.status}`, response.status);
  const value: unknown = await response.json();
  if (!validateContract<T>(contract, value)) throw new ApiResponseError(`Invalid ${contract} response`, 502);
  return value;
}

export function fetchChartToolManifest(): Promise<ChartToolManifestListResponse> {
  return apiFetch(`${API_BASE_URL}/api/v1/chart-tools`).then((response) => contractJson(response, "ChartToolManifestListResponse"));
}

export function fetchChartToolTemplates(): Promise<ChartToolTemplateListResponse> {
  return apiFetch(`${API_BASE_URL}/api/v1/chart-tools/templates`).then((response) => contractJson(response, "ChartToolTemplateListResponse"));
}

export function createChartToolTemplate(payload: CreateChartToolTemplateRequest): Promise<ChartToolTemplate> {
  return apiFetch(`${API_BASE_URL}/api/v1/chart-tools/templates`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  }).then((response) => contractJson(response, "ChartToolTemplate"));
}

export function fetchChartToolPreferences(): Promise<ChartToolPreferenceListResponse> {
  return apiFetch(`${API_BASE_URL}/api/v1/chart-tools/preferences`).then((response) => contractJson(response, "ChartToolPreferenceListResponse"));
}

export function updateChartToolPreference(
  tool: NonNullable<ChartAnnotation["tool"]>,
  payload: UpdateChartToolPreferenceRequest,
): Promise<ChartToolPreference> {
  return apiFetch(`${API_BASE_URL}/api/v1/chart-tools/preferences/${encodeURIComponent(tool)}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  }).then((response) => contractJson(response, "ChartToolPreference"));
}
