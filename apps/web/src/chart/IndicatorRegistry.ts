import {
  getSupportedIndicators,
  registerIndicator,
  type IndicatorTemplate,
  type KLineData,
} from "klinecharts";

export interface AtrValue { readonly atr?: number }
export interface VwapValue { readonly vwap?: number }
export interface BarCountValue { readonly anchor?: number; readonly count: number }
export interface OrderBlockValue {
  readonly bullTop?: number;
  readonly bullBottom?: number;
  readonly bearTop?: number;
  readonly bearBottom?: number;
  readonly bullStatus?: "active" | "mitigated";
  readonly bearStatus?: "active" | "mitigated";
}

function trueRange(current: KLineData, previous?: KLineData): number {
  if (!previous) return current.high - current.low;
  return Math.max(
    current.high - current.low,
    Math.abs(current.high - previous.close),
    Math.abs(current.low - previous.close),
  );
}

export function calculateAtr(data: readonly KLineData[], period = 14): AtrValue[] {
  const safePeriod = Math.max(1, Math.floor(period));
  let running = 0;
  let previousAtr: number | undefined;
  return data.map((bar, index) => {
    const range = trueRange(bar, data[index - 1]);
    if (index < safePeriod) running += range;
    if (index < safePeriod - 1) return {};
    if (index === safePeriod - 1) {
      previousAtr = running / safePeriod;
      return { atr: previousAtr };
    }
    previousAtr = ((previousAtr ?? range) * (safePeriod - 1) + range) / safePeriod;
    return { atr: previousAtr };
  });
}

export function calculateVwap(data: readonly KLineData[]): VwapValue[] {
  let cumulativeVolume = 0;
  let cumulativePriceVolume = 0;
  return data.map((bar) => {
    const volume = Number.isFinite(bar.volume) ? Math.max(0, bar.volume ?? 0) : 0;
    const typical = (bar.high + bar.low + bar.close) / 3;
    cumulativeVolume += volume;
    cumulativePriceVolume += typical * volume;
    return cumulativeVolume > 0 ? { vwap: cumulativePriceVolume / cumulativeVolume } : {};
  });
}

export function calculateBarCount(data: readonly KLineData[]): BarCountValue[] {
  return data.map((bar, index) => ({ anchor: bar.high, count: index + 1 }));
}

interface Zone {
  readonly top: number;
  readonly bottom: number;
  readonly confirmedAt: number;
  mitigated: boolean;
  invalidated: boolean;
}

function confirmedPivotHigh(data: readonly KLineData[], pivotIndex: number, radius: number): boolean {
  const target = data[pivotIndex]?.high;
  if (target === undefined) return false;
  for (let index = pivotIndex - radius; index <= pivotIndex + radius; index += 1) {
    if (index !== pivotIndex && data[index] && data[index].high >= target) return false;
  }
  return true;
}

function confirmedPivotLow(data: readonly KLineData[], pivotIndex: number, radius: number): boolean {
  const target = data[pivotIndex]?.low;
  if (target === undefined) return false;
  for (let index = pivotIndex - radius; index <= pivotIndex + radius; index += 1) {
    if (index !== pivotIndex && data[index] && data[index].low <= target) return false;
  }
  return true;
}

function lastOppositeCandle(
  data: readonly KLineData[],
  before: number,
  bullishBreak: boolean,
  maxLookback = 20,
): KLineData | undefined {
  const start = Math.max(0, before - maxLookback);
  for (let index = before; index >= start; index -= 1) {
    const bar = data[index];
    if (bullishBreak ? bar.close < bar.open : bar.close > bar.open) return bar;
  }
  return undefined;
}

export function calculateOrderBlocks(
  data: readonly KLineData[],
  atrPeriod = 14,
  pivotRadius = 3,
  displacementMultiplier = 1.5,
): OrderBlockValue[] {
  const radius = Math.max(1, Math.floor(pivotRadius));
  const atr = calculateAtr(data, atrPeriod);
  const result: OrderBlockValue[] = [];
  let swingHigh: { index: number; price: number } | undefined;
  let swingLow: { index: number; price: number } | undefined;
  let consumedHigh = -1;
  let consumedLow = -1;
  let bullZone: Zone | undefined;
  let bearZone: Zone | undefined;

  for (let index = 0; index < data.length; index += 1) {
    const confirmedIndex = index - radius;
    if (confirmedIndex >= radius) {
      if (confirmedPivotHigh(data, confirmedIndex, radius)) {
        swingHigh = { index: confirmedIndex, price: data[confirmedIndex].high };
      }
      if (confirmedPivotLow(data, confirmedIndex, radius)) {
        swingLow = { index: confirmedIndex, price: data[confirmedIndex].low };
      }
    }

    const bar = data[index];
    const threshold = (atr[index]?.atr ?? Number.POSITIVE_INFINITY) * displacementMultiplier;
    const displacement = trueRange(bar, data[index - 1]) >= threshold;
    if (displacement && swingHigh && swingHigh.index > consumedHigh && bar.close > swingHigh.price) {
      const source = lastOppositeCandle(data, index - 1, true);
      if (source) {
        bullZone = { top: source.high, bottom: source.low, confirmedAt: index, mitigated: false, invalidated: false };
        consumedHigh = swingHigh.index;
      }
    }
    if (displacement && swingLow && swingLow.index > consumedLow && bar.close < swingLow.price) {
      const source = lastOppositeCandle(data, index - 1, false);
      if (source) {
        bearZone = { top: source.high, bottom: source.low, confirmedAt: index, mitigated: false, invalidated: false };
        consumedLow = swingLow.index;
      }
    }

    if (bullZone && index > bullZone.confirmedAt) {
      if (bar.close < bullZone.bottom) bullZone.invalidated = true;
      else if (bar.low <= bullZone.top && bar.high >= bullZone.bottom) bullZone.mitigated = true;
    }
    if (bearZone && index > bearZone.confirmedAt) {
      if (bar.close > bearZone.top) bearZone.invalidated = true;
      else if (bar.low <= bearZone.top && bar.high >= bearZone.bottom) bearZone.mitigated = true;
    }

    result.push({
      ...(bullZone && !bullZone.invalidated ? {
        bullTop: bullZone.top,
        bullBottom: bullZone.bottom,
        bullStatus: bullZone.mitigated ? "mitigated" as const : "active" as const,
      } : {}),
      ...(bearZone && !bearZone.invalidated ? {
        bearTop: bearZone.top,
        bearBottom: bearZone.bottom,
        bearStatus: bearZone.mitigated ? "mitigated" as const : "active" as const,
      } : {}),
    });
  }
  return result;
}

const atrIndicator: IndicatorTemplate<AtrValue, number> = {
  name: "ATR",
  shortName: "ATR",
  series: "normal",
  calcParams: [14],
  figures: [{ key: "atr", title: "ATR: ", type: "line" }],
  calc: (data, indicator) => calculateAtr(data, indicator.calcParams[0] ?? 14),
};

const vwapIndicator: IndicatorTemplate<VwapValue> = {
  name: "VWAP",
  shortName: "VWAP",
  series: "price",
  figures: [{ key: "vwap", title: "VWAP: ", type: "line" }],
  calc: calculateVwap,
};

const barCountIndicator: IndicatorTemplate<BarCountValue> = {
  name: "BAR_COUNT",
  shortName: "BAR COUNT",
  series: "price",
  shouldOhlc: false,
  figures: [{
    key: "anchor",
    title: "# ",
    type: "text",
    attrs: ({ data, coordinate, barSpace }) => {
      if (!data.current || coordinate.current.anchor === undefined) return null;
      if (barSpace.bar < 7 && data.current.count % 5 !== 0) return null;
      return {
        x: coordinate.current.x,
        y: coordinate.current.anchor - 5,
        text: String(data.current.count),
        align: "center",
        baseline: "bottom",
      };
    },
    styles: () => ({ color: "#687789", size: 9 }),
  }],
  calc: calculateBarCount,
};

const orderBlockIndicator: IndicatorTemplate<OrderBlockValue, number> = {
  name: "ORDER_BLOCK",
  shortName: "ORDER BLOCK",
  series: "price",
  shouldOhlc: false,
  calcParams: [14, 3, 1.5],
  figures: [
    {
      key: "bullTop",
      title: "Bull OB: ",
      type: "rect",
      attrs: ({ coordinate, barSpace }) => {
        const top = coordinate.current.bullTop;
        const bottom = coordinate.current.bullBottom;
        if (top === undefined || bottom === undefined) return null;
        return { x: coordinate.current.x - barSpace.halfBar, y: top, width: barSpace.bar, height: bottom - top };
      },
      styles: ({ data }) => ({
        style: "fill",
        color: data.current?.bullStatus === "mitigated" ? "rgba(33,197,139,.10)" : "rgba(33,197,139,.18)",
      }),
    },
    {
      key: "bearTop",
      title: "Bear OB: ",
      type: "rect",
      attrs: ({ coordinate, barSpace }) => {
        const top = coordinate.current.bearTop;
        const bottom = coordinate.current.bearBottom;
        if (top === undefined || bottom === undefined) return null;
        return { x: coordinate.current.x - barSpace.halfBar, y: top, width: barSpace.bar, height: bottom - top };
      },
      styles: ({ data }) => ({
        style: "fill",
        color: data.current?.bearStatus === "mitigated" ? "rgba(240,91,114,.10)" : "rgba(240,91,114,.18)",
      }),
    },
  ],
  calc: (data, indicator) => calculateOrderBlocks(
    data,
    indicator.calcParams[0] ?? 14,
    indicator.calcParams[1] ?? 3,
    indicator.calcParams[2] ?? 1.5,
  ),
};

let registered = false;

export function registerReplayIndicators(): void {
  if (registered) return;
  const supported = new Set(getSupportedIndicators());
  if (!supported.has(atrIndicator.name)) registerIndicator(atrIndicator);
  if (!supported.has(vwapIndicator.name)) registerIndicator(vwapIndicator);
  if (!supported.has(barCountIndicator.name)) registerIndicator(barCountIndicator);
  if (!supported.has(orderBlockIndicator.name)) registerIndicator(orderBlockIndicator);
  registered = true;
}
