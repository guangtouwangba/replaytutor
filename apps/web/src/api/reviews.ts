import type {
  ReviewArtifact,
  ReviewListResponse,
  ReviewRequest,
} from "@replaytutor/contracts";
import { validateContract } from "@replaytutor/contracts";
import { API_BASE_URL, ApiResponseError, apiFetch } from "./health";

async function contractJson<T>(
  response: Response,
  contract: Parameters<typeof validateContract>[0],
): Promise<T> {
  if (!response.ok) {
    throw new ApiResponseError(`API request failed: ${response.status}`, response.status);
  }
  const value: unknown = await response.json();
  if (!validateContract<T>(contract, value)) {
    throw new ApiResponseError(`Invalid ${contract} response`, 502);
  }
  return value;
}

export async function fetchReviews(): Promise<ReviewListResponse> {
  return contractJson(
    await apiFetch(`${API_BASE_URL}/api/v1/reviews`),
    "ReviewListResponse",
  );
}

export async function createReview(payload: ReviewRequest): Promise<ReviewArtifact> {
  return contractJson(
    await apiFetch(`${API_BASE_URL}/api/v1/reviews`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
    "ReviewArtifact",
  );
}

export function reviewReportUrl(reviewId: string): string {
  return `${API_BASE_URL}/api/v1/reviews/${reviewId}/report`;
}
