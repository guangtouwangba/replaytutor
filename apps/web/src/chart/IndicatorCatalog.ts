export type IndicatorCategory = "trend" | "momentum" | "volatility" | "volume" | "structure";
export type IndicatorPlacement = "main" | "sub";

export interface IndicatorDefinition {
  readonly id: string;
  readonly engineName: string;
  readonly label: string;
  readonly labelZh: string;
  readonly category: IndicatorCategory;
  readonly placement: IndicatorPlacement;
  readonly defaultParams?: readonly number[];
  readonly aliases?: readonly string[];
  readonly descriptionZh: string;
}

export interface IndicatorInstance {
  readonly instanceId: string;
  readonly definitionId: string;
  readonly params?: readonly number[];
  readonly visible: boolean;
}

const definition = (
  id: string,
  label: string,
  labelZh: string,
  category: IndicatorCategory,
  placement: IndicatorPlacement,
  descriptionZh: string,
  defaultParams?: readonly number[],
  aliases?: readonly string[],
): IndicatorDefinition => ({
  id,
  engineName: id,
  label,
  labelZh,
  category,
  placement,
  descriptionZh,
  defaultParams,
  aliases,
});

/**
 * Stable ReplayTutor catalog. The first 27 entries mirror the indicators bundled
 * with the pinned KLineChart 10.0.0 build; the final four are owned extensions.
 */
export const INDICATOR_CATALOG: readonly IndicatorDefinition[] = [
  definition("AVP", "Average Price", "平均价格", "trend", "main", "累计平均成交价格"),
  definition("AO", "Awesome Oscillator", "动量震荡器", "momentum", "sub", "短长周期中间价动量差"),
  definition("BIAS", "BIAS", "乖离率", "momentum", "sub", "价格偏离移动平均线的程度"),
  definition("BOLL", "Bollinger Bands", "布林带", "volatility", "main", "均线与标准差波动通道"),
  definition("BRAR", "BRAR", "情绪意愿指标", "momentum", "sub", "多空意愿与人气强弱"),
  definition("BBI", "Bull and Bear Index", "多空指标", "trend", "main", "多周期均线综合趋势"),
  definition("CCI", "CCI", "顺势指标", "momentum", "sub", "价格偏离统计均值的幅度"),
  definition("CR", "CR", "能量指标", "momentum", "sub", "价格动量与多空力量"),
  definition("DMA", "DMA", "平均线差", "trend", "sub", "不同周期均线差及其均线"),
  definition("DMI", "DMI", "趋向指标", "trend", "sub", "方向强度与趋势强弱"),
  definition("EMV", "EMV", "简易波动指标", "volume", "sub", "价格移动与成交量的关系"),
  definition("EMA", "EMA", "指数移动平均", "trend", "main", "近期价格权重更高的移动平均", [6, 12, 20]),
  definition("MTM", "Momentum", "动量指标", "momentum", "sub", "当前价格相对历史价格的变化"),
  definition("MA", "Moving Average", "移动平均", "trend", "main", "简单移动平均线", [5, 10, 30, 60]),
  definition("MACD", "MACD", "指数平滑异同均线", "momentum", "sub", "趋势与动量组合指标"),
  definition("OBV", "On-Balance Volume", "能量潮", "volume", "sub", "按涨跌方向累计成交量", [30], ["OB"]),
  definition("PVT", "Price Volume Trend", "价量趋势", "volume", "sub", "价格变化率加权累计成交量"),
  definition("PSY", "Psychological Line", "心理线", "momentum", "sub", "上涨 K 线占比"),
  definition("ROC", "Rate of Change", "变动率", "momentum", "sub", "价格相对历史值的变化率"),
  definition("RSI", "RSI", "相对强弱", "momentum", "sub", "上涨与下跌动量的相对强弱"),
  definition("SMA", "SMA", "平滑移动平均", "trend", "main", "递归平滑移动平均"),
  definition("KDJ", "KDJ", "随机指标", "momentum", "sub", "区间位置与短期动量"),
  definition("SAR", "Parabolic SAR", "抛物线转向", "trend", "main", "趋势跟随与潜在转向点"),
  definition("TRIX", "TRIX", "三重指数平滑", "trend", "sub", "过滤短期噪声的趋势变化率"),
  definition("VOL", "Volume", "成交量", "volume", "sub", "成交量柱及成交量均线", [5, 10, 20]),
  definition("VR", "Volume Ratio", "成交量比率", "volume", "sub", "上涨、下跌和平盘成交量比例"),
  definition("WR", "Williams %R", "威廉指标", "momentum", "sub", "收盘价在近期高低区间中的位置"),
  definition("VWAP", "VWAP", "成交量加权均价", "volume", "main", "从会话首根开始累计的成交量加权均价"),
  definition("ATR", "ATR", "平均真实波幅", "volatility", "sub", "Wilder 平滑真实波幅", [14]),
  definition("BAR_COUNT", "Bar Count", "K 线连续编号", "structure", "main", "从会话首根完整 K 线开始连续编号"),
  definition("ORDER_BLOCK", "Order Block", "订单块", "structure", "main", "确认结构突破后生成且不重画的订单块", [14, 3, 1.5], ["OB", "订单区"]),
] as const;

export const DEFAULT_INDICATORS: readonly IndicatorInstance[] = [
  { instanceId: "indicator-default-volume", definitionId: "VOL", visible: true },
];

export const TUTOR_EVIDENCE_INDICATORS = new Set([
  "MA", "EMA", "VOL", "OBV", "VWAP", "ATR", "BAR_COUNT", "ORDER_BLOCK",
]);

export function supportsTutorEvidence(definitionId: string): boolean {
  return TUTOR_EVIDENCE_INDICATORS.has(definitionId);
}

export function indicatorDefinition(definitionId: string): IndicatorDefinition {
  const match = INDICATOR_CATALOG.find((item) => item.id === definitionId);
  if (!match) throw new Error(`Unknown indicator definition: ${definitionId}`);
  return match;
}

export function createIndicatorInstance(definitionId: string): IndicatorInstance {
  const item = indicatorDefinition(definitionId);
  return {
    instanceId: `indicator-${crypto.randomUUID()}`,
    definitionId,
    params: item.defaultParams ? [...item.defaultParams] : undefined,
    visible: true,
  };
}

export function searchIndicators(query: string): readonly IndicatorDefinition[] {
  const normalized = query.trim().toLocaleLowerCase();
  if (!normalized) return INDICATOR_CATALOG;
  return INDICATOR_CATALOG.filter((item) => [
    item.id,
    item.label,
    item.labelZh,
    item.descriptionZh,
    ...(item.aliases ?? []),
  ].some((value) => value.toLocaleLowerCase().includes(normalized)));
}
