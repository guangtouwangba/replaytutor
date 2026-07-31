# ReplayTutor 产品化实施计划 v2

状态：MVP 1A core implemented; product UX hardening pending; W6 deferred
日期：2026-07-31
目标：把现有 M0/M1 数据与真实成交复盘能力，推进为可完成训练闭环的 ReplayTutor MVP 1A。

上游真源：

- [视觉设计](../../DESIGN.md)
- [产品与交互设计](../DESIGN.md)
- [系统架构](../SYSTEM_ARCHITECTURE.md)
- [Agent 绑定规范](../AGENT_BINDING.md)
- [MVP 范围与系统不变量](../MVP_IMPLEMENTATION_PLAN.md)
- [产品规划 v2](2026-07-30-replaytutor-product-plan-v2.md)
- [全页面交互设计](2026-07-30-replaytutor-page-interaction-design.md)
- [可点击原型](../prototypes/replaytutor-product-prototype.html)

后续封板计划：

- [MVP 1A 封板实施计划](2026-07-31-replaytutor-mvp1a-hardening-plan.md)

## 1. 实施结论

不按 13 个页面横向开发。第一优先级是一条可以被测试、恢复和复盘的纵向闭环：

```text
选择固定策略与 BTCUSDT 数据
  → 创建训练会话
  → 在 visible_at 边界内逐 K 回放
  → 用户先画图并锁定交易计划
  → 提交虚拟订单
  → 确定性撮合、账本和风险反馈
  → 结束会话
  → 查看证据化复盘
  → AI 在用户图层之上回应
```

首个可用版本只做：

- BTCUSDT 现货、1m 原始数据，前端可切换服务端派生的 5m/15m。
- 固定 Golden Dataset 和“趋势回调”官方 Playbook。
- 市价、限价、止损市价和一个 bracket/OCO 组合。
- 单账户、单持仓方向、无杠杆、无裸空。
- 强制交易计划卡、用户/AI/策略三层图表标注。
- 会话完成页、单会话复盘和 evidence 回跳。
- Codex Tutor；Agent 不可用时仍能完成确定性训练闭环。

首个可用版本暂不做：

- A 股规则、Codex 之外的 Agent Adapter、完整策略学院内容系统。
- 真实交易同步与训练账户混用。
- 多图布局、移动端交易、社区、云同步、真实下单。
- 任意策略脚本、自动回测、AI 自主改订单或改账本。

## 2. 当前基线

### 2.1 已完成，可直接复用

| 能力 | 当前实现 | 复用方式 |
|---|---|---|
| 本地应用基线 | React/Vite/TS + FastAPI + SQLite WAL | 保持单机双进程拓扑 |
| 契约链 | Pydantic → JSON Schema → TypeScript/Ajv | 所有新增跨端模型继续走生成链 |
| 市场数据 | Golden/File/Binance Adapter、Parquet、DuckDB | Replay 只能通过 Session 解析窗口调用，不能开放自由查询 |
| 固定数据集 | BTCUSDT 2025-01，44,640 根 1m K 线 | 作为第一条 Golden Session |
| 图表验证 | `ChartAdapter`、KLineChart 订单线 Spike | 扩展为 K 线、可见边界和三类 Overlay |
| 真实成交复盘 | Fill → Episode → 价格行为标注 → HTML | 复用证据结构和图表标注语义，不复用私有交易流程 |
| 质量门禁 | contracts、lint、typecheck、pytest、vitest、build | 每个任务完成后保持 `make verify` 全绿 |

2026-07-30 基线验证：

- 前端：2 个测试文件，4 个测试通过。
- 后端：21 个测试通过。
- `make verify` 通过。
- 已知警告：前端生产包约 670 kB，后续页面路由必须 lazy load。

### 2.2 当前剩余缺口

- 完整趋势线、矩形绘制及选择、修改、删除操作；当前只开放价格标记。
- 独立笔记和计划修改历史、会话软删除与回收。
- AI 标注接受、拒绝和修改工作流。
- Playbook 逐条确定性规则检查。
- 复盘 evidence 点击回跳到 K 线、价格、frame 和图层。
- 工作台 5m/15m 派生周期、完整 cancel-and-replace。
- 首页弱项推荐、足量样本后的能力评分、净值曲线和训练时间线。
- 设置中的训练偏好、隐私、数据清理和救援操作。
- 发布级 Playwright/axe E2E、恢复矩阵、性能与构建脱敏验收。

## 3. 模块与 seam

接口必须小，复杂性留在深模块内部。调用者和测试通过同一个接口使用模块。

### 3.1 Training Session Module

外部接口：

```python
create(spec: CreateSessionSpec) -> SessionSnapshot
get(session_id: str) -> SessionSnapshot
apply(command: SessionCommand) -> SessionDelta
finish(session_id: str, expected_revision: int) -> CompletedSession
```

Implementation 内部负责：

- session lock、revision、command idempotency。
- `frame_id` 签发和 `visible_at` 解析。
- 调用 Replay、Execution、Ledger 和 Evidence Review。
- 一个事务中提交 command、事件、账户快照与 revision。

不把 repository、lock 或 transaction 暴露给路由层。

### 3.2 Replay Core

这是纯计算的 in-process module，不额外制造 adapter：

```python
initialize(snapshot, seed, start_policy) -> ReplayState
advance(state, bars: int) -> ReplayTransition
visible_window(state, timeframe, limit) -> VisibleFrame
```

硬约束：

- 客户端不能提交 `visible_at`。
- `frame_id` 必须绑定 session、revision、当前 bar。
- 任何返回对象在序列化前再做一次未来数据扫描。
- 当前完整 K 线出现后提交的订单，只能从下一根开盘激活。

### 3.3 Paper Execution Module

```python
submit(state, order_intent, rules) -> OrderDecision
on_bar(state, bar, rules) -> ExecutionTransition
cancel(state, order_id) -> OrderTransition
```

Implementation 内部处理订单状态机、保守同柱路径、bracket/OCO 和 Decimal。AI 与前端不参与成交计算。

### 3.4 Market Rules seam

这里存在至少两个真实 adapter，因此保留 seam：

```python
validate_order(intent, account, instrument, at) -> RuleDecision
fees(fill, account, instrument, at) -> FeeBreakdown
settlement(fill, account, instrument, at) -> SettlementEffects
```

Adapters：

- `CryptoSpotRules`：MVP 1A 生产实现。
- `CnCashEquityRules`：MVP 1B 实现。
- `FakeRules`：属性测试。

市场差异不得进入 React 页面或 Training Session 条件分支。

### 3.5 Ledger Module

```python
record_fill(account_state, fill, fee) -> LedgerTransition
rebuild(events) -> AccountSnapshot
```

每个 fill 生成可平衡 journal。持仓、现金、费用与 P&L 都能从事件重建；缓存快照只是加速，不是真源。

### 3.6 Evidence Review Module

```python
complete(session_id) -> DeterministicReview
evidence(session_id, evidence_id) -> EvidenceTarget
```

负责 MFE、MAE、R、费用、计划遵守、用户修改记录和图表定位。它不依赖 Agent，保证 Agent 离线时仍有完整复盘。

### 3.7 Tutor 与 Agent Runtime

Tutor 外部接口：

```python
ask(session_id, frame_id, question) -> TutorRun
review(session_id) -> TutorRun
```

Agent Runtime seam：

```python
discover() -> list[AgentCapability]
run(spec: AgentRunSpec) -> AgentRunHandle
cancel(run_id: str) -> None
```

Adapters：

- `CodexAdapter`：MVP 1A。
- `FakeAgentAdapter`：测试。
- `ClaudeAdapter`：Post-MVP 预留，不进入当前实施计划。

Tutor 只能消费经过物理裁剪的证据包，只能输出：

- 结构化文字结论。
- 有效 evidence ID。
- 白名单图形指令：`line`、`zone`、`marker`、`label`、`path`。

它不能提交订单、修改 session、Ledger、市场数据或用户图层。

## 4. 契约与数据库演进

### 4.1 第一批新增契约

在 `apps/api/replaytutor/contracts.py` 新增并生成前端类型：

- `CreateSessionSpec`
- `ReplaySession`
- `ReplayFrame`
- `VisibleFrame`
- `SessionCommand`
- `SessionDelta`
- `OrderIntent`
- `Order`
- `Execution`
- `AccountSnapshot`
- `TradePlan`
- `ChartAnnotation`
- `CompletedSession`
- `DeterministicReview`
- `EvidenceRef`
- `TutorRun`
- `TutorResponse`
- `AgentCapability`

规则：

- 时间全部 UTC ISO 8601。
- 金额、价格、数量、费用继续使用 Decimal 字符串。
- 命令必须带 `command_id` 和 `expected_revision`。
- `SessionDelta` 必须返回最新 revision、frame、事件和账户快照。
- 图形指令只能引用本次证据包中的时间与价格。

### 4.2 Alembic 顺序

| Migration | 内容 | 所属里程碑 |
|---|---|---|
| `0004_training_session` | sessions、session_commands、session_events、replay_frames | W1 |
| `0005_execution_ledger` | orders、executions、ledger_entries、account_snapshots | W2 |
| `0006_training_review` | trade_plans、annotations、notes、deterministic_reviews、evidence_refs | W3 |
| `0007_tutor` | agent_runs、tutor_messages、tutor_artifacts | W4 |
| `0008_playbooks` | playbooks、playbook_versions、session_playbook_bindings | W5 |

迁移必须从空库和 `0003_trade_review` 两种起点验收。训练表与真实成交复盘表保持独立，不共享 order/fill 真源。

## 5. 开发波次

## W0：锁定基线与前端骨架

目标：把高保真原型拆成生产路由和可复用布局，但所有未接后端的动作明确禁用。

任务：

| ID | 工作 | 主要文件 |
|---|---|---|
| W0-01 | 建立 `app/router`、lazy routes、Query 错误边界 | `apps/web/src/app/*`、`App.tsx` |
| W0-02 | 将全局 CSS Token 和壳层拆为共享 UI | `shared/styles/*`、`shell/*` |
| W0-03 | 建立 Today、Academy、Setup、Workbench、Complete、Reviews、Playbooks、Sessions、Settings 路由 | `features/*/pages` |
| W0-04 | 新建 Workbench Dock Layout，接入现有 KLineChart Spike | `features/workbench/*`、`features/chart/*` |
| W0-05 | 为未交付功能统一提供 `UnavailableState`，不使用假数据 | `shared/ui/*` |

退出条件：

- 所有 13 个页面都可进入，但只有已实现能力可操作。
- `/workbench` 使用 lazy chunk，生产包不再把所有页面放进同一个主 chunk。
- 1180、1440、1920 三个宽度无主要内容遮挡。
- 键盘能到达一级导航、页面主操作和 modal。

## W1：Session + Replay 纵向切片

目标：用户可以从固定 BTCUSDT 数据创建、推进、关闭并恢复一个没有未来数据泄露的训练会话。

状态（2026-07-30）：已完成。契约、`0004_training_session`、Replay Core、Session REST、Setup/Workbench、revision 冲突与恢复均已落地；`make verify` 通过，真实浏览器完成“创建 → 推进 → 刷新恢复”验收。

任务：

| ID | 工作 | 主要文件 |
|---|---|---|
| W1-01 | 新增 session/replay 契约与生成类型 | `contracts.py`、`packages/contracts/*` |
| W1-02 | 新增 `0004_training_session` | `apps/api/alembic/versions/*` |
| W1-03 | 实现纯 Replay Core | `modules/replay/*` |
| W1-04 | 实现 Training Session Module 与事务协调 | `modules/training_session/*` |
| W1-05 | 新增 `/sessions` REST 路由 | `routes/sessions.py` |
| W1-06 | 实现 Setup 页面，只开放固定 Golden Dataset | `features/session-setup/*` |
| W1-07 | Workbench 接入可见 K 线、边界、播放/暂停/逐根/速度 | `features/replay/*`、`features/chart/*` |
| W1-08 | 实现关闭重开恢复与 revision 冲突恢复 | 前后端 session 模块 |

关键测试：

- `future_bait`：未来区放置唯一诱饵值，任何回放响应都不能出现。
- 相同 fingerprint 的 frame/event hash 一致。
- 重复 `command_id` 返回原结果，不推进第二次。
- 旧 revision 返回 409，客户端拉取最新快照。
- kill API 后重启，session 恢复到最后提交的 revision。
- 20× 播放时前端最多一个未完成 advance 请求。

退出条件：

> 一个真实用户可以完成“配置 → 回放 → 关闭浏览器 → 恢复 → 继续回放”，且没有订单功能也没有未来泄露。

## W2：强制计划 + Paper Execution + Ledger

目标：用户必须先说明计划，再提交虚拟订单；所有成交和账户结果可确定性重建。

状态（2026-07-31）：核心完成、交互未封板。已交付 `0005_execution_ledger`、计划服务端门禁、Crypto Spot 规则、市价/限价/止损市价下一根激活与撮合、Decimal Ledger/journal、bracket/OCO、待成交订单取消、订单与成交 Overlay、工作台交易计划和订单票据。完整 cancel-and-replace、图上拖动改价和完整用户绘图仍待实现。

任务：

| ID | 工作 | 主要文件 |
|---|---|---|
| W2-01 | 新增订单、成交、账户契约和 `0005_execution_ledger` | contracts、migration |
| W2-02 | 实现 `CryptoSpotRules` | `modules/market_rules/*` |
| W2-03 | 实现订单状态机和 K 线级撮合 | `modules/execution/*` |
| W2-04 | 实现 Ledger、账户重建和风险预算 | `modules/ledger/*` |
| W2-05 | 将 TradePlan 作为下单前服务端门禁 | `modules/training_session/*` |
| W2-06 | 实现工作台交易计划卡、订单票据和图表订单线 | `features/orders/*`、`features/trade-plan/*` |
| W2-07 | 实现底部订单/成交/持仓面板 | `features/portfolio/*` |

关键测试：

- 当前柱看完后提交市价单，只在下一根开盘成交。
- 限价、止损、跳空和同柱止盈/止损采用明确的保守路径。
- bracket 父单未成交前子单不激活；一侧成交后另一侧 OCO 取消。
- Decimal、tick、step、最小名义金额和费用规则。
- 相同命令只产生一次订单和一次 journal。
- 每个事务 journal 平衡；从空状态重建后与缓存快照相同。
- 没有锁定计划时后端拒绝订单，而不仅是前端禁用按钮。

退出条件：

> 用户可以在同一张图完成“先画 → 写计划 → 锁定 → 下单 → 管理 → 退出”，刷新页面后订单、持仓和账户完全一致。

## W3：会话完成 + 确定性证据复盘

目标：即使没有 AI，用户也能得到可信的计划与执行复盘。

状态（2026-07-31）：核心完成、证据交互未封板。会话结束状态机、完成/会话库/复盘页面、确定性 MFE/MAE/R/费用/回撤/退出效率、稳定 review hash 和 evidence ID 已交付。独立笔记、计划修改历史、会话软删除以及 evidence 点击回跳仍待实现。

任务：

| ID | 工作 | 主要文件 |
|---|---|---|
| W3-01 | 新增计划、标注、review、evidence 契约和 migration | contracts、`0006_training_review` |
| W3-02 | 持久化用户绘图、笔记和计划修改历史 | `modules/training_session/*` |
| W3-03 | 实现 MFE、MAE、R、费用、回撤和退出效率 | `modules/analytics/*` |
| W3-04 | 实现 Evidence Review Module | `modules/evidence_review/*` |
| W3-05 | 实现结束会话状态机与完整行情解锁 | `routes/sessions.py` |
| W3-06 | 实现 Complete、Sessions、Review Detail 页面 | `features/sessions/*`、`features/reviews/*` |
| W3-07 | 点击证据后定位时间、价格、frame 和图层 | `features/chart/selectionBridge.ts` |

关键测试：

- `finish` 之前不能查询 MFE/MAE、最终 P&L 或未来行情。
- `finish` 幂等；完成后不能再下单或 advance。
- 盈利但违反计划必须显示为坏过程，亏损但遵守计划可显示为好过程。
- evidence ID 100% 可解析到订单、成交、计划、标注或 bar。
- 删除/修改图表 viewport 不改变 review hash。
- Session 列表可以继续未完成会话并只读打开已完成会话。

退出条件：

> 不安装任何 Agent，也能完成从训练到证据复盘的产品闭环。

## W4：AI 共画 Tutor，形成内部 Alpha

目标：AI 依据当时环境和用户策略提出问题、生成白名单标注，并能在图上与用户对照。

状态（2026-07-31）：核心完成、协作工作流未封板。TutorContext 物理裁剪、Codex/Fake Adapter、结构与证据校验、运行状态/取消/SSE、回放中与事后 Tutor、AI 独立图层和 provenance 已交付。AI 标注接受/拒绝/修改、完整阶段式 Dock 以及发布级失败矩阵 E2E 仍待实现。

任务：

| ID | 工作 | 主要文件 |
|---|---|---|
| W4-01 | 新增 Tutor/Agent 契约与 `0007_tutor` | contracts、migration |
| W4-02 | 实现证据包构建与物理裁剪 | `modules/tutor/context.py` |
| W4-03 | 实现 Agent Runtime、Fake Adapter 和 Codex Adapter | `modules/agent_runtime/*`、`adapters/agents/*` |
| W4-04 | 实现 Schema、evidence 和图形指令校验 | `modules/tutor/validation.py` |
| W4-05 | 实现 Agent run 状态、取消、超时和 SSE | `routes/tutor.py` |
| W4-06 | 实现 AI Dock：环境/计划/持仓/退出四阶段 | `features/tutor/*` |
| W4-07 | 实现接受、修改、追问与图层 provenance | `features/chart/*`、`features/tutor/*` |
| W4-08 | 会话完成后生成 AI review，并与确定性事实分栏 | `features/reviews/*` |

关键测试：

- 回放证据包中不存在未来 bar、最终结果、MFE/MAE 或后续成交。
- 非法 JSON、额外字段、无效 evidence ID 和越界坐标被拒绝。
- AI 图形只能写 AI 图层；用户图层不可变。
- Codex 未安装、未认证、超时、取消、崩溃时回放与交易继续工作。
- SSE 断线后可按 run ID 恢复最终结果。
- Agent workspace 不含数据库、凭据、主目录软链接或未授权文件。

退出条件：

> 内部用户可以在 5–8 分钟内体验“用户先画，AI 再回应”，并清楚区分用户判断、AI 推断、确定性事实和未知项。

## W5：产品页面与学习闭环

目标：把内部 Alpha 从工程闭环变成每日可重复使用的 MVP 1A。

状态（2026-07-31）：部分完成。首页真实数据/空状态、首次引导、策略学院、训练配置、会话库、复盘中心、Playbook 版本化和设置状态页已交付。首页弱项推荐、Playbook 确定性规则检查、足量样本评分与净值时间线、设置偏好/隐私/清理仍待实现。

任务：

| ID | 工作 |
|---|---|
| W5-01 | Today 页面：继续会话、推荐训练、最近弱项 |
| W5-02 | Academy 与 Strategy Detail：先只发布趋势回调、突破回踩、区间反转 |
| W5-03 | Playbook 版本化和策略规则检查 |
| W5-04 | Reviews 聚合页和能力雷达；不生成无样本统计 |
| W5-05 | Settings：训练偏好、AI 模式、隐私和目录状态 |
| W5-06 | 首次引导：固定片段、产品说明和引导完成状态 |

退出条件：

- 首页所有数字来自真实 session 或明确空状态。
- Playbook 修改生成新版本，历史 session 继续引用旧版本。
- 能力雷达低样本维度显示“不足”，不伪造分数。
- 三个官方策略都能创建训练，但仍只使用确定性规则和人工检查。

## W6：MVP 1B 与发布硬化

在 MVP 1A 通过真实用户试用后再启动：

- A 股 File Import、交易日历、T+1、100 股整手、涨跌停和费用。
- Codex Adapter 的兼容性、恢复、隔离和错误救援硬化。
- 1180/1440/1920、键盘、axe、性能和 bundle 分包。
- 崩溃、断电、数据库迁移、备份恢复、日志脱敏和孤儿进程清理。
- 本地启动器、版本信息、已知限制和完整 E2E。

## 6. 页面交付映射

| 页面 | 首次可用 | 完整状态 |
|---|---|---|
| 首次引导 | W4 | W5 |
| 今日训练 | W1 最小入口 | W5 |
| 策略学院 | W0 空状态 | W5 |
| 策略详情 | W0 静态说明 | W5 |
| 训练配置 | W1 | W5 |
| 回放工作台 | W1 | W4 |
| 会话完成 | W3 | W4 |
| 复盘中心 | W3 最小列表 | W5 |
| 复盘详情 | W3 | W4 |
| Playbook | W0 空状态 | W5 |
| 会话库 | W3 | W5 |
| 数据中心 | 已完成 | W6 硬化 |
| 设置 | W0 状态页 | W5 |

## 7. HTTP 接口顺序

W1：

```text
POST   /sessions
GET    /sessions
GET    /sessions/{session_id}
POST   /sessions/{session_id}/commands
POST   /sessions/{session_id}/finish
```

W2：

```text
POST   /sessions/{session_id}/plan
POST   /sessions/{session_id}/orders
DELETE /sessions/{session_id}/orders/{order_id}
GET    /sessions/{session_id}/portfolio
```

W3：

```text
POST   /sessions/{session_id}/annotations
POST   /sessions/{session_id}/notes
GET    /sessions/{session_id}/review
GET    /sessions/{session_id}/evidence/{evidence_id}
DELETE /sessions/{session_id}
```

W4：

```text
GET    /agents
POST   /tutor/runs
GET    /tutor/runs/{run_id}
GET    /tutor/runs/{run_id}/events
DELETE /tutor/runs/{run_id}
```

所有写请求需要 request ID；会改变 session 事实的请求同时需要 `command_id` 或等价幂等键。

## 8. 测试金字塔与 Golden Sessions

### 8.1 纯模块测试

- Replay 状态转换与 fingerprint。
- Execution 订单状态机与歧义路径。
- Market Rules 的 tick、step、fee、settlement。
- Ledger 平衡与事件重建。
- Analytics 与证据解析。
- Tutor context 裁剪和输出校验。

### 8.2 SQLite 集成测试

- 每个 migration 从空库与上一版本升级。
- command、order、fill、journal、revision 在一个事务中提交。
- duplicate command、409 revision、finish idempotency。
- kill/restart 恢复。

### 8.3 前端交互测试

- Setup 表单错误和数据质量阻断。
- 播放器单飞队列。
- 计划未锁定时下单门禁。
- 用户/AI/策略图层开关与 provenance。
- 完成 modal、复盘 evidence 回跳和错误降级。

### 8.4 Browser E2E

至少固定三条：

1. `golden_no_trade`：创建 → 回放 → 不交易 → 完成 → review。
2. `golden_planned_long`：画区间 → 锁定计划 → bracket long → OCO → 完成。
3. `golden_restart_and_agent_failure`：中途重启 → 恢复 → Codex 失败 → 继续完成。

每条保存：

- session fingerprint。
- command/event stream hash。
- 最终 account hash。
- deterministic review hash。
- 截图：Setup、Workbench、Complete、Review。

## 9. 每个任务的 Definition of Done

一个任务只有同时满足以下条件才算完成：

- 契约先更新，生成物无漂移。
- 新的成功、空、错误、重试和恢复状态都有实现。
- 后端拒绝非法状态，不依赖前端按钮禁用。
- 相关测试覆盖成功路径和至少一个失败路径。
- `make verify` 通过。
- 涉及核心闭环时，相应 Browser E2E 通过。
- 没有新增未来数据泄露面、二进制浮点真源或 AI 写交易事实的路径。
- 文档真源同步更新，不只更新页面代码。

## 10. 实施顺序与并行边界

关键路径：

```text
W0 骨架
  → W1 Session/Replay
  → W2 Plan/Execution/Ledger
  → W3 Deterministic Review
  → W4 AI Tutor
  → W5 Product Loop
  → W6 MVP 1B（仍为 Codex-only）
```

允许并行：

- W0 页面骨架可与 W1 契约/迁移并行。
- W1 后端 Replay Core 可与前端 Chart Surface 并行，但以生成契约汇合。
- W2 Execution 与 Ledger 可在共同订单事件模型冻结后并行。
- W4 Agent Runtime 与 Tutor UI 可在 TutorRun/TutorResponse 契约冻结后并行。

禁止并行：

- 契约未冻结前同时编写前后端私有类型。
- Replay 反前视门禁未通过前实现 Paper Execution。
- Ledger 重建未通过前实现收益统计和能力雷达。
- 确定性复盘未完成前让 AI 生成正式评分。

## 11. 第一批可直接执行的 Backlog

按顺序执行：

1. `W0-01`：路由与 lazy page 基线。
2. `W1-01`：Session/Replay Pydantic 契约。
3. `W1-02`：`0004_training_session` migration。
4. `W1-03`：纯 Replay Core + property tests。
5. `W1-04`：Training Session Module + SQLite integration tests。
6. `W1-05`：Session REST routes。
7. `W0-04` + `W1-07`：Workbench 图表与播放器。
8. `W1-06`：Setup 页面。
9. `W1-08`：revision 冲突与恢复。
10. W1 Golden Session 与浏览器验收。

第一批结束前，不开始订单、AI 或策略学院内容制作。

## 12. 工期与人员节奏

估算口径：一名熟悉仓库的工程师使用 Coding Agent 全职开发，包含实现、测试、文档和浏览器验收，不包含等待外部用户反馈的时间。

| 波次 | 预计工程日 | 主交付 |
|---|---:|---|
| W0 | 2–3 | 路由、壳层、页面骨架、lazy chunk |
| W1 | 5–7 | Session、Replay、反前视、恢复 |
| W2 | 7–10 | 计划门禁、撮合、Ledger、账户 UI |
| W3 | 5–7 | 会话完成、Analytics、证据复盘 |
| W4 | 6–9 | Codex Runtime、Tutor、AI 共画 |
| W5 | 5–7 | 今日训练、学院、Playbook、设置 |
| W6 | 8–12 | A 股、Codex 硬化、发布硬化 |

MVP 1A 为 W0–W5，单人约 30–43 个有效工程日。建议按 6–9 周日历时间安排，保留真实用户试用和修正缓冲，不以页面完成数量判断进度。

两人并行时：

- Stream A：契约、migration、Replay、Execution、Ledger、Tutor Runtime。
- Stream B：App Shell、Chart Surface、Setup、Workbench、Review、Tutor UI。
- 两条流只在生成契约和每个波次的 Golden Session 汇合；不得维护两套私有模型。

## 13. 风险门禁

| 风险 | 最早验证点 | 失败后的救援 |
|---|---|---|
| KLineChart Overlay 难以承载三图层 | W0-04 | 保留 Chart Adapter，AI/用户标注改为 SVG overlay |
| DuckDB 内部预取造成未来泄露 | W1-03 | 允许内部预取，但响应构造强制裁剪和诱饵扫描 |
| SQLite command 并发冲突 | W1-04 | 单 session lock + 短事务 + busy timeout，不提前换数据库 |
| 前端播放器请求乱序 | W1-07 | 单飞队列，revision 409 后以服务端快照覆盖 |
| K 线级撮合歧义 | W2-03 | 固定保守路径并写入 execution reason |
| Agent CLI 访问范围过大 | W4-03 | 默认关闭不满足隔离级别的 Adapter，Fake/确定性复盘继续可用 |
| 页面数量拖慢闭环 | 每个 W | 未交付页面使用明确空状态，不能阻塞关键路径 |
| AI 评分污染确定性事实 | W4-04 | 事实、推断、未知和图形 provenance 分栏持久化 |

## 14. MVP 1A 发布门

以下全部满足才可称为 MVP 1A：

- [ ] BTCUSDT Golden Session 可完成并在重启后恢复。
- [ ] 所有回放接口通过未来诱饵测试。
- [ ] 订单只在下一根激活，撮合结果和账户可重复。
- [ ] Ledger 平衡并能从事件重建。
- [ ] 强制计划卡由服务端门禁。
- [ ] 用户、AI、策略图层可独立显示且 provenance 不混淆。
- [ ] 无 Agent 时确定性训练与复盘完整可用。
- [ ] Codex 正常与五类失败路径均有明确结果。
- [ ] evidence ID 可回跳到正确图表位置。
- [ ] 三条 Browser Golden Sessions 全绿。
- [ ] 1180、1440、1920 三档视觉验收通过。
- [ ] `make verify` 通过，生产构建不含用户数据、secret 和本机路径。

## 15. 下一步

下一次开发从 `W0-01 + W1-01` 开始：先建立 lazy page/router 基线并冻结 Session/Replay 契约，再实现 `0004_training_session` 与纯 Replay Core。
