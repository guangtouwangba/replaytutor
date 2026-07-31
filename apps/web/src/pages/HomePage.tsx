import { useQuery } from "@tanstack/react-query";
import { ArrowRight, Database, PlayCircle, ShieldCheck } from "lucide-react";
import { Link } from "react-router-dom";
import { useState } from "react";
import { fetchDatasets } from "../api/datasets";
import { fetchSessions, fetchTrainingReviews } from "../api/sessions";

export function HomePage() {
  const [onboarding, setOnboarding] = useState(
    () => window.localStorage.getItem("replaytutor:onboarding-complete") !== "1",
  );
  const datasets = useQuery({ queryKey: ["datasets"], queryFn: fetchDatasets });
  const sessions = useQuery({ queryKey: ["sessions"], queryFn: fetchSessions });
  const reviews = useQuery({
    queryKey: ["training-reviews"],
    queryFn: fetchTrainingReviews,
  });
  const first = datasets.data?.datasets[0];
  const resumable = sessions.data?.sessions.find((item) => item.status !== "completed");

  function finishOnboarding() {
    window.localStorage.setItem("replaytutor:onboarding-complete", "1");
    setOnboarding(false);
  }

  return (
    <section className="page home-page">
      {onboarding && (
        <div className="onboarding-banner" role="region" aria-label="首次使用 ReplayTutor">
          <div>
            <div className="page-kicker">FIRST SESSION · CODEX ONLY</div>
            <h2>先用固定片段完成一场可核验训练</h2>
            <p>你先画图并锁定计划，确定性引擎负责成交和指标，Codex 只负责基于证据提问与复盘。</p>
          </div>
          <div className="header-actions">
            <button className="secondary-action" onClick={finishOnboarding} type="button">我已了解</button>
            <Link className="primary-action" onClick={finishOnboarding} to={first ? "/setup" : "/data"}>{first ? "开始固定训练" : "载入示例数据"}</Link>
          </div>
        </div>
      )}
      <div className="page-kicker">LOCAL TRADING LAB</div>
      <div className="home-heading">
        <div>
          <h1>用当时可见的信息，重新训练一次决策。</h1>
          <p>行情、订单、账本和 Tutor 共享同一时间边界。所有结果都能重放和核对。</p>
        </div>
        <Link className="primary-action" to={first ? "/setup" : "/data"}>
          {first ? "创建回放" : "准备真实数据"}<ArrowRight size={16} />
        </Link>
      </div>

      <div className="home-status-grid">
        <div className="status-block">
          <Database size={18} />
          <span>可用快照</span>
          <strong>{datasets.isLoading ? "—" : (datasets.data?.datasets.length ?? 0)}</strong>
          <small>{first ? `${first.instrument.canonical_symbol} · ${first.quality.row_count.toLocaleString()} bars` : "尚未载入行情"}</small>
        </div>
        <div className="status-block">
          <ShieldCheck size={18} />
          <span>数据纪律</span>
          <strong>不可变</strong>
          <small>Snapshot hash + UTC + Decimal</small>
        </div>
        <div className="status-block is-muted">
          <PlayCircle size={18} />
          <span>训练会话</span>
          <strong>{sessions.isLoading ? "—" : (sessions.data?.sessions.length ?? 0)}</strong>
          <small>{sessions.data?.sessions.some((item) => item.status !== "completed") ? "存在可继续会话" : "服务端 frame_id + visible_at"}</small>
        </div>
      </div>

      <div className="recent-section">
        {resumable && (
          <div className="section-title">
            <h2>继续上次训练</h2>
            <Link to={`/sessions/${resumable.session_id}`}>恢复到 revision {resumable.revision}</Link>
          </div>
        )}
        {reviews.data?.recommendation && (
          <div className="training-recommendation">
            <div>
              <div className="page-kicker">NEXT TRAINING · DETERMINISTIC</div>
              <h2>
                {reviews.data.recommendation.status === "ready"
                  ? `重点训练：${reviews.data.recommendation.dimension}`
                  : "继续积累可解析样本"}
              </h2>
              <p>{reviews.data.recommendation.reason}</p>
              <small>{reviews.data.recommendation.sample_count} 个可解析会话</small>
            </div>
            <Link className="secondary-action" to={reviews.data.recommendation.setup_path ?? "/setup"}>
              {reviews.data.recommendation.status === "ready" ? "开始推荐训练" : "完成下一场"}
            </Link>
          </div>
        )}
        <div className="section-title"><h2>行情快照</h2><Link to="/data">管理数据</Link></div>
        {datasets.isError && <div className="inline-error">无法读取数据中心：{datasets.error.message}</div>}
        {!datasets.isLoading && !first && (
          <div className="empty-row">没有伪造的默认行情。先去数据中心载入真实 BTCUSDT Snapshot。</div>
        )}
        {first && (
          <div className="dataset-row">
            <span className="asset-symbol">₿</span>
            <span><strong>{first.instrument.canonical_symbol}</strong><small>{first.source_id}</small></span>
            <span><small>覆盖区间</small><b>{first.coverage_start.slice(0, 10)} → {first.coverage_end.slice(0, 10)}</b></span>
            <span><small>质量</small><b className={`quality-${first.quality.status}`}>{first.quality.status}</b></span>
            <span><small>内容哈希</small><code>{first.content_hash.slice(0, 12)}</code></span>
          </div>
        )}
      </div>
    </section>
  );
}
