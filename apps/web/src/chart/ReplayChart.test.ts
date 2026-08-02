import { describe, expect, it } from "vitest";
import type { Bar } from "@replaytutor/contracts";
import { chartPeriodFor, resolveDrawingPoint } from "./ReplayChart";

describe("chartPeriodFor", () => {
  it("maps every replay timeframe to the chart engine period", () => {
    expect(chartPeriodFor("1m")).toEqual({ type: "minute", span: 1 });
    expect(chartPeriodFor("5m")).toEqual({ type: "minute", span: 5 });
    expect(chartPeriodFor("15m")).toEqual({ type: "minute", span: 15 });
    expect(chartPeriodFor("1h")).toEqual({ type: "hour", span: 1 });
    expect(chartPeriodFor("4h")).toEqual({ type: "hour", span: 4 });
    expect(chartPeriodFor("1d")).toEqual({ type: "day", span: 1 });
  });

  it("rejects drawing anchors after visible_at", () => {
    expect(resolveDrawingPoint(
      { timestamp: Date.parse("2026-01-01T00:02:00Z"), value: 102 },
      [],
      "2026-01-01T00:01:00Z",
      2,
      false,
    )).toBeNull();
  });

  it("magnet-snaps to the nearest visible candle OHLC", () => {
    const bar = {
      open_time: "2026-01-01T00:00:00Z",
      close_time: "2026-01-01T00:01:00Z",
      raw: { open: "100", high: "110", low: "90", close: "105", volume: "1" },
    } as Bar;
    expect(resolveDrawingPoint(
      { timestamp: Date.parse("2026-01-01T00:00:40Z"), value: 108.7 },
      [bar],
      "2026-01-01T00:01:00Z",
      2,
      true,
    )).toEqual({ time: bar.close_time, price: "110.00" });
  });
});
