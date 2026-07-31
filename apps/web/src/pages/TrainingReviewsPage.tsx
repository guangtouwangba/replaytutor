import { useQuery } from "@tanstack/react-query";
import { BarChart3, ExternalLink } from "lucide-react";
import { Link } from "react-router-dom";
import { fetchTrainingReviews } from "../api/sessions";

export function TrainingReviewsPage() {
  const reviews = useQuery({
    queryKey: ["training-reviews"],
    queryFn: fetchTrainingReviews,
  });
  const items = reviews.data?.reviews ?? [];
  const dimensions = reviews.data?.dimensions ?? [];
  const hasReadyDimension = dimensions.some((item) => item.status === "ready");
  return (
    <section className="page training-reviews-page">
      <header className="page-header">
        <div>
          <div className="page-kicker">DETERMINISTIC TRAINING REVIEW</div>
          <h1>训练复盘中心</h1>
          <p>过程、盈亏与 Codex 推断分开。低样本维度不生成分数。</p>
        </div>
        <Link className="secondary-action" to="/reviews/binance">
          Binance 真实成交复盘<ExternalLink size={14} />
        </Link>
      </header>
      {reviews.isError && <div className="inline-error">{reviews.error.message}</div>}
      <div className="review-summary-grid">
        <article className="capability-panel">
          <div className="panel-title">能力雷达 <span>{items.length} sessions</span></div>
          {!hasReadyDimension && <div className="capability-radar-empty">
            <BarChart3 size={32} />
            <strong>样本尚不足</strong>
            <p>每个维度至少需要 5 个可解析会话。当前不会用默认值或盈亏冒充能力分数。</p>
          </div>}
          <div className="dimension-list">
            {dimensions.map((item) => (
              <div key={item.key}>
                <span>{item.label}</span>
                <strong>{item.status === "insufficient" ? "不足" : item.score}</strong>
                <small>{item.sample_count} 个样本 · {item.passed_count ?? 0}/{item.evaluated_count ?? 0} checks</small>
              </div>
            ))}
          </div>
          {reviews.data?.recommendation && (
            <div className={`review-recommendation ${reviews.data.recommendation.status}`}>
              <strong>{reviews.data.recommendation.status === "ready" ? "推荐训练" : "样本门槛"}</strong>
              <p>{reviews.data.recommendation.reason}</p>
              <Link to={reviews.data.recommendation.setup_path ?? "/setup"}>进入训练配置</Link>
            </div>
          )}
        </article>
        <article className="training-review-list">
          <div className="panel-title">已完成训练 <span>{items.length}</span></div>
          {items.map((review) => {
            const net = review.metrics.find((metric) => metric.key === "net_pnl");
            return (
              <Link key={review.review_id} to={`/sessions/${review.session_id}/review`}>
                <div>
                  <strong>{review.process_outcome.replaceAll("_", " ")}</strong>
                  <small>{new Date(review.created_at).toLocaleString("zh-CN")}</small>
                </div>
                <span>{net?.value ?? "—"} {net?.unit}</span>
              </Link>
            );
          })}
          {!reviews.isLoading && items.length === 0 && (
            <div className="panel-empty">完成第一场回放后，这里会显示确定性复盘。</div>
          )}
        </article>
      </div>
    </section>
  );
}
