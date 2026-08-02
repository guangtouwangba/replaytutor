import type { HealthResponse } from "@replaytutor/contracts";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { BookOpenText, Database, DownloadCloud, FileChartColumn, GraduationCap, Home, ListTree, Settings, ShieldCheck } from "lucide-react";
import { useEffect } from "react";
import { useTranslation } from "react-i18next";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import { fetchDatasetDownloadJobs } from "../api/datasets";

export type StartupState =
  | { kind: "loading" }
  | { kind: "available"; health: HealthResponse }
  | { kind: "unavailable"; message: string }
  | { kind: "incompatible"; receivedVersion: string };

interface AppShellProps {
  readonly startup: StartupState;
  readonly onRetry: () => void;
}

function StatusPill({ startup, onRetry }: AppShellProps) {
  const { t } = useTranslation();
  if (startup.kind === "loading") return <span className="status-pill is-loading">{t("api.connecting")}</span>;
  if (startup.kind === "available") return <span className="status-pill is-online"><span className="status-dot" />API {startup.health.api.version ?? "unknown"}</span>;
  if (startup.kind === "incompatible") return <button className="status-pill is-warning" onClick={onRetry} type="button">{t("api.incompatible", { version: startup.receivedVersion })}</button>;
  return <button className="status-pill is-offline" onClick={onRetry} type="button">{t("api.unavailable")}</button>;
}

const navigation = [
  { to: "/", labelKey: "nav.home", icon: Home },
  { to: "/academy", labelKey: "nav.academy", icon: GraduationCap },
  { to: "/workbench", labelKey: "nav.workbench", icon: ShieldCheck },
  { to: "/reviews", labelKey: "nav.reviews", icon: FileChartColumn },
  { to: "/playbooks", labelKey: "nav.playbooks", icon: ListTree },
  { to: "/sessions", labelKey: "nav.sessions", icon: BookOpenText },
  { to: "/data", labelKey: "nav.data", icon: Database },
  { to: "/settings", labelKey: "nav.settings", icon: Settings },
] as const;

function DownloadStatus({ enabled }: { readonly enabled: boolean }) {
  const queryClient = useQueryClient();
  const jobs = useQuery({
    queryKey: ["dataset-downloads"],
    queryFn: fetchDatasetDownloadJobs,
    enabled,
    refetchInterval: (query) => query.state.data?.jobs.some(
      (job) => job.status === "queued" || job.status === "running",
    ) ? 1_000 : false,
  });
  const active = jobs.data?.jobs.find(
    (job) => job.status === "queued" || job.status === "running",
  );
  const succeeded = jobs.data?.jobs.filter((job) => job.status === "succeeded").length ?? 0;

  useEffect(() => {
    if (succeeded > 0) void queryClient.invalidateQueries({ queryKey: ["datasets"] });
  }, [queryClient, succeeded]);

  if (!active) return null;
  const progress = Math.round(active.progress * 100);
  return (
    <NavLink className="download-status-pill" to="/data" aria-label={`行情下载 ${progress}%`}>
      <DownloadCloud className="spin" size={14} />
      <span><strong>{active.symbol} 行情下载</strong><small>{active.status === "queued" ? "等待开始" : `${progress}% · 可继续浏览其他页面`}</small></span>
    </NavLink>
  );
}

export function AppShell({ startup, onRetry }: AppShellProps) {
  const { pathname } = useLocation();
  const { t } = useTranslation();
  const isWorkbenchRoute = pathname === "/workbench" || /^\/sessions\/[^/]+$/.test(pathname);

  return (
    <main className={`app-shell ${isWorkbenchRoute ? "is-workbench-route" : ""}`} data-api-state={startup.kind}>
      <a className="skip-link" href="#main-content">{t("app.skip")}</a>
      <header className="topbar">
        <NavLink className="brand" to="/"><span className="brand-mark">R</span><span>ReplayTutor</span></NavLink>
        <div className="environment-label">{t("app.environment")}</div>
        <div className="topbar-actions"><DownloadStatus enabled={startup.kind === "available"} /><StatusPill startup={startup} onRetry={onRetry} /><NavLink className="icon-button" aria-label={t("nav.settings")} to="/settings"><Settings size={17} /></NavLink></div>
      </header>
      {!isWorkbenchRoute && (
        <aside className="rail" aria-label={t("nav.primary")}>
          {navigation.map(({ to, labelKey, icon: Icon }) => (
            <NavLink end={to === "/"} className={({ isActive }) => `rail-link ${isActive ? "is-active" : ""}`} to={to} key={to}><Icon size={18} /><span>{t(labelKey)}</span></NavLink>
          ))}
        </aside>
      )}
      <div className="app-content" id="main-content" tabIndex={-1}><Outlet /></div>
    </main>
  );
}
