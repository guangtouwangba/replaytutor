import { describe, expect, it } from "vitest";
import {
  DEFAULT_PANE_TIMEFRAMES,
  isChartLayout,
  paneCountForLayout,
} from "./ChartWorkspaceLayout";

describe("chart workspace layouts", () => {
  it("maps every supported layout to its visible pane count", () => {
    expect(paneCountForLayout("single")).toBe(1);
    expect(paneCountForLayout("vertical")).toBe(2);
    expect(paneCountForLayout("horizontal")).toBe(2);
    expect(paneCountForLayout("quad")).toBe(4);
  });

  it("rejects unknown persisted layout values", () => {
    expect(isChartLayout("quad")).toBe(true);
    expect(isChartLayout("three-pane")).toBe(false);
    expect(isChartLayout(null)).toBe(false);
  });

  it("starts multi-chart mode with distinct useful timeframes", () => {
    expect(DEFAULT_PANE_TIMEFRAMES).toEqual(["1m", "5m", "15m", "1h"]);
  });
});
