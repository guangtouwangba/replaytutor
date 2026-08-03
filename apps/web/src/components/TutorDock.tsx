import type {
  ChartAnnotation,
  IndicatorSpec,
  TutorRequest,
  TutorResponse,
  TutorRun,
} from "@replaytutor/contracts";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Bot,
  ChevronDown,
  LoaderCircle,
  MessageSquarePlus,
  Pencil,
  Square,
  Trash2,
  X,
} from "lucide-react";
import { FormEvent, KeyboardEvent, useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  cancelTutorRun,
  createTutorThread,
  deleteTutorThread,
  discoverCodex,
  fetchTutorThread,
  fetchTutorThreads,
  startTutor,
  updateTutorThread,
} from "../api/tutor";
import { currentLocale } from "../i18n";

type TutorStage = TutorRequest["stage"];

function TutorResponseView({
  response,
  contextBundleId,
  onEvidenceSelect,
}: {
  readonly response: TutorResponse;
  readonly contextBundleId?: string | null;
  readonly onEvidenceSelect?: (evidenceId: string) => void;
}) {
  const observations = response.observations ?? [];
  const inferences = response.inferences ?? [];
  const risks = response.risks_and_unknowns ?? [];
  const ruleChecks = response.rule_checks ?? [];
  const nextQuestions = response.next_questions ?? [];
  const annotations = response.annotations ?? [];
  return <div className="tutor-result chat-response">
    <h3>{response.summary}</h3>
    {contextBundleId && <div className="context-bundle-badge"><span>已锁定图表上下文</span><code>{contextBundleId.slice(0, 18)}…</code></div>}
    {observations.map((item, index) => <article key={`${index}-${item.text}`}><span>事实观察</span><p>{item.text}</p><div className="tutor-evidence-links">{(item.evidence_ids ?? []).map((evidenceId) => <button key={evidenceId} onClick={() => onEvidenceSelect?.(evidenceId)} type="button">{evidenceId}</button>)}</div></article>)}
    {inferences.map((item, index) => <article key={`${index}-${item.text}`}><span>推断 · {item.confidence}</span><p>{item.text}</p></article>)}
    {risks.map((item, index) => <article key={`${index}-${item}`}><span>风险 / 未知</span><p>{item}</p></article>)}
    {ruleChecks.length > 0 && <article><span>规则检查</span>{ruleChecks.map((check) => <p key={check.rule_id}><b className={`rule-status ${check.status}`}>{check.status}</b> {check.reason}</p>)}</article>}
    {nextQuestions.length > 0 && <article><span>可以继续追问</span>{nextQuestions.map((item) => <p key={item}>{item}</p>)}</article>}
    {annotations.length > 0 && <article><span>AI 图上标注</span><p>已将 {annotations.length} 条证据标注写入独立 AI 图层。</p></article>}
    <small className="tutor-disclaimer">{response.disclaimer}</small>
  </div>;
}

function RunMessage({
  run,
  cancelling,
  onCancel,
  onEvidenceSelect,
  onRetry,
}: {
  readonly run: TutorRun;
  readonly cancelling: boolean;
  readonly onCancel: (runId: string) => void;
  readonly onEvidenceSelect?: (evidenceId: string) => void;
  readonly onRetry: (question: string) => void;
}) {
  return <div className="chat-turn" data-status={run.status}>
    <div className="chat-user-message"><small>你 · {run.stage}</small><p>{run.question}</p></div>
    {run.status === "running" && <div className="chat-assistant-message tutor-running"><LoaderCircle className="spin" size={17} /><p>Codex 正在读取本轮可见证据。图表与交易仍可继续使用。</p><button disabled={cancelling} onClick={() => onCancel(run.run_id)} type="button"><Square size={11} />取消</button></div>}
    {run.status === "completed" && run.response && <div className="chat-assistant-message"><div className="chat-assistant-label"><Bot size={13} />Codex Tutor</div><TutorResponseView contextBundleId={run.context_bundle_id} onEvidenceSelect={onEvidenceSelect} response={run.response} /></div>}
    {["failed", "cancelled", "timed_out"].includes(run.status) && <div className="chat-assistant-message inline-error"><strong>{run.status}</strong><p>{run.error}</p><button onClick={() => onRetry(run.question)} type="button">重新编辑并发送</button></div>}
  </div>;
}

export function TutorDock({
  sessionId,
  afterAction = false,
  contextAnnotations = [],
  contextIndicators = [],
  onContextRemove,
  onContextClear,
  onIndicatorContextRemove,
  onEvidenceSelect,
  onAnnotationsChanged,
  onRunningChange,
  active = true,
}: {
  readonly sessionId: string;
  readonly afterAction?: boolean;
  readonly contextAnnotations?: readonly ChartAnnotation[];
  readonly contextIndicators?: readonly IndicatorSpec[];
  readonly onContextRemove?: (annotationId: string) => void;
  readonly onContextClear?: () => void;
  readonly onIndicatorContextRemove?: (instanceId: string) => void;
  readonly onEvidenceSelect?: (evidenceId: string) => void;
  readonly onAnnotationsChanged?: () => void;
  readonly onRunningChange?: (running: boolean) => void;
  readonly active?: boolean;
}) {
  const { i18n } = useTranslation();
  const english = !i18n.resolvedLanguage?.startsWith("zh");
  const l = (en: string, zh: string) => english ? en : zh;
  const queryClient = useQueryClient();
  const storageKey = `replaytutor:tutor-thread:${sessionId}`;
  const [activeThreadId, setActiveThreadId] = useState<string | null>(() => window.localStorage.getItem(storageKey));
  const [question, setQuestion] = useState("");
  const [stage, setStage] = useState<TutorStage>(afterAction ? "after_action" : "environment");
  const [showContext, setShowContext] = useState(false);
  const [showJump, setShowJump] = useState(false);
  const [keepPolling, setKeepPolling] = useState(false);
  const initialCreationAttempted = useRef(false);
  const messageListRef = useRef<HTMLDivElement>(null);
  const nearBottomRef = useRef(true);
  const capability = useQuery({ queryKey: ["codex-capability"], queryFn: discoverCodex, enabled: active });
  const threads = useQuery({
    queryKey: ["tutor-threads", sessionId],
    queryFn: () => fetchTutorThreads(sessionId),
    enabled: active,
  });
  const create = useMutation({
    mutationFn: () => createTutorThread(sessionId),
    onSuccess: (created) => {
      setActiveThreadId(created.thread_id);
      queryClient.invalidateQueries({ queryKey: ["tutor-threads", sessionId] });
    },
  });
  const threadItems = threads.data?.threads ?? [];
  useEffect(() => {
    if (!threads.data || threadItems.length > 0 || initialCreationAttempted.current) return;
    initialCreationAttempted.current = true;
    create.mutate();
  }, [create, threads.data]);
  useEffect(() => {
    if (threadItems.length === 0) return;
    if (!activeThreadId || !threadItems.some((item) => item.thread_id === activeThreadId)) {
      setActiveThreadId(threadItems[0].thread_id);
    }
  }, [activeThreadId, threads.data]);
  useEffect(() => {
    if (activeThreadId) window.localStorage.setItem(storageKey, activeThreadId);
  }, [activeThreadId, storageKey]);
  const detail = useQuery({
    queryKey: ["tutor-thread", activeThreadId],
    queryFn: () => fetchTutorThread(activeThreadId!),
    enabled: Boolean(activeThreadId && (active || keepPolling)),
    refetchInterval: (query) => (query.state.data?.runs ?? []).some((item) => item.status === "running") ? 500 : false,
  });
  const runs = detail.data?.runs ?? [];
  const runningRun = runs.find((item) => item.status === "running");
  useEffect(() => onRunningChange?.(Boolean(runningRun)), [onRunningChange, runningRun]);
  const latestRun = runs.at(-1);
  useEffect(() => {
    if (!latestRun || latestRun.status === "running") return;
    setKeepPolling(false);
    queryClient.invalidateQueries({ queryKey: ["tutor-threads", sessionId] });
    if (latestRun.status === "completed" && (latestRun.response?.annotations?.length ?? 0) > 0) onAnnotationsChanged?.();
  }, [latestRun?.run_id, latestRun?.status, onAnnotationsChanged, queryClient, sessionId]);
  useEffect(() => {
    const list = messageListRef.current;
    if (!list || !nearBottomRef.current) return;
    list.scrollTo({ top: list.scrollHeight, behavior: "smooth" });
  }, [runs.length, latestRun?.status]);
  const start = useMutation({
    mutationFn: () => startTutor(sessionId, {
      question: question.trim(),
      thread_id: activeThreadId!,
      stage: afterAction ? "after_action" : stage,
      locale: currentLocale(),
      context_annotation_ids: contextAnnotations.map((item) => item.annotation_id),
      context_indicators: [...contextIndicators] as NonNullable<TutorRequest["context_indicators"]>,
    }),
    onSuccess: (created) => {
      setKeepPolling(true);
      setQuestion("");
      nearBottomRef.current = true;
      queryClient.setQueryData(["tutor-thread", activeThreadId], (current: typeof detail.data) => current ? { ...current, runs: [...(current.runs ?? []), created], run_count: current.run_count + 1, last_question: created.question, last_status: created.status } : current);
      queryClient.invalidateQueries({ queryKey: ["tutor-threads", sessionId] });
    },
  });
  const cancel = useMutation({
    mutationFn: (runId: string) => cancelTutorRun(runId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["tutor-thread", activeThreadId] }),
  });
  const rename = useMutation({
    mutationFn: ({ threadId, title }: { threadId: string; title: string }) => updateTutorThread(threadId, { title }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["tutor-threads", sessionId] }),
  });
  const remove = useMutation({
    mutationFn: (threadId: string) => deleteTutorThread(threadId),
    onSuccess: (_, threadId) => {
      if (activeThreadId === threadId) setActiveThreadId(null);
      queryClient.invalidateQueries({ queryKey: ["tutor-threads", sessionId] });
    },
  });
  const submit = (event?: FormEvent) => {
    event?.preventDefault();
    if (!activeThreadId || question.trim().length < 2 || runningRun || start.isPending) return;
    start.mutate();
  };
  const handleComposerKey = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key !== "Enter" || event.shiftKey || event.nativeEvent.isComposing) return;
    event.preventDefault();
    submit();
  };
  const jumpToLatest = () => {
    const list = messageListRef.current;
    if (!list) return;
    nearBottomRef.current = true;
    setShowJump(false);
    list.scrollTo({ top: list.scrollHeight, behavior: "smooth" });
  };
  const error = capability.error ?? threads.error ?? detail.error ?? create.error ?? start.error ?? cancel.error ?? rename.error ?? remove.error;
  return <section className="tutor-chat" aria-label={l("Codex Tutor chat", "Codex Tutor 对话")}>
    <aside className="chat-thread-sidebar">
      <header><span><Bot size={15} /><strong>Chat</strong></span><button aria-label={l("New conversation", "新建对话")} disabled={create.isPending} onClick={() => create.mutate()} title={l("New conversation", "新建对话")} type="button"><MessageSquarePlus size={15} /></button></header>
      <div className="chat-thread-list">
        {threads.isLoading && <p className="chat-empty"><LoaderCircle className="spin" size={16} />{l("Loading history…", "正在加载历史…")}</p>}
        {threadItems.map((thread) => <div className={`chat-thread-item ${thread.thread_id === activeThreadId ? "is-active" : ""}`} key={thread.thread_id}>
          <button className="chat-thread-select" onClick={() => setActiveThreadId(thread.thread_id)} type="button"><strong>{thread.title}</strong><span>{thread.last_question ?? l("Empty conversation", "空对话")}</span><small>{new Date(thread.updated_at).toLocaleString(english ? "en-US" : "zh-CN", { month: "numeric", day: "numeric", hour: "2-digit", minute: "2-digit" })}{thread.last_status === "running" ? ` · ${l("Running", "运行中")}` : ""}</small></button>
          <div className="chat-thread-actions"><button aria-label={l("Rename", "重命名")} onClick={() => { const title = window.prompt(l("Conversation title", "对话标题"), thread.title)?.trim(); if (title && title !== thread.title) rename.mutate({ threadId: thread.thread_id, title }); }} type="button"><Pencil size={11} /></button><button aria-label={l("Delete", "删除")} disabled={thread.last_status === "running"} onClick={() => { if (window.confirm(l("Delete this conversation from history?", "从历史记录中删除这个对话？"))) remove.mutate(thread.thread_id); }} type="button"><Trash2 size={11} /></button></div>
        </div>)}
      </div>
      <footer>{l("History belongs to this replay session", "历史仅属于当前回放会话")}</footer>
    </aside>
    <div className="chat-conversation">
      <header className="chat-conversation-head"><div><strong>{detail.data?.title ?? l("New conversation", "新对话")}</strong><span>{l("Recent 12 completed turns are used as context", "本次上下文使用最近 12 个成功回合")}</span></div><code>{capability.data?.available ? capability.data.version : l("Unavailable", "不可用")}</code></header>
      <div className="chat-message-list" onScroll={(event) => { const target = event.currentTarget; const nearBottom = target.scrollHeight - target.scrollTop - target.clientHeight < 80; nearBottomRef.current = nearBottom; setShowJump(!nearBottom); }} ref={messageListRef}>
        {detail.isLoading && <p className="chat-empty"><LoaderCircle className="spin" size={18} />{l("Loading conversation…", "正在加载对话…")}</p>}
        {runs.length === 0 && <div className="chat-welcome"><Bot size={22} /><strong>{l("Ask about the current visible market", "询问当前可见行情")}</strong><p>{l("Attach chart plans, drawings, or indicators as explicit context. Future bars remain hidden.", "可以把图形计划、画线或指标作为明确上下文；未来 K 线仍然不可见。")}</p></div>}
        {runs.map((run) => <RunMessage cancelling={cancel.isPending} key={run.run_id} onCancel={(runId) => cancel.mutate(runId)} onEvidenceSelect={onEvidenceSelect} onRetry={setQuestion} run={run} />)}
      </div>
      {showJump && <button className="chat-jump-latest" onClick={jumpToLatest} type="button"><ChevronDown size={13} />{l("Latest", "回到最新")}</button>}
      <form className="chat-composer" onSubmit={submit}>
        <button aria-expanded={showContext} className="chat-context-toggle" onClick={() => setShowContext((value) => !value)} type="button"><span>{l("Chart context", "图表上下文")} · {contextAnnotations.length + contextIndicators.length}</span><ChevronDown className={showContext ? "is-open" : ""} size={13} /></button>
        {showContext && <div className="context-tray" aria-label={l("Chart context sent to Codex", "发送给 Codex 的图表上下文")}><div className="context-tray-head"><span>{l("Explicit evidence for this turn", "本轮明确证据")}</span>{(contextAnnotations.length + contextIndicators.length) > 0 && <button onClick={onContextClear} type="button">{l("Clear", "清空")}</button>}</div>{(contextAnnotations.length + contextIndicators.length) === 0 ? <p>{l("Use + AI in Layer Objects or the indicator panel.", "在“图层对象”或指标面板中点击 AI 加入本轮问题。")}</p> : <div className="context-chips">{contextAnnotations.map((annotation) => <button className={`context-chip role-${annotation.semantic_role}`} key={annotation.annotation_id} onClick={() => onContextRemove?.(annotation.annotation_id)} type="button"><span>{annotation.label}</span><small>{annotation.tool}</small><X size={11} /></button>)}{contextIndicators.map((indicator) => <button className="context-chip role-analysis" key={indicator.instance_id} onClick={() => onIndicatorContextRemove?.(indicator.instance_id)} type="button"><span>{indicator.definition_id}</span><small>{indicator.timeframe} · {l("server evidence", "服务端证据")}</small><X size={11} /></button>)}</div>}</div>}
        <div className="chat-compose-row">
          {!afterAction && <select aria-label={l("Review stage", "检查阶段")} onChange={(event) => setStage(event.target.value as TutorStage)} value={stage}><option value="environment">{l("Environment", "市场环境")}</option><option value="plan">{l("Plan", "交易计划")}</option><option value="position">{l("Position", "持仓管理")}</option><option value="exit">{l("Exit", "退出决策")}</option></select>}
          {afterAction && <span className="after-action-chip">AFTER ACTION</span>}
          <textarea aria-label={l("Message Codex Tutor", "发送给 Codex Tutor")} onChange={(event) => setQuestion(event.target.value)} onKeyDown={handleComposerKey} placeholder={afterAction ? l("Review my plan and execution using deterministic evidence…", "结合确定性证据复盘我的计划与执行…") : l("Ask about this frame…", "询问当前 frame…")} value={question} />
          <button className="chat-send" disabled={!capability.data?.available || !activeThreadId || question.trim().length < 2 || Boolean(runningRun) || start.isPending} type="submit">{start.isPending ? <LoaderCircle className="spin" size={14} /> : l("Send", "发送")}</button>
        </div>
        <small>{l("Enter to send · Shift+Enter for newline · read-only agent", "Enter 发送 · Shift+Enter 换行 · Agent 只读")}</small>
      </form>
      {error && <div className="chat-global-error" role="alert">{error.message}</div>}
    </div>
  </section>;
}
