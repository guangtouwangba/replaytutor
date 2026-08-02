import type { Bar } from "@replaytutor/contracts";
import { act, render } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import i18n from "../i18n";

const chartHarness = vi.hoisted(() => {
  const callbacks = new Map<string, () => void>();
  let candleX = 700;
  const chart = {
    convertToPixel: vi.fn(() => ({ x: candleX })),
    createOverlay: vi.fn((overlay: { id?: string }) => overlay.id ?? null),
    createIndicator: vi.fn(() => "indicator-pane"),
    getIndicators: vi.fn(() => []),
    overrideIndicator: vi.fn(() => true),
    removeIndicator: vi.fn(() => true),
    removeOverlay: vi.fn(() => true),
    resetData: vi.fn(),
    setDataLoader: vi.fn(),
    setOffsetRightDistance: vi.fn(),
    setPeriod: vi.fn(),
    setRightMinVisibleBarCount: vi.fn(),
    setSymbol: vi.fn(),
    subscribeAction: vi.fn((type: string, callback: () => void) => callbacks.set(type, callback)),
    unsubscribeAction: vi.fn(),
  };
  return {
    callbacks,
    chart,
    moveLastCandleTo(x: number) {
      candleX = x;
      callbacks.get("onVisibleRangeChange")?.();
    },
    reset() {
      callbacks.clear();
      candleX = 700;
      vi.clearAllMocks();
    },
  };
});

vi.mock("klinecharts", () => ({
  dispose: vi.fn(),
  getSupportedIndicators: vi.fn(() => []),
  init: vi.fn(() => chartHarness.chart),
  registerIndicator: vi.fn(),
  registerOverlay: vi.fn(),
}));

import { ReplayChart } from "./ReplayChart";

const bars = [{
  bar_id: "bar-1",
  instrument_id: "BTCUSDT",
  timeframe: "1m",
  open_time: "2025-08-02T13:24:00Z",
  close_time: "2025-08-02T13:25:00Z",
  raw: { open: "100", high: "110", low: "90", close: "105", volume: "1" },
}] as unknown as Bar[];

describe("ReplayChart visible boundary", () => {
  beforeEach(async () => {
    chartHarness.reset();
    await i18n.changeLanguage("zh-CN");
  });

  it("tracks the last visible candle when the chart viewport is dragged", () => {
    const { container } = render(
      <ReplayChart
        bars={bars}
        symbol="BTCUSDT"
        timeframe="1m"
        pricePrecision={2}
        visibleAt="2025-08-02T13:25:00Z"
        hideRealDate
      />,
    );
    const boundary = container.querySelector<HTMLElement>(".visible-boundary");
    expect(boundary).toHaveStyle({ left: "700px" });

    act(() => chartHarness.moveLastCandleTo(402));

    expect(boundary).toHaveStyle({ left: "402px" });
    expect(chartHarness.chart.convertToPixel).toHaveBeenLastCalledWith(
      { timestamp: Date.parse("2025-08-02T13:24:00Z") },
      { paneId: "candle_pane" },
    );
  });
});
