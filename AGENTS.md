# AGENTS.md

## 项目目标

构建本地优先的多市场交易回放与 AI 复盘应用。支持 A 股、美股、加密和外汇，提供确定性历史回放、虚拟交易、真实成交复盘及原生 Coding Agent Tutor。

## 开发前必读

1. `DESIGN.md`（视觉与交互设计系统）
2. `docs/DESIGN.md`（产品设计）
3. `docs/SYSTEM_ARCHITECTURE.md`
4. `docs/AGENT_BINDING.md`
5. `docs/MVP_IMPLEMENTATION_PLAN.md`（进入实现时）

修改产品行为、架构或 Agent 契约时同步更新相关文档，避免实现与设计分叉。

## 不可违反的约束

- 回放中不得向 UI 或 AI 暴露 `visible_at` 之后的数据。
- 撮合、费用、盈亏、MFE/MAE 和规则检查必须由确定性模块计算。
- AI 输出不能直接修改订单、成交、账本或市场数据。
- A 股、美股、加密和外汇规则通过 Market Rules Adapter 实现，不在 UI 到处写条件分支。
- 新增行情源或 Agent 必须走适配器契约和共享契约测试。
- Agent 默认只读、最小环境、隔离运行目录；不得使用危险权限绕过参数。
- 不复制 TradingView 品牌、Logo、专有图标或闭源 Charting Library。

## 初期技术方向

- React + Vite + TypeScript
- FastAPI + Python
- SQLite 保存业务元数据
- Parquet + DuckDB 保存和查询大体量行情
- KLineChart 作为首选图表内核
- Pydantic / JSON Schema 作为前后端和 Agent 的统一契约

## 验证优先级

1. 无未来数据泄露。
2. 回放和撮合确定性。
3. 账本可重建且平衡。
4. 市场规则边界正确。
5. Agent 输出结构与证据引用有效。
6. UI 交互与性能。
