import type {
  CompletedSession,
  CancelOrderRequest,
  ChartAnnotation,
  CreateAnnotationRequest,
  CreateSessionSpec,
  FinishSessionRequest,
  LockTradePlanRequest,
  OrderResult,
  SessionCommand,
  SessionDelta,
  SessionListResponse,
  SubmitOrderRequest,
  TradePlanResult,
  TrainingReview,
  TrainingReviewListResponse,
} from "@replaytutor/contracts";
import { validateContract } from "@replaytutor/contracts";
import { API_BASE_URL, ApiResponseError } from "./health";

async function contractJson<T>(
  response: Response,
  contract: Parameters<typeof validateContract>[0],
): Promise<T> {
  if (!response.ok) {
    let message = `Session request failed: ${response.status}`;
    try {
      const payload = await response.json() as { error?: { message?: string } };
      message = payload.error?.message ?? message;
    } catch {
      // The status remains actionable even when the response body is unavailable.
    }
    throw new ApiResponseError(message, response.status);
  }
  const value: unknown = await response.json();
  if (!validateContract<T>(contract, value)) {
    throw new ApiResponseError(`Invalid ${contract} response`, 502);
  }
  return value;
}

export function commandId(): string {
  return `cmd_${crypto.randomUUID()}`;
}

export async function fetchSessions(): Promise<SessionListResponse> {
  return contractJson(
    await fetch(`${API_BASE_URL}/api/v1/sessions`),
    "SessionListResponse",
  );
}

export async function fetchSession(sessionId: string): Promise<SessionDelta> {
  return contractJson(
    await fetch(`${API_BASE_URL}/api/v1/sessions/${sessionId}`),
    "SessionDelta",
  );
}

export async function createSession(payload: CreateSessionSpec): Promise<SessionDelta> {
  return contractJson(
    await fetch(`${API_BASE_URL}/api/v1/sessions`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
    "SessionDelta",
  );
}

export async function applySessionCommand(
  sessionId: string,
  payload: SessionCommand,
): Promise<SessionDelta> {
  return contractJson(
    await fetch(`${API_BASE_URL}/api/v1/sessions/${sessionId}/commands`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
    "SessionDelta",
  );
}

export async function finishSession(
  sessionId: string,
  payload: FinishSessionRequest,
): Promise<CompletedSession> {
  return contractJson(
    await fetch(`${API_BASE_URL}/api/v1/sessions/${sessionId}/finish`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
    "CompletedSession",
  );
}

export async function lockTradePlan(
  sessionId: string,
  payload: LockTradePlanRequest,
): Promise<TradePlanResult> {
  return contractJson(
    await fetch(`${API_BASE_URL}/api/v1/sessions/${sessionId}/plan`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
    "TradePlanResult",
  );
}

export async function submitOrder(
  sessionId: string,
  payload: SubmitOrderRequest,
): Promise<OrderResult> {
  return contractJson(
    await fetch(`${API_BASE_URL}/api/v1/sessions/${sessionId}/orders`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
    "OrderResult",
  );
}

export async function cancelOrder(
  sessionId: string,
  payload: CancelOrderRequest,
): Promise<OrderResult> {
  return contractJson(
    await fetch(`${API_BASE_URL}/api/v1/sessions/${sessionId}/orders/cancel`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
    "OrderResult",
  );
}

export async function createAnnotation(
  sessionId: string,
  payload: CreateAnnotationRequest,
): Promise<ChartAnnotation> {
  return contractJson(
    await fetch(`${API_BASE_URL}/api/v1/sessions/${sessionId}/annotations`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
    "ChartAnnotation",
  );
}

export async function fetchTrainingReview(
  sessionId: string,
): Promise<TrainingReview> {
  return contractJson(
    await fetch(`${API_BASE_URL}/api/v1/sessions/${sessionId}/review`),
    "TrainingReview",
  );
}

export async function fetchTrainingReviews(): Promise<TrainingReviewListResponse> {
  return contractJson(
    await fetch(`${API_BASE_URL}/api/v1/training-reviews`),
    "TrainingReviewListResponse",
  );
}
