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
  const equityValues = (data.equity_curve ?? []).map((point) => Number(point.equity));
  const equityMin = Math.min(...equityValues);
  const equityMax = Math.max(...equityValues);
  const equityRange = Math.max(equityMax - equityMin, 1);
  const equityPolyline = (data.equity_curve ?? []).map((point, index, points) => {
    const x = points.length === 1 ? 0 : index / (points.length - 1) * 100;
    const y = 100 - (Number(point.equity) - equityMin) / equityRange * 100;
    return `${x},${y}`;
  }).join(" ");
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
      <article className="review-rule-checks">
        <div className="review-section-heading">
          <div><div className="page-kicker">DETERMINISTIC PLAYBOOK</div><h2>规则检查</h2></div>
          <code>evaluator {data.playbook_evaluator_version}</code>
        </div>
        {(data.rule_checks ?? []).length === 0 ? <p>当前会话未绑定可评估规则。</p> : (data.rule_checks ?? []).map((check) => (
          <div className="review-rule-row" key={check.rule_id}>
            <span className={`rule-status ${check.status}`}>{check.status}</span>
            <div><strong>{check.rule_id.replaceAll("_", " ")}</strong><p>{check.summary}</p></div>
            <div className="rule-evidence-links">
              {(check.evidence_ids ?? []).map((evidenceId) => (
                <Link key={evidenceId} to={evidenceWorkbenchUrl(sessionId!, evidenceId)}>
                  {evidenceId.slice(0, 10)}
                </Link>
              ))}
            </div>
          </div>
        ))}
      </article>
      <div className="review-detail-grid">
        <article className="review-equity-panel">
          <div className="review-section-heading"><div><div className="page-kicker">ACCOUNT PATH</div><h2>净值曲线</h2></div><span>{(data.equity_curve ?? []).length} points</span></div>
          {(data.equity_curve ?? []).length > 0 ? (
            <svg aria-label="会话净值曲线" preserveAspectRatio="none" role="img" viewBox="0 0 100 100">
              <polyline fill="none" points={equityPolyline} stroke="currentColor" strokeWidth="1.5" vectorEffect="non-scaling-stroke" />
            </svg>
          ) : <p>没有可生成曲线的可见行情。</p>}
        </article>
        <article className="review-timeline-panel">
          <div className="review-section-heading"><div><div className="page-kicker">AUDIT TRAIL</div><h2>操作时间线</h2></div></div>
          <div className="review-timeline">
            {(data.timeline ?? []).map((item, index) => (
              <div key={`${item.kind}-${item.evidence_id ?? index}`}>
                <time>{new Date(item.occurred_at).toLocaleString("zh-CN", { hour12: false })}</time>
                {item.evidence_id ? <Link to={evidenceWorkbenchUrl(sessionId!, item.evidence_id)}>{item.label}</Link> : <strong>{item.label}</strong>}
                <span>{item.kind}</span>
              </div>
            ))}
          </div>
        </article>
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
