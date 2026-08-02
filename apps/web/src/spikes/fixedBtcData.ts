import type { KLineData } from "klinecharts";

export const FIXED_BTCUSDT_BARS: readonly KLineData[] = Array.from(
  { length: 96 },
  (_, index) => {
    const baseline = 64_200 + index * 38 + Math.sin(index / 4) * 460;
    const open = baseline + Math.sin(index * 1.7) * 95;
    const close = baseline + Math.cos(index * 1.2) * 110;
    return {
      timestamp: Date.UTC(2025, 0, 8, 0, index * 15),
      open: Number(open.toFixed(2)),
      high: Number((Math.max(open, close) + 130 + (index % 5) * 12).toFixed(2)),
      low: Number((Math.min(open, close) - 115 - (index % 4) * 14).toFixed(2)),
      close: Number(close.toFixed(2)),
      volume: 230 + (index * 47) % 780,
    };
  },
);
