import type {
  AnnotationActionRequest,
  AnnotationPoint,
  ChartAnnotation,
  CreateAnnotationRequest,
} from "@replaytutor/contracts";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Bot, ChevronRight, MapPin, Pause, Play, Square, StepForward } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import {
  applySessionCommand,
  actOnAnnotation,
  cancelOrder,
  commandId,
  createAnnotation,
  fetchAnnotationDispositions,
  fetchEvidenceTarget,
  fetchSession,
  finishSession,
  lockTradePlan,
  submitOrder,
} from "../api/sessions";
import { ReplayChart } from "../chart/ReplayChart";
import type { DrawingTool } from "../chart/DrawingController";
import { evidenceReturnUrl } from "../chart/EvidenceSelectionBridge";
import { AnnotationInspector } from "../components/AnnotationInspector";
import { TutorDock } from "../components/TutorDock";

function boundedPoints(points: AnnotationPoint[]): CreateAnnotationRequest["points"] {
  if (points.length < 1 || points.length > 4) {
    throw new Error("Annotations require between one and four points");
  }
  return points as CreateAnnotationRequest["points"];
}

export function WorkbenchPage() {
  const { sessionId } = useParams();
  const [searchParams] = useSearchParams();
  const evidenceId = searchParams.get("evidence");
  const reviewMode = searchParams.get("mode") === "review";
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState(1);
  const [side, setSide] = useState<"BUY" | "SELL">("BUY");
  const [thesis, setThesis] = useState("");
  const [invalidation, setInvalidation] = useState("");
  const [riskAmount, setRiskAmount] = useState("100");
  const [orderType, setOrderType] = useState<"MARKET" | "LIMIT" | "STOP_MARKET">("MARKET");
  const [quantity, setQuantity] = useState("0.01");
  const [triggerPrice, setTriggerPrice] = useState("");
  const [takeProfit, setTakeProfit] = useState("");
  const [protectiveStop, setProtectiveStop] = useState("");
  const [annotationLabel, setAnnotationLabel] = useState("我的观察");
  const [drawingTool, setDrawingTool] = useState<DrawingTool>("select");
  const [drawingRequest, setDrawingRequest] = useState(0);
  const [selectedAnnotationId, setSelectedAnnotationId] = useState<string | null>(null);
  const session = useQuery({
    queryKey: ["session", sessionId],
    queryFn: () => fetchSession(sessionId!),
    enabled: Boolean(sessionId),
  });
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
        limit_price: orderType === "LIMIT" ? triggerPrice : null,
        stop_price: orderType === "STOP_MARKET" ? triggerPrice : null,
        take_profit_price: takeProfit || null,
        protective_stop_price: protectiveStop || null,
      });
    },
    onSuccess: (result) => {
      queryClient.setQueryData(
        ["session", sessionId],
        { ...session.data!, session: result.session, execution: result.execution },
      );
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
      shape,
      points,
    }: {
      shape: ChartAnnotation["shape"];
      points: AnnotationPoint[];
    }) => {
      if (!sessionId || !session.data) throw new Error("Session is not ready");
      return createAnnotation(sessionId, {
        command_id: commandId(),
        expected_revision: session.data.session.revision,
        shape,
        label: annotationLabel,
        points: boundedPoints(points),
      });
    },
    onSuccess: (annotation) => {
      queryClient.setQueryData(
        ["session", sessionId],
        { ...session.data!, annotations: [...(session.data?.annotations ?? []), annotation] },
      );
      setDrawingTool("select");
      setSelectedAnnotationId(annotation.annotation_id);
      void queryClient.invalidateQueries({ queryKey: ["annotation-dispositions", sessionId] });
    },
  });
  const annotationAction = useMutation({
    mutationFn: async ({
      annotationId,
      action,
      label,
      points,
    }: {
      annotationId: string;
      action: "accepted" | "rejected" | "revised" | "deleted";
      label?: string;
      points?: AnnotationPoint[];
    }) => {
      if (!sessionId || !session.data) throw new Error("Session is not ready");
      return actOnAnnotation(sessionId, annotationId, {
        command_id: commandId(),
        expected_revision: session.data.session.revision,
        action,
        label,
        points: points ? boundedPoints(points) as AnnotationActionRequest["points"] : undefined,
      });
    },
    onSuccess: (updated) => {
      queryClient.setQueryData(
        ["annotation-dispositions", sessionId],
        {
          schema_version: "1.0",
          dispositions: (dispositions.data?.dispositions ?? []).map((item) => (
            item.annotation_id === updated.annotation_id ? updated : item
          )),
        },
      );
    },
  });

  const effectiveAnnotations = useMemo(
    () => (dispositions.data?.dispositions ?? [])
      .filter((item) => !["rejected", "deleted"].includes(item.state))
      .map((item) => ({
        ...item.original_annotation,
        label: item.effective_label,
        points: item.effective_points,
      })),
    [dispositions.data],
  );
  const selectedDisposition = dispositions.data?.dispositions.find(
    (item) => item.annotation_id === selectedAnnotationId,
  ) ?? null;
  const handleDrawingComplete = useCallback(
    (shape: ChartAnnotation["shape"], points: AnnotationPoint[]) => {
      createDrawing.mutate({ shape, points });
    },
    [createDrawing],
  );
  const startDrawing = (tool: Exclude<DrawingTool, "select">) => {
    if (reviewMode) return;
    setDrawingTool(tool);
    setDrawingRequest((value) => value + 1);
  };
  const handleAnnotationsChanged = useCallback(() => {
    void queryClient.invalidateQueries({
      queryKey: ["annotation-dispositions", sessionId],
    });
  }, [queryClient, sessionId]);

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

  if (!sessionId) {
    return (
      <section className="page centered-page">
        <StepForward size={36} />
        <h1>还没有打开训练会话</h1>
        <p>从训练配置创建一个由服务端签发 frame_id 和 visible_at 的真实回放。</p>
        <Link className="primary-action" to="/setup">创建训练</Link>
      </section>
    );
  }
  if (session.isLoading) return <div className="workbench-loading">正在恢复会话…</div>;
  if (session.isError || !session.data) {
    return <section className="page centered-page"><h1>无法恢复会话</h1><p>{session.error?.message ?? "会话响应缺失"}</p><Link className="secondary-action" to="/setup">重新创建</Link></section>;
  }

  const delta = session.data;
  const state = delta.session;
  const execution = delta.execution;
  const readOnly = reviewMode || state.status === "completed";
  const visibleLabel = state.hidden_real_date
    ? `Frame ${String(state.frame.current_index).padStart(5, "0")}`
    : new Date(state.frame.visible_at).toLocaleString("zh-CN", { hour12: false });

  return (
    <section className="workbench-page">
      <header className="workbench-top">
        <strong>{state.instrument.canonical_symbol}</strong>
        <span>1m</span>
        <span className="replay-pill">{readOnly ? "REVIEW" : "REPLAY"}</span>
        <span className="workbench-meta">{visibleLabel}</span>
        <span className="workbench-meta">revision {state.revision}</span>
        <span className="data-ok">数据质量 · OK</span>
        {readOnly ? (
          <Link
            className="secondary-action"
            to={
              evidenceId
                ? evidenceReturnUrl(sessionId, evidenceId)
                : `/sessions/${sessionId}/review`
            }
          >
            {evidenceId ? "返回证据索引" : "返回完整复盘"}
          </Link>
        ) : <button
          className="danger-action"
          disabled={finish.isPending}
          onClick={() => { setPlaying(false); finish.mutate(); }}
          type="button"
        >
          <Square size={12} />结束会话
        </button>}
      </header>

      <div className="workbench-grid">
        <aside className="drawing-rail" aria-label="绘图工具">
          <button className={drawingTool === "select" ? "is-active" : ""} disabled={readOnly} onClick={() => setDrawingTool("select")} title="选择" type="button">↖</button>
          <button className={drawingTool === "line" ? "is-active" : ""} disabled={readOnly} onClick={() => startDrawing("line")} title="趋势线" type="button">╱</button>
          <button className={drawingTool === "zone" ? "is-active" : ""} disabled={readOnly} onClick={() => startDrawing("zone")} title="矩形" type="button">□</button>
          <button
            className={drawingTool === "marker" ? "is-active" : ""}
            disabled={readOnly}
            onClick={() => startDrawing("marker")}
            title="在图上标记观察"
            type="button"
          >
            <MapPin size={15} />
          </button>
        </aside>
        <main className="chart-stage">
          <div className="chart-stage-head">
            <span>{state.instrument.canonical_symbol} · 1m</span>
            <span>{delta.bars.length} visible bars</span>
            <span className="fingerprint">fp {state.fingerprint.slice(0, 10)}</span>
          </div>
          <ReplayChart
            bars={delta.bars}
            symbol={state.instrument.canonical_symbol}
            pricePrecision={state.instrument.price_scale}
            visibleAt={state.frame.visible_at}
            hideRealDate={state.hidden_real_date}
            orders={execution?.orders}
            fills={execution?.fills}
            annotations={effectiveAnnotations}
            drawingTool={drawingTool}
            drawingRequest={drawingRequest}
            onDrawingComplete={handleDrawingComplete}
            onAnnotationSelect={setSelectedAnnotationId}
            evidenceTarget={evidence.data ?? null}
          />
        </main>
        <aside className="workbench-dock">
          <div className="dock-heading"><Bot size={17} /><strong>交易决策台</strong><span>W2</span></div>
          <div className="stage-tabs"><button type="button">环境</button><button className="is-active" type="button">计划</button><button type="button">持仓</button><button type="button">AI</button></div>
          {!execution?.plan ? (
            <form className="dock-card decision-form" onSubmit={(event) => { event.preventDefault(); lockPlan.mutate(); }}>
              <span className="page-kicker">PLAN GATE</span>
              <h2>先锁定交易计划</h2>
              <div className="segmented"><button className={side === "BUY" ? "is-active" : ""} onClick={() => setSide("BUY")} type="button">做多</button><button className={side === "SELL" ? "is-active" : ""} onClick={() => setSide("SELL")} type="button">卖出</button></div>
              <label>交易逻辑<textarea onChange={(event) => setThesis(event.target.value)} placeholder="为什么此刻值得交易？" required value={thesis} /></label>
              <label>失效条件<textarea onChange={(event) => setInvalidation(event.target.value)} placeholder="什么发生时证明判断错误？" required value={invalidation} /></label>
              <label>风险金额<input min="0.01" onChange={(event) => setRiskAmount(event.target.value)} step="0.01" type="number" value={riskAmount} /></label>
              <button className="primary-action" disabled={readOnly || lockPlan.isPending || thesis.length < 3 || invalidation.length < 3} type="submit">锁定计划</button>
            </form>
          ) : (
            <form className="dock-card decision-form" onSubmit={(event) => { event.preventDefault(); placeOrder.mutate(); }}>
              <span className="page-kicker">PLAN LOCKED · {execution.plan.side}</span>
              <h2>提交模拟订单</h2>
              <p>{execution.plan.thesis}</p>
              <label>订单类型<select onChange={(event) => setOrderType(event.target.value as typeof orderType)} value={orderType}><option value="MARKET">市价</option><option value="LIMIT">限价</option><option value="STOP_MARKET">止损市价</option></select></label>
              <label>数量<input min="0.00001" onChange={(event) => setQuantity(event.target.value)} step="0.00001" type="number" value={quantity} /></label>
              {orderType !== "MARKET" && <label>{orderType === "LIMIT" ? "限价" : "触发价"}<input min="0.01" onChange={(event) => setTriggerPrice(event.target.value)} step="0.01" type="number" value={triggerPrice} /></label>}
              {side === "BUY" && <><label>止盈价（可选）<input min="0.01" onChange={(event) => setTakeProfit(event.target.value)} step="0.01" type="number" value={takeProfit} /></label><label>保护止损（成对）<input min="0.01" onChange={(event) => setProtectiveStop(event.target.value)} step="0.01" type="number" value={protectiveStop} /></label></>}
              <button className="primary-action" disabled={readOnly || placeOrder.isPending || (orderType !== "MARKET" && !triggerPrice)} type="submit">提交 · 下一根激活</button>
            </form>
          )}
          <div className="dock-card">
            <span className="page-kicker">图上笔记</span>
            <label>
              标注文字
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
              标记当前价格
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
          {!readOnly && <TutorDock
            sessionId={sessionId}
            onAnnotationsChanged={handleAnnotationsChanged}
          />}
          {reviewMode && (
            <div className="dock-card evidence-focus-card" role="status">
              <span className="page-kicker">EVIDENCE FOCUS</span>
              {evidence.isLoading && <p>正在定位证据…</p>}
              {evidence.isError && <p>无法定位：{evidence.error.message}</p>}
              {evidence.data && (
                <>
                  <strong>{evidence.data.kind}</strong>
                  <code>{evidence.data.evidence_id}</code>
                  <p>{evidence.data.occurred_at ?? "该证据没有时间坐标"}</p>
                  <p>{evidence.data.price ? `价格 ${evidence.data.price}` : "该证据没有价格坐标"}</p>
                </>
              )}
            </div>
          )}
          <div className="dock-card annotation-list">
            <span className="page-kicker">图层对象</span>
            {(dispositions.data?.dispositions ?? []).map((item) => (
              <button className={selectedAnnotationId === item.annotation_id ? "is-active" : ""} key={item.annotation_id} onClick={() => setSelectedAnnotationId(item.annotation_id)} type="button">
                <span>{item.effective_label}</span><small>{item.original_annotation.layer} · {item.state}</small>
              </button>
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
            aria-label={playing ? "暂停" : "播放"}
            className="play-button"
            disabled={readOnly}
            onClick={() => setPlaying((value) => !value)}
            type="button"
          >
            {playing ? <Pause size={15} /> : <Play size={15} />}
          </button>
          <button disabled={readOnly || advance.isPending} onClick={() => advance.mutate(1)} type="button">下一根 K 线<ChevronRight size={13} /></button>
          <span>速度</span>
          {[1, 2, 5, 10, 20].map((value) => (
            <button className={speed === value ? "is-active" : ""} disabled={readOnly} key={value} onClick={() => setSpeed(value)} type="button">{value}×</button>
          ))}
          <div className="timeline"><span style={{ width: `${state.frame.progress * 100}%` }} /></div>
          <code>{visibleLabel}</code>
        </footer>
        <section className="workbench-bottom">
          <nav><button className="is-active" type="button">事件 {delta.events.length}</button><button type="button">订单 {execution?.orders?.length ?? 0}</button><button type="button">成交 {execution?.fills?.length ?? 0}</button><button type="button">持仓 {execution?.portfolio.position_quantity === "0" ? 0 : 1}</button></nav>
          <div className="event-row">
            <span>状态</span><strong>{state.status}</strong>
            <span>现金</span><strong>{execution?.portfolio.cash ?? state.initial_cash} {state.instrument.quote_currency}</strong>
            <span>持仓</span><strong>{execution?.portfolio.position_quantity ?? "0"} {state.instrument.base_currency}</strong>
            <span>最新订单</span><strong>{execution?.orders?.at(-1)?.status ?? "无"}</strong>
          </div>
          {!readOnly && execution?.orders?.some((order) => order.status === "PENDING" && !order.parent_order_id) && <button className="cancel-pending" disabled={cancelPending.isPending} onClick={() => { const pending = execution.orders?.find((order) => order.status === "PENDING" && !order.parent_order_id); if (pending) cancelPending.mutate(pending.order_id); }} type="button">取消待成交订单</button>}
          {(advance.isError || finish.isError || lockPlan.isError || placeOrder.isError) && <div className="inline-error">{advance.error?.message ?? finish.error?.message ?? lockPlan.error?.message ?? placeOrder.error?.message}</div>}
        </section>
      </div>
    </section>
  );
}
