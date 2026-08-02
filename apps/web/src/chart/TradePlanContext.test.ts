import { describe, expect, it } from "vitest";
import { chartTradePlanContext } from "./TradePlanContext";

function positionDisposition(overrides: Record<string, string> = {}) {
  return {
    annotation_id: "ann_long",
    state: "active",
    original_annotation: { tool: "long_position" },
    effective_label: "多头仓位计划 · R:R 2.4",
    effective_metadata: {
      side: "long",
      entry_price: "66900",
      stop_price: "66320",
      target_price: "68300",
      risk_reward_ratio: "2.4",
      ...overrides,
    },
  };
}

describe("chartTradePlanContext", () => {
  it("turns an active long-position object into a plan seed", () => {
    expect(chartTradePlanContext(positionDisposition() as never)).toEqual({
      annotationId: "ann_long",
      label: "多头仓位计划 · R:R 2.4",
      side: "BUY",
      entryPrice: "66900",
      stopPrice: "66320",
      targetPrice: "68300",
      riskRewardRatio: "2.4",
    });
  });

  it("uses the explicit short side for a neutral risk-reward object", () => {
    const result = chartTradePlanContext(positionDisposition({ side: "short" }) as never);
    expect(result?.side).toBe("SELL");
  });

  it("rejects inactive or incomplete objects", () => {
    expect(chartTradePlanContext({ ...positionDisposition(), state: "deleted" } as never)).toBeNull();
    expect(chartTradePlanContext(positionDisposition({ stop_price: "" }) as never)).toBeNull();
  });
});
