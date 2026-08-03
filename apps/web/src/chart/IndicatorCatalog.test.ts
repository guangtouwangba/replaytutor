import { describe, expect, it } from "vitest";
import { DEFAULT_INDICATORS, INDICATOR_CATALOG, searchIndicators } from "./IndicatorCatalog";

describe("indicator catalog", () => {
  it("exposes every pinned built-in plus ReplayTutor extensions with stable unique ids", () => {
    expect(INDICATOR_CATALOG).toHaveLength(31);
    expect(new Set(INDICATOR_CATALOG.map((item) => item.id)).size).toBe(31);
    expect(INDICATOR_CATALOG.slice(-4).map((item) => item.id)).toEqual(["VWAP", "ATR", "BAR_COUNT", "ORDER_BLOCK"]);
  });

  it("starts with a removable volume pane and supports Chinese and alias search", () => {
    expect(DEFAULT_INDICATORS[0]?.definitionId).toBe("VOL");
    expect(searchIndicators("成交量").map((item) => item.id)).toContain("VOL");
    expect(searchIndicators("订单区").map((item) => item.id)).toContain("ORDER_BLOCK");
  });
});
