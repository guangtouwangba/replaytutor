import { useQuery } from "@tanstack/react-query";
import { CheckCircle2, ExternalLink } from "lucide-react";
import { useEffect } from "react";
import { Link, useLocation, useParams } from "react-router-dom";
import { fetchTrainingReview } from "../api/sessions";
import { evidenceWorkbenchUrl } from "../chart/EvidenceSelectionBridge";
import { TutorDock } from "../components/TutorDock";

export function SessionReviewPage({ complete = false }: { readonly complete?: boolean }) {
  const { sessionId } = useParams();
  const location = useLocation();
  const review = useQuery({
    queryKey: ["training-review", sessionId],
    queryFn: () => fetchTrainingReview(sessionId!),
    enabled: Boolean(sessionId),
  });
  useEffect(() => {
    if (!location.hash.startsWith("#evidence-")) return;
    const element = document.getElementById(location.hash.slice(1));
    element?.focus();
  }, [location.hash, review.data]);
  if (review.isLoading) return <div className="route-loading">正在生成确定性复盘…</div>;
  if (review.isError || !review.data) return <section className="page centered-page"><h1>复盘不可用</h1><p>{review.error?.message ?? "缺少复盘数据"}</p></section>;
  const data = review.data;
  return (
    <section className="page deterministic-review">
      <div className="review-hero">
        {complete && <CheckCircle2 size={34} />}
        <div><div className="page-kicker">{complete ? "SESSION COMPLETE" : "EVIDENCE REVIEW"}</div><h1>{complete ? "训练已完成" : "确定性训练复盘"}</h1><p>事实指标与过程纪律分开呈现。AI 结论尚未混入本区。</p></div>
        <span className={`outcome-badge ${data.process_outcome.includes("good") ? "good" : ""}`}>{data.process_outcome}</span>
      </div>
      <div className="review-metrics">{data.metrics.map((metric) => <article key={metric.key}><small>{metric.label}</small><strong>{metric.value}</strong><span>{metric.unit}</span></article>)}</div>
      <div className="review-columns">
        <article><h2>过程发现</h2>{data.findings.map((finding) => <p key={finding}>{finding}</p>)}</article>
        <article><h2>证据索引</h2>{data.evidence.map((item) => <Link className="evidence-row" id={`evidence-${item.evidence_id}`} key={item.evidence_id} tabIndex={-1} to={evidenceWorkbenchUrl(sessionId!, item.evidence_id)}><span>{item.kind}</span><strong>{item.summary}</strong><code>{item.evidence_id.slice(0, 12)}</code></Link>)}</article>
      </div>
      {!complete && (
        <div className="after-action-review">
          <div>
            <div className="page-kicker">CODEX · AFTER ACTION</div>
            <h2>AI 事后审查</h2>
            <p>Codex 只能读取上方确定性复盘和证据索引；输出与事实指标分栏保存。</p>
          </div>
          <TutorDock afterAction sessionId={sessionId!} />
        </div>
      )}
      <footer className="review-actions"><code>review hash · {data.review_hash.slice(0, 20)}</code>{complete ? <Link className="primary-action" to={`/sessions/${sessionId}/review`}>打开完整复盘 <ExternalLink size={14} /></Link> : <Link className="secondary-action" to="/sessions">返回会话库</Link>}</footer>
    </section>
  );
}

export function SessionCompletePage() {
  return <SessionReviewPage complete />;
}
