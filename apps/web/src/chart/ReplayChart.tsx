import type {
  AnnotationPoint,
  Bar,
  ChartAnnotation,
  EvidenceTarget,
  PaperFill,
  PaperOrder,
} from "@replaytutor/contracts";
import { dispose, init, type Chart, type KLineData, type Point } from "klinecharts";
import { Copy, EyeOff, Lock, Save, Trash2, Unlock } from "lucide-react";
import { type MouseEvent as ReactMouseEvent, useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { draftPreviewPoints, drawingDefinition, isDrawingTool, type DrawingTool } from "./DrawingController";
import type { IndicatorInstance } from "./IndicatorCatalog";
import { syncChartIndicators } from "./IndicatorController";
import { registerReplayIndicators } from "./IndicatorRegistry";
import { registerReplayOverlays } from "./OverlayRegistry";

registerReplayOverlays();
registerReplayIndicators();

interface ReplayChartProps {
  readonly bars: readonly Bar[];
  readonly symbol: string;
  readonly timeframe: ReplayTimeframe;
  readonly pricePrecision: number;
  readonly visibleAt: string;
  readonly hideRealDate: boolean;
  readonly orders?: readonly PaperOrder[];
  readonly fills?: readonly PaperFill[];
  readonly annotations?: readonly ChartAnnotation[];
  readonly annotationsLocked?: boolean;
  readonly drawingTool?: DrawingTool;
  readonly drawingRequest?: number;
  readonly magnetEnabled?: boolean;
  readonly drawingPending?: boolean;
  readonly drawingError?: string | null;
  readonly resetRequest?: number;
  readonly zoomRequest?: { readonly sequence: number; readonly scale: number };
  readonly contextAnnotationIds?: readonly string[];
  readonly onDrawingComplete?: (
    tool: Exclude<DrawingTool, "select">,
    points: AnnotationPoint[],
  ) => void;
  readonly onAnnotationSelect?: (annotationId: string) => void;
  readonly onAnnotationChange?: (annotationId: string, points: AnnotationPoint[]) => void;
  readonly selectedAnnotationId?: string | null;
  readonly onAnnotationDelete?: (annotationId: string) => void;
  readonly onAnnotationDuplicate?: (annotationId: string) => void;
  readonly onAnnotationStyleChange?: (
    annotationId: string,
    style: NonNullable<ChartAnnotation["style"]>,
  ) => void;
  readonly onAnnotationPropertiesChange?: (
    annotationId: string,
    properties: Record<string, unknown>,
  ) => void;
  readonly onAnnotationSaveTemplate?: (annotationId: string) => void;
  readonly evidenceTarget?: EvidenceTarget | null;
  readonly indicators?: readonly IndicatorInstance[];
}

export type ReplayTimeframe = "1m" | "5m" | "15m" | "1h" | "4h" | "1d";

export function chartPeriodFor(timeframe: ReplayTimeframe) {
  if (timeframe.endsWith("m")) {
    return { type: "minute", span: Number(timeframe.slice(0, -1)) } as const;
  }
  if (timeframe.endsWith("h")) {
    return { type: "hour", span: Number(timeframe.slice(0, -1)) } as const;
  }
  return { type: "day", span: 1 } as const;
}

export function resolveDrawingPoint(
  converted: { timestamp?: number; value?: number } | null | undefined,
  bars: readonly Bar[],
  visibleAt: string,
  pricePrecision: number,
  magnetEnabled: boolean,
): AnnotationPoint | null {
  if (converted?.timestamp === undefined || converted.value === undefined) return null;
  const visibleAtMs = new Date(visibleAt).getTime();
  if (!Number.isFinite(converted.timestamp) || converted.timestamp > visibleAtMs) return null;
  const visibleBars = bars.filter((bar) => new Date(bar.close_time).getTime() <= visibleAtMs);
  if (!magnetEnabled || visibleBars.length === 0) {
    return {
      time: new Date(converted.timestamp).toISOString(),
      price: converted.value.toFixed(pricePrecision),
    };
  }
  const nearestBar = visibleBars.reduce((nearest, bar) => {
    const nearestDistance = Math.abs(new Date(nearest.close_time).getTime() - converted.timestamp!);
    const distance = Math.abs(new Date(bar.close_time).getTime() - converted.timestamp!);
    return distance < nearestDistance ? bar : nearest;
  });
  const nearestPrice = [nearestBar.raw.open, nearestBar.raw.high, nearestBar.raw.low, nearestBar.raw.close]
    .map(Number)
    .reduce((nearest, price) => (
      Math.abs(price - converted.value!) < Math.abs(nearest - converted.value!) ? price : nearest
    ));
  return {
    time: nearestBar.close_time,
    price: nearestPrice.toFixed(pricePrecision),
  };
}

function movedAnnotationPoints(
  overlayPoints: Array<Partial<Point>>,
  originalPoints: readonly AnnotationPoint[],
  visibleAt: string,
  pricePrecision: number,
): AnnotationPoint[] | null {
  if (overlayPoints.length !== originalPoints.length) return null;
  const visibleAtMs = new Date(visibleAt).getTime();
  const next = overlayPoints.map((point, index) => {
    const timestamp = point.timestamp ?? new Date(originalPoints[index].time).getTime();
    const value = point.value ?? Number(originalPoints[index].price);
    return {
      time: new Date(timestamp).toISOString(),
      price: value.toFixed(pricePrecision),
    };
  });
  if (next.some((point) => new Date(point.time).getTime() > visibleAtMs)) return null;
  return next;
}

function toKLineData(bar: Bar): KLineData {
  return {
    timestamp: new Date(bar.open_time).getTime(),
    open: Number(bar.raw.open),
    high: Number(bar.raw.high),
    low: Number(bar.raw.low),
    close: Number(bar.raw.close),
    volume: Number(bar.raw.volume),
  };
}

function visibleBoundaryCoordinate(chart: Chart, lastBar?: KLineData): number | null {
  if (!lastBar) return null;
  const converted = chart.convertToPixel(
    { timestamp: lastBar.timestamp },
    { paneId: "candle_pane" },
  );
  const point = Array.isArray(converted) ? converted[0] : converted;
  return typeof point?.x === "number" && Number.isFinite(point.x) ? point.x : null;
}

export function ReplayChart({
  bars,
  symbol,
  timeframe,
  pricePrecision,
  visibleAt,
  hideRealDate,
  orders = [],
  fills = [],
  annotations = [],
  annotationsLocked = false,
  drawingTool = "select",
  drawingRequest = 0,
  magnetEnabled = true,
  drawingPending = false,
  drawingError = null,
  resetRequest = 0,
  zoomRequest,
  contextAnnotationIds = [],
  onDrawingComplete,
  onAnnotationSelect,
  onAnnotationChange,
  selectedAnnotationId = null,
  onAnnotationDelete,
  onAnnotationDuplicate,
  onAnnotationStyleChange,
  onAnnotationPropertiesChange,
  onAnnotationSaveTemplate,
  evidenceTarget = null,
  indicators = [],
}: ReplayChartProps) {
  const { i18n } = useTranslation();
  const english = !i18n.resolvedLanguage?.startsWith("zh");
  const hostRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<Chart | null>(null);
  const barsRef = useRef<KLineData[]>([]);
  const executionOverlayIds = useRef<string[]>([]);
  const draftOverlayId = useRef<string | null>(null);
  const evidenceOverlayId = useRef<string | null>(null);
  const draftPoints = useRef<AnnotationPoint[]>([]);
  const [draftPointCount, setDraftPointCount] = useState(0);
  const [pointError, setPointError] = useState<string | null>(null);
  const [hoveredAnnotationId, setHoveredAnnotationId] = useState<string | null>(null);
  const [visibleBoundaryX, setVisibleBoundaryX] = useState<number | null>(null);

  useEffect(() => {
    const host = hostRef.current;
    if (!host) return;
    const chart = init(host, {
      timezone: "Etc/UTC",
      styles: {
        grid: {
          horizontal: { color: "#1b2634" },
          vertical: { color: "#1b2634" },
        },
        candle: {
          bar: {
            upColor: "#25c792",
            downColor: "#f2687d",
            noChangeColor: "#8a96a8",
          },
        },
        xAxis: { axisLine: { color: "#2b3746" } },
        yAxis: { axisLine: { color: "#2b3746" } },
      },
    });
    if (!chart) throw new Error("Unable to initialize Replay chart");
    chart.setDataLoader({
      getBars: ({ callback }) => callback([...barsRef.current], false),
    });
    chart.setPeriod({ type: "minute", span: 1 });
    chart.setOffsetRightDistance(220);
    chart.setRightMinVisibleBarCount(14);
    chartRef.current = chart;
    const updateVisibleBoundary = () => {
      setVisibleBoundaryX(visibleBoundaryCoordinate(chart, barsRef.current.at(-1)));
    };
    chart.subscribeAction("onVisibleRangeChange", updateVisibleBoundary);
    const resizeObserver = typeof ResizeObserver === "undefined"
      ? null
      : new ResizeObserver(updateVisibleBoundary);
    resizeObserver?.observe(host);
    updateVisibleBoundary();
    return () => {
      resizeObserver?.disconnect();
      chart.unsubscribeAction("onVisibleRangeChange", updateVisibleBoundary);
      chartRef.current = null;
      dispose(host);
    };
  }, []);

  useEffect(() => {
    const chart = chartRef.current;
    if (!chart) return;
    chart.setPeriod(chartPeriodFor(timeframe));
    chart.resetData();
  }, [timeframe]);

  useEffect(() => {
    barsRef.current = bars.map(toKLineData);
    const chart = chartRef.current;
    if (!chart) return;
    chart.setSymbol({
      ticker: symbol,
      pricePrecision,
      volumePrecision: 4,
    });
    chart.resetData();
    setVisibleBoundaryX(visibleBoundaryCoordinate(chart, barsRef.current.at(-1)));
  }, [bars, pricePrecision, symbol]);

  useEffect(() => {
    const chart = chartRef.current;
    if (!chart) return;
    syncChartIndicators(chart, indicators);
  }, [indicators]);

  useEffect(() => {
    if (resetRequest === 0) return;
    chartRef.current?.scrollToRealTime(160);
  }, [resetRequest]);

  useEffect(() => {
    if (!zoomRequest) return;
    chartRef.current?.zoomAtCoordinate(zoomRequest.scale, undefined, 120);
  }, [zoomRequest]);

  useEffect(() => {
    if (drawingTool === "select" || drawingRequest === 0) return;
    const chart = chartRef.current;
    if (!chart) return;
    if (draftOverlayId.current) {
      chart.removeOverlay({ id: draftOverlayId.current });
      draftOverlayId.current = null;
    }
    draftPoints.current = [];
    setDraftPointCount(0);
    setPointError(null);
    const cancel = (event: KeyboardEvent) => {
      if (event.key !== "Escape") return;
      if (draftOverlayId.current) chart.removeOverlay({ id: draftOverlayId.current });
      draftOverlayId.current = null;
      draftPoints.current = [];
      setDraftPointCount(0);
      setPointError(null);
    };
    window.addEventListener("keydown", cancel);
    return () => window.removeEventListener("keydown", cancel);
  }, [drawingRequest, drawingTool]);

  const resolveClientPoint = (clientX: number, clientY: number) => {
    const chart = chartRef.current;
    const host = hostRef.current;
    if (!chart || !host) return null;
    const bounds = host.getBoundingClientRect();
    const converted = chart.convertFromPixel(
      [{ x: clientX - bounds.left, y: clientY - bounds.top }],
      { paneId: "candle_pane" },
    );
    const point = Array.isArray(converted) ? converted[0] : converted;
    return resolveDrawingPoint(point, bars, visibleAt, pricePrecision, magnetEnabled);
  };

  const updateDraftPreview = (
    anchors: readonly AnnotationPoint[],
    cursor: AnnotationPoint,
  ) => {
    if (drawingTool === "select") return;
    const chart = chartRef.current;
    if (!chart) return;
    const definition = drawingDefinition(drawingTool);
    if (definition.requiredPoints <= 1 || anchors.length === 0) return;
    const points = draftPreviewPoints(anchors, cursor, definition.requiredPoints).map((item) => ({
      timestamp: new Date(item.time).getTime(),
      value: Number(item.price),
    }));
    const id = `draft-${drawingRequest}`;
    if (draftOverlayId.current) {
      chart.overrideOverlay({ id, points });
      return;
    }
    const created = chart.createOverlay({
      id,
      name: definition.overlayName,
      lock: true,
      points,
      extendData: "绘图草稿",
      styles: {
        line: { color: "#8cbbff", size: 1, style: "dashed" },
        polygon: { color: "#315b8e22", borderColor: "#8cbbff" },
        point: { color: "#8cbbff", borderColor: "#101722" },
        text: { color: "#d9e8ff", backgroundColor: "#183154" },
      },
    });
    if (created === id) draftOverlayId.current = id;
  };

  const handleChartMouseMove = (event: ReactMouseEvent<HTMLDivElement>) => {
    if (drawingTool === "select" || draftPoints.current.length === 0) return;
    const cursor = resolveClientPoint(event.clientX, event.clientY);
    if (!cursor) return;
    updateDraftPreview(draftPoints.current, cursor);
  };

  const handleChartClick = (event: ReactMouseEvent<HTMLDivElement>) => {
    if (drawingTool === "select" || drawingRequest === 0) return;
    const chart = chartRef.current;
    if (!chart) return;
    const resolvedPoint = resolveClientPoint(event.clientX, event.clientY);
    if (!resolvedPoint) {
      setPointError("未来区域不能作为绘图锚点");
      return;
    }
    setPointError(null);
    const next = [
      ...draftPoints.current,
      resolvedPoint,
    ];
    const definition = drawingDefinition(drawingTool);
    const requiredPoints = definition.requiredPoints;
    if (next.length >= requiredPoints) {
      if (draftOverlayId.current) chart.removeOverlay({ id: draftOverlayId.current });
      draftOverlayId.current = null;
      draftPoints.current = [];
      setDraftPointCount(0);
      onDrawingComplete?.(drawingTool, next);
      return;
    }
    draftPoints.current = next;
    setDraftPointCount(next.length);
    updateDraftPreview(next, resolvedPoint);
  };

  useEffect(() => {
    const chart = chartRef.current;
    if (!chart) return;
    for (const id of executionOverlayIds.current) chart.removeOverlay({ id });
    const ids: string[] = [];
    for (const order of orders) {
      if (order.status !== "PENDING") continue;
      const rawPrice = order.limit_price ?? order.stop_price;
      if (!rawPrice) continue;
      const id = `paper-${order.order_id}`;
      const created = chart.createOverlay({
        id,
        name: "horizontalStraightLine",
        lock: true,
        points: [{ value: Number(rawPrice) }],
        styles: {
          line: {
            color: order.order_type === "STOP_MARKET" ? "#f2687d" : "#f5a623",
            size: 1,
            style: "dashed",
          },
          point: { color: "transparent", borderColor: "transparent" },
        },
      });
      if (created === id) ids.push(id);
    }
    for (const fill of fills) {
      const id = `fill-${fill.fill_id}`;
      const created = chart.createOverlay({
        id,
        name: "simpleAnnotation",
        lock: true,
        points: [{
          timestamp: new Date(fill.executed_at).getTime(),
          value: Number(fill.price),
        }],
        extendData: `${fill.side} ${fill.quantity}`,
        styles: evidenceTarget?.fill_id === fill.fill_id
          ? { point: { color: "#f5d66f", borderColor: "#f5d66f" }, text: { color: "#f5d66f" } }
          : undefined,
      });
      if (created === id) ids.push(id);
    }
    for (const annotation of annotations) {
      if (annotation.properties?.hidden === true) continue;
      const id = `annotation-${annotation.annotation_id}`;
      const points = annotation.points.map((point) => ({
        timestamp: new Date(point.time).getTime(),
        value: Number(point.price),
      }));
      const fallbackName = annotation.shape === "line"
        ? "segment"
        : annotation.shape === "zone"
          ? "replayRect"
          : "simpleAnnotation";
      const tool = annotation.tool ?? (annotation.shape === "line"
        ? "trend_line"
        : annotation.shape === "zone"
          ? "zone"
          : annotation.shape === "label"
            ? "text"
            : "note_marker");
      const drawingKind = annotation.metadata?.drawing_kind ?? "";
      const renderTool = isDrawingTool(drawingKind)
        ? drawingKind
        : tool !== "ai_suggestion" && isDrawingTool(tool)
          ? tool
          : null;
      const definition = renderTool ? drawingDefinition(renderTool) : null;
      const name = definition?.overlayName ?? fallbackName;
      const color = annotation.layer === "ai" ? "#7c5cff" : "#20b7f5";
      const objectColor = annotation.style?.line_color ?? color;
      const objectWidth = annotation.style?.line_width ?? 1;
      const requestedDash = annotation.style?.line_dash ?? (annotation.layer === "ai" ? "dashed" : "solid");
      const objectDash: "solid" | "dashed" = requestedDash === "solid" ? "solid" : "dashed";
      const fillColor = annotation.style?.fill_color ?? objectColor;
      const selected = evidenceTarget?.annotation_id === annotation.annotation_id
        || contextAnnotationIds.includes(annotation.annotation_id)
        || selectedAnnotationId === annotation.annotation_id;
      if (["risk_reward", "long_position", "short_position"].includes(tool) && points.length === 3) {
        const [entry, stop, target] = points;
        for (const [suffix, areaPoints, areaColor] of [
          ["risk", [entry, stop], "#f2687d"],
          ["reward", [entry, target], "#25c792"],
        ] as const) {
          const areaId = `${id}-${suffix}`;
          const areaCreated = chart.createOverlay({
            id: areaId,
            name: "replayRect",
            lock: true,
            points: [...areaPoints],
            extendData: annotation.label,
            styles: {
              line: { color: selected ? "#f5d66f" : areaColor, size: selected ? 3 : 1 },
              polygon: { color: `${areaColor}22`, borderColor: areaColor },
              point: { color: areaColor, borderColor: areaColor },
              text: { color: areaColor, backgroundColor: "#101722" },
            },
            onClick: () => onAnnotationSelect?.(annotation.annotation_id),
            onMouseEnter: () => setHoveredAnnotationId(annotation.annotation_id),
            onMouseLeave: () => setHoveredAnnotationId(null),
          });
          if (areaCreated === areaId) ids.push(areaId);
        }
        const labelId = `${id}-label`;
        const labelCreated = chart.createOverlay({
          id: labelId,
          name: "simpleAnnotation",
          lock: true,
          points: [target],
          extendData: annotation.label,
          styles: {
            point: { color: selected ? "#f5d66f" : "#25c792", borderColor: "#101722" },
            text: { color: selected ? "#111820" : "#b7f2d9", backgroundColor: selected ? "#f5d66f" : "#16382d" },
          },
          onClick: () => onAnnotationSelect?.(annotation.annotation_id),
          onMouseEnter: () => setHoveredAnnotationId(annotation.annotation_id),
          onMouseLeave: () => setHoveredAnnotationId(null),
        });
        if (labelCreated === labelId) ids.push(labelId);
        if (annotation.layer === "user" && onAnnotationChange && !annotationsLocked) {
          const handleLabels = ["入场", "止损", "目标"];
          const handleColors = ["#8cbbff", "#f2687d", "#25c792"];
          points.forEach((handlePoint, pointIndex) => {
            const handleId = `${id}-handle-${pointIndex}`;
            const handleCreated = chart.createOverlay({
              id: handleId,
              name: "simpleAnnotation",
              lock: false,
              mode: magnetEnabled ? "strong_magnet" : "normal",
              points: [handlePoint],
              extendData: handleLabels[pointIndex],
              styles: {
                point: { color: handleColors[pointIndex], borderColor: "#101722" },
                text: { color: handleColors[pointIndex], backgroundColor: "#101722" },
              },
              onClick: () => onAnnotationSelect?.(annotation.annotation_id),
              onMouseEnter: () => setHoveredAnnotationId(annotation.annotation_id),
              onMouseLeave: () => setHoveredAnnotationId(null),
              onPressedMoveEnd: (event) => {
                const moved = movedAnnotationPoints(
                  event.overlay.points,
                  [annotation.points[pointIndex]],
                  visibleAt,
                  pricePrecision,
                );
                if (!moved) return;
                const next = annotation.points.map((point, index) => (
                  index === pointIndex ? moved[0] : point
                ));
                onAnnotationChange(annotation.annotation_id, next);
              },
            });
            if (handleCreated === handleId) ids.push(handleId);
          });
        }
        continue;
      }
      const editable = annotation.layer === "user"
        && Boolean(onAnnotationChange)
        && !annotationsLocked
        && annotation.properties?.locked !== true;
      const created = chart.createOverlay({
        id,
        name,
        lock: !editable,
        mode: magnetEnabled ? "strong_magnet" : "normal",
        points,
        extendData: annotation.label,
        styles: {
          line: { color: selected ? "#f5d66f" : objectColor, size: selected ? Math.max(3, objectWidth) : objectWidth, style: objectDash },
          polygon: { color: `${fillColor}26`, borderColor: objectColor },
          point: { color: objectColor, borderColor: objectColor },
          text: { color: annotation.style?.text_color ?? objectColor, backgroundColor: "#101722", size: annotation.style?.font_size ?? 12 },
        },
        onClick: () => onAnnotationSelect?.(annotation.annotation_id),
        onMouseEnter: () => setHoveredAnnotationId(annotation.annotation_id),
        onMouseLeave: () => setHoveredAnnotationId(null),
        onPressedMoveEnd: editable
          ? (event) => {
            const moved = movedAnnotationPoints(
              event.overlay.points,
              annotation.points,
              visibleAt,
              pricePrecision,
            );
            if (moved) onAnnotationChange?.(annotation.annotation_id, moved);
          }
          : undefined,
      });
      if (created === id) ids.push(id);
      if (renderTool === "measure" && points.length === 2) {
        const labelId = `${id}-measure-label`;
        const labelCreated = chart.createOverlay({
          id: labelId,
          name: "simpleAnnotation",
          lock: true,
          points: [points[1]],
          extendData: annotation.label,
          styles: {
            point: { color, borderColor: "#101722" },
            text: { color: "#d9e8ff", backgroundColor: "#183154" },
          },
          onClick: () => onAnnotationSelect?.(annotation.annotation_id),
          onMouseEnter: () => setHoveredAnnotationId(annotation.annotation_id),
          onMouseLeave: () => setHoveredAnnotationId(null),
        });
        if (labelCreated === labelId) ids.push(labelId);
      }
    }
    executionOverlayIds.current = ids;
  }, [annotations, annotationsLocked, contextAnnotationIds, evidenceTarget, fills, magnetEnabled, onAnnotationChange, onAnnotationSelect, orders, pricePrecision, selectedAnnotationId, visibleAt]);

  useEffect(() => {
    const chart = chartRef.current;
    if (!chart) return;
    if (evidenceOverlayId.current) {
      chart.removeOverlay({ id: evidenceOverlayId.current });
      evidenceOverlayId.current = null;
    }
    if (!evidenceTarget?.occurred_at) return;
    const timestamp = new Date(evidenceTarget.occurred_at).getTime();
    chart.scrollToTimestamp(timestamp, 200);
    const closestBar = [...bars]
      .reverse()
      .find((bar) => new Date(bar.close_time).getTime() <= timestamp);
    const price = evidenceTarget.price ?? closestBar?.raw.close;
    if (!price) return;
    const id = "evidence-focus";
    const created = chart.createOverlay({
      id,
      name: "simpleAnnotation",
      lock: true,
      points: [{ timestamp, value: Number(price) }],
      extendData: `证据 · ${evidenceTarget.kind}`,
      styles: {
        point: { color: "#f5d66f", borderColor: "#fff2a8" },
        text: { color: "#111820", backgroundColor: "#f5d66f" },
      },
    });
    if (created === id) evidenceOverlayId.current = id;
  }, [bars, evidenceTarget]);

  const hoveredAnnotation = annotations.find(
    (annotation) => annotation.annotation_id === hoveredAnnotationId,
  ) ?? null;
  const selectedAnnotation = annotations.find(
    (annotation) => annotation.annotation_id === selectedAnnotationId,
  ) ?? null;

  return (
    <div className="replay-chart-shell" data-evidence-id={evidenceTarget?.evidence_id}>
      <div
        aria-label={`${symbol} ${timeframe} ${english ? "replay candlestick chart" : "回放 K 线图"}`}
        className={`replay-chart ${drawingTool !== "select" ? "is-drawing" : ""}`}
        data-preview-active={draftPointCount > 0 ? "true" : "false"}
        onClick={handleChartClick}
        onMouseMove={handleChartMouseMove}
        ref={hostRef}
      />
      {drawingTool !== "select" && (
        <div className="drawing-hud" role="status">
          <strong>{drawingDefinition(drawingTool).label}</strong>
          <span>{drawingPending ? "正在保存…" : drawingDefinition(drawingTool).instruction}</span>
          <code>{draftPointCount}/{drawingDefinition(drawingTool).requiredPoints}</code>
          {(pointError || drawingError) && <small>{pointError ?? drawingError}</small>}
          <kbd>Esc 取消</kbd>
        </div>
      )}
      {hoveredAnnotation && hoveredAnnotation.annotation_id !== selectedAnnotationId && (
        <div className="chart-object-hover" role="tooltip">
          <strong>{hoveredAnnotation.label}</strong>
          <span>{hoveredAnnotation.metadata?.drawing_kind ?? hoveredAnnotation.tool}</span>
        </div>
      )}
      {selectedAnnotation && onAnnotationDelete && (
        <div className="chart-object-actions" role="toolbar" aria-label="选中图表对象操作">
          <span>
            <strong>{selectedAnnotation.label}</strong>
            <small>{selectedAnnotation.metadata?.drawing_kind ?? selectedAnnotation.tool}</small>
          </span>
          <label title="线条颜色">
            <span className="sr-only">线条颜色</span>
            <input
              aria-label="线条颜色"
              onChange={(event) => onAnnotationStyleChange?.(selectedAnnotation.annotation_id, {
                ...selectedAnnotation.style,
                line_color: event.target.value,
              })}
              type="color"
              value={selectedAnnotation.style?.line_color ?? "#20b7f5"}
            />
          </label>
          <select
            aria-label="线宽"
            onChange={(event) => onAnnotationStyleChange?.(selectedAnnotation.annotation_id, {
              ...selectedAnnotation.style,
              line_width: Number(event.target.value),
            })}
            value={selectedAnnotation.style?.line_width ?? 1}
          >
            {[1, 2, 3, 4].map((width) => <option key={width} value={width}>{width}px</option>)}
          </select>
          <select
            aria-label="线型"
            onChange={(event) => onAnnotationStyleChange?.(selectedAnnotation.annotation_id, {
              ...selectedAnnotation.style,
              line_dash: event.target.value as "solid" | "dashed" | "dotted",
            })}
            value={selectedAnnotation.style?.line_dash ?? "solid"}
          >
            <option value="solid">实线</option>
            <option value="dashed">虚线</option>
            <option value="dotted">点线</option>
          </select>
          <button aria-label="复制图表对象" onClick={() => onAnnotationDuplicate?.(selectedAnnotation.annotation_id)} title="复制" type="button">
            <Copy aria-hidden="true" size={14} />
          </button>
          <button aria-label="保存为工具模板" onClick={() => onAnnotationSaveTemplate?.(selectedAnnotation.annotation_id)} title="保存模板" type="button">
            <Save aria-hidden="true" size={14} />
          </button>
          <button
            aria-label={selectedAnnotation.properties?.locked === true ? "解锁图表对象" : "锁定图表对象"}
            onClick={() => onAnnotationPropertiesChange?.(selectedAnnotation.annotation_id, {
              ...selectedAnnotation.properties,
              locked: selectedAnnotation.properties?.locked !== true,
            })}
            title={selectedAnnotation.properties?.locked === true ? "解锁" : "锁定"}
            type="button"
          >
            {selectedAnnotation.properties?.locked === true ? <Unlock aria-hidden="true" size={14} /> : <Lock aria-hidden="true" size={14} />}
          </button>
          <button
            aria-label="隐藏图表对象"
            onClick={() => onAnnotationPropertiesChange?.(selectedAnnotation.annotation_id, { ...selectedAnnotation.properties, hidden: true })}
            title="隐藏"
            type="button"
          >
            <EyeOff aria-hidden="true" size={14} />
          </button>
          <button
            aria-label={`删除 ${selectedAnnotation.label}`}
            className="is-danger"
            onClick={() => onAnnotationDelete(selectedAnnotation.annotation_id)}
            title="删除图表对象"
            type="button"
          >
            <Trash2 aria-hidden="true" size={14} strokeWidth={1.8} />
            删除
          </button>
        </div>
      )}
      <div
        className="visible-boundary"
        aria-hidden="true"
        style={{
          left: visibleBoundaryX ?? 0,
          visibility: visibleBoundaryX === null ? "hidden" : "visible",
        }}
      >
        <span>{hideRealDate ? (english ? "Visible to current frame" : "Visible to 当前帧") : `Visible to ${new Date(visibleAt).toLocaleString(english ? "en-US" : "zh-CN", { hour12: false })}`}</span>
      </div>
      <div className="future-mask-label">{english ? "Future data hidden" : "未来数据不可见"}</div>
    </div>
  );
}
