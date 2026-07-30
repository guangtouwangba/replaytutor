import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Bot, ChevronRight, MapPin, Pause, Play, Square, StepForward } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import {
  applySessionCommand,
  cancelOrder,
  commandId,
  createAnnotation,
  fetchSession,
  finishSession,
  lockTradePlan,
  submitOrder,
} from "../api/sessions";
import { ReplayChart } from "../chart/ReplayChart";
import { TutorDock } from "../components/TutorDock";

export function WorkbenchPage() {
  const { sessionId } = useParams();
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
  const session = useQuery({
    queryKey: ["session", sessionId],
    queryFn: () => fetchSession(sessionId!),
    enabled: Boolean(sessionId),
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
    },
  });

  useEffect(() => {
    if (!playing || advance.isPending || !session.data) return;
    const timer = window.setTimeout(() => advance.mutate(speed), 650);
    return () => window.clearTimeout(timer);
  }, [advance, playing, session.data, speed]);

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
  const visibleLabel = state.hidden_real_date
    ? `Frame ${String(state.frame.current_index).padStart(5, "0")}`
    : new Date(state.frame.visible_at).toLocaleString("zh-CN", { hour12: false });

  return (
    <section className="workbench-page">
      <header className="workbench-top">
        <strong>{state.instrument.canonical_symbol}</strong>
        <span>1m</span>
        <span className="replay-pill">REPLAY</span>
        <span className="workbench-meta">{visibleLabel}</span>
        <span className="workbench-meta">revision {state.revision}</span>
        <span className="data-ok">数据质量 · OK</span>
        <button
          className="danger-action"
          disabled={finish.isPending}
          onClick={() => { setPlaying(false); finish.mutate(); }}
          type="button"
        >
          <Square size={12} />结束会话
        </button>
      </header>

      <div className="workbench-grid">
        <aside className="drawing-rail" aria-label="绘图工具">
          <button className="is-active" title="选择" type="button">↖</button>
          <button disabled title="W3 开放趋势线" type="button">╱</button>
          <button disabled title="W3 开放矩形" type="button">□</button>
          <button
            className={markCurrent.isPending ? "is-active" : ""}
            onClick={() => markCurrent.mutate()}
            title="在当前 K 线标记观察"
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
            annotations={delta.annotations}
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
              <button className="primary-action" disabled={lockPlan.isPending || thesis.length < 3 || invalidation.length < 3} type="submit">锁定计划</button>
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
              <button className="primary-action" disabled={placeOrder.isPending || (orderType !== "MARKET" && !triggerPrice)} type="submit">提交 · 下一根激活</button>
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
              disabled={!annotationLabel.trim() || markCurrent.isPending}
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
          <TutorDock sessionId={sessionId} />
        </aside>
        <footer className="replay-controls">
          <button
            aria-label={playing ? "暂停" : "播放"}
            className="play-button"
            onClick={() => setPlaying((value) => !value)}
            type="button"
          >
            {playing ? <Pause size={15} /> : <Play size={15} />}
          </button>
          <button disabled={advance.isPending} onClick={() => advance.mutate(1)} type="button">下一根 K 线<ChevronRight size={13} /></button>
          <span>速度</span>
          {[1, 2, 5, 10, 20].map((value) => (
            <button className={speed === value ? "is-active" : ""} key={value} onClick={() => setSpeed(value)} type="button">{value}×</button>
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
          {execution?.orders?.some((order) => order.status === "PENDING" && !order.parent_order_id) && <button className="cancel-pending" disabled={cancelPending.isPending} onClick={() => { const pending = execution.orders?.find((order) => order.status === "PENDING" && !order.parent_order_id); if (pending) cancelPending.mutate(pending.order_id); }} type="button">取消待成交订单</button>}
          {(advance.isError || finish.isError || lockPlan.isError || placeOrder.isError) && <div className="inline-error">{advance.error?.message ?? finish.error?.message ?? lockPlan.error?.message ?? placeOrder.error?.message}</div>}
        </section>
      </div>
    </section>
  );
}
