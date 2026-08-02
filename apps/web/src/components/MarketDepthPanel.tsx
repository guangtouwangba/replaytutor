import type { MarketDepthLevel, MarketDepthResponse } from "@replaytutor/contracts";

interface MarketDepthPanelProps {
  readonly depth: MarketDepthResponse | undefined;
  readonly error: string | null;
  readonly loading: boolean;
  readonly quoteCurrency: string;
  readonly priceScale: number;
  readonly english: boolean;
}

function DepthRows({
  levels,
  side,
  maximum,
  priceScale,
}: {
  readonly levels: readonly MarketDepthLevel[];
  readonly side: "ask" | "bid";
  readonly maximum: number;
  readonly priceScale: number;
}) {
  const rendered = side === "ask" ? [...levels].reverse() : levels;
  return rendered.map((level) => {
    const width = maximum > 0 ? Math.max(2, Number(level.cumulative_quantity) / maximum * 100) : 0;
    return (
      <div className={`depth-row ${side}`} key={`${side}-${level.price}`}>
        <span className="depth-fill" style={{ width: `${Math.min(width, 100)}%` }} />
        <span>{Number(level.price).toFixed(priceScale)}</span>
        <span>{Number(level.quantity).toLocaleString(undefined, { maximumFractionDigits: 6 })}</span>
        <span>{Number(level.cumulative_quantity).toLocaleString(undefined, { maximumFractionDigits: 6 })}</span>
      </div>
    );
  });
}

export function MarketDepthPanel({
  depth,
  error,
  loading,
  quoteCurrency,
  priceScale,
  english,
}: MarketDepthPanelProps) {
  const l = (en: string, zh: string) => english ? en : zh;
  if (loading) return <div className="depth-state">{l("Loading the frame order book…", "正在读取当前帧盘口…")}</div>;
  if (error) return <div className="depth-state error">{error}</div>;
  if (!depth || depth.status === "unavailable" || !depth.depth) {
    return (
      <div className="depth-state unavailable">
        <strong>{l("Historical L2 was not captured", "该时刻没有历史 L2 盘口")}</strong>
        <p>{l(
          "This dataset contains candles only. ReplayTutor will not substitute today's live order book or invent depth from OHLCV.",
          "这个数据集只有 K 线。ReplayTutor 不会用今天的实时盘口冒充历史盘口，也不会从 OHLCV 虚构深度。",
        )}</p>
        <small>{l("Import timestamped L2 snapshots or capture Binance depth while building a current dataset.", "请导入带时间戳的 L2 快照，或在构建当前数据集时同步采集 Binance 深度。")}</small>
      </div>
    );
  }

  const book = depth.depth;
  const maximum = Math.max(
    ...book.bids.map((level) => Number(level.cumulative_quantity)),
    ...book.asks.map((level) => Number(level.cumulative_quantity)),
    0,
  );
  return (
    <section className="market-depth" aria-label={l("Market depth", "市场深度")}>
      {depth.status === "stale" && (
        <div className="depth-warning">
          {l("Stale snapshot", "盘口已陈旧")} · {Math.round(depth.age_seconds ?? 0)}s
        </div>
      )}
      <header className="depth-meta">
        <span>{book.source_kind === "binance_rest" ? "BINANCE L2" : "IMPORTED L2"}</span>
        <small>{new Date(book.captured_at).toLocaleTimeString(english ? "en-US" : "zh-CN", { hour12: false })}</small>
      </header>
      <div className="depth-columns"><span>{l("Price", "价格")} ({quoteCurrency})</span><span>{l("Size", "数量")}</span><span>{l("Total", "累计")}</span></div>
      <DepthRows levels={book.asks} maximum={maximum} priceScale={priceScale} side="ask" />
      <div className="depth-spread">
        <strong>{Number(book.midpoint).toFixed(priceScale)}</strong>
        <span>{l("Spread", "价差")} {Number(book.spread).toFixed(priceScale)}</span>
      </div>
      <DepthRows levels={book.bids} maximum={maximum} priceScale={priceScale} side="bid" />
      <footer>{l("Point-in-time snapshot constrained by the replay frame", "只展示不晚于当前回放帧的时点快照")}</footer>
    </section>
  );
}
