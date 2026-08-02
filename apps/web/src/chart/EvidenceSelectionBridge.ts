import type { EvidenceTarget } from "@replaytutor/contracts";

export function evidenceEntityId(target: EvidenceTarget | null): string | null {
  return target?.annotation_id ?? target?.fill_id ?? target?.order_id ?? null;
}

export function evidenceReturnUrl(sessionId: string, evidenceId: string): string {
  return `/sessions/${sessionId}/review#evidence-${evidenceId}`;
}

export function evidenceWorkbenchUrl(sessionId: string, evidenceId: string): string {
  const params = new URLSearchParams({ mode: "review", evidence: evidenceId });
  return `/sessions/${sessionId}?${params.toString()}`;
}
