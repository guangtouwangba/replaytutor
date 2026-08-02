import type { DataSnapshot } from "@replaytutor/contracts";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowRight, Database, DownloadCloud, HardDrive, Shuffle, Target } from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate, useSearchParams } from "react-router-dom";
import { fetchDatasetDownloadJobs, fetchDatasets, startBinanceDatasetDownload } from "../api/datasets";
import { fetchPlaybooks } from "../api/playbooks";
import { createSession } from "../api/sessions";

type MarketType = "SPOT" | "USDT_PERPETUAL";
type HistoryDays = 30 | 365;
type StartMode = "beginning" | "random" | "specific";

const WARMUP_BARS = 120;
const ONE_MINUTE_MS = 60_000;

const TRAINING_SYMBOLS = [
  { symbol: "BTCUSDT", label: "BTC / USDT" },
  { symbol: "ETHUSDT", label: "ETH / USDT" },
] as const;
const HISTORY_RANGES: { days: HistoryDays; labelKey: string; barsKey: string }[] = [
  { days: 30, labelKey: "setup.range30", barsKey: "setup.bars30" },
  { days: 365, labelKey: "setup.range365", barsKey: "setup.bars365" },
];

export function selectLocalSnapshot(
  snapshots: DataSnapshot[],
  symbol: string,
  marketType: MarketType,
  requiredDays: HistoryDays,
  selectedSnapshotId?: string,
): DataSnapshot | undefined {
  const assetClass = marketType === "USDT_PERPETUAL" ? "crypto_perpetual" : "crypto_spot";
  const requiredCoverageMs = requiredDays * 24 * 60 * 60 * 1000 - 60_000;
  const candidates = snapshots
    .filter((snapshot) => (
      snapshot.instrument.canonical_symbol === symbol
      && snapshot.instrument.asset_class === assetClass
      && snapshot.timeframe === "1m"
      && snapshot.quality.status !== "failed"
      && snapshot.quality.row_count > WARMUP_BARS
    ))
    .sort((left, right) => Date.parse(right.created_at) - Date.parse(left.created_at));
  const selected = candidates.find((snapshot) => snapshot.snapshot_id === selectedSnapshotId);
  if (selected) return selected;
  return candidates.find((snapshot) => (
    Date.parse(snapshot.coverage_end) - Date.parse(snapshot.coverage_start) >= requiredCoverageMs
  ));
}

export function selectableLocalSnapshots(
  snapshots: DataSnapshot[],
  symbol: string,
  marketType: MarketType,
): DataSnapshot[] {
  const assetClass = marketType === "USDT_PERPETUAL" ? "crypto_perpetual" : "crypto_spot";
  return snapshots
    .filter((snapshot) => (
      snapshot.instrument.canonical_symbol === symbol
      && snapshot.instrument.asset_class === assetClass
      && snapshot.timeframe === "1m"
      && snapshot.quality.status !== "failed"
      && snapshot.quality.row_count > WARMUP_BARS
    ))
    .sort((left, right) => Date.parse(right.created_at) - Date.parse(left.created_at));
}

function toDatetimeLocal(timestamp: number): string {
  return new Date(timestamp).toISOString().slice(0, 16);
}

function specificStartBounds(snapshot?: DataSnapshot) {
  if (!snapshot) return null;
  const minimum = Date.parse(snapshot.coverage_start) + (WARMUP_BARS - 1) * ONE_MINUTE_MS;
  const maximum = Date.parse(snapshot.coverage_end) - ONE_MINUTE_MS;
  if (!Number.isFinite(minimum) || !Number.isFinite(maximum) || minimum > maximum) return null;
  const midpoint = Math.floor((minimum + maximum) / (2 * ONE_MINUTE_MS)) * ONE_MINUTE_MS;
  return {
    min: toDatetimeLocal(minimum),
    max: toDatetimeLocal(maximum),
    defaultValue: toDatetimeLocal(Math.min(maximum, Math.max(minimum, midpoint))),
  };
}

export function automaticDownloadRange(
  now: Date,
  historyDays: HistoryDays = 30,
): { start_time: string; end_time: string } {
  const end = new Date(now);
  end.setUTCSeconds(0, 0);
  const start = new Date(end.getTime() - historyDays * 24 * 60 * 60 * 1000);
  return { start_time: start.toISOString(), end_time: end.toISOString() };
}

export function SessionSetupPage() {
  const { t, i18n } = useTranslation();
  const locale = i18n.resolvedLanguage?.startsWith("zh") ? "zh-CN" : "en-US";
  const playbookName = (slug: string, fallback: string) => locale === "zh-CN" ? fallback : ({
    "trend-pullback": "Trend Pullback",
    "breakout-retest": "Breakout Retest",
    "range-reversal": "Range Reversal",
  }[slug] ?? fallback);
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [searchParams] = useSearchParams();
  const datasets = useQuery({ queryKey: ["datasets"], queryFn: fetchDatasets });
  const downloadJobs = useQuery({
    queryKey: ["dataset-downloads"],
    queryFn: fetchDatasetDownloadJobs,
    refetchInterval: (query) => query.state.data?.jobs.some(
      (job) => job.status === "queued" || job.status === "running",
    ) ? 1_000 : false,
  });
  const playbooks = useQuery({ queryKey: ["playbooks"], queryFn: fetchPlaybooks });
  const [symbol, setSymbol] = useState("BTCUSDT");
  const [marketType, setMarketType] = useState<MarketType>("USDT_PERPETUAL");
  const [historyDays, setHistoryDays] = useState<HistoryDays>(30);
  const [selectedSnapshotId, setSelectedSnapshotId] = useState(() => searchParams.get("snapshot_id") ?? "");
  const [startMode, setStartMode] = useState<StartMode>("beginning");
  const [selectedStartTime, setSelectedStartTime] = useState("");
  const [hiddenRealDate, setHiddenRealDate] = useState(true);
  const [playbookId, setPlaybookId] = useState("");
  const [initialCash, setInitialCash] = useState("100000");
  const [leverage, setLeverage] = useState(10);
  const [marginMode, setMarginMode] = useState<"ISOLATED" | "CROSS">("ISOLATED");
  const [positionMode, setPositionMode] = useState<"ONEWAY" | "HEDGE">("ONEWAY");
  const latestOfficialPlaybooks = playbooks.data?.playbooks.filter(
    (item, _, all) => item.official && !all.some(
      (candidate) => candidate.slug === item.slug && candidate.version > item.version,
    ),
  ) ?? [];
  const activePlaybook = playbooks.data?.playbooks.find(
    (item) => item.playbook_id === (
      playbookId
      || searchParams.get("playbook_id")
      || latestOfficialPlaybooks[0]?.playbook_id
    ),
  );
  const availableSnapshots = selectableLocalSnapshots(
    datasets.data?.datasets ?? [], symbol, marketType,
  );
  const recommendedSnapshot = selectLocalSnapshot(
    availableSnapshots, symbol, marketType, historyDays,
  );
  const activeSnapshot = availableSnapshots.find(
    (snapshot) => snapshot.snapshot_id === selectedSnapshotId,
  );
  const startBounds = specificStartBounds(activeSnapshot);
  const effectiveStartTime = selectedStartTime && startBounds
    && selectedStartTime >= startBounds.min && selectedStartTime <= startBounds.max
    ? selectedStartTime
    : startBounds?.defaultValue ?? "";
  const perpetual = marketType === "USDT_PERPETUAL";
  const matchingJob = downloadJobs.data?.jobs.find((job) => (
    job.symbol === symbol
    && job.market_type === marketType
    && job.total_bars === historyDays * 24 * 60
    && (job.status === "queued" || job.status === "running")
  ));
  const download = useMutation({
    mutationFn: () => startBinanceDatasetDownload({
      symbol,
      market_type: marketType,
      timeframe: "1m",
      ...automaticDownloadRange(new Date(), historyDays),
    }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["dataset-downloads"] });
    },
  });
  const create = useMutation({
    mutationFn: () => createSession({
        snapshot_id: activeSnapshot!.snapshot_id,
        start_mode: startMode,
        start_time: startMode === "specific"
          ? new Date(`${effectiveStartTime}:00Z`).toISOString()
          : null,
        seed: 7,
        warmup_bars: WARMUP_BARS,
        initial_cash: initialCash,
        hidden_real_date: hiddenRealDate,
        playbook_id: activePlaybook?.playbook_id ?? null,
        account_type: perpetual ? "USDT_PERPETUAL" : "SPOT",
        margin_mode: marginMode,
        position_mode: positionMode,
        leverage: perpetual ? leverage : 1,
      }),
    onSuccess: (delta) => navigate(`/sessions/${delta.session.session_id}`),
  });

  const actionLabel = create.isPending
    ? t("setup.creating")
    : activeSnapshot
      ? activePlaybook
        ? t("setup.startLocal")
        : t("setup.loading")
      : availableSnapshots.length > 0
        ? t("setup.selectSnapshotRequired")
      : matchingJob
        ? t("setup.downloadingProgress", { progress: Math.round(matchingJob.progress * 100) })
        : download.isPending
          ? t("setup.submitting")
          : t("setup.downloadAction");

  return (
    <section className="page setup-page">
      <header className="page-header">
        <div>
          <div className="page-kicker">NEW TRAINING SESSION</div>
          <h1>{t("setup.title")}</h1>
          <p>{t("setup.description")}</p>
        </div>
      </header>

      <ol className="setup-progress" aria-label={t("setup.stepsLabel")}>
        <li className={activeSnapshot ? "is-complete" : "is-current"}><span>1</span><div><strong>{t("setup.chooseInstrument")}</strong><small>{t("setup.localFirst")}</small></div></li>
        <li className={activeSnapshot ? (activePlaybook ? "is-complete" : "is-current") : ""}><span>2</span><div><strong>{t("setup.bindPlaybook")}</strong><small>{t("setup.defineConstraints")}</small></div></li>
        <li className={activeSnapshot && activePlaybook ? "is-current" : ""}><span>3</span><div><strong>{t("setup.startTraining")}</strong><small>{t("setup.noLookaheadWorkbench")}</small></div></li>
      </ol>

      <div className="setup-layout">
        <div className="setup-form">
          <section className="setup-section">
            <div className="setup-section-title"><Database size={16} /><span>{t("setup.instrumentData")}</span></div>
            <div className="segmented setup-symbols" aria-label={t("setup.trainingInstrument")}>
              {TRAINING_SYMBOLS.map((item) => (
                <button className={symbol === item.symbol ? "is-active" : ""} key={item.symbol} onClick={() => { setSymbol(item.symbol); setSelectedSnapshotId(""); setSelectedStartTime(""); }} type="button">
                  {item.label}
                </button>
              ))}
            </div>
            <div className="segmented setup-market-type" aria-label={t("setup.marketType")}>
              <button className={marketType === "USDT_PERPETUAL" ? "is-active" : ""} onClick={() => { setMarketType("USDT_PERPETUAL"); setSelectedSnapshotId(""); setSelectedStartTime(""); }} type="button">{t("setup.usdtPerpetual")}</button>
              <button className={marketType === "SPOT" ? "is-active" : ""} onClick={() => { setMarketType("SPOT"); setSelectedSnapshotId(""); setSelectedStartTime(""); }} type="button">{t("setup.spot")}</button>
            </div>
            <div className="setup-range-label"><span>{t("setup.historyRange")}</span><small>{t("setup.default30")}</small></div>
            <div className="segmented setup-history-range" aria-label={t("setup.historyRange")}>
              {HISTORY_RANGES.map((range) => (
                <button className={historyDays === range.days ? "is-active" : ""} key={range.days} onClick={() => setHistoryDays(range.days)} type="button">
                  <strong>{t(range.labelKey)}</strong><small>{t(range.barsKey)}</small>
                </button>
              ))}
            </div>

            {datasets.isLoading && <div className="inline-notice data-resolution"><Database size={15} /><span><strong>{t("setup.checkingLocal")}</strong><small>{t("setup.readingIndex")}</small></span></div>}
            {datasets.isError && <div className="inline-error">{t("setup.localError", { message: datasets.error.message })}</div>}
            {!datasets.isLoading && !datasets.isError && availableSnapshots.length > 0 && (
              <>
                <div className="setup-snapshot-picker">
                  <div className="setup-snapshot-heading">
                    <span><strong>{t("setup.snapshotVersion")}</strong><small>{t("setup.selectSnapshotHint")}</small></span>
                    <b>{availableSnapshots.length}</b>
                  </div>
                  <div aria-label={t("setup.snapshotVersion")} className="setup-snapshot-options" role="radiogroup">
                    {availableSnapshots.map((snapshot) => {
                      const selected = snapshot.snapshot_id === selectedSnapshotId;
                      const recommended = snapshot.snapshot_id === recommendedSnapshot?.snapshot_id;
                      return (
                        <button
                          aria-checked={selected}
                          className={selected ? "snapshot-choice is-active" : "snapshot-choice"}
                          key={snapshot.snapshot_id}
                          onClick={() => {
                            setSelectedSnapshotId(snapshot.snapshot_id);
                            setSelectedStartTime("");
                          }}
                          role="radio"
                          type="button"
                        >
                          <span className="snapshot-choice-main">
                            <strong>{snapshot.coverage_start.slice(0, 10)} → {snapshot.coverage_end.slice(0, 10)}</strong>
                            <small>{snapshot.quality.row_count.toLocaleString(locale)} bars · {snapshot.quality.status}</small>
                          </span>
                          <span className="snapshot-choice-meta">
                            {recommended && <em>{t("setup.snapshotRecommended")}</em>}
                            <code>{snapshot.snapshot_id.slice(-12)}</code>
                            <small>{new Date(snapshot.created_at).toLocaleString(locale, { hour12: false })}</small>
                          </span>
                        </button>
                      );
                    })}
                  </div>
                </div>
                {!activeSnapshot && <div className="inline-notice data-resolution is-selection-required">
                  <Database size={15} />
                  <span><strong>{t("setup.selectSnapshotRequired")}</strong><small>{t("setup.selectSnapshotBeforeConfig")}</small></span>
                </div>}
                {activeSnapshot && <div className="inline-notice data-resolution is-local">
                  <HardDrive size={15} />
                  <span>
                    <strong>{t("setup.localHit")}</strong>
                    <small>{t("setup.localCoverage", { count: activeSnapshot.quality.row_count, start: activeSnapshot.coverage_start.slice(0, 10), end: activeSnapshot.coverage_end.slice(0, 10) })}</small>
                    <code>{activeSnapshot.snapshot_id} · {t("setup.snapshotCreated", { date: new Date(activeSnapshot.created_at).toLocaleString(locale, { hour12: false }) })}</code>
                  </span>
                </div>}
              </>
            )}
            {!datasets.isLoading && !datasets.isError && availableSnapshots.length === 0 && (
              <div className="inline-notice data-resolution">
                <DownloadCloud size={15} />
                <span><strong>{matchingJob ? t("setup.downloading") : t("setup.localMissing")}</strong><small>{matchingJob ? t("setup.downloadingHint", { progress: Math.round(matchingJob.progress * 100) }) : t("setup.downloadHint", { range: t(historyDays === 365 ? "setup.range365" : "setup.range30") })}</small></span>
              </div>
            )}
          </section>

          {activeSnapshot ? <>
          <section className="setup-section setup-section-revealed">
            <div className="setup-section-title"><Target size={16} /><span>{t("setup.accountRisk")}</span></div>
            <div className="constraint-grid">
              <label><small>{t("setup.initialEquity")}</small><input min="1" onChange={(event) => setInitialCash(event.target.value)} step="1" type="number" value={initialCash} /></label>
              <span><small>{t("setup.accountType")}</small><strong>{perpetual ? t("setup.usdtPerpetual") : t("setup.spot")}</strong></span>
            </div>
            {perpetual && <>
              <label>{t("setup.leverage")} · {leverage}×<input max="125" min="1" onChange={(event) => setLeverage(Number(event.target.value))} type="range" value={leverage} /></label>
              <div className="segmented">
                <button className={marginMode === "ISOLATED" ? "is-active" : ""} onClick={() => setMarginMode("ISOLATED")} type="button">{t("setup.isolated")}</button>
                <button className={marginMode === "CROSS" ? "is-active" : ""} onClick={() => setMarginMode("CROSS")} type="button">{t("setup.cross")}</button>
              </div>
              <div className="segmented">
                <button className={positionMode === "ONEWAY" ? "is-active" : ""} onClick={() => setPositionMode("ONEWAY")} type="button">{t("setup.oneway")}</button>
                <button className={positionMode === "HEDGE" ? "is-active" : ""} onClick={() => setPositionMode("HEDGE")} type="button">{t("setup.hedge")}</button>
              </div>
              <p className="inline-notice">{t("setup.deterministicRisk")}</p>
            </>}
          </section>

          <section className="setup-section">
            <div className="setup-section-title"><Shuffle size={16} /><span>{t("setup.startBlind")}</span></div>
            <div className="segmented setup-start-modes">
              <button className={startMode === "beginning" ? "is-active" : ""} onClick={() => setStartMode("beginning")} type="button">{t("setup.fromBeginning")}</button>
              <button className={startMode === "specific" ? "is-active" : ""} onClick={() => { setStartMode("specific"); setHiddenRealDate(false); }} type="button">{t("setup.specificTime")}</button>
              <button className={startMode === "random" ? "is-active" : ""} onClick={() => setStartMode("random")} type="button">{t("setup.randomSegment")}</button>
            </div>
            {startMode === "specific" && startBounds && (
              <label className="setup-start-time">
                <small>{t("setup.replayStartTime")}</small>
                <input
                  aria-label={t("setup.replayStartTime")}
                  max={startBounds.max}
                  min={startBounds.min}
                  onChange={(event) => setSelectedStartTime(event.target.value)}
                  type="datetime-local"
                  value={effectiveStartTime}
                />
                <span>{t("setup.replayStartHint", { start: startBounds.min.replace("T", " "), end: startBounds.max.replace("T", " ") })}</span>
              </label>
            )}
            <label className="check-row">
              <input checked={hiddenRealDate} onChange={(event) => setHiddenRealDate(event.target.checked)} type="checkbox" />
              <span><strong>{t("setup.hideDate")}</strong><small>{t("setup.hideDateHint")}</small></span>
            </label>
          </section>

          <section className="setup-section">
            <div className="setup-section-title"><Target size={16} /><span>{t("setup.constraints")}</span></div>
            <div className="segmented">
              {latestOfficialPlaybooks.map((item) => <button className={activePlaybook?.playbook_id === item.playbook_id ? "is-active" : ""} key={item.playbook_id} onClick={() => setPlaybookId(item.playbook_id)} type="button">{playbookName(item.slug, item.name)}</button>)}
            </div>
            <div className="constraint-grid">
              <span><small>{t("setup.playbook")}</small><strong>{activePlaybook ? `${playbookName(activePlaybook.slug, activePlaybook.name)} · v${activePlaybook.version}` : t("setup.loading")}</strong></span>
              <span><small>{t("setup.initialCapital")}</small><strong>{Number(initialCash || 0).toLocaleString(locale)} USDT</strong></span>
              <span><small>{t("setup.warmup")}</small><strong>{WARMUP_BARS} bars</strong></span>
              <span><small>{t("setup.aiMode")}</small><strong>{t("setup.codexConnected")}</strong></span>
            </div>
          </section>
          </> : !datasets.isLoading && availableSnapshots.length > 0 ? (
            <section className="setup-section setup-locked-sections" aria-live="polite">
              <HardDrive size={18} />
              <div><strong>{t("setup.configurationLocked")}</strong><p>{t("setup.selectSnapshotBeforeConfig")}</p></div>
            </section>
          ) : null}
        </div>

        <aside className="setup-summary">
          <div className="page-kicker">SESSION CONTRACT</div>
          <h2>{symbol}</h2>
          <p>{t("setup.contractHint")}</p>
          <dl>
            <div><dt>{t("setup.market")}</dt><dd>{perpetual ? t("setup.binancePerpetual") : t("setup.binanceSpot")}</dd></div>
            <div><dt>{t("setup.data")}</dt><dd>{activeSnapshot ? t("setup.localSnapshot", { start: activeSnapshot.coverage_start.slice(0, 10), end: activeSnapshot.coverage_end.slice(0, 10) }) : availableSnapshots.length > 0 ? t("setup.selectSnapshotRequired") : t("setup.autoDownload", { range: t(historyDays === 365 ? "setup.range365" : "setup.range30") })}</dd></div>
            {activeSnapshot && <div><dt>Snapshot</dt><dd><code>{activeSnapshot.snapshot_id.slice(-12)}</code></dd></div>}
            <div><dt>{t("setup.replayStart")}</dt><dd>{!activeSnapshot ? "—" : startMode === "specific" ? `${effectiveStartTime.replace("T", " ")} UTC` : startMode === "random" ? t("setup.randomSegment") : activeSnapshot.coverage_start.slice(0, 16).replace("T", " ")}</dd></div>
            <div><dt>{t("setup.rules")}</dt><dd>{perpetual ? "binance_usdm_perpetual_v1" : "crypto_spot_v1"}</dd></div>
            <div><dt>{t("setup.quality")}</dt><dd>{activeSnapshot?.quality.status ?? t("setup.verifyAfterDownload")}</dd></div>
          </dl>
          {(download.isError || create.isError) && <div className="inline-error">{t("setup.prepareFailed", { message: download.error?.message ?? create.error?.message })}</div>}
          <button
            className="primary-action setup-submit"
            disabled={datasets.isLoading || datasets.isError || (Boolean(activeSnapshot) && (playbooks.isLoading || !activePlaybook)) || create.isPending || download.isPending || Boolean(matchingJob) || (availableSnapshots.length > 0 && !activeSnapshot) || (startMode === "specific" && !effectiveStartTime)}
            onClick={() => activeSnapshot ? create.mutate() : availableSnapshots.length === 0 ? download.mutate() : undefined}
            type="button"
          >
            {actionLabel}<ArrowRight size={15} />
          </button>
        </aside>
      </div>
    </section>
  );
}
