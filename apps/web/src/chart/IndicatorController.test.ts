import { describe, expect, it, vi } from "vitest";
import { syncChartIndicators } from "./IndicatorController";

describe("indicator chart seam", () => {
  it("creates main overlays in the candle pane and removes stale instances", () => {
    const chart = {
      createIndicator: vi.fn(() => "pane"),
      getIndicators: vi.fn()
        .mockReturnValueOnce([{ id: "indicator-stale" }])
        .mockReturnValueOnce([{ id: "indicator-stale" }]),
      overrideIndicator: vi.fn(() => true),
      removeIndicator: vi.fn(() => true),
    };
    syncChartIndicators(chart as never, [
      { instanceId: "indicator-ma", definitionId: "MA", params: [5, 20], visible: true },
    ]);
    expect(chart.removeIndicator).toHaveBeenCalledWith({ id: "indicator-stale" });
    expect(chart.createIndicator).toHaveBeenCalledWith(expect.objectContaining({
      id: "indicator-ma",
      name: "MA",
      paneId: "candle_pane",
      calcParams: [5, 20],
    }), false);
  });
});
