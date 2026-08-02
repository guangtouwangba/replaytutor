import type {
  BarListResponse,
  BinanceDownloadRequest,
  DataSnapshot,
  DatasetDownloadJob,
  DatasetDownloadJobListResponse,
  DatasetListResponse,
  ImportPreview,
  SnapshotDeleteResponse,
} from "@replaytutor/contracts";
import { validateContract } from "@replaytutor/contracts";
import { API_BASE_URL, ApiResponseError, apiFetch } from "./health";
import { localeHeaders } from "./locale";

async function responseJson<T>(response: Response, contract: Parameters<typeof validateContract>[0]): Promise<T> {
  if (!response.ok) {
    let message = `Market data request failed: ${response.status}`;
    try {
      const payload = await response.json() as { error?: { message?: string } };
      message = payload.error?.message ?? message;
    } catch {
      // Preserve the HTTP status when the upstream response is not JSON.
    }
    throw new ApiResponseError(message, response.status);
  }
  const value: unknown = await response.json();
  if (!validateContract<T>(contract, value)) {
    throw new ApiResponseError(`Invalid ${contract} response`, 502);
  }
  return value;
}

export async function fetchDatasets(): Promise<DatasetListResponse> {
  return responseJson(await apiFetch(`${API_BASE_URL}/api/v1/datasets`, { headers: localeHeaders() }), "DatasetListResponse");
}

export async function deleteDatasetSnapshot(snapshotId: string): Promise<SnapshotDeleteResponse> {
  return responseJson(
    await apiFetch(`${API_BASE_URL}/api/v1/datasets/${snapshotId}`, {
      method: "DELETE",
      headers: localeHeaders(),
    }),
    "SnapshotDeleteResponse",
  );
}

export async function loadGoldenDataset(): Promise<DataSnapshot> {
  return responseJson(
    await apiFetch(`${API_BASE_URL}/api/v1/datasets/golden`, {
      method: "POST",
      headers: localeHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify({}),
    }),
    "DataSnapshot",
  );
}

export async function startBinanceDatasetDownload(
  payload: BinanceDownloadRequest,
): Promise<DatasetDownloadJob> {
  return responseJson(
    await apiFetch(`${API_BASE_URL}/api/v1/dataset-downloads`, {
      method: "POST",
      headers: localeHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify(payload),
    }),
    "DatasetDownloadJob",
  );
}

export async function fetchDatasetDownloadJobs(): Promise<DatasetDownloadJobListResponse> {
  return responseJson(
    await apiFetch(`${API_BASE_URL}/api/v1/dataset-downloads?limit=20`),
    "DatasetDownloadJobListResponse",
  );
}

export async function fetchDatasetDownloadJob(jobId: string): Promise<DatasetDownloadJob> {
  return responseJson(
    await apiFetch(`${API_BASE_URL}/api/v1/dataset-downloads/${jobId}`),
    "DatasetDownloadJob",
  );
}

export async function fetchBars(snapshotId: string, limit = 20): Promise<BarListResponse> {
  return responseJson(
    await apiFetch(`${API_BASE_URL}/api/v1/datasets/${snapshotId}/bars?limit=${limit}`),
    "BarListResponse",
  );
}

export async function stageDatasetImport(file: File): Promise<ImportPreview> {
  const form = new FormData();
  form.append("file", file);
  return responseJson(
    await apiFetch(`${API_BASE_URL}/api/v1/datasets/imports`, { method: "POST", body: form }),
    "ImportPreview",
  );
}
