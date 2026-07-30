import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FileChartColumn, RefreshCw } from "lucide-react";
import { useState } from "react";
import { createReview, fetchReviews, reviewReportUrl } from "../api/reviews";

export function TradeReviewPage() {
  const queryClient = useQueryClient();
  const reviews = useQuery({ queryKey: ["trade-reviews"], queryFn: fetchReviews });
  const [selected, setSelected] = useState<string | null>(null);
  const activeId = selected ?? reviews.data?.reviews[0]?.review_id ?? null;
  const generate = useMutation({
    mutationFn: createReview,
    onSuccess: async (artifact) => {
      setSelected(artifact.review_id);
      await queryClient.invalidateQueries({ queryKey: ["trade-reviews"] });
    },
  });

  return (
    <section className="page review-page">
      <header className="page-header">
        <div>
          <div className="page-kicker">BINANCE · PRICE ACTION</div>
          <h1>交易复盘</h1>
          <p>真实成交、五周期行情、价格行为证据和反前视过程审查。</p>
        </div>
        <div className="header-actions">
          <button
            className="secondary-action"
            disabled={generate.isPending}
            type="button"
            onClick={() => generate.mutate({ scope_kind: "recent", count: 10, sync_first: true })}
          >
            {generate.isPending ? <RefreshCw className="spin" size={15} /> : <FileChartColumn size={15} />}
            最近 10 笔
          </button>
          <button
            className="primary-action"
            disabled={generate.isPending}
            type="button"
            onClick={() => generate.mutate({ scope_kind: "today", count: 10, sync_first: true })}
          >
            {generate.isPending ? <RefreshCw className="spin" size={15} /> : <FileChartColumn size={15} />}
            复盘今天
          </button>
        </div>
      </header>
      {generate.isError && <div className="inline-error">{generate.error.message}</div>}
      <div className="review-layout">
        <aside className="review-list">
          <div className="panel-title">复盘记录 <span>{reviews.data?.reviews.length ?? 0}</span></div>
          {reviews.data?.reviews.map((review) => (
            <button
              className={`review-list-item ${activeId === review.review_id ? "is-active" : ""}`}
              key={review.review_id}
              onClick={() => setSelected(review.review_id)}
              type="button"
            >
              <strong>{review.scope_kind === "today" ? "今日交易" : review.scope_kind === "recent" ? `最近 ${review.scope_value} 笔` : "单笔复盘"}</strong>
              <span>{review.episode_count} Episodes · PnL {review.total_realized_pnl}</span>
              <small>{new Date(review.created_at).toLocaleString("zh-CN")}</small>
            </button>
          ))}
          {!reviews.isLoading && reviews.data?.reviews.length === 0 && (
            <div className="panel-empty">尚无复盘，先生成今天或最近 10 笔。</div>
          )}
        </aside>
        <div className="review-frame-wrap">
          {activeId ? (
            <iframe
              className="review-frame"
              key={activeId}
              src={reviewReportUrl(activeId)}
              title="Binance 价格行为交易复盘"
            />
          ) : (
            <div className="large-empty">
              <FileChartColumn size={32} />
              <h2>生成第一份价格行为复盘</h2>
              <p>系统会只读同步币安成交，重建交易并绘制 4h、2h、1h、15m、5m 五周期证据。</p>
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
