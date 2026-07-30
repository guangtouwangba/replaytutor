import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Database, Download, FileUp, RefreshCw } from "lucide-react";
import { useState } from "react";
import { fetchBars, fetchDatasets, loadGoldenDataset, stageDatasetImport } from "../api/datasets";

export function DataCenterPage() {
  const queryClient = useQueryClient();
  const datasets = useQuery({ queryKey: ["datasets"], queryFn: fetchDatasets });
  const [selected, setSelected] = useState<string | null>(null);
  const [previewMessage, setPreviewMessage] = useState<string | null>(null);
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

      {(golden.isError || upload.isError) && <div className="inline-error">{golden.error?.message ?? upload.error?.message}</div>}
      {previewMessage && <div className="inline-notice">导入预览已完成：{previewMessage}。确认字段与市场参数后才会生成 Snapshot。</div>}

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
              <div className="inspector-title"><div><span>RAW OHLCV</span><strong>{bars.data?.bars[0]?.open_time.slice(0, 10) ?? "读取中"}</strong></div><code>{activeId}</code></div>
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
