import type { HealthResponse } from "@replaytutor/contracts";
import { BookOpenText, Database, FileChartColumn, GraduationCap, Home, ListTree, Settings, ShieldCheck } from "lucide-react";
import { NavLink, Outlet } from "react-router-dom";

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
  if (startup.kind === "loading") return <span className="status-pill is-loading">正在连接本地 API</span>;
  if (startup.kind === "available") return <span className="status-pill is-online"><span className="status-dot" />API {startup.health.api.version ?? "unknown"}</span>;
  if (startup.kind === "incompatible") return <button className="status-pill is-warning" onClick={onRetry} type="button">API 版本不兼容 · {startup.receivedVersion}</button>;
  return <button className="status-pill is-offline" onClick={onRetry} type="button">API 不可用 · 重试</button>;
}

const navigation = [
  { to: "/", label: "今日", icon: Home },
  { to: "/academy", label: "学院", icon: GraduationCap },
  { to: "/workbench", label: "工作台", icon: ShieldCheck },
  { to: "/reviews", label: "复盘", icon: FileChartColumn },
  { to: "/playbooks", label: "策略", icon: ListTree },
  { to: "/sessions", label: "会话", icon: BookOpenText },
  { to: "/data", label: "数据", icon: Database },
  { to: "/settings", label: "设置", icon: Settings },
];

export function AppShell({ startup, onRetry }: AppShellProps) {
  return (
    <main className="app-shell" data-api-state={startup.kind}>
      <header className="topbar">
        <NavLink className="brand" to="/"><span className="brand-mark">R</span><span>ReplayTutor</span></NavLink>
        <div className="environment-label">LOCAL · MVP</div>
        <div className="topbar-actions"><StatusPill startup={startup} onRetry={onRetry} /><NavLink className="icon-button" aria-label="设置" to="/settings"><Settings size={17} /></NavLink></div>
      </header>
      <aside className="rail" aria-label="主要导航">
        {navigation.map(({ to, label, icon: Icon }) => (
          <NavLink end={to === "/"} className={({ isActive }) => `rail-link ${isActive ? "is-active" : ""}`} to={to} key={to}><Icon size={18} /><span>{label}</span></NavLink>
        ))}
      </aside>
      <div className="app-content"><Outlet /></div>
    </main>
  );
}
