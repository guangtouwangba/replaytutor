import { describe, expect, it } from "vitest";
import type { Bar } from "@replaytutor/contracts";
import { DRAWING_DEFINITIONS, anchoredVwapPoints, annotationShape, draftPreviewPoints, drawingDefinition, measurementSummary, overlayName, positionPlanSummary, regressionTrendPoints } from "./DrawingController";

const calculationBars = [
  ["2026-01-01T00:01:00Z", 100, 2],
  ["2026-01-01T00:02:00Z", 102, 3],
  ["2026-01-01T00:03:00Z", 104, 4],
  ["2026-01-01T00:04:00Z", 999, 100],
].map(([close_time, close, volume], index) => ({
  bar_id: `bar_${index}`,
  close_time,
  raw: { open: String(close), high: String(close), low: String(close), close: String(close), volume: String(volume) },
})) as unknown as Bar[];

describe("DrawingController", () => {
  it.each([
    ["trend_line", "segment", "line"],
    ["trend_ray", "rayLine", "line"],
    ["extended_line", "straightLine", "line"],
    ["price_line", "priceLine", "line"],
    ["horizontal_ray", "horizontalRayLine", "line"],
    ["vertical_line", "verticalStraightLine", "line"],
    ["parallel_channel", "parallelStraightLine", "zone"],
    ["price_channel", "priceChannelLine", "zone"],
    ["fibonacci_retracement", "fibonacciLine", "line"],
    ["measure", "segment", "line"],
    ["horizontal_line", "horizontalStraightLine", "line"],
    ["zone", "replayRect", "zone"],
    ["planned_entry", "simpleAnnotation", "marker"],
    ["stop_loss", "horizontalStraightLine", "line"],
    ["risk_reward", "replayRiskReward", "zone"],
    ["long_position", "replayRiskReward", "zone"],
    ["short_position", "replayRiskReward", "zone"],
  ] as const)("maps %s to a supported KLineChart overlay", (tool, overlay, shape) => {
    expect(overlayName(tool)).toBe(overlay);
    expect(annotationShape(tool)).toBe(shape);
  });

  it("persists long and short position plans as risk/reward chart objects", () => {
    expect(drawingDefinition("long_position").persistenceTool).toBe("long_position");
    expect(drawingDefinition("short_position").persistenceTool).toBe("short_position");
  });

  it("registers exactly forty professional tools", () => {
    const tools = new Set(DRAWING_DEFINITIONS.map((definition) => definition.tool));
    expect(DRAWING_DEFINITIONS).toHaveLength(40);
    expect(tools.size).toBe(40);
  });

  it("calculates a deterministic long position risk/reward ratio", () => {
    expect(positionPlanSummary("long_position", [
      { time: "2026-01-01T00:00:00Z", price: "100" },
      { time: "2026-01-01T00:01:00Z", price: "95" },
      { time: "2026-01-01T00:02:00Z", price: "115" },
    ])).toEqual({
      side: "long",
      entryPrice: "100",
      stopPrice: "95",
      targetPrice: "115",
      riskRewardRatio: "3.00",
    });
  });

  it("rejects an inverted short position plan", () => {
    expect(() => positionPlanSummary("short_position", [
      { time: "2026-01-01T00:00:00Z", price: "100" },
      { time: "2026-01-01T00:01:00Z", price: "95" },
      { time: "2026-01-01T00:02:00Z", price: "115" },
    ])).toThrow("空头计划要求止损高于入场价、目标低于入场价");
  });

  it("calculates price movement and duration for the ruler", () => {
    expect(measurementSummary([
      { time: "2026-01-01T00:00:00Z", price: "100" },
      { time: "2026-01-01T00:05:00Z", price: "108" },
    ])).toEqual({ change: "8", percent: "8.00", durationMs: "300000" });
  });

  it("builds a visible two-point preview immediately after the first anchor", () => {
    const anchor = { time: "2026-01-01T00:00:00Z", price: "100" };
    const cursor = { time: "2026-01-01T00:03:00Z", price: "104" };
    expect(draftPreviewPoints([anchor], cursor, 2)).toEqual([anchor, cursor]);
    expect(draftPreviewPoints([anchor], cursor, 3)).toEqual([anchor, cursor, cursor]);
  });

  it("calculates anchored VWAP only from bars inside visible_at", () => {
    const points = anchoredVwapPoints(calculationBars, [
      { time: "2026-01-01T00:01:00Z", price: "100" },
      { time: "2026-01-01T00:04:00Z", price: "999" },
    ], "2026-01-01T00:03:00Z", 2);
    expect(points).toHaveLength(3);
    expect(points.at(-1)?.time).toBe("2026-01-01T00:03:00Z");
    expect(points.at(-1)?.price).not.toBe("999.00");
  });

  it("pins regression calculations to visible bars", () => {
    const result = regressionTrendPoints(calculationBars, [
      { time: "2026-01-01T00:01:00Z", price: "100" },
      { time: "2026-01-01T00:04:00Z", price: "999" },
    ], "2026-01-01T00:03:00Z", 2);
    expect(result.slope).toBeCloseTo(2);
    expect(result.points.at(-1)?.time).toBe("2026-01-01T00:03:00Z");
  });
});
