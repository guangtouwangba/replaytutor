import type {
  AnnotationActionRequest,
  AnnotationDisposition,
  AnnotationPoint,
  ChartAnnotation,
  CreateAnnotationRequest,
  SubmitOrderRequest,
} from "@replaytutor/contracts";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Bot, ChevronRight, Keyboard, Pause, Play, Square, StepForward } from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import {
  applySessionCommand,
  actOnAnnotation,
  cancelOrder,
  commandId,
  createAnnotation,
  fetchAnnotationDispositions,
  fetchEvidenceTarget,
  fetchPlaybookEvaluation,
  fetchSession,
  fetchSessionBars,
  finishSession,
  lockTradePlan,
  submitOrder,
} from "../api/sessions";
import { fetchPreferences } from "../api/localSystem";
import { createChartToolTemplate, fetchChartToolManifest } from "../api/chartTools";
import { ReplayChart } from "../chart/ReplayChart";
import {
  drawingDefinition,
  DRAWING_DEFINITIONS,
  geometryKind,
  anchoredVwapPoints,
  measurementSummary,
  positionPlanSummary,
  regressionTrendPoints,
  type DrawingTool,
} from "../chart/DrawingController";
import {
  isEditableShortcutTarget,
  isTimeframePrefix,
  resolveWorkbenchShortcut,
  timeframeFromDigits,
} from "../chart/WorkbenchShortcuts";
import { evidenceReturnUrl } from "../chart/EvidenceSelectionBridge";
import { AnnotationInspector } from "../components/AnnotationInspector";
import { DrawingToolbar } from "../components/DrawingToolbar";
import { TutorDock } from "../components/TutorDock";
import {
  CommandPalette,
  ShortcutHelp,
  type WorkbenchCommandAction,
} from "../components/WorkbenchShortcutOverlay";

const REPLAY_TIMEFRAMES = ["1m", "5m", "15m", "1h", "4h", "1d"] as const;
type ReplayTimeframe = typeof REPLAY_TIMEFRAMES[number];

interface SavedChartLayout {
  readonly timeframe?: ReplayTimeframe;
  readonly annotationsVisible?: boolean;
  readonly annotationsLocked?: boolean;
  readonly magnetEnabled?: boolean;
  readonly continuousDrawing?: boolean;
}

function savedChartLayout(): SavedChartLayout {
  if (typeof window === "undefined") return {};
  try {
    const parsed = JSON.parse(window.localStorage.getItem("replaytutor:chart-layout") ?? "{}") as SavedChartLayout;
    return {
      timeframe: REPLAY_TIMEFRAMES.includes(parsed.timeframe as ReplayTimeframe) ? parsed.timeframe : undefined,
      annotationsVisible: typeof parsed.annotationsVisible === "boolean" ? parsed.annotationsVisible : undefined,
      annotationsLocked: typeof parsed.annotationsLocked === "boolean" ? parsed.annotationsLocked : undefined,
      magnetEnabled: typeof parsed.magnetEnabled === "boolean" ? parsed.magnetEnabled : undefined,
      continuousDrawing: typeof parsed.continuousDrawing === "boolean" ? parsed.continuousDrawing : undefined,
    };
  } catch {
    return {};
  }
}

function boundedPoints(points: AnnotationPoint[]): CreateAnnotationRequest["points"] {
  if (points.length < 1 || points.length > 16) {
    throw new Error("Annotations require between one and sixteen points");
  }
  return points as CreateAnnotationRequest["points"];
}

interface ChartObjectState {
  readonly label: string;
  readonly points: AnnotationPoint[];
  readonly metadata: Record<string, string>;
  readonly style: NonNullable<ChartAnnotation["style"]>;
  readonly properties: Record<string, unknown>;
}

interface ChartHistoryEntry {
  readonly annotationId: string;
  readonly before: ChartObjectState | null;
  readonly after: ChartObjectState | null;
}

function revisedChartObject(
  disposition: AnnotationDisposition,
  points: AnnotationPoint[],
  pricePrecision: number,
): ChartObjectState {
  const metadata = { ...disposition.effective_metadata };
  const drawingKind = metadata.drawing_kind;
  if (["risk_reward", "long_position", "short_position"].includes(disposition.original_annotation.tool ?? "")) {
    const positionTool = ["long_position", "short_position", "risk_reward"].includes(drawingKind)
      ? drawingKind as "long_position" | "short_position" | "risk_reward"
      : "risk_reward";
    const plan = positionPlanSummary(
      positionTool,
      points,
      metadata.side === "short" ? "short" : "long",
    );
    return {
      label: `${plan.side === "long" ? "多头" : "空头"}仓位计划 · R:R ${plan.riskRewardRatio}`,
      points,
      metadata: {
        ...metadata,
        side: plan.side,
        entry_price: plan.entryPrice,
        stop_price: plan.stopPrice,
        target_price: plan.targetPrice,
        risk_reward_ratio: plan.riskRewardRatio,
      },
      style: disposition.effective_style,
      properties: disposition.effective_properties ?? {},
    };
  }
  if (drawingKind === "measure") {
    const measurement = measurementSummary(points);
    const change = Number(measurement.change).toFixed(pricePrecision);
    return {
      label: `测量 ${Number(change) >= 0 ? "+" : ""}${change} (${measurement.percent}%)`,
      points,
      metadata: {
        ...metadata,
        price_change: measurement.change,
        percent_change: measurement.percent,
        duration_ms: measurement.durationMs,
      },
      style: disposition.effective_style,
      properties: disposition.effective_properties ?? {},
    };
  }
  return {
    label: disposition.effective_label,
    points,
    metadata,
    style: disposition.effective_style,
    properties: disposition.effective_properties ?? {},
  };
}

export function WorkbenchPage() {
  const { i18n } = useTranslation();
  const english = !i18n.resolvedLanguage?.startsWith("zh");
  const l = (en: string, zh: string) => english ? en : zh;
  const { sessionId } = useParams();
  const [searchParams] = useSearchParams();
  const evidenceId = searchParams.get("evidence");
  const reviewMode = searchParams.get("mode") === "review";
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState(1);
  const initialChartLayout = useMemo(savedChartLayout, []);
  const [timeframe, setTimeframe] = useState<ReplayTimeframe>(initialChartLayout.timeframe ?? "1m");
  const [side, setSide] = useState<"BUY" | "SELL">("BUY");
  const [thesis, setThesis] = useState("");
  const [invalidation, setInvalidation] = useState("");
  const [riskAmount, setRiskAmount] = useState("100");
  const [orderType, setOrderType] = useState<SubmitOrderRequest["order_type"]>("MARKET");
  const [quantity, setQuantity] = useState("0.01");
  const [triggerPrice, setTriggerPrice] = useState("");
  const [limitPrice, setLimitPrice] = useState("");
  const [callbackRate, setCallbackRate] = useState("0.01");
  const [timeInForce, setTimeInForce] = useState<NonNullable<SubmitOrderRequest["time_in_force"]>>("GTC");
  const [reduceOnly, setReduceOnly] = useState(false);
  const [closePosition, setClosePosition] = useState(false);
  const [postOnly, setPostOnly] = useState(false);
  const [goodTillIndex, setGoodTillIndex] = useState("");
  const [positionSide, setPositionSide] = useState<NonNullable<SubmitOrderRequest["position_side"]>>("BOTH");
  const [takeProfit, setTakeProfit] = useState("");
  const [protectiveStop, setProtectiveStop] = useState("");
  const [annotationLabel, setAnnotationLabel] = useState(() => english ? "My observation" : "我的观察");
  const [drawingTool, setDrawingTool] = useState<DrawingTool>("select");
  const [drawingRequest, setDrawingRequest] = useState(0);
  const [magnetEnabled, setMagnetEnabled] = useState(initialChartLayout.magnetEnabled ?? true);
  const [continuousDrawing, setContinuousDrawing] = useState(initialChartLayout.continuousDrawing ?? false);
  const [annotationsVisible, setAnnotationsVisible] = useState(initialChartLayout.annotationsVisible ?? true);
  const [annotationsLocked, setAnnotationsLocked] = useState(initialChartLayout.annotationsLocked ?? false);
  const [selectedAnnotationId, setSelectedAnnotationId] = useState<string | null>(null);
  const [contextAnnotationIds, setContextAnnotationIds] = useState<string[]>([]);
  const [chartHistory, setChartHistory] = useState<ChartHistoryEntry[]>([]);
  const [chartHistoryIndex, setChartHistoryIndex] = useState(0);
  const [chartEditError, setChartEditError] = useState<string | null>(null);
  const [shortcutHelpOpen, setShortcutHelpOpen] = useState(false);
  const [commandPaletteQuery, setCommandPaletteQuery] = useState<string | null>(null);
  const [shortcutNotice, setShortcutNotice] = useState<string | null>(null);
  const [copiedAnnotationId, setCopiedAnnotationId] = useState<string | null>(null);
  const [chartResetRequest, setChartResetRequest] = useState(0);
  const [chartZoomRequest, setChartZoomRequest] = useState<{ sequence: number; scale: number } | undefined>();
  const timeframeDigitsRef = useRef("");
  const timeframeTimerRef = useRef<number | null>(null);
  const orderTicketRef = useRef<HTMLFormElement>(null);
  const recordChartHistory = useCallback((entry: ChartHistoryEntry) => {
    setChartHistory((items) => [...items.slice(0, chartHistoryIndex), entry]);
    setChartHistoryIndex((value) => value + 1);
  }, [chartHistoryIndex]);
  const session = useQuery({
    queryKey: ["session", sessionId],
    queryFn: () => fetchSession(sessionId!),
    enabled: Boolean(sessionId),
  });
  const timeframeBars = useQuery({
    queryKey: ["session-bars", sessionId, timeframe, session.data?.session.revision],
    queryFn: () => fetchSessionBars(sessionId!, timeframe),
    enabled: Boolean(sessionId && session.data && timeframe !== "1m"),
    placeholderData: (previous) => previous,
  });
  const preferences = useQuery({
    queryKey: ["local-preferences"],
    queryFn: fetchPreferences,
  });
  const chartToolManifest = useQuery({
    queryKey: ["chart-tool-manifest"],
    queryFn: fetchChartToolManifest,
  });
  const chartToolRegistryReady = useMemo(() => {
    if (!chartToolManifest.data || chartToolManifest.data.tools.length !== DRAWING_DEFINITIONS.length) return false;
    const serverIds = new Set(chartToolManifest.data.tools.map((tool) => tool.tool_id));
    return DRAWING_DEFINITIONS.every((definition) => serverIds.has(definition.tool));
  }, [chartToolManifest.data]);
  const dispositions = useQuery({
    queryKey: ["annotation-dispositions", sessionId],
    queryFn: () => fetchAnnotationDispositions(sessionId!),
    enabled: Boolean(sessionId),
  });
  const evidence = useQuery({
    queryKey: ["evidence-target", sessionId, evidenceId],
    queryFn: () => fetchEvidenceTarget(sessionId!, evidenceId!),
    enabled: Boolean(sessionId && evidenceId && reviewMode),
  });
  const playbookEvaluation = useQuery({
    queryKey: ["playbook-evaluation", sessionId],
    queryFn: () => fetchPlaybookEvaluation(sessionId!),
    enabled: Boolean(sessionId),
  });
  const refreshPlaybookEvaluation = () => queryClient.invalidateQueries({
    queryKey: ["playbook-evaluation", sessionId],
  });
  const advance = useMutation({
    mutationFn: async (bars: number) => {
      if (!sessionId || !session.data) throw new Error("Session is not ready");
      return applySessionCommand(sessionId, {
        command_id: commandId(),
        expected_revision: session.data.session.revision,
        kind: "advance",
        bars,
      });
    },
    onSuccess: (delta) => {
      queryClient.setQueryData(["session", sessionId], delta);
      void refreshPlaybookEvaluation();
      if (delta.session.frame.current_index === delta.session.frame.total_bars - 1) {
        setPlaying(false);
      }
    },
    onError: async () => {
      setPlaying(false);
      await queryClient.invalidateQueries({ queryKey: ["session", sessionId] });
    },
  });
  const finish = useMutation({
    mutationFn: async () => {
      if (!sessionId || !session.data) throw new Error("Session is not ready");
      return finishSession(sessionId, {
        command_id: commandId(),
        expected_revision: session.data.session.revision,
      });
    },
    onSuccess: (completed) => {
      queryClient.setQueryData(
        ["session", sessionId],
        { session: completed.session, bars: session.data?.bars ?? [], events: [] },
      );
      navigate(`/sessions/${sessionId}/complete`);
    },
  });
  const lockPlan = useMutation({
    mutationFn: async () => {
      if (!sessionId || !session.data) throw new Error("Session is not ready");
      return lockTradePlan(sessionId, {
        command_id: commandId(),
        expected_revision: session.data.session.revision,
        side,
        thesis,
        invalidation,
        risk_amount: riskAmount,
      });
    },
    onSuccess: (result) => {
      queryClient.setQueryData(
        ["session", sessionId],
        { ...session.data!, session: result.session, execution: result.execution },
      );
      void refreshPlaybookEvaluation();
    },
  });
  const placeOrder = useMutation({
    mutationFn: async () => {
      if (!sessionId || !session.data) throw new Error("Session is not ready");
      return submitOrder(sessionId, {
        command_id: commandId(),
        expected_revision: session.data.session.revision,
        side,
        order_type: orderType,
        quantity,
        limit_price: ["LIMIT", "STOP_LIMIT", "TAKE_PROFIT_LIMIT"].includes(orderType)
          ? (orderType === "LIMIT" ? triggerPrice : limitPrice)
          : null,
        stop_price: ["STOP_MARKET", "STOP_LIMIT", "TAKE_PROFIT_MARKET", "TAKE_PROFIT_LIMIT"].includes(orderType)
          ? triggerPrice
          : null,
        activation_price: orderType === "TRAILING_STOP_MARKET" ? (triggerPrice || null) : null,
        callback_rate: orderType === "TRAILING_STOP_MARKET" ? callbackRate : null,
        time_in_force: timeInForce,
        good_till_index: timeInForce === "GTD" ? Number(goodTillIndex) : null,
        reduce_only: reduceOnly,
        close_position: closePosition,
        post_only: postOnly,
        position_side: session.data.session.position_mode === "HEDGE"
          ? (positionSide === "BOTH" ? (side === "BUY" ? "LONG" : "SHORT") : positionSide)
          : "BOTH",
        take_profit_price: takeProfit || null,
        protective_stop_price: protectiveStop || null,
      });
    },
    onSuccess: (result) => {
      queryClient.setQueryData(
        ["session", sessionId],
        { ...session.data!, session: result.session, execution: result.execution },
      );
      void refreshPlaybookEvaluation();
    },
  });
  const cancelPending = useMutation({
    mutationFn: async (orderId: string) => {
      if (!sessionId || !session.data) throw new Error("Session is not ready");
      return cancelOrder(sessionId, {
        command_id: commandId(),
        expected_revision: session.data.session.revision,
        order_id: orderId,
      });
    },
    onSuccess: (result) => {
      queryClient.setQueryData(
        ["session", sessionId],
        { ...session.data!, session: result.session, execution: result.execution },
      );
      void refreshPlaybookEvaluation();
    },
  });
  const markCurrent = useMutation({
    mutationFn: async () => {
      if (!sessionId || !session.data) throw new Error("Session is not ready");
      const bar = session.data.bars.at(-1);
      if (!bar) throw new Error("Current bar is missing");
      return createAnnotation(sessionId, {
        command_id: commandId(),
        expected_revision: session.data.session.revision,
        shape: "marker",
        label: annotationLabel,
        points: [{ time: bar.close_time, price: bar.raw.close }],
      });
    },
    onSuccess: (annotation) => {
      queryClient.setQueryData(
        ["session", sessionId],
        { ...session.data!, annotations: [...(session.data?.annotations ?? []), annotation] },
      );
      setSelectedAnnotationId(annotation.annotation_id);
      void queryClient.invalidateQueries({ queryKey: ["annotation-dispositions", sessionId] });
    },
  });
  const createDrawing = useMutation({
    mutationFn: async ({
      tool,
      points,
    }: {
      tool: Exclude<DrawingTool, "select">;
      points: AnnotationPoint[];
    }) => {
      if (!sessionId || !session.data) throw new Error("Session is not ready");
      const definition = drawingDefinition(tool);
      const precision = session.data.session.instrument.price_scale;
      const vwapPoints = tool === "anchored_vwap"
        ? anchoredVwapPoints(session.data.bars, points, session.data.session.frame.visible_at, precision)
        : null;
      const regression = tool === "regression_trend"
        ? regressionTrendPoints(session.data.bars, points, session.data.session.frame.visible_at, precision)
        : null;
      const objectPoints = vwapPoints ?? regression?.points ?? points;
      const positionTool = ["long_position", "short_position", "risk_reward"].includes(tool)
        ? tool as "long_position" | "short_position" | "risk_reward"
        : null;
      const plan = positionTool
        ? positionPlanSummary(
          positionTool,
          points,
          side === "BUY" ? "long" : "short",
        )
        : null;
      const measurement = tool === "measure" ? measurementSummary(points) : null;
      const measurementChange = measurement
        ? Number(measurement.change).toFixed(session.data.session.instrument.price_scale)
        : null;
      const derivedFacts: Record<string, unknown> = plan
        ? { ...plan }
        : measurement
          ? { ...measurement }
          : regression
            ? {
              slope: regression.slope,
              standard_deviation: regression.deviation,
              sample_count: session.data.bars.filter((bar) => (
                Date.parse(bar.close_time) >= Math.min(...points.map((point) => Date.parse(point.time)))
                && Date.parse(bar.close_time) <= Math.min(
                  Math.max(...points.map((point) => Date.parse(point.time))),
                  Date.parse(session.data!.session.frame.visible_at),
                )
              )).length,
            }
            : vwapPoints
              ? { sample_count: vwapPoints.length, price_basis: "hlc3", weighting: "volume" }
              : {};
      return createAnnotation(sessionId, {
        command_id: commandId(),
        expected_revision: session.data.session.revision,
        shape: definition.shape,
        tool: definition.persistenceTool,
        semantic_role: definition.semanticRole,
        label: plan
          ? `${plan.side === "long" ? "多头" : "空头"}仓位计划 · R:R ${plan.riskRewardRatio}`
          : measurement && measurementChange
            ? `测量 ${Number(measurementChange) >= 0 ? "+" : ""}${measurementChange} (${measurement.percent}%)`
          : annotationLabel,
        points: boundedPoints(objectPoints),
        tool_version: 1,
        geometry: { kind: geometryKind(tool), anchors: boundedPoints(objectPoints) },
        style: {
          line_color: "#20b7f5",
          line_width: 1,
          line_dash: "solid",
          opacity: 1,
          fill_color: "#20b7f5",
          fill_opacity: 0.15,
          text_color: "#d9e8ff",
          font_size: 12,
          start_cap: "none",
          end_cap: "none",
        },
        properties: {
          locked: false,
          hidden: false,
          z_index: 0,
        },
        derived_facts: derivedFacts,
        algorithm_version: "1",
        metadata: {
          side: plan?.side ?? (side === "BUY" ? "long" : "short"),
          source: "drawing_rail",
          ...(plan ? {
            entry_price: plan.entryPrice,
            stop_price: plan.stopPrice,
            target_price: plan.targetPrice,
            risk_reward_ratio: plan.riskRewardRatio,
          } : {}),
          ...(measurement ? {
            price_change: measurement.change,
            percent_change: measurement.percent,
            duration_ms: measurement.durationMs,
          } : {}),
        },
      });
    },
    onSuccess: (annotation, variables) => {
      queryClient.setQueryData(
        ["session", sessionId],
        { ...session.data!, annotations: [...(session.data?.annotations ?? []), annotation] },
      );
      if (continuousDrawing) {
        setDrawingTool(variables.tool);
        setDrawingRequest((value) => value + 1);
      } else {
        setDrawingTool("select");
      }
      setSelectedAnnotationId(annotation.annotation_id);
      recordChartHistory({
        annotationId: annotation.annotation_id,
        before: null,
        after: {
          label: annotation.label,
          points: annotation.points,
          metadata: annotation.metadata ?? {},
          style: annotation.style ?? {},
          properties: annotation.properties ?? {},
        },
      });
      void queryClient.invalidateQueries({ queryKey: ["annotation-dispositions", sessionId] });
    },
  });
  const annotationAction = useMutation({
    mutationFn: async ({
      annotationId,
      action,
      label,
      points,
      metadata,
      style,
      properties,
    }: {
      annotationId: string;
      action: "accepted" | "rejected" | "revised" | "deleted";
      label?: string;
      points?: AnnotationPoint[];
      metadata?: Record<string, string>;
      style?: NonNullable<ChartAnnotation["style"]>;
      properties?: Record<string, unknown>;
    }) => {
      if (!sessionId || !session.data) throw new Error("Session is not ready");
      const before = dispositions.data?.dispositions.find(
        (item) => item.annotation_id === annotationId,
      ) ?? null;
      const updated = await actOnAnnotation(sessionId, annotationId, {
        command_id: commandId(),
        expected_revision: session.data.session.revision,
        action,
        label,
        points: points ? boundedPoints(points) as AnnotationActionRequest["points"] : undefined,
        metadata,
        style,
        properties,
      });
      return { updated, before, action };
    },
    onSuccess: ({ updated, before, action }) => {
      queryClient.setQueryData(
        ["annotation-dispositions", sessionId],
        {
          schema_version: "1.0",
          dispositions: (dispositions.data?.dispositions ?? []).map((item) => (
            item.annotation_id === updated.annotation_id ? updated : item
          )),
        },
      );
      if (before?.original_annotation.layer === "user" && ["revised", "deleted"].includes(action)) {
        recordChartHistory({
          annotationId: updated.annotation_id,
          before: {
            label: before.effective_label,
            points: before.effective_points,
            metadata: before.effective_metadata ?? {},
            style: before.effective_style,
            properties: before.effective_properties ?? {},
          },
          after: action === "deleted"
            ? null
            : {
              label: updated.effective_label,
              points: updated.effective_points,
              metadata: updated.effective_metadata ?? {},
              style: updated.effective_style,
              properties: updated.effective_properties ?? {},
            },
        });
      }
    },
  });
  const chartHistoryAction = useMutation({
    mutationFn: async ({
      entry,
      direction,
    }: {
      entry: ChartHistoryEntry;
      direction: "undo" | "redo";
    }) => {
      if (!sessionId || !session.data) throw new Error("Session is not ready");
      const target = direction === "undo" ? entry.before : entry.after;
      const updated = await actOnAnnotation(sessionId, entry.annotationId, {
        command_id: commandId(),
        expected_revision: session.data.session.revision,
        action: target ? "revised" : "deleted",
        label: target?.label,
        points: target ? boundedPoints(target.points) as AnnotationActionRequest["points"] : undefined,
        metadata: target?.metadata,
        style: target?.style,
        properties: target?.properties,
      });
      return { updated, direction };
    },
    onSuccess: ({ updated, direction }) => {
      queryClient.setQueryData(
        ["annotation-dispositions", sessionId],
        {
          schema_version: "1.0",
          dispositions: (dispositions.data?.dispositions ?? []).map((item) => (
            item.annotation_id === updated.annotation_id ? updated : item
          )),
        },
      );
      setChartHistoryIndex((value) => direction === "undo" ? value - 1 : value + 1);
    },
  });

  const effectiveAnnotations = useMemo(
    () => (dispositions.data?.dispositions ?? [])
      .filter((item) => !["rejected", "deleted"].includes(item.state))
      .map((item) => ({
        ...item.original_annotation,
        label: item.effective_label,
        points: item.effective_points,
        metadata: item.effective_metadata,
        style: item.effective_style,
        properties: item.effective_properties ?? {},
      })),
    [dispositions.data],
  );
  const selectedDisposition = dispositions.data?.dispositions.find(
    (item) => item.annotation_id === selectedAnnotationId,
  ) ?? null;
  const handleDrawingComplete = useCallback(
    (tool: Exclude<DrawingTool, "select">, points: AnnotationPoint[]) => {
      createDrawing.mutate({ tool, points });
    },
    [createDrawing],
  );
  const startDrawing = (tool: Exclude<DrawingTool, "select">) => {
    if (reviewMode || !chartToolRegistryReady) return;
    createDrawing.reset();
    setAnnotationLabel(drawingDefinition(tool).label);
    setDrawingTool(tool);
    setDrawingRequest((value) => value + 1);
  };
  const reviseAnnotationFromChart = useCallback((annotationId: string, points: AnnotationPoint[]) => {
    const disposition = dispositions.data?.dispositions.find(
      (item) => item.annotation_id === annotationId,
    );
    if (!disposition || disposition.original_annotation.layer !== "user" || annotationAction.isPending) return;
    let revised: ChartObjectState;
    try {
      revised = revisedChartObject(
        disposition,
        points,
        session.data?.session.instrument.price_scale ?? 2,
      );
      setChartEditError(null);
    } catch (error) {
      setChartEditError(error instanceof Error ? error.message : "图表对象坐标无效");
      void queryClient.invalidateQueries({ queryKey: ["annotation-dispositions", sessionId] });
      return;
    }
    annotationAction.mutate({
      annotationId,
      action: "revised",
      label: revised.label,
      points: revised.points,
      metadata: revised.metadata,
      style: revised.style,
      properties: revised.properties,
    });
  }, [annotationAction, dispositions.data, queryClient, session.data?.session.instrument.price_scale, sessionId]);
  const undoChartAction = () => {
    if (chartHistoryIndex < 1) return;
    chartHistoryAction.mutate({
      entry: chartHistory[chartHistoryIndex - 1],
      direction: "undo",
    });
  };
  const redoChartAction = () => {
    if (chartHistoryIndex >= chartHistory.length) return;
    chartHistoryAction.mutate({
      entry: chartHistory[chartHistoryIndex],
      direction: "redo",
    });
  };
  const deleteSelectedAnnotation = () => {
    if (!selectedDisposition || ["rejected", "deleted"].includes(selectedDisposition.state)) return;
    annotationAction.mutate({
      annotationId: selectedDisposition.annotation_id,
      action: "deleted",
    });
  };
  const deleteAnnotationFromChart = (annotationId: string) => {
    const disposition = dispositions.data?.dispositions.find(
      (item) => item.annotation_id === annotationId,
    );
    if (!disposition || ["rejected", "deleted"].includes(disposition.state)) return;
    annotationAction.mutate({ annotationId, action: "deleted" });
  };
  const updateAnnotationAppearance = (
    annotationId: string,
    update: { style?: NonNullable<ChartAnnotation["style"]>; properties?: Record<string, unknown> },
  ) => {
    const disposition = dispositions.data?.dispositions.find((item) => item.annotation_id === annotationId);
    if (!disposition || disposition.original_annotation.layer !== "user") return;
    annotationAction.mutate({
      annotationId,
      action: "revised",
      label: disposition.effective_label,
      points: disposition.effective_points,
      metadata: disposition.effective_metadata,
      style: update.style ?? disposition.effective_style,
      properties: update.properties ?? disposition.effective_properties ?? {},
    });
  };
  const duplicateChartObject = useMutation({
    mutationFn: async (annotationId: string) => {
      if (!sessionId || !session.data) throw new Error("Session is not ready");
      const source = effectiveAnnotations.find((annotation) => annotation.annotation_id === annotationId);
      if (!source || source.layer !== "user") throw new Error("Only user chart objects can be duplicated");
      const scale = session.data.session.instrument.price_scale;
      const offset = 5 * (10 ** -scale);
      const points = source.points.map((point) => ({
        ...point,
        price: (Number(point.price) + offset).toFixed(scale),
      }));
      return createAnnotation(sessionId, {
        command_id: commandId(),
        expected_revision: session.data.session.revision,
        shape: source.shape,
        tool: source.tool,
        semantic_role: source.semantic_role,
        label: `${source.label} · 副本`,
        points: boundedPoints(points),
        metadata: source.metadata ?? {},
        tool_version: source.tool_version ?? 1,
        geometry: source.geometry ? { ...source.geometry, anchors: boundedPoints(points) } : undefined,
        style: source.style,
        properties: { ...(source.properties ?? {}), hidden: false, locked: false },
        derived_facts: source.derived_facts ?? {},
        algorithm_version: source.algorithm_version ?? "1",
      });
    },
    onSuccess: (annotation) => {
      queryClient.setQueryData(
        ["session", sessionId],
        { ...session.data!, annotations: [...(session.data?.annotations ?? []), annotation] },
      );
      setSelectedAnnotationId(annotation.annotation_id);
      void queryClient.invalidateQueries({ queryKey: ["annotation-dispositions", sessionId] });
    },
  });
  const saveChartToolTemplate = useMutation({
    mutationFn: async (annotationId: string) => {
      const source = effectiveAnnotations.find((annotation) => annotation.annotation_id === annotationId);
      if (!source || source.layer !== "user" || !source.tool || source.tool === "ai_suggestion") {
        throw new Error("Only user chart objects can be saved as templates");
      }
      return createChartToolTemplate({
        tool: source.tool,
        tool_version: source.tool_version ?? 1,
        name: `${source.label} · 样式`,
        style: source.style ?? {},
        properties: source.properties ?? {},
      });
    },
    onSuccess: () => setChartEditError(null),
    onError: (error) => setChartEditError(error instanceof Error ? error.message : "保存模板失败"),
  });
  const handleAnnotationsChanged = useCallback(() => {
    void queryClient.invalidateQueries({
      queryKey: ["annotation-dispositions", sessionId],
    });
  }, [queryClient, sessionId]);
  const toggleContextAnnotation = (annotationId: string) => {
    setContextAnnotationIds((items) => (
      items.includes(annotationId)
        ? items.filter((item) => item !== annotationId)
        : [...items, annotationId]
    ));
  };

  useEffect(() => {
    if (!playing || advance.isPending || !session.data) return;
    const timer = window.setTimeout(() => advance.mutate(speed), 650);
    return () => window.clearTimeout(timer);
  }, [advance, playing, session.data, speed]);

  useEffect(() => {
    if (evidence.data?.annotation_id) {
      setSelectedAnnotationId(evidence.data.annotation_id);
    }
  }, [evidence.data?.annotation_id]);

  useEffect(() => {
    const applyTimeframeDigits = (digits: string) => {
      const nextTimeframe = timeframeFromDigits(digits);
      timeframeDigitsRef.current = "";
      if (!nextTimeframe) return;
      setTimeframe(nextTimeframe);
      setShortcutNotice(`${l("Timeframe", "周期")} · ${nextTimeframe}`);
    };
    const handleShortcut = (event: KeyboardEvent) => {
      const target = event.target instanceof Element ? event.target : null;
      if (target?.closest("button, a") && ["Space", "ArrowLeft", "ArrowRight"].includes(event.code)) return;
      const command = resolveWorkbenchShortcut(event);
      if (!command && !isEditableShortcutTarget(event.target) && !event.metaKey && !event.ctrlKey && !event.altKey && /^\d$/.test(event.key)) {
        event.preventDefault();
        const candidate = `${timeframeDigitsRef.current}${event.key}`;
        timeframeDigitsRef.current = isTimeframePrefix(candidate)
          ? candidate
          : isTimeframePrefix(event.key) ? event.key : "";
        if (timeframeTimerRef.current !== null) window.clearTimeout(timeframeTimerRef.current);
        const immediate = timeframeFromDigits(timeframeDigitsRef.current);
        if (immediate && timeframeDigitsRef.current !== "1") {
          applyTimeframeDigits(timeframeDigitsRef.current);
        } else if (timeframeDigitsRef.current) {
          timeframeTimerRef.current = window.setTimeout(() => applyTimeframeDigits(timeframeDigitsRef.current), 650);
        }
        return;
      }
      if (!command) return;
      event.preventDefault();
      const readOnlyShortcut = reviewMode || session.data?.session.status === "completed";
      switch (command.kind) {
        case "command_palette": setCommandPaletteQuery(""); break;
        case "indicator_search": setCommandPaletteQuery("指标"); break;
        case "shortcut_help": setShortcutHelpOpen(true); break;
        case "cancel":
          setCommandPaletteQuery(null);
          setShortcutHelpOpen(false);
          setDrawingTool("select");
          setDrawingRequest((value) => value + 1);
          break;
        case "drawing":
          if (!readOnlyShortcut) startDrawing(command.tool);
          break;
        case "undo": if (!readOnlyShortcut) undoChartAction(); break;
        case "redo": if (!readOnlyShortcut) redoChartAction(); break;
        case "copy":
          if (selectedAnnotationId) {
            setCopiedAnnotationId(selectedAnnotationId);
            setShortcutNotice(l("Chart object copied", "已复制图表对象"));
          }
          break;
        case "paste": {
          const sourceId = copiedAnnotationId ?? selectedAnnotationId;
          if (!readOnlyShortcut && sourceId && !duplicateChartObject.isPending) duplicateChartObject.mutate(sourceId);
          break;
        }
        case "delete": if (!readOnlyShortcut) deleteSelectedAnnotation(); break;
        case "toggle_drawings": setAnnotationsVisible((value) => !value); break;
        case "save_layout":
          window.localStorage.setItem("replaytutor:chart-layout", JSON.stringify({ timeframe, annotationsVisible, annotationsLocked, magnetEnabled, continuousDrawing }));
          setShortcutNotice(l("Chart layout saved locally", "图表布局已保存到本机"));
          break;
        case "reset_chart": setChartResetRequest((value) => value + 1); break;
        case "zoom_in": setChartZoomRequest((value) => ({ sequence: (value?.sequence ?? 0) + 1, scale: 1.05 })); break;
        case "zoom_out": setChartZoomRequest((value) => ({ sequence: (value?.sequence ?? 0) + 1, scale: 0.95 })); break;
        case "play_pause": if (!readOnlyShortcut) setPlaying((value) => !value); break;
        case "advance":
          if (!readOnlyShortcut && !advance.isPending && session.data && session.data.session.frame.current_index < session.data.session.frame.total_bars - 1) advance.mutate(command.bars);
          break;
        case "order_draft":
          if (readOnlyShortcut) break;
          setSide(command.side);
          setOrderType(command.orderType);
          setShortcutNotice(session.data?.execution?.plan
            ? `${command.side === "BUY" ? l("Buy", "买入") : l("Sell", "卖出")} · ${command.orderType === "MARKET" ? l("market draft", "市价草稿") : l("limit draft", "限价草稿")} · ${l("confirm to submit", "确认后才提交")}`
            : l("Direction selected; lock the trade plan before creating an order", "已选择方向；请先锁定交易计划，再创建订单草稿"));
          orderTicketRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
          break;
      }
    };
    window.addEventListener("keydown", handleShortcut);
    return () => window.removeEventListener("keydown", handleShortcut);
  }, [advance, annotationsLocked, annotationsVisible, chartHistory, chartHistoryAction, chartHistoryIndex, continuousDrawing, copiedAnnotationId, duplicateChartObject, english, magnetEnabled, reviewMode, selectedAnnotationId, session.data, timeframe]);

  useEffect(() => () => {
    if (timeframeTimerRef.current !== null) window.clearTimeout(timeframeTimerRef.current);
  }, []);

  useEffect(() => {
    if (!shortcutNotice) return;
    const timer = window.setTimeout(() => setShortcutNotice(null), 2400);
    return () => window.clearTimeout(timer);
  }, [shortcutNotice]);

  if (!sessionId) {
    return (
      <section className="page centered-page">
        <StepForward size={36} />
        <h1>{l("No training session is open", "还没有打开训练会话")}</h1>
        <p>{l("Create a replay whose frame_id and visible_at boundary are signed by the server.", "从训练配置创建一个由服务端签发 frame_id 和 visible_at 的真实回放。")}</p>
        <Link className="primary-action" to="/setup">{l("Create training", "创建训练")}</Link>
      </section>
    );
  }
  if (session.isLoading) return <div className="workbench-loading">{l("Restoring session…", "正在恢复会话…")}</div>;
  if (session.isError || !session.data) {
    return <section className="page centered-page"><h1>{l("Could not restore session", "无法恢复会话")}</h1><p>{session.error?.message ?? l("Session response is missing", "会话响应缺失")}</p><Link className="secondary-action" to="/setup">{l("Create again", "重新创建")}</Link></section>;
  }

  const delta = session.data;
  const state = delta.session;
  const execution = delta.execution;
  const chartBars = timeframe === "1m" ? delta.bars : (timeframeBars.data?.bars ?? []);
  const perpetual = state.account_type === "USDT_PERPETUAL";
  const needsTrigger = orderType !== "MARKET";
  const needsSecondaryLimit = ["STOP_LIMIT", "TAKE_PROFIT_LIMIT"].includes(orderType);
  const readOnly = reviewMode || state.status === "completed";
  const visibleLabel = state.hidden_real_date
    ? `Frame ${String(state.frame.current_index).padStart(5, "0")}`
    : new Date(state.frame.visible_at).toLocaleString(english ? "en-US" : "zh-CN", { hour12: false });
  const commandActions: WorkbenchCommandAction[] = [
    ...DRAWING_DEFINITIONS.map((definition) => ({
      id: `draw-${definition.tool}`,
      label: english ? definition.tool.replaceAll("_", " ") : definition.label,
      detail: english ? "Create this chart object using visible market data only." : definition.instruction,
      keywords: `${definition.tool} drawing 画线 绘图`,
      disabled: readOnly || !chartToolRegistryReady,
      run: () => startDrawing(definition.tool),
    })),
    ...REPLAY_TIMEFRAMES.map((item) => ({
      id: `timeframe-${item}`,
      label: `${l("Switch timeframe", "切换周期")} · ${item}`,
      detail: l("Aggregate only bars visible at visible_at.", "只聚合 visible_at 以内的可见行情"),
      keywords: "周期 timeframe",
      run: () => setTimeframe(item),
    })),
    { id: "play", label: playing ? l("Pause replay", "暂停回放") : l("Play replay", "播放回放"), detail: l("Keep one advance command in flight.", "保持单飞 advance 命令"), shortcut: "Space", disabled: readOnly, run: () => setPlaying((value) => !value) },
    { id: "advance", label: l("Advance one bar", "前进一根 K 线"), detail: l("Advance only the server-signed replay frame.", "只向前推进服务端签发的回放帧"), shortcut: "→", disabled: readOnly || advance.isPending, run: () => advance.mutate(1) },
    { id: "reset", label: l("Reset chart viewport", "复位图表视口"), detail: l("Return to the right edge of visible data.", "回到当前可见数据最右侧"), shortcut: "⌥/Alt + R", run: () => setChartResetRequest((value) => value + 1) },
    { id: "toggle-drawings", label: annotationsVisible ? l("Hide all drawings", "隐藏全部绘图") : l("Show all drawings", "显示全部绘图"), detail: l("Toggle visibility without deleting objects.", "不删除对象，只切换可见性"), shortcut: "⌘/Ctrl + ⌥/Alt + H", run: () => setAnnotationsVisible((value) => !value) },
    { id: "shortcuts", label: l("View keyboard shortcuts", "查看快捷键"), detail: l("Show available actions and safety limits.", "显示已接入操作和安全限制"), shortcut: "?", run: () => setShortcutHelpOpen(true) },
    { id: "indicators", label: l("Indicators", "指标"), detail: l("Indicator management is not connected; no fake action is provided.", "指标管理模块尚未接入，当前不创建假操作"), keywords: "indicator 指标", disabled: true, run: () => undefined },
    { id: "symbol", label: l("Switch instrument", "切换品种"), detail: l("The instrument is part of the deterministic session contract. Create a new session from Training setup.", "会话品种属于确定性契约，请从训练配置创建新会话"), keywords: "symbol 品种 代码", disabled: true, run: () => undefined },
    { id: "date", label: l("Go to date", "定位到指定日期"), detail: l("Disabled in replay to prevent crossing visible_at into future data.", "回放内禁用，避免越过 visible_at 查看未来数据"), keywords: "date 日期", disabled: true, run: () => undefined },
  ];

  return (
    <section className="workbench-page">
      <header className="workbench-top">
        <strong>{state.instrument.canonical_symbol}</strong>
        <span>{timeframe}</span>
        <span className="replay-pill">{readOnly ? "REVIEW" : "REPLAY"}</span>
        <span className="workbench-meta">{visibleLabel}</span>
        <span className="workbench-meta">revision {state.revision}</span>
        <span className="data-ok">{l("Data quality · OK", "数据质量 · OK")}</span>
        {readOnly ? (
          <Link
            className="secondary-action"
            to={
              evidenceId
                ? evidenceReturnUrl(sessionId, evidenceId)
                : `/sessions/${sessionId}/review`
            }
          >
            {evidenceId ? l("Back to evidence index", "返回证据索引") : l("Back to full review", "返回完整复盘")}
          </Link>
        ) : <button
          className="danger-action"
          disabled={finish.isPending}
          onClick={() => {
            if (
              preferences.data?.confirm_before_finish !== false
              && !window.confirm(l("The session becomes read-only after finishing. Continue?", "结束后会话进入只读复盘，继续吗？"))
            ) return;
            setPlaying(false);
            finish.mutate();
          }}
          type="button"
        >
          <Square size={12} />{l("Finish session", "结束会话")}
        </button>}
      </header>

      <div className="workbench-grid">
        <DrawingToolbar
          activeTool={drawingTool}
          annotationsLocked={annotationsLocked}
          annotationsVisible={annotationsVisible}
          canDelete={Boolean(selectedDisposition && !["rejected", "deleted"].includes(selectedDisposition.state))}
          canRedo={chartHistoryIndex < chartHistory.length}
          canUndo={chartHistoryIndex > 0}
          disabled={readOnly || !chartToolRegistryReady}
          historyPending={chartHistoryAction.isPending}
          magnetEnabled={magnetEnabled}
          continuousDrawing={continuousDrawing}
          onSelect={(tool) => {
            if (tool === "select") {
              createDrawing.reset();
              setDrawingTool("select");
              return;
            }
            startDrawing(tool);
          }}
          onToggleAnnotations={() => setAnnotationsVisible((value) => !value)}
          onToggleMagnet={() => setMagnetEnabled((value) => !value)}
          onToggleContinuous={() => setContinuousDrawing((value) => !value)}
          onUndo={undoChartAction}
          onRedo={redoChartAction}
          onDelete={deleteSelectedAnnotation}
          onToggleLock={() => setAnnotationsLocked((value) => !value)}
        />
        <main className="chart-stage">
          <div className="chart-stage-head">
            <span>{state.instrument.canonical_symbol}</span>
            <div className="timeframe-switcher" aria-label={l("Chart timeframe", "K 线周期")}>
              {REPLAY_TIMEFRAMES.map((item) => (
                <button
                  aria-pressed={timeframe === item}
                  className={timeframe === item ? "is-active" : ""}
                  key={item}
                  onClick={() => setTimeframe(item)}
                  type="button"
                >
                  {item}
                </button>
              ))}
            </div>
            <span className={timeframeBars.isError && timeframe !== "1m" ? "timeframe-error" : ""}>
              {timeframeBars.isError && timeframe !== "1m"
                ? l("Timeframe data failed", "周期数据加载失败")
                : timeframeBars.isFetching && timeframe !== "1m"
                  ? l("Aggregating…", "聚合中…")
                  : `${chartBars.length} visible bars`}
            </span>
            <span className="fingerprint">fp {state.fingerprint.slice(0, 10)}</span>
            <button
              aria-label={l("Keyboard shortcuts", "键盘快捷键")}
              className="shortcut-help-button"
              onClick={() => setShortcutHelpOpen(true)}
              title={`${l("Keyboard shortcuts", "键盘快捷键")} (?)`}
              type="button"
            >
              <Keyboard aria-hidden="true" size={14} />
              <kbd>?</kbd>
            </button>
            {!chartToolRegistryReady && <span className="timeframe-error">{l("Chart tool registry is not ready", "绘图注册表未就绪")}</span>}
          </div>
          <ReplayChart
            bars={chartBars}
            symbol={state.instrument.canonical_symbol}
            timeframe={timeframe}
            pricePrecision={state.instrument.price_scale}
            visibleAt={state.frame.visible_at}
            hideRealDate={state.hidden_real_date}
            orders={execution?.orders}
            fills={execution?.fills}
            annotations={annotationsVisible ? effectiveAnnotations : []}
            annotationsLocked={annotationsLocked}
            drawingTool={drawingTool}
            drawingRequest={drawingRequest}
            magnetEnabled={magnetEnabled}
            drawingPending={createDrawing.isPending}
            drawingError={createDrawing.error?.message ?? null}
            resetRequest={chartResetRequest}
            zoomRequest={chartZoomRequest}
            contextAnnotationIds={selectedAnnotationId ? [...contextAnnotationIds, selectedAnnotationId] : contextAnnotationIds}
            onDrawingComplete={handleDrawingComplete}
            onAnnotationSelect={setSelectedAnnotationId}
            onAnnotationChange={reviseAnnotationFromChart}
            selectedAnnotationId={selectedAnnotationId}
            onAnnotationDelete={readOnly ? undefined : deleteAnnotationFromChart}
            onAnnotationDuplicate={readOnly ? undefined : (annotationId) => duplicateChartObject.mutate(annotationId)}
            onAnnotationStyleChange={readOnly ? undefined : (annotationId, style) => updateAnnotationAppearance(annotationId, { style })}
            onAnnotationPropertiesChange={readOnly ? undefined : (annotationId, properties) => updateAnnotationAppearance(annotationId, { properties })}
            onAnnotationSaveTemplate={readOnly ? undefined : (annotationId) => saveChartToolTemplate.mutate(annotationId)}
            evidenceTarget={evidence.data ?? null}
          />
          <details className="chart-data-table">
            <summary>{l("View accessible market-data table", "查看可访问行情数据表")}</summary>
            <table>
              <thead><tr><th>{l("Time", "时间")}</th><th>{l("Open", "开")}</th><th>{l("High", "高")}</th><th>{l("Low", "低")}</th><th>{l("Close", "收")}</th></tr></thead>
              <tbody>{chartBars.slice(-20).map((bar) => <tr key={bar.bar_id}><td>{new Date(bar.close_time).toLocaleString(english ? "en-US" : "zh-CN", { hour12: false })}</td><td>{bar.raw.open}</td><td>{bar.raw.high}</td><td>{bar.raw.low}</td><td>{bar.raw.close}</td></tr>)}</tbody>
            </table>
          </details>
        </main>
        <aside className="workbench-dock">
          <div className="dock-heading"><Bot size={17} /><strong>{l("Decision desk", "交易决策台")}</strong><span>W2</span></div>
          <div className="stage-tabs"><button type="button">{l("Context", "环境")}</button><button className="is-active" type="button">{l("Plan", "计划")}</button><button type="button">{l("Position", "持仓")}</button><button type="button">AI</button></div>
          {!execution?.plan ? (
            <form className="dock-card decision-form" onSubmit={(event) => { event.preventDefault(); lockPlan.mutate(); }} ref={orderTicketRef}>
              <span className="page-kicker">PLAN GATE</span>
              <h2>{l("Lock the trading plan first", "先锁定交易计划")}</h2>
              <div className="segmented"><button className={side === "BUY" ? "is-active" : ""} onClick={() => setSide("BUY")} type="button">{l("Long", "做多")}</button><button className={side === "SELL" ? "is-active" : ""} onClick={() => setSide("SELL")} type="button">{perpetual ? l("Short", "做空") : l("Sell", "卖出")}</button></div>
              <label>{l("Trade thesis", "交易逻辑")}<textarea onChange={(event) => setThesis(event.target.value)} placeholder={l("Why is this trade worth taking now?", "为什么此刻值得交易？")} required value={thesis} /></label>
              <label>{l("Invalidation", "失效条件")}<textarea onChange={(event) => setInvalidation(event.target.value)} placeholder={l("What would prove this idea wrong?", "什么发生时证明判断错误？")} required value={invalidation} /></label>
              <label>{l("Risk amount", "风险金额")}<input min="0.01" onChange={(event) => setRiskAmount(event.target.value)} step="0.01" type="number" value={riskAmount} /></label>
              <button className="primary-action" disabled={readOnly || lockPlan.isPending || thesis.length < 3 || invalidation.length < 3} type="submit">{l("Lock plan", "锁定计划")}</button>
            </form>
          ) : (
            <form className="dock-card decision-form" onSubmit={(event) => { event.preventDefault(); placeOrder.mutate(); }} ref={orderTicketRef}>
              <span className="page-kicker">PLAN LOCKED · {execution.plan.side}</span>
              <h2>{l("Submit paper order", "提交模拟订单")}</h2>
              <p>{execution.plan.thesis}</p>
              {perpetual && <div className="account-risk-strip"><strong>{state.leverage}×</strong><span>{state.margin_mode === "ISOLATED" ? l("Isolated", "逐仓") : l("Cross", "全仓")}</span><span>{state.position_mode === "ONEWAY" ? l("One-way", "单向") : l("Hedge", "双向")}</span></div>}
              <label>{l("Order type", "订单类型")}<select onChange={(event) => setOrderType(event.target.value as typeof orderType)} value={orderType}>
                <option value="MARKET">{l("Market", "市价")}</option>
                <option value="LIMIT">{l("Limit", "限价")}</option>
                <option value="STOP_MARKET">{l("Stop market", "止损市价")}</option>
                <option value="STOP_LIMIT">{l("Stop limit", "止损限价")}</option>
                <option value="TAKE_PROFIT_MARKET">{l("Take-profit market", "止盈市价")}</option>
                <option value="TAKE_PROFIT_LIMIT">{l("Take-profit limit", "止盈限价")}</option>
                <option value="TRAILING_STOP_MARKET">{l("Trailing stop", "追踪止损")}</option>
              </select></label>
              <label>{l("Quantity", "数量")}<input min="0.00001" onChange={(event) => setQuantity(event.target.value)} step="0.00001" type="number" value={quantity} /></label>
              {needsTrigger && <label>{orderType === "LIMIT" ? l("Limit price", "委托价") : orderType === "TRAILING_STOP_MARKET" ? l("Activation price (optional)", "激活价（可选）") : l("Trigger price", "触发价")}<input min="0.01" onChange={(event) => setTriggerPrice(event.target.value)} step="0.01" type="number" value={triggerPrice} /></label>}
              {needsSecondaryLimit && <label>{l("Limit price", "限价")}<input min="0.01" onChange={(event) => setLimitPrice(event.target.value)} step="0.01" type="number" value={limitPrice} /></label>}
              {orderType === "TRAILING_STOP_MARKET" && <label>{l("Callback rate", "回调比例")}<input max="0.1" min="0.001" onChange={(event) => setCallbackRate(event.target.value)} step="0.001" type="number" value={callbackRate} /></label>}
              <label>{l("Time in force", "有效方式")}<select onChange={(event) => setTimeInForce(event.target.value as typeof timeInForce)} value={timeInForce}><option value="GTC">GTC · {l("Good till canceled", "持续有效")}</option><option value="IOC">IOC · {l("Immediate or cancel", "立即成交否则撤销")}</option><option value="FOK">FOK · {l("Fill or kill", "全成否则撤销")}</option><option value="GTD">GTD · {l("Good till bar", "指定 K 线前有效")}</option></select></label>
              {timeInForce === "GTD" && <label>{l("Expiry bar index", "到期 K 线 Index")}<input min={state.frame.current_index + 1} onChange={(event) => setGoodTillIndex(event.target.value)} step="1" type="number" value={goodTillIndex} /></label>}
              {perpetual && state.position_mode === "HEDGE" && <label>{l("Position side", "持仓方向")}<select onChange={(event) => setPositionSide(event.target.value as typeof positionSide)} value={positionSide}><option value="LONG">{l("Long", "多头仓")}</option><option value="SHORT">{l("Short", "空头仓")}</option></select></label>}
              {perpetual && <label className="check-row"><input checked={reduceOnly} onChange={(event) => setReduceOnly(event.target.checked)} type="checkbox" /><span><strong>{l("Reduce only", "只减仓")}</strong><small>{l("Prevent the order from increasing or reversing a position.", "禁止订单增加或反向打开持仓。")}</small></span></label>}
              {perpetual && <label className="check-row"><input checked={closePosition} onChange={(event) => setClosePosition(event.target.checked)} type="checkbox" /><span><strong>{l("Close the entire side", "平掉该方向全部持仓")}</strong><small>{l("Use the closable quantity at execution instead of the input quantity.", "成交时按可平数量计算，不依赖输入数量。")}</small></span></label>}
              {["LIMIT", "STOP_LIMIT", "TAKE_PROFIT_LIMIT"].includes(orderType) && <label className="check-row"><input checked={postOnly} onChange={(event) => setPostOnly(event.target.checked)} type="checkbox" /><span><strong>Post-only</strong><small>{l("Enter the order book only as a maker order.", "只作为挂单进入订单簿。")}</small></span></label>}
              <label>{l("Take-profit price (optional)", "止盈价（可选）")}<input min="0.01" onChange={(event) => setTakeProfit(event.target.value)} step="0.01" type="number" value={takeProfit} /></label><label>{l("Protective stop (optional)", "保护止损（可选）")}<input min="0.01" onChange={(event) => setProtectiveStop(event.target.value)} step="0.01" type="number" value={protectiveStop} /></label>
              <button className="primary-action" disabled={readOnly || placeOrder.isPending || (needsTrigger && orderType !== "TRAILING_STOP_MARKET" && !triggerPrice) || (needsSecondaryLimit && !limitPrice) || (timeInForce === "GTD" && !goodTillIndex)} type="submit">{l("Submit · activates on next bar", "提交 · 下一根激活")}</button>
            </form>
          )}
          <div className="dock-card">
            <span className="page-kicker">{l("CHART NOTE", "图上笔记")}</span>
            <label>
              {l("Label", "标注文字")}
              <input
                maxLength={200}
                onChange={(event) => setAnnotationLabel(event.target.value)}
                value={annotationLabel}
              />
            </label>
            <button
              className="secondary-action"
              disabled={readOnly || !annotationLabel.trim() || markCurrent.isPending}
              onClick={() => markCurrent.mutate()}
              type="button"
            >
              {l("Mark current price", "标记当前价格")}
            </button>
          </div>
          <div className="dock-card">
            <span className="page-kicker">CURRENT FRAME</span>
            <dl>
              <div><dt>Frame ID</dt><dd>{state.frame.frame_id.slice(0, 18)}…</dd></div>
              <div><dt>Index</dt><dd>{state.frame.current_index} / {state.frame.total_bars - 1}</dd></div>
              <div><dt>Progress</dt><dd>{(state.frame.progress * 100).toFixed(2)}%</dd></div>
            </dl>
          </div>
          <div className="dock-card rule-checklist">
            <span className="page-kicker">
              PLAYBOOK CHECKS · {playbookEvaluation.data?.evaluator_version ?? "—"}
            </span>
            {playbookEvaluation.isLoading && <p>{l("Evaluating current rules…", "正在计算当前规则状态…")}</p>}
            {playbookEvaluation.data?.checks.length === 0 && <p>{l("No evaluable rules are bound to this session.", "当前会话未绑定可评估规则。")}</p>}
            {playbookEvaluation.data?.checks.map((check) => (
              <div className="rule-check-row" key={check.rule_id}>
                <span className={`rule-status ${check.status}`}>{check.status}</span>
                <div>
                  <strong>{check.rule_id.replaceAll("_", " ")}</strong>
                  <small>{check.summary}</small>
                </div>
              </div>
            ))}
          </div>
          {!readOnly && preferences.data?.ai_mode !== "off" && <TutorDock
            sessionId={sessionId}
            contextAnnotations={effectiveAnnotations.filter((item) => contextAnnotationIds.includes(item.annotation_id))}
            onContextClear={() => setContextAnnotationIds([])}
            onContextRemove={(annotationId) => setContextAnnotationIds((items) => items.filter((item) => item !== annotationId))}
            onEvidenceSelect={(targetId) => {
              if (effectiveAnnotations.some((item) => item.annotation_id === targetId)) {
                setSelectedAnnotationId(targetId);
              }
            }}
            onAnnotationsChanged={handleAnnotationsChanged}
          />}
          {reviewMode && (
            <div className="dock-card evidence-focus-card" role="status">
              <span className="page-kicker">EVIDENCE FOCUS</span>
              {evidence.isLoading && <p>{l("Locating evidence…", "正在定位证据…")}</p>}
              {evidence.isError && <p>{l("Could not locate evidence: ", "无法定位：")}{evidence.error.message}</p>}
              {evidence.data && (
                <>
                  <strong>{evidence.data.kind}</strong>
                  <code>{evidence.data.evidence_id}</code>
                  <p>{evidence.data.occurred_at ?? l("This evidence has no time coordinate", "该证据没有时间坐标")}</p>
                  <p>{evidence.data.price ? `${l("Price", "价格")} ${evidence.data.price}` : l("This evidence has no price coordinate", "该证据没有价格坐标")}</p>
                </>
              )}
            </div>
          )}
          <div className="dock-card annotation-list">
            <span className="page-kicker">{l("LAYER OBJECTS", "图层对象")}</span>
            {(dispositions.data?.dispositions ?? []).map((item) => (
              <div className={`annotation-list-row ${selectedAnnotationId === item.annotation_id ? "is-active" : ""}`} key={item.annotation_id}>
                <button onClick={() => setSelectedAnnotationId(item.annotation_id)} type="button">
                  <span>{item.effective_label}</span><small>{item.original_annotation.tool} · {item.state}</small>
                </button>
                {!['rejected', 'deleted'].includes(item.state) && <button
                  aria-label={contextAnnotationIds.includes(item.annotation_id) ? `${l("Remove from AI context", "从 AI 上下文移除")} ${item.effective_label}` : `${l("Add to AI context", "加入 AI 上下文")} ${item.effective_label}`}
                  className={contextAnnotationIds.includes(item.annotation_id) ? "context-toggle is-active" : "context-toggle"}
                  onClick={() => toggleContextAnnotation(item.annotation_id)}
                  title={contextAnnotationIds.includes(item.annotation_id) ? l("Remove from AI context", "从 AI 上下文移除") : l("Add to AI context", "加入 AI 上下文")}
                  type="button"
                >
                  {contextAnnotationIds.includes(item.annotation_id) ? "AI ✓" : "+ AI"}
                </button>}
              </div>
            ))}
          </div>
          <AnnotationInspector
            disposition={selectedDisposition}
            pending={annotationAction.isPending}
            readOnly={readOnly}
            onAction={(action, label, points) => {
              if (selectedAnnotationId) annotationAction.mutate({ annotationId: selectedAnnotationId, action, label, points });
            }}
          />
        </aside>
        <footer className="replay-controls">
          <button
            aria-label={playing ? l("Pause", "暂停") : l("Play", "播放")}
            className="play-button"
            disabled={readOnly}
            onClick={() => setPlaying((value) => !value)}
            type="button"
          >
            {playing ? <Pause size={15} /> : <Play size={15} />}
          </button>
          <button disabled={readOnly || advance.isPending} onClick={() => advance.mutate(1)} type="button">{l("Next bar", "下一根 K 线")}<ChevronRight size={13} /></button>
          <span>{l("Speed", "速度")}</span>
          {[1, 2, 5, 10, 20].map((value) => (
            <button className={speed === value ? "is-active" : ""} disabled={readOnly} key={value} onClick={() => setSpeed(value)} type="button">{value}×</button>
          ))}
          <div className="timeline"><span style={{ width: `${state.frame.progress * 100}%` }} /></div>
          <code>{visibleLabel}</code>
        </footer>
        <section className="workbench-bottom">
          <nav><button className="is-active" type="button">{l("Events", "事件")} {delta.events.length}</button><button type="button">{l("Orders", "订单")} {execution?.orders?.length ?? 0}</button><button type="button">{l("Fills", "成交")} {execution?.fills?.length ?? 0}</button><button type="button">{l("Position", "持仓")} {execution?.portfolio.position_quantity === "0" ? 0 : 1}</button></nav>
          <div className="event-row">
            <span>{l("Status", "状态")}</span><strong>{state.status}</strong>
            <span>{perpetual ? l("Wallet equity", "钱包权益") : l("Cash", "现金")}</span><strong>{execution?.portfolio.wallet_balance ?? execution?.portfolio.cash ?? state.initial_cash} {state.instrument.quote_currency}</strong>
            <span>{l("Position", "持仓")}</span><strong>{execution?.portfolio.position_quantity ?? "0"} {state.instrument.base_currency}</strong>
            {perpetual && <><span>{l("Available margin", "可用保证金")}</span><strong>{execution?.portfolio.available_balance ?? "0"} USDT</strong><span>{l("Unrealized P&L", "未实现盈亏")}</span><strong>{execution?.portfolio.unrealized_pnl ?? "0"} USDT</strong></>}
            <span>{l("Latest order", "最新订单")}</span><strong>{execution?.orders?.at(-1)?.status ?? l("None", "无")}</strong>
          </div>
          {!readOnly && execution?.orders?.some((order) => order.status === "PENDING" && !order.parent_order_id) && <button className="cancel-pending" disabled={cancelPending.isPending} onClick={() => { const pending = execution.orders?.find((order) => order.status === "PENDING" && !order.parent_order_id); if (pending) cancelPending.mutate(pending.order_id); }} type="button">{l("Cancel pending order", "取消待成交订单")}</button>}
          {(advance.isError || finish.isError || lockPlan.isError || placeOrder.isError || createDrawing.isError || annotationAction.isError || chartHistoryAction.isError || chartEditError) && <div className="inline-error">{advance.error?.message ?? finish.error?.message ?? lockPlan.error?.message ?? placeOrder.error?.message ?? createDrawing.error?.message ?? annotationAction.error?.message ?? chartHistoryAction.error?.message ?? chartEditError}</div>}
        </section>
      </div>
      {shortcutNotice && <div className="shortcut-notice" role="status">{shortcutNotice}</div>}
      {commandPaletteQuery !== null && (
        <CommandPalette
          actions={commandActions}
          initialQuery={commandPaletteQuery}
          onClose={() => setCommandPaletteQuery(null)}
        />
      )}
      {shortcutHelpOpen && <ShortcutHelp onClose={() => setShortcutHelpOpen(false)} />}
    </section>
  );
}
