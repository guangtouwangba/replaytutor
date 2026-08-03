import type { KLineData } from "klinecharts";
import { describe, expect, it } from "vitest";
import { calculateAtr, calculateBarCount, calculateOrderBlocks, calculateVwap } from "./IndicatorRegistry";

const bars = (values: Array<[number, number, number, number, number]>): KLineData[] => values.map(
  ([open, high, low, close, volume], index) => ({ timestamp: index * 60_000, open, high, low, close, volume }),
);

describe("ReplayTutor indicators", () => {
  it("calculates Wilder ATR without emitting warmup values", () => {
    const result = calculateAtr(bars([
      [10, 12, 9, 11, 1], [11, 13, 10, 12, 1], [12, 14, 11, 13, 1], [13, 16, 12, 15, 1],
    ]), 3);
    expect(result.slice(0, 2)).toEqual([{}, {}]);
    expect(result[2]?.atr).toBeCloseTo(3);
    expect(result[3]?.atr).toBeCloseTo(10 / 3);
  });

  it("calculates session-anchored VWAP and one-based bar numbers", () => {
    const source = bars([[10, 12, 8, 11, 2], [12, 14, 10, 13, 1]]);
    expect(calculateVwap(source)[1]?.vwap).toBeCloseTo((10.3333333333 * 2 + 12.3333333333) / 3);
    expect(calculateBarCount(source).map((item) => item.count)).toEqual([1, 2]);
  });

  it("never changes an already visible Order Block prefix when future bars are appended", () => {
    const source = bars([
      [100, 103, 99, 102, 10], [102, 105, 101, 104, 10], [104, 106, 102, 103, 10],
      [103, 104, 98, 99, 10], [99, 101, 96, 98, 10], [98, 100, 97, 99, 10],
      [99, 102, 98, 101, 10], [101, 104, 100, 103, 10], [103, 108, 102, 107, 10],
      [107, 114, 106, 113, 10], [113, 116, 111, 115, 10], [115, 118, 114, 117, 10],
      [117, 119, 112, 113, 10], [113, 114, 108, 109, 10],
    ]);
    const prefix = calculateOrderBlocks(source.slice(0, 12), 3, 2, 1);
    const extended = calculateOrderBlocks(source, 3, 2, 1);
    expect(extended.slice(0, prefix.length)).toEqual(prefix);
  });
});
