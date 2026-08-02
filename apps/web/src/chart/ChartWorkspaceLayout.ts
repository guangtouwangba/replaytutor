import type { ReplayTimeframe } from "./ReplayChart";

export const CHART_LAYOUTS = ["single", "vertical", "horizontal", "quad"] as const;
export type ChartLayout = typeof CHART_LAYOUTS[number];

export const CHART_LAYOUT_PANE_COUNT: Record<ChartLayout, number> = {
  single: 1,
  vertical: 2,
  horizontal: 2,
  quad: 4,
};

export const DEFAULT_PANE_TIMEFRAMES: readonly ReplayTimeframe[] = ["1m", "5m", "15m", "1h"];

export function isChartLayout(value: unknown): value is ChartLayout {
  return typeof value === "string" && CHART_LAYOUTS.includes(value as ChartLayout);
}

export function paneCountForLayout(layout: ChartLayout): number {
  return CHART_LAYOUT_PANE_COUNT[layout];
}
