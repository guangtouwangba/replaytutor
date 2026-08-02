import type { EvidenceTarget } from "@replaytutor/contracts";
import { describe, expect, it } from "vitest";
import {
  evidenceEntityId,
  evidenceReturnUrl,
  evidenceWorkbenchUrl,
} from "./EvidenceSelectionBridge";

const target = {
  schema_version: "1.0",
  evidence_id: "fil_00000000-0000-0000-0000-000000000001",
  session_id: "ses_00000000-0000-0000-0000-000000000001",
  kind: "fill",
  fill_id: "fil_00000000-0000-0000-0000-000000000001",
} satisfies EvidenceTarget;

describe("EvidenceSelectionBridge", () => {
  it("builds stable deep and return links", () => {
    expect(evidenceWorkbenchUrl(target.session_id, target.evidence_id)).toContain(
      "mode=review&evidence=",
    );
    expect(evidenceReturnUrl(target.session_id, target.evidence_id)).toBe(
      `/sessions/${target.session_id}/review#evidence-${target.evidence_id}`,
    );
    expect(evidenceEntityId(target)).toBe(target.fill_id);
  });
});
