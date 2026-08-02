import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Database, Download, FileUp, RefreshCw, Trash2 } from "lucide-react";
import { useState } from "react";
import {
  deleteDatasetSnapshot,
  fetchDatasetDownloadJobs,
  fetchBars,
  fetchDatasets,
  loadGoldenDataset,
  stageDatasetImport,
  startBinanceDatasetDownload,
} from "../api/datasets";

export function DataCenterPage() {
  const queryClient = useQueryClient();
  const datasets = useQuery({ queryKey: ["datasets"], queryFn: fetchDatasets });
  const downloadJobs = useQuery({
    queryKey: ["dataset-downloads"],
    queryFn: fetchDatasetDownloadJobs,
    refetchInterval: (query) => query.state.data?.jobs.some(
      (job) => job.status === "queued" || job.status === "running",
    ) ? 1_000 : false,
  });
  const [selected, setSelected] = useState<string | null>(null);
  const [previewMessage, setPreviewMessage] = useState<string | null>(null);
  const [symbol, setSymbol] = useState("BTCUSDT");
  const [marketType, setMarketType] = useState<"SPOT" | "USDT_PERPETUAL">("USDT_PERPETUAL");
  const [startTime, setStartTime] = useState("2025-01-01T00:00");
  const [endTime, setEndTime] = useState("2025-01-03T00:00");
  const activeId = selected ?? datasets.data?.datasets[0]?.snapshot_id ?? null;
  const bars = useQuery({
    queryKey: ["bars", activeId],
    queryFn: () => fetchBars(activeId!, 20),
    enabled: activeId !== null,
  });
  const golden = useMutation({
    mutationFn: loadGoldenDataset,
    onSuccess: async (snapshot) => {
      setSelected(snapshot.snapshot_id);
      await queryClient.invalidateQueries({ queryKey: ["datasets"] });
    },
  });
  const upload = useMutation({
    mutationFn: stageDatasetImport,
    onSuccess: (preview) => setPreviewMessage(
      `${preview.filename}: ${preview.quality.row_count} 行，质量 ${preview.quality.status}`,
    ),
  });
  const download = useMutation({
    mutationFn: () => startBinanceDatasetDownload({
      symbol,
      market_type: marketType,
      timeframe: "1m",
      start_time: new Date(`${startTime}:00Z`).toISOString(),
      end_time: new Date(`${endTime}:00Z`).toISOString(),
    }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["dataset-downloads"] });
    },
  });
  const removeSnapshot = useMutation({
    mutationFn: deleteDatasetSnapshot,
    onSuccess: async (result) => {
      setSelected(null);
      queryClient.removeQueries({ queryKey: ["bars", result.snapshot_id] });
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["datasets"] }),
        queryClient.invalidateQueries({ queryKey: ["dataset-downloads"] }),
      ]);
    },
  });

  return (
    <section className="page data-page">
      <header className="page-header">
        <div><div className="page-kicker">MARKET DATA</div><h1>数据中心</h1><p>只读、版本化的真实行情快照。更新永远生成新版本。</p></div>
        <div className="header-actions">
          <label className="secondary-action file-action"><FileUp size={15} />预览 CSV / Parquet<input type="file" accept=".csv,.parquet" onChange={(event) => { const file = event.target.files?.[0]; if (file) upload.mutate(file); }} /></label>
          <button className="primary-action" type="button" disabled={golden.isPending} onClick={() => golden.mutate()}>
            {golden.isPending ? <RefreshCw className="spin" size={15} /> : <Download size={15} />}载入真实 BTC 样例
          </button>
        </div>
      </header>

      {(golden.isError || upload.isError || removeSnapshot.isError) && <div className="inline-error">{golden.error?.message ?? upload.error?.message ?? removeSnapshot.error?.message}</div>}
      {previewMessage && <div className="inline-notice">导入预览已完成：{previewMessage}。确认字段与市场参数后才会生成 Snapshot。</div>}
      <section className="dataset-download-card">
        <div><strong>Binance 行情下载</strong><small>现货与 USDT 永续会保存为不同、不可变的 Snapshot。</small></div>
        <label>品种<input onChange={(event) => setSymbol(event.target.value.toUpperCase())} value={symbol} /></label>
        <label>市场<select onChange={(event) => setMarketType(event.target.value as typeof marketType)} value={marketType}><option value="USDT_PERPETUAL">USDT 永续</option><option value="SPOT">现货</option></select></label>
        <label>开始 UTC<input onChange={(event) => setStartTime(event.target.value)} type="datetime-local" value={startTime} /></label>
        <label>结束 UTC<input onChange={(event) => setEndTime(event.target.value)} type="datetime-local" value={endTime} /></label>
        <button className="secondary-action" disabled={download.isPending} onClick={() => download.mutate()} type="button">{download.isPending ? "正在提交…" : "后台生成 Snapshot"}</button>
      </section>
      {download.isError && <div className="inline-error">{download.error.message}</div>}
      {download.isSuccess && <div className="inline-notice">下载任务已进入后台。你可以切换到其他页面，顶部会持续显示进度。</div>}
      {(downloadJobs.data?.jobs.length ?? 0) > 0 && (
        <section className="download-job-list" aria-label="行情下载任务">
          {downloadJobs.data?.jobs.slice(0, 4).map((job) => (
            <div className={`download-job-row is-${job.status}`} key={job.job_id}>
              <span><strong>{job.symbol} · {job.market_type === "USDT_PERPETUAL" ? "U 本位永续" : "现货"}</strong><small>{job.start_time.slice(0, 10)} 至 {job.end_time.slice(0, 10)}</small></span>
              <span><b>{job.status === "succeeded" ? "已完成" : job.status === "failed" ? "失败" : `${Math.round(job.progress * 100)}%`}</b><small>{job.error ?? (job.status === "succeeded" ? "Snapshot 已可用" : "后台运行，可离开本页")}</small></span>
            </div>
          ))}
        </section>
      )}

      <div className="data-layout">
        <aside className="snapshot-list">
          <div className="panel-title"><Database size={15} />Snapshots <span>{datasets.data?.datasets.length ?? 0}</span></div>
          {datasets.data?.datasets.map((snapshot) => (
            <button key={snapshot.snapshot_id} className={`snapshot-item ${activeId === snapshot.snapshot_id ? "is-active" : ""}`} type="button" onClick={() => setSelected(snapshot.snapshot_id)}>
              <span><strong>{snapshot.instrument.canonical_symbol}</strong><small>{snapshot.source_kind.replaceAll("_", " ")}</small></span>
              <span><b>{snapshot.quality.row_count.toLocaleString()}</b><small>1m bars</small></span>
            </button>
          ))}
          {!datasets.isLoading && datasets.data?.datasets.length === 0 && <div className="panel-empty">尚无 Snapshot</div>}
        </aside>

        <div className="data-inspector">
          {!activeId && <div className="large-empty"><Database size={30} /><h2>载入第一份真实行情</h2><p>内置样例来自 Binance 公开 BTCUSDT 1 分钟历史数据，共 44,640 根。</p></div>}
          {activeId && (
            <>
              <div className="inspector-title"><div><span>RAW OHLCV</span><strong>{bars.data?.bars[0]?.open_time.slice(0, 10) ?? "读取中"}</strong></div><div className="inspector-actions"><code>{activeId}</code><button className="snapshot-delete" disabled={removeSnapshot.isPending} onClick={() => { if (window.confirm("删除这个 Snapshot？已被训练会话使用的 Snapshot 不允许删除；文件会先移入本地回收目录。")) removeSnapshot.mutate(activeId); }} type="button"><Trash2 size={13} />删除 Snapshot</button></div></div>
              <div className="bar-table-wrap"><table className="bar-table"><thead><tr><th>UTC 时间</th><th>开</th><th>高</th><th>低</th><th>收</th><th>成交量</th></tr></thead><tbody>
                {bars.data?.bars.map((bar) => <tr key={bar.bar_id}><td>{bar.open_time.replace("T", " ").slice(0, 19)}</td><td>{bar.raw.open}</td><td>{bar.raw.high}</td><td>{bar.raw.low}</td><td>{bar.raw.close}</td><td>{bar.raw.volume}</td></tr>)}
              </tbody></table></div>
              {bars.isLoading && <div className="table-loading">正在从本地 Parquet 查询…</div>}
            </>
          )}
        </div>
      </div>
    </section>
  );
}
