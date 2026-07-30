# ReplayTutor（暂定名）

一个本地优先的交易训练与复盘应用：提供类似 TradingView 的专业图表体验、隐藏未来的历史回放、确定性虚拟交易，以及通过本机 Codex CLI 工作的证据化 AI Tutor。

> 当前阶段：MVP 1A 的 BTCUSDT 核心纵向闭环已落地，包括 Snapshot、逐 K 回放、计划门禁、模拟订单、Decimal 账本、用户/AI 图层、确定性复盘、Playbook 和 Codex Tutor。完整绘图、证据回跳、AI 标注接受/拒绝、Playbook 确定性规则检查和发布级 E2E 仍待封板。Binance U 本位只读成交复盘作为独立切片保留。本项目不提供任何真实下单能力。

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
- 数据中心：<http://127.0.0.1:5173/data>
- 训练复盘：<http://127.0.0.1:5173/reviews>
- Binance 复盘：<http://127.0.0.1:5173/reviews/binance>

常用入口：

```bash
make api         # 只启动 FastAPI
make web         # 只启动 Vite
make migrate     # 幂等升级 SQLite
make verify      # contracts → lint → typecheck → test → build
make clean       # 只清构建缓存，不删除 data/ 和 logs/
```

`make verify` 是当前可执行的工程质量门，覆盖契约、静态检查、前后端单元测试和生产构建。发布计划中的完整浏览器 E2E 尚未接入根命令，不能用 `make verify` 代替发布验收。

首次启动后打开“数据中心”，点击“载入真实 BTC 样例”。系统会把仓库内经过哈希校验的 44,640 根 BTCUSDT 1m Golden Dataset 写成运行时不可变 Snapshot；首页不会用假价格或随机 K 线填充空状态。

数据 API：

```text
GET  /api/v1/datasets
POST /api/v1/datasets/golden
POST /api/v1/datasets/binance
GET  /api/v1/datasets/{snapshot_id}/bars
POST /api/v1/datasets/imports
POST /api/v1/datasets/imports/{import_id}/commit
POST /api/v1/sessions
POST /api/v1/sessions/{session_id}/commands
POST /api/v1/sessions/{session_id}/plan
POST /api/v1/sessions/{session_id}/orders
POST /api/v1/sessions/{session_id}/annotations
POST /api/v1/sessions/{session_id}/tutor
GET  /api/v1/sessions/{session_id}/review
```

重新生成跨端契约或核验 Golden Dataset：

```bash
pnpm contracts:update
uv run --project apps/api replaytutor data build-golden
```

Binance 只读复盘：

```bash
replaytutor binance check
replaytutor binance sync --days 180
replaytutor review today
replaytutor review recent --count 10
replaytutor review trade <episode_id>
```

凭据只从知识库的 `tools/config.json` 读取。同步器只实现 Binance 签名 `GET`，复盘产物不会保存 Key、Secret、签名或私有下载地址。

本地覆盖配置复制 `.env.example` 为 `.env`；所有服务端配置使用 `REPLAYTUTOR_` 前缀。Vite 与 FastAPI 都固定监听 loopback，端口被占用时直接失败。

如果当前终端没有继承 nvm、pnpm 或 uv 的 PATH，可先检查项目解析结果：

```bash
make runtime
```

无需全局启用 pnpm；`make` 会通过 `scripts/pnpm` 调用 Corepack。若 Node 24 尚未安装，脚本会给出明确的 `nvm install 24` 提示。

M0 Spike 仍可通过以下方式复现：

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

MVP 1A 只接入 Codex CLI。A 股规则、其他 Agent、现货/币本位真实成交、美股、外汇和跨周期报告属于后续阶段。

MVP 不包含真实下单、跟单、收益承诺、社交社区和 Pine Script 兼容层。

当前已知产品缺口：

- 工作台只支持当前价格标记，趋势线、矩形及完整编辑操作尚未开放。
- AI 标注写入独立图层，但接受、拒绝和修改工作流尚未实现。
- 复盘证据已有稳定 ID，但点击回跳到 K 线、价格和图层尚未实现。
- Playbook 已版本化，逐条确定性规则检查仍待实现。
- 设置页当前以运行状态和安全边界展示为主，训练偏好、隐私和清理功能尚未开放。
- A 股规则、其他市场、发布硬化和完整浏览器 E2E 属于后续阶段。

## 工作原则

- 图表可以模仿 TradingView 的信息架构和效率，但不复制其品牌、图标或受保护资源。
- 市场规则不是 UI 特例：交易日历、T+1、涨跌停、最小报价单位、每手数量都由市场规则模块统一执行。
- AI 不决定盈亏真相；盈亏、成交、MFE/MAE 和规则违规由确定性引擎计算，AI 只解释有证据的数据。
- “当时教学”和“事后复盘”严格分开，避免未来函数和后见之明污染训练。
- 原始成交与行情数据保留来源、时间和版本，任何 AI 结论都能追溯。
