# ADR 0002：本地 Agent 隔离 Spike

状态：Accepted with constraints  
日期：2026-07-19

## 问题

需要区分 `prompt_only`、`workspace_read_only` 与 `host_read_only`，并验证 CLI 的工作目录参数是否真的构成读取隔离。不能把 `--cd`、cwd 或“只读”误认为“只能读取工作区”。

## 可复现探测

`scripts/agent-isolation-probe.py` 在一次性目录中创建工作区 canary 和工作区外诱饵，调用 CLI 后只输出读取结果布尔值。脚本使用 Codex `--ephemeral --sandbox read-only` 和 Claude `--no-session-persistence --safe-mode`，不使用危险权限，不保存模型输出、提示词或认证信息。

```bash
python3 scripts/agent-isolation-probe.py             # 无副作用 dry-run
python3 scripts/agent-isolation-probe.py --execute   # 显式运行探测
uv run --project apps/api pytest tests/backend/test_agent_isolation_probe.py
```

2026-07-19 本机结果：

| Agent | prompt_only | workspace_read_only | host_read_only |
|---|---|---|---|
| Codex CLI 0.139.0 | 通过 | 不安全：工作区和外部诱饵均可读 | 禁用 |
| Claude Code 2.1.211 | 认证阻塞：组织禁用订阅访问 | 认证阻塞，未形成隔离结论 | 禁用 |

## 决策

1. M0 健康检查只做 executable 探测，不触发联网认证。
2. `prompt_only` 不提供交易文件或工具，作为后续 Tutor 的默认候选模式。
3. Codex 的 `--sandbox read-only --cd` 仅限制写入并设置工作目录，不满足目录级读取隔离；在引入独立 OS 沙箱前，不启用其 `workspace_read_only`。
4. Claude 的两种模式保持不可用，直到用户修复本机认证后重新运行同一探测。
5. 所有 `host_read_only` Adapter 默认禁用，不能以 `--cd`、cwd 或只读权限作为启用依据。

Spike 未传入行情、订单、账本或 Tutor 数据，也未创建 Agent 会话持久化文件。
