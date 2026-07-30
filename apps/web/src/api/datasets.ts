import type {
  BarListResponse,
  DataSnapshot,
  DatasetListResponse,
  ImportPreview,
} from "@replaytutor/contracts";
import { validateContract } from "@replaytutor/contracts";
import { API_BASE_URL, ApiResponseError } from "./health";

async function responseJson<T>(response: Response, contract: Parameters<typeof validateContract>[0]): Promise<T> {
  if (!response.ok) {
    throw new ApiResponseError(`API request failed: ${response.status}`, response.status);
  }
  const value: unknown = await response.json();
  if (!validateContract<T>(contract, value)) {
    throw new ApiResponseError(`Invalid ${contract} response`, 502);
  }
  return value;
}

export async function fetchDatasets(): Promise<DatasetListResponse> {
  return responseJson(await fetch(`${API_BASE_URL}/api/v1/datasets`), "DatasetListResponse");
}

export async function loadGoldenDataset(): Promise<DataSnapshot> {
  return responseJson(
    await fetch(`${API_BASE_URL}/api/v1/datasets/golden`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({}),
    }),
    "DataSnapshot",
  );
}

export async function fetchBars(snapshotId: string, limit = 20): Promise<BarListResponse> {
  return responseJson(
    await fetch(`${API_BASE_URL}/api/v1/datasets/${snapshotId}/bars?limit=${limit}`),
    "BarListResponse",
  );
}

export async function stageDatasetImport(file: File): Promise<ImportPreview> {
  const form = new FormData();
  form.append("file", file);
  return responseJson(
    await fetch(`${API_BASE_URL}/api/v1/datasets/imports`, { method: "POST", body: form }),
    "ImportPreview",
  );
}
