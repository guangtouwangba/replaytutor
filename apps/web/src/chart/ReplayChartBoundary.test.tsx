import type { Bar, ChartAnnotation } from "@replaytutor/contracts";
import { act, fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import i18n from "../i18n";

const chartHarness = vi.hoisted(() => {
  const callbacks = new Map<string, () => void>();
  let candleX = 700;
  const chart = {
    convertFromPixel: vi.fn(() => [{ value: 108852.6 }]),
    convertToPixel: vi.fn(() => ({ x: candleX })),
    createOverlay: vi.fn((overlay: { id?: string }) => overlay.id ?? null),
    createIndicator: vi.fn(() => "indicator-pane"),
    getIndicators: vi.fn(() => []),
    getSize: vi.fn(() => ({ width: 82, height: 640, left: 918, right: 0, top: 0, bottom: 0 })),
    overrideIndicator: vi.fn(() => true),
    removeIndicator: vi.fn(() => true),
    removeOverlay: vi.fn(() => true),
    resetData: vi.fn(),
    setDataLoader: vi.fn(),
    setOffsetRightDistance: vi.fn(),
    setPeriod: vi.fn(),
    setRightMinVisibleBarCount: vi.fn(),
    setStyles: vi.fn(),
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

const annotations = [{
  annotation_id: "annotation-1",
  label: "我的观察",
  tool: "horizontal_line",
  layer: "user",
  points: [{ time: "2025-08-02T13:25:00Z", price: "105" }],
  style: { line_color: "#20b7f5", line_width: 1, line_dash: "solid" },
  properties: {},
  metadata: { drawing_kind: "horizontal_line" },
}] as unknown as ChartAnnotation[];

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

  it("collapses indicator legends without hiding the indicator", () => {
    render(
      <ReplayChart
        bars={bars}
        symbol="BTCUSDT"
        timeframe="1m"
        pricePrecision={2}
        visibleAt="2025-08-02T13:25:00Z"
        hideRealDate
        indicators={[{ instanceId: "indicator-ma", definitionId: "MA", visible: true }]}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "收起指标图例" }));

    expect(screen.getByRole("button", { name: "展开指标图例" })).toHaveAttribute("aria-expanded", "false");
    expect(chartHarness.chart.setStyles).toHaveBeenLastCalledWith({
      indicator: { tooltip: { showRule: "none" } },
    });
    expect(chartHarness.chart.createIndicator).toHaveBeenLastCalledWith(expect.objectContaining({
      id: "indicator-ma",
      visible: true,
    }), false);
  });

  it("creates a visible-frame horizontal line from the right price scale", () => {
    const onPriceAxisHorizontalLine = vi.fn();
    const { container } = render(
      <ReplayChart
        bars={bars}
        symbol="BTCUSDT"
        timeframe="1m"
        pricePrecision={2}
        visibleAt="2025-08-02T13:25:00Z"
        hideRealDate
        onPriceAxisHorizontalLine={onPriceAxisHorizontalLine}
      />,
    );

    fireEvent.mouseMove(container.querySelector(".replay-chart")!, { clientX: 950, clientY: 220 });
    const addButton = screen.getByRole("button", { name: "打开价格 108852.60 的操作" });
    expect(addButton).toBeVisible();
    expect(container.querySelector(".price-axis-guide")).toHaveStyle({ top: "220px", right: "82px" });
    expect(screen.queryByRole("menu", { name: "价格刻度操作" })).not.toBeInTheDocument();

    fireEvent.mouseMove(container.querySelector(".replay-chart")!, { clientX: 950, clientY: 310 });
    expect(container.querySelector(".price-axis-guide")).toHaveStyle({ top: "310px", right: "82px" });

    fireEvent.click(addButton);
    expect(screen.getByRole("menu", { name: "价格刻度操作" })).toBeVisible();
    expect(screen.getByRole("menuitem")).toHaveTextContent("108,852.60");

    fireEvent.click(screen.getByRole("menuitem"));

    expect(onPriceAxisHorizontalLine).toHaveBeenCalledWith({
      time: "2025-08-02T13:25:00Z",
      price: "108852.60",
    });
    expect(chartHarness.chart.convertFromPixel).toHaveBeenCalledWith(
      [{ y: 220 }],
      { paneId: "candle_pane", absolute: true },
    );
  });

  it("keeps selected-object actions compact until the user expands them", () => {
    const { container } = render(
      <ReplayChart
        annotations={annotations}
        bars={bars}
        symbol="BTCUSDT"
        timeframe="1m"
        pricePrecision={2}
        visibleAt="2025-08-02T13:25:00Z"
        hideRealDate
        onAnnotationDelete={vi.fn()}
        selectedAnnotationId="annotation-1"
      />,
    );

    expect(container.querySelector(".chart-object-actions")).toHaveClass("is-collapsed");
    expect(screen.queryByRole("combobox", { name: "线宽" })).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "展开图表对象工具栏" }));

    expect(container.querySelector(".chart-object-actions")).toHaveClass("is-expanded");
    expect(screen.getByRole("combobox", { name: "线宽" })).toBeVisible();

    fireEvent.click(screen.getByRole("button", { name: "收起图表对象工具栏" }));
    expect(screen.queryByRole("combobox", { name: "线宽" })).not.toBeInTheDocument();
  });
});
