import type { ChartAnnotation } from "@replaytutor/contracts";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Bot, LoaderCircle, Square, X } from "lucide-react";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  cancelTutorRun,
  discoverCodex,
  fetchTutorRun,
  startTutor,
} from "../api/tutor";
import { currentLocale } from "../i18n";

export function TutorDock({
  sessionId,
  afterAction = false,
  contextAnnotations = [],
  onContextRemove,
  onContextClear,
  onEvidenceSelect,
  onAnnotationsChanged,
}: {
  readonly sessionId: string;
  readonly afterAction?: boolean;
  readonly contextAnnotations?: readonly ChartAnnotation[];
  readonly onContextRemove?: (annotationId: string) => void;
  readonly onContextClear?: () => void;
  readonly onEvidenceSelect?: (evidenceId: string) => void;
  readonly onAnnotationsChanged?: () => void;
}) {
  const { i18n } = useTranslation();
  const english = !i18n.resolvedLanguage?.startsWith("zh");
  const l = (en: string, zh: string) => english ? en : zh;
  const [question, setQuestion] = useState("");
  const [stage, setStage] = useState<"environment" | "plan" | "position" | "exit" | "after_action">(
    afterAction ? "after_action" : "environment",
  );
  const [runId, setRunId] = useState<string | null>(null);
  const capability = useQuery({
    queryKey: ["codex-capability"],
    queryFn: discoverCodex,
  });
  const run = useQuery({
    queryKey: ["tutor-run", runId],
    queryFn: () => fetchTutorRun(runId!),
    enabled: Boolean(runId),
    refetchInterval: (query) => query.state.data?.status === "running" ? 500 : false,
  });
  const start = useMutation({
    mutationFn: () => startTutor(sessionId, {
      question,
      stage,
      locale: currentLocale(),
      context_annotation_ids: contextAnnotations.map((item) => item.annotation_id),
    }),
    onSuccess: (created) => setRunId(created.run_id),
  });
  const cancel = useMutation({
    mutationFn: () => cancelTutorRun(runId!),
    onSuccess: (cancelled) => {
      run.refetch();
      setRunId(cancelled.run_id);
    },
  });
  const current = run.data;
  useEffect(() => {
    if (current?.status === "completed" && (current.response?.annotations?.length ?? 0) > 0) {
      onAnnotationsChanged?.();
    }
  }, [current?.response?.annotations?.length, current?.status, onAnnotationsChanged]);
  return (
    <section className="dock-card tutor-card">
      <div className="tutor-title"><Bot size={15} /><span className="page-kicker">CODEX TUTOR</span><strong>{capability.data?.available ? capability.data.version : l("Unavailable", "不可用")}</strong></div>
      {!current && <form onSubmit={(event) => { event.preventDefault(); start.mutate(); }}>
        <div className="context-tray" aria-label={l("Chart context sent to Codex", "发送给 Codex 的图表上下文")}>
          <div className="context-tray-head">
            <span>{l("Chart context", "图表上下文")} · {contextAnnotations.length}</span>
            {contextAnnotations.length > 0 && <button onClick={onContextClear} type="button">{l("Clear", "清空")}</button>}
          </div>
          {contextAnnotations.length === 0 ? <p>{l("Use + AI in Layer Objects to attach trend lines, entries, and stops to this question.", "在“图层对象”中点击 + AI，把趋势线、开仓、止损等加入本轮问题。")}</p> : <div className="context-chips">
            {contextAnnotations.map((annotation) => <button className={`context-chip role-${annotation.semantic_role}`} key={annotation.annotation_id} onClick={() => onContextRemove?.(annotation.annotation_id)} title="从本轮上下文移除" type="button"><span>{annotation.label}</span><small>{annotation.tool}</small><X size={11} /></button>)}
          </div>}
        </div>
        {!afterAction && <label>{l("Review stage", "检查阶段")}<select onChange={(event) => setStage(event.target.value as typeof stage)} value={stage}><option value="environment">{l("Market context", "市场环境")}</option><option value="plan">{l("Trade plan", "交易计划")}</option><option value="position">{l("Position management", "持仓管理")}</option><option value="exit">{l("Exit decision", "退出决策")}</option></select></label>}
        <label>{afterAction ? l("Ask Codex to review the full session", "让 Codex 审查完整会话") : l("Ask Codex about the current frame", "向 Codex 询问当前 frame")}<textarea onChange={(event) => setQuestion(event.target.value)} placeholder={afterAction ? l("Use deterministic metrics to identify issues in my plan and execution.", "结合确定性指标，指出我的计划与执行问题。") : l("Does this entry follow my locked plan?", "这次入场是否符合我锁定的计划？")} required value={question} /></label>
        <button className="primary-action" disabled={!capability.data?.available || question.length < 2 || start.isPending} type="submit">{start.isPending ? l("Starting run…", "正在创建运行…") : l("Ask Codex to check", "让 Codex 检查")}</button>
      </form>}
      {current?.status === "running" && <div className="tutor-running"><LoaderCircle className="spin" size={18} /><p>Codex 正在读取当前可见证据。回放和订单仍可继续使用。</p><button onClick={() => cancel.mutate()} type="button"><Square size={11} />取消</button></div>}
      {current?.status === "completed" && current.response && <div className="tutor-result">
        <h3>{current.response.summary}</h3>
        {current.context_bundle_id && <div className="context-bundle-badge"><span>已锁定图表上下文</span><code>{current.context_bundle_id.slice(0, 18)}…</code></div>}
        {current.response.observations?.map((item) => <article key={item.text}><span>事实观察</span><p>{item.text}</p><div className="tutor-evidence-links">{item.evidence_ids?.map((evidenceId) => <button key={evidenceId} onClick={() => onEvidenceSelect?.(evidenceId)} type="button">{evidenceId}</button>)}</div></article>)}
        {current.response.inferences?.map((item) => <article key={item.text}><span>推断 · {item.confidence}</span><p>{item.text}</p></article>)}
        {current.response.risks_and_unknowns?.map((item) => <article key={item}><span>风险 / 未知</span><p>{item}</p></article>)}
        {(current.response.annotations?.length ?? 0) > 0 && <article><span>AI 图上标注</span><p>已将 {current.response.annotations?.length ?? 0} 条证据标注写入独立 AI 图层。</p></article>}
        <button className="secondary-action" onClick={() => { setRunId(null); setQuestion(""); }} type="button">继续追问</button>
      </div>}
      {current && ["failed", "cancelled", "timed_out"].includes(current.status) && <div className="inline-error"><strong>{current.status}</strong><p>{current.error}</p><button onClick={() => setRunId(null)} type="button">返回</button></div>}
      {(capability.isError || start.isError || run.isError) && <div className="inline-error">{capability.error?.message ?? start.error?.message ?? run.error?.message}</div>}
    </section>
  );
}
