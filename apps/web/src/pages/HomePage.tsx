import { useQuery } from "@tanstack/react-query";
import { ArrowRight, Database, PlayCircle, RotateCcw, ShieldCheck } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { fetchDatasets } from "../api/datasets";
import { fetchSessions, fetchTrainingReviews } from "../api/sessions";
import { currentLocale } from "../i18n";

export function HomePage() {
  const { t } = useTranslation();
  const datasets = useQuery({ queryKey: ["datasets"], queryFn: fetchDatasets });
  const sessions = useQuery({ queryKey: ["sessions"], queryFn: fetchSessions });
  const reviews = useQuery({ queryKey: ["training-reviews"], queryFn: fetchTrainingReviews });
  const first = datasets.data?.datasets[0];
  const resumable = sessions.data?.sessions.find((item) => item.status !== "completed");
  const primaryPath = resumable ? `/sessions/${resumable.session_id}` : (first ? "/setup" : "/data");
  const primaryLabel = resumable ? t("home.continue") : (first ? t("home.create") : t("home.prepare"));

  return <section className="page home-page">
    <div className="page-kicker">LOCAL-FIRST TRADING REPLAY</div>
    <header className="home-heading">
      <div><h1>{t("home.hero")}</h1><p>{t("home.subhero")}</p></div>
      <Link className="primary-action" to={primaryPath}>{primaryLabel}<ArrowRight size={16} /></Link>
    </header>
    <div className="home-status-grid"><div className="status-block"><Database size={18} /><span>{t("home.snapshots")}</span><strong>{datasets.isLoading ? "—" : (datasets.data?.datasets.length ?? 0)}</strong><small>{first ? `${first.instrument.canonical_symbol} · ${first.quality.row_count.toLocaleString(currentLocale())} bars` : t("home.none")}</small></div><div className="status-block"><ShieldCheck size={18} /><span>{t("home.discipline")}</span><strong>{t("home.immutable")}</strong><small>Snapshot hash + UTC + Decimal</small></div><div className="status-block is-muted"><PlayCircle size={18} /><span>{t("home.sessions")}</span><strong>{sessions.isLoading ? "—" : (sessions.data?.sessions.length ?? 0)}</strong><small>{sessions.data?.sessions.some((item) => item.status !== "completed") ? t("home.resumable") : "server frame_id + visible_at"}</small></div></div>
    <div className="recent-section">{resumable && <div className="resume-session-card"><div className="resume-session-icon"><RotateCcw size={18} /></div><div><div className="page-kicker">RESUME SESSION</div><h2>{t("home.resume", { symbol: resumable.instrument.canonical_symbol })}</h2><p>{t("home.revision", { revision: resumable.revision })}</p></div><Link className="primary-action" to={`/sessions/${resumable.session_id}`}>{t("home.back")}<ArrowRight size={15} /></Link></div>}
      {reviews.data?.recommendation && <div className="training-recommendation"><div><div className="page-kicker">NEXT TRAINING · DETERMINISTIC</div><h2>{reviews.data.recommendation.status === "ready" ? t("home.focus", { dimension: reviews.data.recommendation.dimension }) : t("home.moreSamples")}</h2><p>{reviews.data.recommendation.status === "ready" ? reviews.data.recommendation.reason : t("home.sampleReason")}</p><small>{t("home.samples", { count: reviews.data.recommendation.sample_count })}</small></div><Link className="secondary-action" to={reviews.data.recommendation.setup_path ?? "/setup"}>{reviews.data.recommendation.status === "ready" ? t("home.startRecommended") : t("home.next")}</Link></div>}
      <div className="section-title"><h2>{t("home.marketSnapshots")}</h2><Link to="/data">{t("home.manage")}</Link></div>{datasets.isError && <div className="inline-error">{t("home.dataError", { message: datasets.error.message })}</div>}{!datasets.isLoading && !first && <div className="empty-row">{t("home.empty")}</div>}{first && <div className="dataset-row"><span className="asset-symbol">₿</span><span><strong>{first.instrument.canonical_symbol}</strong><small>{first.source_id}</small></span><span><small>{t("home.coverage")}</small><b>{first.coverage_start.slice(0, 10)} → {first.coverage_end.slice(0, 10)}</b></span><span><small>{t("home.quality")}</small><b className={`quality-${first.quality.status}`}>{first.quality.status}</b></span><span><small>{t("home.hash")}</small><code>{first.content_hash.slice(0, 12)}</code></span></div>}
    </div>
  </section>;
}
