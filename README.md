# ReplayTutor（暂定名）

一个本地优先、面向多市场的交易训练与复盘应用：提供类似 TradingView 的专业图表体验，支持 A 股、美股、加密货币和外汇历史回放、虚拟交易，以及可绑定 Codex、Claude Code、Kimi 等原生 Coding Agent 的 AI Tutor。

> 当前阶段：M0 本地基础设施已经落地，回放、撮合、账本和 Tutor 业务功能尚未实现，也不连接真实资金账户。

## 核心体验

```text
版本化历史数据 → 图表与逐根回放 → 虚拟买卖 → 交易过程留痕
                                             ↓
                                  AI Tutor 解释、追问、复盘
                                             ↓
                                 单笔 / 每日 / 每周改进报告
```

## 设计文档

- [视觉与交互设计系统](DESIGN.md)
- [产品与交互设计](docs/DESIGN.md)
- [系统架构](docs/SYSTEM_ARCHITECTURE.md)
- [Coding Agent 绑定规范](docs/AGENT_BINDING.md)
- [MVP v1 实施计划](docs/MVP_IMPLEMENTATION_PLAN.md)

## 本地开发

要求：Node 24、Corepack、uv 和 GNU Make。项目自带运行时解析脚本：会从 nvm 加载 Node 24，由 Corepack 按 `packageManager` 固定 pnpm 11.9.0，并查找常见位置中的 uv。Python 3.12 由 uv 安装与固定，不使用系统 Python。

```bash
make setup
make dev
```

启动后访问：

- Web：<http://127.0.0.1:5173>
- API：<http://127.0.0.1:8788>
- Health：<http://127.0.0.1:8788/api/v1/health>

常用入口：

```bash
make api         # 只启动 FastAPI
make web         # 只启动 Vite
make migrate     # 幂等升级 SQLite
make verify      # contracts → lint → typecheck → test → build
make clean       # 只清构建缓存，不删除 data/ 和 logs/
```

本地覆盖配置复制 `.env.example` 为 `.env`；所有服务端配置使用 `REPLAYTUTOR_` 前缀。Vite 与 FastAPI 都固定监听 loopback，端口被占用时直接失败。

如果当前终端没有继承 nvm、pnpm 或 uv 的 PATH，可先检查项目解析结果：

```bash
make runtime
```

无需全局启用 pnpm；`make` 会通过 `scripts/pnpm` 调用 Corepack。若 Node 24 尚未安装，脚本会给出明确的 `nvm install 24` 提示。

M0 Spike 可通过以下方式复现：

```bash
# 固定 BTCUSDT K 线与订单线创建/选择/拖动/删除
make dev
open 'http://127.0.0.1:5173/?spike=kline'

# Agent 权限探测；默认 dry-run，显式 --execute 才调用本机 CLI
python3 scripts/agent-isolation-probe.py
python3 scripts/agent-isolation-probe.py --execute
```

Spike 决策见 [`docs/decisions/`](docs/decisions/)。

## MVP 边界

首个可用版本采用纵向切片，先把时间安全和确定性跑通：

1. BTCUSDT 固定历史快照、单图和 1 分钟周期。
2. 历史数据逐根回放，整套 UI 受同一个 `visible_at` 约束。
3. 市价单、限价单、止损市价单和虚拟持仓/P&L。
4. 成交点、仓位变化、笔记和事件留痕。
5. 右侧 Codex Tutor：当下讲解和单笔事后复盘。
6. Golden Session、未来数据诱饵、撮合确定性和账本平衡门禁。

第一条切片稳定后接入 A 股规则与 Claude Code；真实成交导入、美股、外汇和周期报告属于后续阶段。

MVP 不包含真实下单、跟单、收益承诺、社交社区和 Pine Script 兼容层。

## 工作原则

- 图表可以模仿 TradingView 的信息架构和效率，但不复制其品牌、图标或受保护资源。
- 市场规则不是 UI 特例：交易日历、T+1、涨跌停、最小报价单位、每手数量都由市场规则模块统一执行。
- AI 不决定盈亏真相；盈亏、成交、MFE/MAE 和规则违规由确定性引擎计算，AI 只解释有证据的数据。
- “当时教学”和“事后复盘”严格分开，避免未来函数和后见之明污染训练。
- 原始成交与行情数据保留来源、时间和版本，任何 AI 结论都能追溯。
