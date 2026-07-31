import type { LocalPreferences } from "@replaytutor/contracts";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArchiveRestore, DatabaseBackup, ShieldCheck, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";
import { fetchHealth } from "../api/health";
import {
  cleanupAgentRuns,
  createBackup,
  fetchMaintenance,
  fetchPreferences,
  restoreBackup,
  savePreferences,
} from "../api/localSystem";
import { discoverCodex } from "../api/tutor";

export function SettingsPage() {
  const queryClient = useQueryClient();
  const health = useQuery({ queryKey: ["health-detail"], queryFn: () => fetchHealth() });
  const codex = useQuery({ queryKey: ["codex-capability"], queryFn: discoverCodex });
  const preferences = useQuery({ queryKey: ["local-preferences"], queryFn: fetchPreferences });
  const maintenance = useQuery({ queryKey: ["maintenance"], queryFn: fetchMaintenance });
  const [draft, setDraft] = useState<LocalPreferences | null>(null);
  useEffect(() => {
    if (preferences.data) setDraft(preferences.data);
  }, [preferences.data]);
  const save = useMutation({
    mutationFn: savePreferences,
    onSuccess: (value) => {
      queryClient.setQueryData(["local-preferences"], value);
      setDraft(value);
    },
  });
  const backup = useMutation({
    mutationFn: createBackup,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["maintenance"] }),
  });
  const restore = useMutation({
    mutationFn: restoreBackup,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["maintenance"] }),
  });
  const cleanup = useMutation({
    mutationFn: cleanupAgentRuns,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["maintenance"] }),
  });

  return (
    <section className="page settings-page">
      <div className="page-kicker">PREFERENCES & SAFETY</div>
      <h1>本地设置与恢复</h1>
      <div className="settings-grid">
        <article><ShieldCheck size={20} /><h2>Codex Tutor</h2><dl><div><dt>可执行文件</dt><dd>{codex.data?.executable ?? "未找到"}</dd></div><div><dt>版本</dt><dd>{codex.data?.version ?? "—"}</dd></div><div><dt>状态</dt><dd>{codex.data?.available ? "可运行" : "不可用"}</dd></div><div><dt>权限</dt><dd>read-only · ephemeral</dd></div></dl></article>
        <article><h2>确定性系统</h2><dl><div><dt>数据库</dt><dd>{health.data?.database.status ?? "检查中"}</dd></div><div><dt>迁移</dt><dd>{health.data?.database.migration_current ?? "—"}</dd></div><div><dt>行情目录</dt><dd>{health.data?.data.path ?? "—"}</dd></div><div><dt>网络绑定</dt><dd>127.0.0.1</dd></div></dl></article>
      </div>
      {draft && (
        <form className="settings-form" onSubmit={(event) => { event.preventDefault(); save.mutate(draft); }}>
          <div><div className="page-kicker">TRAINING PREFERENCES</div><h2>训练与隐私</h2></div>
          <label>AI 模式<select onChange={(event) => setDraft({ ...draft, ai_mode: event.target.value as "codex" | "off" })} value={draft.ai_mode}><option value="codex">Codex Tutor</option><option value="off">关闭 AI</option></select></label>
          <label>Agent 运行目录保留天数<input min="1" max="365" onChange={(event) => setDraft({ ...draft, retain_agent_runs_days: Number(event.target.value) })} type="number" value={draft.retain_agent_runs_days} /></label>
          <label className="check-row"><input checked={draft.confirm_before_finish} onChange={(event) => setDraft({ ...draft, confirm_before_finish: event.target.checked })} type="checkbox" /><span><strong>结束会话前确认</strong><small>偏好保存在本地 SQLite。</small></span></label>
          <div className="inline-notice">隐私模式固定为 local_only；设置、行情、账户和 Tutor 证据不会由应用上传。</div>
          <button className="primary-action" disabled={save.isPending} type="submit">保存本地偏好</button>
        </form>
      )}
      <section className="maintenance-panel">
        <div className="review-section-heading"><div><div className="page-kicker">RECOVERABLE MAINTENANCE</div><h2>备份与清理</h2></div><button className="secondary-action" disabled={backup.isPending} onClick={() => backup.mutate()} type="button"><DatabaseBackup size={14} />创建数据库备份</button></div>
        <p>恢复前会自动再创建一份备份。Agent 清理只移动到本地回收目录。</p>
        <div className="backup-list">
          {maintenance.data?.backups.map((item) => (
            <div key={item.backup_id}><code>{item.backup_id}</code><span>{(item.size_bytes / 1024).toFixed(1)} KB · {item.sha256.slice(0, 10)}</span><button disabled={restore.isPending} onClick={() => { if (window.confirm("恢复会替换当前数据库，继续吗？")) restore.mutate(item.backup_id); }} type="button"><ArchiveRestore size={13} />恢复</button></div>
          ))}
          {!maintenance.isLoading && maintenance.data?.backups.length === 0 && <div className="panel-empty">还没有本地备份。</div>}
        </div>
        <button className="secondary-action" disabled={cleanup.isPending} onClick={() => cleanup.mutate()} type="button"><Trash2 size={13} />清理过期 Agent 运行目录</button>
        {cleanup.data && <small>已移动 {cleanup.data.moved_agent_runs} 个目录到回收站。</small>}
      </section>
      <div className="inline-notice">Codex 不参与撮合、账本或确定性指标。失败时回放和模拟交易继续可用。</div>
    </section>
  );
}
