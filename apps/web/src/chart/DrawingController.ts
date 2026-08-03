import type { AnnotationPoint, Bar, ChartAnnotation, CreateAnnotationRequest } from "@replaytutor/contracts";

export type DrawingTool =
  | "select"
  | "trend_line"
  | "trend_ray"
  | "extended_line"
  | "price_line"
  | "horizontal_ray"
  | "vertical_line"
  | "parallel_channel"
  | "price_channel"
  | "info_line"
  | "trend_angle"
  | "cross_line"
  | "regression_trend"
  | "flat_top_bottom"
  | "disjoint_channel"
  | "anchored_vwap"
  | "fibonacci_retracement"
  | "fibonacci_extension"
  | "fibonacci_channel"
  | "fibonacci_time_zone"
  | "pitchfork"
  | "measure"
  | "price_range"
  | "date_range"
  | "horizontal_line"
  | "zone"
  | "brush"
  | "polyline"
  | "head_shoulders"
  | "triangle_pattern"
  | "text"
  | "note_marker"
  | "planned_entry"
  | "add_position"
  | "reduce_position"
  | "planned_exit"
  | "stop_loss"
  | "take_profit"
  | "long_position"
  | "short_position"
  | "risk_reward";

export type DrawingGroup = "analysis" | "fibonacci" | "measure" | "shapes" | "notes" | "trade" | "position";

export interface DrawingDefinition {
  readonly tool: Exclude<DrawingTool, "select">;
  readonly label: string;
  readonly shortLabel: string;
  readonly shape: ChartAnnotation["shape"];
  readonly semanticRole: CreateAnnotationRequest["semantic_role"];
  readonly persistenceTool: ChartAnnotation["tool"];
  readonly group: DrawingGroup;
  readonly instruction: string;
  readonly requiredPoints: number;
  readonly overlayName:
    | "segment"
    | "rayLine"
    | "straightLine"
    | "priceLine"
    | "horizontalRayLine"
    | "verticalStraightLine"
    | "horizontalStraightLine"
    | "parallelStraightLine"
    | "priceChannelLine"
    | "fibonacciLine"
    | "replayRect"
    | "replayRiskReward"
    | "replayPolyline"
    | "replayLevels"
    | "replayHorizontalLine"
    | "simpleAnnotation";
}

export const DRAWING_DEFINITIONS: readonly DrawingDefinition[] = [
  { tool: "trend_line", label: "趋势线", shortLabel: "趋势", shape: "line", semanticRole: "analysis", persistenceTool: "trend_line", group: "analysis", instruction: "依次点击趋势起点和终点", requiredPoints: 2, overlayName: "segment" },
  { tool: "trend_ray", label: "射线", shortLabel: "射线", shape: "line", semanticRole: "analysis", persistenceTool: "trend_ray", group: "analysis", instruction: "点击起点和方向点，射线向后延伸", requiredPoints: 2, overlayName: "rayLine" },
  { tool: "extended_line", label: "延长线", shortLabel: "延长", shape: "line", semanticRole: "analysis", persistenceTool: "extended_line", group: "analysis", instruction: "点击两个点，直线向两端延伸", requiredPoints: 2, overlayName: "straightLine" },
  { tool: "price_line", label: "价格线", shortLabel: "价格", shape: "line", semanticRole: "analysis", persistenceTool: "price_line", group: "analysis", instruction: "点击起点，显示该价格并向右延伸", requiredPoints: 1, overlayName: "priceLine" },
  { tool: "horizontal_ray", label: "水平射线", shortLabel: "水平射线", shape: "line", semanticRole: "analysis", persistenceTool: "horizontal_ray", group: "analysis", instruction: "点击起点和延伸方向", requiredPoints: 2, overlayName: "horizontalRayLine" },
  { tool: "vertical_line", label: "垂直线", shortLabel: "垂直", shape: "line", semanticRole: "analysis", persistenceTool: "vertical_line", group: "analysis", instruction: "点击一个时间位置", requiredPoints: 1, overlayName: "verticalStraightLine" },
  { tool: "parallel_channel", label: "平行通道", shortLabel: "通道", shape: "zone", semanticRole: "analysis", persistenceTool: "parallel_channel", group: "analysis", instruction: "先画基准趋势线，再点击通道宽度", requiredPoints: 3, overlayName: "parallelStraightLine" },
  { tool: "price_channel", label: "等距价格通道", shortLabel: "价格通道", shape: "zone", semanticRole: "analysis", persistenceTool: "price_channel", group: "analysis", instruction: "先画中线，再点击通道宽度", requiredPoints: 3, overlayName: "priceChannelLine" },
  { tool: "info_line", label: "信息线", shortLabel: "信息", shape: "line", semanticRole: "analysis", persistenceTool: "info_line", group: "analysis", instruction: "点击起点和终点，显示价格与时间变化", requiredPoints: 2, overlayName: "segment" },
  { tool: "trend_angle", label: "趋势角度", shortLabel: "角度", shape: "line", semanticRole: "analysis", persistenceTool: "trend_angle", group: "analysis", instruction: "点击起点和方向点，测量趋势角度", requiredPoints: 2, overlayName: "segment" },
  { tool: "cross_line", label: "十字线", shortLabel: "十字", shape: "line", semanticRole: "analysis", persistenceTool: "cross_line", group: "analysis", instruction: "点击时间与价格交点", requiredPoints: 1, overlayName: "simpleAnnotation" },
  { tool: "regression_trend", label: "回归趋势", shortLabel: "回归", shape: "zone", semanticRole: "analysis", persistenceTool: "regression_trend", group: "analysis", instruction: "选择可见行情区间计算回归通道", requiredPoints: 2, overlayName: "parallelStraightLine" },
  { tool: "flat_top_bottom", label: "平顶／平底", shortLabel: "平顶底", shape: "zone", semanticRole: "analysis", persistenceTool: "flat_top_bottom", group: "analysis", instruction: "标记水平边界与趋势边界", requiredPoints: 3, overlayName: "priceChannelLine" },
  { tool: "disjoint_channel", label: "不相交通道", shortLabel: "不相交", shape: "zone", semanticRole: "analysis", persistenceTool: "disjoint_channel", group: "analysis", instruction: "分别绘制两条独立通道边界", requiredPoints: 4, overlayName: "replayPolyline" },
  { tool: "anchored_vwap", label: "锚定 VWAP", shortLabel: "AVWAP", shape: "line", semanticRole: "analysis", persistenceTool: "anchored_vwap", group: "analysis", instruction: "选择起点与可见终点计算锚定 VWAP", requiredPoints: 2, overlayName: "replayPolyline" },
  { tool: "fibonacci_retracement", label: "斐波那契回撤", shortLabel: "斐波", shape: "line", semanticRole: "analysis", persistenceTool: "fibonacci_retracement", group: "fibonacci", instruction: "依次点击波段起点和终点", requiredPoints: 2, overlayName: "fibonacciLine" },
  { tool: "fibonacci_extension", label: "斐波那契扩展", shortLabel: "Fib 扩展", shape: "line", semanticRole: "analysis", persistenceTool: "fibonacci_extension", group: "fibonacci", instruction: "选择波段起点、终点和回调点", requiredPoints: 3, overlayName: "replayLevels" },
  { tool: "fibonacci_channel", label: "斐波那契通道", shortLabel: "Fib 通道", shape: "zone", semanticRole: "analysis", persistenceTool: "fibonacci_channel", group: "fibonacci", instruction: "选择基准线和通道宽度", requiredPoints: 3, overlayName: "parallelStraightLine" },
  { tool: "fibonacci_time_zone", label: "斐波那契时间区间", shortLabel: "Fib 时间", shape: "line", semanticRole: "analysis", persistenceTool: "fibonacci_time_zone", group: "fibonacci", instruction: "选择时间波段起点和终点", requiredPoints: 2, overlayName: "replayLevels" },
  { tool: "pitchfork", label: "Pitchfork", shortLabel: "Pitchfork", shape: "zone", semanticRole: "analysis", persistenceTool: "pitchfork", group: "fibonacci", instruction: "选择枢轴点和两侧结构点", requiredPoints: 3, overlayName: "priceChannelLine" },
  { tool: "measure", label: "日期与价格测量", shortLabel: "测量", shape: "line", semanticRole: "analysis", persistenceTool: "measure", group: "measure", instruction: "依次点击测量起点和终点", requiredPoints: 2, overlayName: "segment" },
  { tool: "price_range", label: "价格范围", shortLabel: "价格范围", shape: "zone", semanticRole: "analysis", persistenceTool: "price_range", group: "measure", instruction: "选择价格区间的两个边界", requiredPoints: 2, overlayName: "replayRect" },
  { tool: "date_range", label: "日期范围", shortLabel: "日期范围", shape: "zone", semanticRole: "analysis", persistenceTool: "date_range", group: "measure", instruction: "选择时间区间的起点和终点", requiredPoints: 2, overlayName: "replayRect" },
  { tool: "horizontal_line", label: "水平线", shortLabel: "水平", shape: "line", semanticRole: "analysis", persistenceTool: "horizontal_line", group: "analysis", instruction: "点击一个关键价格", requiredPoints: 1, overlayName: "replayHorizontalLine" },
  { tool: "zone", label: "价格区域", shortLabel: "区域", shape: "zone", semanticRole: "analysis", persistenceTool: "zone", group: "shapes", instruction: "点击区域的两个对角点", requiredPoints: 2, overlayName: "replayRect" },
  { tool: "brush", label: "画笔", shortLabel: "画笔", shape: "line", semanticRole: "analysis", persistenceTool: "brush", group: "shapes", instruction: "连续点击最多 16 个结构点", requiredPoints: 4, overlayName: "replayPolyline" },
  { tool: "polyline", label: "多段线", shortLabel: "多段线", shape: "line", semanticRole: "analysis", persistenceTool: "polyline", group: "shapes", instruction: "依次点击折线控制点", requiredPoints: 4, overlayName: "replayPolyline" },
  { tool: "head_shoulders", label: "头肩形态", shortLabel: "头肩", shape: "line", semanticRole: "analysis", persistenceTool: "head_shoulders", group: "shapes", instruction: "依次标记左肩、头部、右肩和颈线", requiredPoints: 4, overlayName: "replayPolyline" },
  { tool: "triangle_pattern", label: "三角形态", shortLabel: "三角", shape: "zone", semanticRole: "analysis", persistenceTool: "triangle_pattern", group: "shapes", instruction: "选择上下边界的四个点", requiredPoints: 4, overlayName: "replayPolyline" },
  { tool: "text", label: "文字说明", shortLabel: "文字", shape: "label", semanticRole: "note", persistenceTool: "text", group: "notes", instruction: "点击文字的锚点", requiredPoints: 1, overlayName: "simpleAnnotation" },
  { tool: "note_marker", label: "观察标记", shortLabel: "观察", shape: "marker", semanticRole: "note", persistenceTool: "note_marker", group: "notes", instruction: "点击要记录的位置", requiredPoints: 1, overlayName: "simpleAnnotation" },
  { tool: "planned_entry", label: "计划开仓", shortLabel: "开仓", shape: "marker", semanticRole: "entry", persistenceTool: "planned_entry", group: "trade", instruction: "点击计划开仓价", requiredPoints: 1, overlayName: "simpleAnnotation" },
  { tool: "add_position", label: "计划加仓", shortLabel: "加仓", shape: "marker", semanticRole: "add_position", persistenceTool: "add_position", group: "trade", instruction: "点击计划加仓价", requiredPoints: 1, overlayName: "simpleAnnotation" },
  { tool: "reduce_position", label: "计划减仓", shortLabel: "减仓", shape: "marker", semanticRole: "reduce_position", persistenceTool: "reduce_position", group: "trade", instruction: "点击计划减仓价", requiredPoints: 1, overlayName: "simpleAnnotation" },
  { tool: "planned_exit", label: "计划平仓", shortLabel: "平仓", shape: "marker", semanticRole: "exit", persistenceTool: "planned_exit", group: "trade", instruction: "点击计划平仓价", requiredPoints: 1, overlayName: "simpleAnnotation" },
  { tool: "stop_loss", label: "止损线", shortLabel: "止损", shape: "line", semanticRole: "stop_loss", persistenceTool: "stop_loss", group: "trade", instruction: "点击止损价格", requiredPoints: 1, overlayName: "horizontalStraightLine" },
  { tool: "take_profit", label: "止盈线", shortLabel: "止盈", shape: "line", semanticRole: "take_profit", persistenceTool: "take_profit", group: "trade", instruction: "点击止盈价格", requiredPoints: 1, overlayName: "horizontalStraightLine" },
  { tool: "long_position", label: "多头仓位计划", shortLabel: "多头", shape: "zone", semanticRole: "risk_reward", persistenceTool: "long_position", group: "position", instruction: "依次点击入场、止损、目标价", requiredPoints: 3, overlayName: "replayRiskReward" },
  { tool: "short_position", label: "空头仓位计划", shortLabel: "空头", shape: "zone", semanticRole: "risk_reward", persistenceTool: "short_position", group: "position", instruction: "依次点击入场、止损、目标价", requiredPoints: 3, overlayName: "replayRiskReward" },
  { tool: "risk_reward", label: "风险收益测算", shortLabel: "盈亏比", shape: "zone", semanticRole: "risk_reward", persistenceTool: "risk_reward", group: "position", instruction: "依次点击入场、止损、目标价", requiredPoints: 3, overlayName: "replayRiskReward" },
] as const;

export const LINE_TOOL_SECTIONS = [
  {
    label: "线",
    tools: [
      "trend_line",
      "trend_ray",
      "extended_line",
      "price_line",
      "horizontal_line",
      "horizontal_ray",
      "vertical_line",
      "info_line",
      "trend_angle",
      "cross_line",
      "regression_trend",
    ],
  },
  {
    label: "通道",
    tools: ["parallel_channel", "price_channel", "disjoint_channel"],
  },
] as const satisfies readonly {
  readonly label: string;
  readonly tools: readonly Exclude<DrawingTool, "select">[];
}[];

export const LINE_TOOL_IDS = LINE_TOOL_SECTIONS.flatMap((section) => section.tools);

export const FIBONACCI_TOOL_SECTIONS = [
  { label: "斐波那契", tools: ["fibonacci_retracement", "fibonacci_extension", "fibonacci_channel", "fibonacci_time_zone", "pitchfork"] },
] as const satisfies readonly {
  readonly label: string;
  readonly tools: readonly Exclude<DrawingTool, "select">[];
}[];

export const FIBONACCI_TOOL_IDS = FIBONACCI_TOOL_SECTIONS.flatMap((section) => section.tools);

export const PREDICTION_TOOL_SECTIONS = [
  { label: "预测", tools: ["long_position", "short_position", "risk_reward"] },
  { label: "基于成交量", tools: ["anchored_vwap"] },
  { label: "测量", tools: ["measure", "price_range", "date_range"] },
] as const satisfies readonly {
  readonly label: string;
  readonly tools: readonly Exclude<DrawingTool, "select">[];
}[];

export const PREDICTION_TOOL_IDS = PREDICTION_TOOL_SECTIONS.flatMap((section) => section.tools);

export const PATTERN_TOOL_SECTIONS = [
  { label: "图表形态", tools: ["head_shoulders", "triangle_pattern", "flat_top_bottom"] },
  { label: "形状", tools: ["zone", "brush", "polyline"] },
] as const satisfies readonly {
  readonly label: string;
  readonly tools: readonly Exclude<DrawingTool, "select">[];
}[];

export const PATTERN_TOOL_IDS = PATTERN_TOOL_SECTIONS.flatMap((section) => section.tools);

export function draftPreviewPoints(
  anchors: readonly AnnotationPoint[],
  cursor: AnnotationPoint,
  requiredPoints: number,
): AnnotationPoint[] {
  if (anchors.length === 0 || requiredPoints <= 1) return [...anchors];
  return Array.from(
    { length: requiredPoints },
    (_, index) => anchors[index] ?? cursor,
  );
}

export interface PositionPlanSummary {
  readonly side: "long" | "short";
  readonly entryPrice: string;
  readonly stopPrice: string;
  readonly targetPrice: string;
  readonly riskRewardRatio: string;
}

export interface MeasurementSummary {
  readonly change: string;
  readonly percent: string;
  readonly durationMs: string;
}

export function measurementSummary(points: readonly AnnotationPoint[]): MeasurementSummary {
  if (points.length !== 2) throw new Error("价格测量需要起点和终点");
  const [start, end] = points;
  const startPrice = Number(start.price);
  const endPrice = Number(end.price);
  if (!Number.isFinite(startPrice) || !Number.isFinite(endPrice) || startPrice === 0) {
    throw new Error("测量价格无效");
  }
  const change = endPrice - startPrice;
  const durationMs = Math.abs(new Date(end.time).getTime() - new Date(start.time).getTime());
  return {
    change: String(change),
    percent: ((change / startPrice) * 100).toFixed(2),
    durationMs: String(durationMs),
  };
}

export function positionPlanSummary(
  tool: "long_position" | "short_position" | "risk_reward",
  points: readonly AnnotationPoint[],
  fallbackSide: "long" | "short" = "long",
): PositionPlanSummary {
  if (points.length !== 3) throw new Error("仓位计划需要入场、止损和目标三个点");
  const [entry, stop, target] = points;
  const entryValue = Number(entry.price);
  const stopValue = Number(stop.price);
  const targetValue = Number(target.price);
  if (![entryValue, stopValue, targetValue].every(Number.isFinite)) {
    throw new Error("仓位计划价格无效");
  }
  const side = tool === "long_position" ? "long" : tool === "short_position" ? "short" : fallbackSide;
  if (side === "long" && !(stopValue < entryValue && targetValue > entryValue)) {
    throw new Error("多头计划要求止损低于入场价、目标高于入场价");
  }
  if (side === "short" && !(stopValue > entryValue && targetValue < entryValue)) {
    throw new Error("空头计划要求止损高于入场价、目标低于入场价");
  }
  const risk = Math.abs(entryValue - stopValue);
  const reward = Math.abs(targetValue - entryValue);
  if (risk === 0) throw new Error("止损价不能等于入场价");
  return {
    side,
    entryPrice: entry.price,
    stopPrice: stop.price,
    targetPrice: target.price,
    riskRewardRatio: (reward / risk).toFixed(2),
  };
}

function samplePoints(points: AnnotationPoint[], limit = 16): AnnotationPoint[] {
  if (points.length <= limit) return points;
  return Array.from({ length: limit }, (_, index) => (
    points[Math.round((index * (points.length - 1)) / (limit - 1))]
  ));
}

export function anchoredVwapPoints(
  bars: readonly Bar[],
  anchors: readonly AnnotationPoint[],
  visibleAt: string,
  pricePrecision: number,
): AnnotationPoint[] {
  if (anchors.length !== 2) throw new Error("锚定 VWAP 需要起点和可见终点");
  const from = Math.min(...anchors.map((point) => Date.parse(point.time)));
  const to = Math.min(Math.max(...anchors.map((point) => Date.parse(point.time))), Date.parse(visibleAt));
  let priceVolume = 0;
  let volume = 0;
  const points = bars
    .filter((bar) => {
      const time = Date.parse(bar.close_time);
      return time >= from && time <= to && time <= Date.parse(visibleAt);
    })
    .map((bar) => {
      const barVolume = Number(bar.raw.volume);
      const typicalPrice = (Number(bar.raw.high) + Number(bar.raw.low) + Number(bar.raw.close)) / 3;
      priceVolume += typicalPrice * barVolume;
      volume += barVolume;
      return {
        time: bar.close_time,
        price: (volume > 0 ? priceVolume / volume : typicalPrice).toFixed(pricePrecision),
      };
    });
  if (points.length < 2) throw new Error("锚定区间内至少需要两根可见 K 线");
  return samplePoints(points);
}

export function regressionTrendPoints(
  bars: readonly Bar[],
  anchors: readonly AnnotationPoint[],
  visibleAt: string,
  pricePrecision: number,
): { points: AnnotationPoint[]; slope: number; deviation: number } {
  if (anchors.length !== 2) throw new Error("回归趋势需要区间起点和终点");
  const from = Math.min(...anchors.map((point) => Date.parse(point.time)));
  const to = Math.min(Math.max(...anchors.map((point) => Date.parse(point.time))), Date.parse(visibleAt));
  const selected = bars.filter((bar) => {
    const time = Date.parse(bar.close_time);
    return time >= from && time <= to && time <= Date.parse(visibleAt);
  });
  if (selected.length < 2) throw new Error("回归区间内至少需要两根可见 K 线");
  const closes = selected.map((bar) => Number(bar.raw.close));
  const xMean = (selected.length - 1) / 2;
  const yMean = closes.reduce((total, value) => total + value, 0) / closes.length;
  const numerator = closes.reduce((total, value, index) => total + ((index - xMean) * (value - yMean)), 0);
  const denominator = closes.reduce((total, _value, index) => total + ((index - xMean) ** 2), 0);
  const slope = denominator === 0 ? 0 : numerator / denominator;
  const fitted = closes.map((_value, index) => yMean + (slope * (index - xMean)));
  const deviation = Math.sqrt(closes.reduce((total, value, index) => total + ((value - fitted[index]) ** 2), 0) / closes.length);
  return {
    points: [
      { time: selected[0].close_time, price: fitted[0].toFixed(pricePrecision) },
      { time: selected.at(-1)!.close_time, price: fitted.at(-1)!.toFixed(pricePrecision) },
      { time: selected.at(-1)!.close_time, price: (fitted.at(-1)! + deviation).toFixed(pricePrecision) },
    ],
    slope,
    deviation,
  };
}

export function drawingDefinition(tool: Exclude<DrawingTool, "select">): DrawingDefinition {
  const definition = DRAWING_DEFINITIONS.find((item) => item.tool === tool);
  if (!definition) throw new Error(`Unknown drawing tool: ${tool}`);
  return definition;
}

export function isDrawingTool(value: string): value is Exclude<DrawingTool, "select"> {
  return DRAWING_DEFINITIONS.some((item) => item.tool === value);
}

export function overlayName(tool: Exclude<DrawingTool, "select">): DrawingDefinition["overlayName"] {
  return drawingDefinition(tool).overlayName;
}

export function annotationShape(tool: Exclude<DrawingTool, "select">): ChartAnnotation["shape"] {
  return drawingDefinition(tool).shape;
}

const SUPPORTED_RENDERERS = new Set<DrawingDefinition["overlayName"]>([
  "segment", "rayLine", "straightLine", "priceLine", "horizontalRayLine",
  "verticalStraightLine", "horizontalStraightLine", "parallelStraightLine",
  "priceChannelLine", "fibonacciLine", "simpleAnnotation", "replayRect",
  "replayRiskReward", "replayPolyline", "replayLevels", "replayHorizontalLine",
]);

export function assertDrawingRegistry(): void {
  if (DRAWING_DEFINITIONS.length !== 40) {
    throw new Error(`Drawing registry must expose exactly 40 tools, received ${DRAWING_DEFINITIONS.length}`);
  }
  const ids = new Set(DRAWING_DEFINITIONS.map((definition) => definition.tool));
  if (ids.size !== DRAWING_DEFINITIONS.length) throw new Error("Drawing registry contains duplicate tool ids");
  for (const definition of DRAWING_DEFINITIONS) {
    if (!SUPPORTED_RENDERERS.has(definition.overlayName)) {
      throw new Error(`Drawing tool ${definition.tool} has no registered renderer`);
    }
    if (definition.requiredPoints < 1 || definition.requiredPoints > 16) {
      throw new Error(`Drawing tool ${definition.tool} has an invalid anchor count`);
    }
  }
}

assertDrawingRegistry();

export function geometryKind(
  tool: Exclude<DrawingTool, "select">,
): NonNullable<ChartAnnotation["geometry"]>["kind"] {
  if (["long_position", "short_position", "risk_reward"].includes(tool)) return "risk_reward";
  if (tool === "anchored_vwap") return "anchored_series";
  if (["head_shoulders", "triangle_pattern"].includes(tool)) return "pattern";
  if (["brush", "polyline", "disjoint_channel"].includes(tool)) return "polyline";
  if (tool.startsWith("fibonacci_") || tool === "pitchfork") return "levels";
  if (["measure", "price_range", "date_range", "info_line", "trend_angle"].includes(tool)) return "measurement";
  const definition = drawingDefinition(tool);
  if (definition.group === "analysis" && definition.requiredPoints > 2) return "channel";
  if (definition.shape === "zone") return "region";
  if (definition.requiredPoints === 1) return "point";
  return "line";
}
