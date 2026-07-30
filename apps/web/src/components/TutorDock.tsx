import { useMutation, useQuery } from "@tanstack/react-query";
import { Bot, LoaderCircle, Square } from "lucide-react";
import { useState } from "react";
import {
  cancelTutorRun,
  discoverCodex,
  fetchTutorRun,
  startTutor,
} from "../api/tutor";

export function TutorDock({
  sessionId,
  afterAction = false,
}: {
  readonly sessionId: string;
  readonly afterAction?: boolean;
}) {
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
  return (
    <section className="dock-card tutor-card">
      <div className="tutor-title"><Bot size={15} /><span className="page-kicker">CODEX TUTOR</span><strong>{capability.data?.available ? capability.data.version : "不可用"}</strong></div>
      {!current && <form onSubmit={(event) => { event.preventDefault(); start.mutate(); }}>
        {!afterAction && <label>检查阶段<select onChange={(event) => setStage(event.target.value as typeof stage)} value={stage}><option value="environment">市场环境</option><option value="plan">交易计划</option><option value="position">持仓管理</option><option value="exit">退出决策</option></select></label>}
        <label>{afterAction ? "让 Codex 审查完整会话" : "向 Codex 询问当前 frame"}<textarea onChange={(event) => setQuestion(event.target.value)} placeholder={afterAction ? "结合确定性指标，指出我的计划与执行问题。" : "这次入场是否符合我锁定的计划？"} required value={question} /></label>
        <button className="primary-action" disabled={!capability.data?.available || question.length < 2 || start.isPending} type="submit">{start.isPending ? "正在创建运行…" : "让 Codex 检查"}</button>
      </form>}
      {current?.status === "running" && <div className="tutor-running"><LoaderCircle className="spin" size={18} /><p>Codex 正在读取当前可见证据。回放和订单仍可继续使用。</p><button onClick={() => cancel.mutate()} type="button"><Square size={11} />取消</button></div>}
      {current?.status === "completed" && current.response && <div className="tutor-result">
        <h3>{current.response.summary}</h3>
        {current.response.observations?.map((item) => <article key={item.text}><span>事实观察</span><p>{item.text}</p><code>{item.evidence_ids?.join(" · ")}</code></article>)}
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
