import { useQuery } from "@tanstack/react-query";
import { ShieldCheck } from "lucide-react";
import { fetchHealth } from "../api/health";
import { discoverCodex } from "../api/tutor";

export function SettingsPage() {
  const health = useQuery({ queryKey: ["health-detail"], queryFn: () => fetchHealth() });
  const codex = useQuery({ queryKey: ["codex-capability"], queryFn: discoverCodex });
  return <section className="page settings-page"><div className="page-kicker">PREFERENCES & SAFETY</div><h1>本地运行状态</h1><div className="settings-grid"><article><ShieldCheck size={20} /><h2>Codex Tutor</h2><dl><div><dt>可执行文件</dt><dd>{codex.data?.executable ?? "未找到"}</dd></div><div><dt>版本</dt><dd>{codex.data?.version ?? "—"}</dd></div><div><dt>状态</dt><dd>{codex.data?.available ? "可运行" : "不可用"}</dd></div><div><dt>权限</dt><dd>read-only · ephemeral</dd></div></dl></article><article><h2>确定性系统</h2><dl><div><dt>数据库</dt><dd>{health.data?.database.status ?? "检查中"}</dd></div><div><dt>迁移</dt><dd>{health.data?.database.migration_current ?? "—"}</dd></div><div><dt>行情目录</dt><dd>{health.data?.data.path ?? "—"}</dd></div><div><dt>网络绑定</dt><dd>127.0.0.1</dd></div></dl></article></div><div className="inline-notice">Codex 不参与撮合、账本或确定性指标。失败时回放和模拟交易继续可用。</div></section>;
}
