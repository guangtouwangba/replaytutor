import {
  BarChart3,
  BookOpenText,
  Bot,
  ChevronDown,
  CircleHelp,
  Clock3,
  Crosshair,
  Database,
  Gauge,
  Layers3,
  PanelRight,
  Play,
  Settings,
  TrendingUp,
} from "lucide-react";
import type { HealthResponse } from "@replaytutor/contracts";

export type StartupState =
  | { kind: "loading" }
  | { kind: "available"; health: HealthResponse }
  | { kind: "unavailable"; message: string }
  | { kind: "incompatible"; receivedVersion: string };

interface AppShellProps {
  readonly startup: StartupState;
  readonly onRetry: () => void;
}

const bars = [32, 46, 39, 54, 62, 49, 58, 74, 67, 83, 77, 91, 82, 96, 87, 104, 98, 112, 106, 120];

function StatusPill({ startup, onRetry }: AppShellProps) {
  if (startup.kind === "loading") {
    return <span className="status-pill is-loading">正在连接本地 API</span>;
  }
  if (startup.kind === "available") {
    return (
      <span className="status-pill is-online">
        <span className="status-dot" /> API {startup.health.api.version}
      </span>
    );
  }
  if (startup.kind === "incompatible") {
    return (
      <button className="status-pill is-warning" onClick={onRetry} type="button">
        API 版本不兼容 · {startup.receivedVersion}
      </button>
    );
  }
  return (
    <button className="status-pill is-offline" onClick={onRetry} type="button">
      API 不可用 · 重试
    </button>
  );
}

function CandlePreview() {
  return (
    <div className="chart-stage" aria-label="行情图表占位预览">
      <div className="chart-watermark">BTCUSDT</div>
      <svg viewBox="0 0 960 430" preserveAspectRatio="none" role="img">
        <title>ReplayTutor 行情工作区预览</title>
        <defs>
          <linearGradient id="area" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor="#2962ff" stopOpacity="0.22" />
            <stop offset="1" stopColor="#2962ff" stopOpacity="0" />
          </linearGradient>
        </defs>
        <g className="grid-lines">
          {[70, 140, 210, 280, 350].map((y) => <line key={y} x1="0" x2="960" y1={y} y2={y} />)}
          {[120, 240, 360, 480, 600, 720, 840].map((x) => <line key={x} x1={x} x2={x} y1="0" y2="430" />)}
        </g>
        <path className="area-line" d="M0 340 C90 326 100 354 180 318 S300 255 360 280 S450 238 520 210 S610 239 680 174 S770 195 830 130 S900 148 960 92 L960 430 L0 430 Z" />
        <path className="price-line" d="M0 340 C90 326 100 354 180 318 S300 255 360 280 S450 238 520 210 S610 239 680 174 S770 195 830 130 S900 148 960 92" />
        {bars.map((height, index) => {
          const x = 26 + index * 46;
          const rising = index % 3 !== 0;
          const y = 352 - height - (index * 8);
          return (
            <g key={x} className={rising ? "candle-up" : "candle-down"}>
              <line x1={x} x2={x} y1={y - 18} y2={y + 38} />
              <rect x={x - 7} y={y} width="14" height={Math.max(15, height / 3)} rx="1" />
            </g>
          );
        })}
        <line className="order-line" x1="0" x2="960" y1="171" y2="171" />
      </svg>
      <div className="order-tag">计划买入 67,420.0</div>
    </div>
  );
}

export function AppShell({ startup, onRetry }: AppShellProps) {
  return (
    <main className="app-shell" data-api-state={startup.kind}>
      <header className="topbar">
        <div className="brand"><span className="brand-mark"><TrendingUp size={18} /></span><span>ReplayTutor</span></div>
        <nav className="workspace-tabs" aria-label="工作区">
          <button className="tab is-active" type="button">回放</button>
          <button className="tab" type="button">复盘</button>
          <button className="tab" type="button">数据</button>
        </nav>
        <div className="topbar-actions">
          <StatusPill startup={startup} onRetry={onRetry} />
          <button className="icon-button" aria-label="帮助" type="button"><CircleHelp size={18} /></button>
          <button className="avatar" type="button">RT</button>
        </div>
      </header>

      <aside className="rail" aria-label="主要导航">
        <button className="rail-button is-active" aria-label="行情回放" type="button"><BarChart3 size={20} /></button>
        <button className="rail-button" aria-label="交易记录" type="button"><BookOpenText size={20} /></button>
        <button className="rail-button" aria-label="AI Tutor" type="button"><Bot size={20} /></button>
        <button className="rail-button" aria-label="数据" type="button"><Database size={20} /></button>
        <span className="rail-spacer" />
        <button className="rail-button" aria-label="设置" type="button"><Settings size={20} /></button>
      </aside>

      <section className="workspace">
        <div className="chart-toolbar">
          <button className="symbol-button" type="button"><span className="asset-badge">₿</span><strong>BTCUSDT</strong><ChevronDown size={14} /></button>
          <span className="toolbar-divider" />
          <button className="toolbar-button is-active" type="button">15m</button>
          <button className="toolbar-button" type="button">1H</button>
          <button className="toolbar-button" type="button">4H</button>
          <button className="toolbar-button" type="button">1D</button>
          <span className="toolbar-divider" />
          <button className="toolbar-button" type="button"><Gauge size={16} /> 指标</button>
          <button className="toolbar-button" type="button"><Layers3 size={16} /> 图层</button>
          <span className="toolbar-fill" />
          <span className="market-summary"><span>67,842.1</span><em>+1.84%</em></span>
        </div>

        <div className="chart-layout">
          <div className="drawing-tools">
            <button className="tool-button is-active" aria-label="十字光标" type="button"><Crosshair size={18} /></button>
            <button className="tool-button" aria-label="趋势线" type="button">╱</button>
            <button className="tool-button" aria-label="水平线" type="button">—</button>
            <button className="tool-button" aria-label="文字" type="button">T</button>
          </div>
          <CandlePreview />
          <aside className="watchlist">
            <div className="panel-heading"><strong>自选列表</strong><PanelRight size={16} /></div>
            <div className="watch-row is-selected"><span><b>BTCUSDT</b><small>Bitcoin</small></span><span><b>67,842.1</b><em>+1.84%</em></span></div>
            <div className="watch-row"><span><b>ETHUSDT</b><small>Ethereum</small></span><span><b>3,486.2</b><em>+0.92%</em></span></div>
            <div className="watch-row"><span><b>AAPL</b><small>Apple</small></span><span><b>224.31</b><em className="negative">-0.38%</em></span></div>
            <div className="watch-row"><span><b>600519</b><small>贵州茅台</small></span><span><b>1,526.00</b><em>+0.57%</em></span></div>
          </aside>
        </div>

        <footer className="replay-bar">
          <div className="timeline-meta"><Clock3 size={16} /><span>2025-01-08 10:45</span></div>
          <div className="timeline"><span style={{ width: "38%" }} /></div>
          <button className="play-button" aria-label="开始回放" type="button"><Play size={17} fill="currentColor" /></button>
          <button className="speed-button" type="button">1× <ChevronDown size={13} /></button>
          <div className="session-stat"><small>可见 K 线</small><strong>128 / 842</strong></div>
        </footer>
      </section>
    </main>
  );
}
