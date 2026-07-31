import type { AnnotationPoint, Bar, ChartAnnotation, PaperFill, PaperOrder } from "@replaytutor/contracts";
import { dispose, init, type Chart, type KLineData } from "klinecharts";
import { type MouseEvent as ReactMouseEvent, useEffect, useRef } from "react";
import { overlayName, type DrawingTool } from "./DrawingController";

interface ReplayChartProps {
  readonly bars: readonly Bar[];
  readonly symbol: string;
  readonly pricePrecision: number;
  readonly visibleAt: string;
  readonly hideRealDate: boolean;
  readonly orders?: readonly PaperOrder[];
  readonly fills?: readonly PaperFill[];
  readonly annotations?: readonly ChartAnnotation[];
  readonly drawingTool?: DrawingTool;
  readonly drawingRequest?: number;
  readonly onDrawingComplete?: (
    shape: ChartAnnotation["shape"],
    points: AnnotationPoint[],
  ) => void;
  readonly onAnnotationSelect?: (annotationId: string) => void;
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

export function ReplayChart({
  bars,
  symbol,
  pricePrecision,
  visibleAt,
  hideRealDate,
  orders = [],
  fills = [],
  annotations = [],
  drawingTool = "select",
  drawingRequest = 0,
  onDrawingComplete,
  onAnnotationSelect,
}: ReplayChartProps) {
  const hostRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<Chart | null>(null);
  const barsRef = useRef<KLineData[]>([]);
  const executionOverlayIds = useRef<string[]>([]);
  const draftOverlayId = useRef<string | null>(null);
  const draftPoints = useRef<AnnotationPoint[]>([]);

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
    return () => {
      chartRef.current = null;
      dispose(host);
    };
  }, []);

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
  }, [bars, pricePrecision, symbol]);

  useEffect(() => {
    if (drawingTool === "select" || drawingRequest === 0) return;
    const chart = chartRef.current;
    if (!chart) return;
    if (draftOverlayId.current) {
      chart.removeOverlay({ id: draftOverlayId.current });
      draftOverlayId.current = null;
    }
    draftPoints.current = [];
    const cancel = (event: KeyboardEvent) => {
      if (event.key !== "Escape") return;
      if (draftOverlayId.current) chart.removeOverlay({ id: draftOverlayId.current });
      draftOverlayId.current = null;
      draftPoints.current = [];
    };
    window.addEventListener("keydown", cancel);
    return () => window.removeEventListener("keydown", cancel);
  }, [drawingRequest, drawingTool]);

  const handleChartClick = (event: ReactMouseEvent<HTMLDivElement>) => {
    if (drawingTool === "select" || drawingRequest === 0) return;
    const chart = chartRef.current;
    const host = hostRef.current;
    if (!chart || !host) return;
    const bounds = host.getBoundingClientRect();
    const converted = chart.convertFromPixel(
      [{ x: event.clientX - bounds.left, y: event.clientY - bounds.top }],
      { paneId: "candle_pane" },
    );
    const point = Array.isArray(converted) ? converted[0] : converted;
    if (point?.timestamp === undefined || point.value === undefined) return;
    const next = [
      ...draftPoints.current,
      { time: new Date(point.timestamp).toISOString(), price: String(point.value) },
    ];
    const requiredPoints = drawingTool === "marker" ? 1 : 2;
    if (next.length >= requiredPoints) {
      if (draftOverlayId.current) chart.removeOverlay({ id: draftOverlayId.current });
      draftOverlayId.current = null;
      draftPoints.current = [];
      onDrawingComplete?.(drawingTool, next);
      return;
    }
    draftPoints.current = next;
    const id = `draft-${drawingRequest}`;
    if (draftOverlayId.current) chart.removeOverlay({ id: draftOverlayId.current });
    chart.createOverlay({
      id,
      name: overlayName(drawingTool),
      lock: true,
      points: next.map((item) => ({
        timestamp: new Date(item.time).getTime(),
        value: Number(item.price),
      })),
      extendData: "绘图草稿",
    });
    draftOverlayId.current = id;
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
      });
      if (created === id) ids.push(id);
    }
    for (const annotation of annotations) {
      const id = `annotation-${annotation.annotation_id}`;
      const points = annotation.points.map((point) => ({
        timestamp: new Date(point.time).getTime(),
        value: Number(point.price),
      }));
      const name = annotation.shape === "line"
        ? "segment"
        : annotation.shape === "zone"
          ? "rect"
          : "simpleAnnotation";
      const color = annotation.layer === "ai" ? "#7c5cff" : "#20b7f5";
      const created = chart.createOverlay({
        id,
        name,
        lock: true,
        points,
        extendData: annotation.label,
        styles: {
          line: { color, size: 1, style: annotation.layer === "ai" ? "dashed" : "solid" },
          polygon: { color: `${color}26`, borderColor: color },
          point: { color, borderColor: color },
          text: { color, backgroundColor: "#101722" },
        },
        onClick: () => onAnnotationSelect?.(annotation.annotation_id),
      });
      if (created === id) ids.push(id);
    }
    executionOverlayIds.current = ids;
  }, [annotations, fills, onAnnotationSelect, orders]);

  return (
    <div className="replay-chart-shell">
      <div className="replay-chart" onClick={handleChartClick} ref={hostRef} aria-label={`${symbol} 回放 K 线图`} />
      <div className="visible-boundary" aria-hidden="true">
        <span>{hideRealDate ? "Visible to 当前帧" : `Visible to ${new Date(visibleAt).toLocaleString("zh-CN", { hour12: false })}`}</span>
      </div>
      <div className="future-mask-label">未来数据不可见</div>
    </div>
  );
}
