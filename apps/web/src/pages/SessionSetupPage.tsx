import { useMutation, useQuery } from "@tanstack/react-query";
import { ArrowRight, Database, Shuffle, Target } from "lucide-react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { fetchDatasets } from "../api/datasets";
import { fetchPlaybooks } from "../api/playbooks";
import { createSession } from "../api/sessions";

export function SessionSetupPage() {
  const navigate = useNavigate();
  const datasets = useQuery({ queryKey: ["datasets"], queryFn: fetchDatasets });
  const playbooks = useQuery({ queryKey: ["playbooks"], queryFn: fetchPlaybooks });
  const [snapshotId, setSnapshotId] = useState("");
  const [startMode, setStartMode] = useState<"beginning" | "random">("beginning");
  const [hiddenRealDate, setHiddenRealDate] = useState(true);
  const [playbookId, setPlaybookId] = useState("");
  const activePlaybook = playbooks.data?.playbooks.find(
    (item) => item.playbook_id === (playbookId || playbooks.data?.playbooks[0]?.playbook_id),
  );
  const activeSnapshotId = snapshotId || datasets.data?.datasets[0]?.snapshot_id || "";
  const activeSnapshot = datasets.data?.datasets.find(
    (snapshot) => snapshot.snapshot_id === activeSnapshotId,
  );
  const create = useMutation({
    mutationFn: createSession,
    onSuccess: (delta) => navigate(`/sessions/${delta.session.session_id}`),
  });

  return (
    <section className="page setup-page">
      <header className="page-header">
        <div>
          <div className="page-kicker">NEW TRAINING SESSION</div>
          <h1>训练配置</h1>
          <p>首个纵向切片使用真实 BTCUSDT Snapshot；所有市场进度由服务端签发。</p>
        </div>
      </header>

      <div className="setup-layout">
        <div className="setup-form">
          <section className="setup-section">
            <div className="setup-section-title"><Database size={16} /><span>行情 Snapshot</span></div>
            {datasets.isLoading && <div className="panel-empty">正在读取 Snapshot…</div>}
            {datasets.isError && <div className="inline-error">{datasets.error.message}</div>}
            {datasets.data?.datasets.map((snapshot) => (
              <button
                className={`setup-choice ${activeSnapshotId === snapshot.snapshot_id ? "is-selected" : ""}`}
                key={snapshot.snapshot_id}
                onClick={() => setSnapshotId(snapshot.snapshot_id)}
                type="button"
              >
                <span><strong>{snapshot.instrument.canonical_symbol}</strong><small>{snapshot.source_id}</small></span>
                <span><b>{snapshot.quality.row_count.toLocaleString()}</b><small>1m bars</small></span>
              </button>
            ))}
            {!datasets.isLoading && datasets.data?.datasets.length === 0 && (
              <div className="inline-notice">尚无可训练 Snapshot，请先到数据中心载入真实 BTC 样例。</div>
            )}
          </section>

          <section className="setup-section">
            <div className="setup-section-title"><Shuffle size={16} /><span>起点与盲测</span></div>
            <div className="segmented">
              <button className={startMode === "beginning" ? "is-active" : ""} onClick={() => setStartMode("beginning")} type="button">从数据开头</button>
              <button className={startMode === "random" ? "is-active" : ""} onClick={() => setStartMode("random")} type="button">随机片段</button>
            </div>
            <label className="check-row">
              <input checked={hiddenRealDate} onChange={(event) => setHiddenRealDate(event.target.checked)} type="checkbox" />
              <span><strong>隐藏真实日期</strong><small>结束会话后才揭示完整覆盖区间。</small></span>
            </label>
          </section>

          <section className="setup-section">
            <div className="setup-section-title"><Target size={16} /><span>本次训练约束</span></div>
            <div className="segmented">
              {playbooks.data?.playbooks.filter((item) => item.official).map((item) => <button className={activePlaybook?.playbook_id === item.playbook_id ? "is-active" : ""} key={item.playbook_id} onClick={() => setPlaybookId(item.playbook_id)} type="button">{item.name}</button>)}
            </div>
            <div className="constraint-grid">
              <span><small>策略</small><strong>{activePlaybook ? `${activePlaybook.name} · v${activePlaybook.version}` : "载入中"}</strong></span>
              <span><small>初始资金</small><strong>100,000 USDT</strong></span>
              <span><small>预热窗口</small><strong>120 bars</strong></span>
              <span><small>AI 模式</small><strong>Codex · 已接入</strong></span>
            </div>
          </section>
        </div>

        <aside className="setup-summary">
          <div className="page-kicker">SESSION CONTRACT</div>
          <h2>{activeSnapshot?.instrument.canonical_symbol ?? "等待行情"}</h2>
          <p>客户端只提交 Snapshot、随机种子和训练参数，不能指定 visible_at。</p>
          <dl>
            <div><dt>市场</dt><dd>{activeSnapshot?.instrument.market ?? "—"}</dd></div>
            <div><dt>规则</dt><dd>{activeSnapshot?.instrument.market_rule_set_id ?? "—"}</dd></div>
            <div><dt>质量</dt><dd>{activeSnapshot?.quality.status ?? "—"}</dd></div>
          </dl>
          {create.isError && <div className="inline-error">{create.error.message}</div>}
          <button
            className="primary-action setup-submit"
            disabled={!activeSnapshotId || create.isPending}
            onClick={() => create.mutate({
              snapshot_id: activeSnapshotId,
              start_mode: startMode,
              seed: 7,
              warmup_bars: 120,
              initial_cash: "100000",
              hidden_real_date: hiddenRealDate,
              playbook_id: activePlaybook?.playbook_id ?? null,
            })}
            type="button"
          >
            {create.isPending ? "正在创建…" : "创建训练会话"}<ArrowRight size={15} />
          </button>
        </aside>
      </div>
    </section>
  );
}
