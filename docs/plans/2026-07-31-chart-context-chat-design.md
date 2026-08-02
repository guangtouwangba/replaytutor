# ReplayTutor 图表上下文与 AI 对话设计

日期：2026-07-31
状态：P0 纵向闭环已实现，计划组与多周期上下文待后续迭代
范围：回放工作台、图表绘图系统、右侧 Codex Tutor、证据解析

## 1. 产品定义

这项功能不是“把图表截图发给 AI”，而是让用户在图表上使用一套可被 AI
精确理解的图形语言。趋势线、区域、计划开仓、止损、止盈、加减仓、文字和
真实成交等对象，都可以加入本轮对话上下文。

核心闭环：

```text
用户绘图或标记计划
        ↓
选择一个或多个图表对象
        ↓
上下文托盘显示对象、时间范围和关联 K 线
        ↓
用户在 Chat 中陈述判断
        ↓
服务端按 frame_id / visible_at 构造不可变证据包
        ↓
Codex 分析事实、推断、策略一致性和风险
        ↓
回答中的证据可回跳图表，AI 建议可写入独立提议图层
```

## 2. 工作台形态

```text
┌─绘图栏─┬──────────────────── K 线图 ────────────────────┬─ Codex Tutor ───────┐
│ 趋势线 │              ╱ 用户趋势线 #T3                 │ 对话 证据 检查表     │
│ 水平线 │     [用户框选的突破回踩区 #Z2]                 │                     │
│ 区域框 │                    ↑ 计划开仓 #E1              │ 当前上下文 3 项      │
│ 开仓   │                    ├──── 止损 #SL1              │ [T3][Z2][E1+SL1]    │
│ 加仓   │                    └──────── 目标 #TP1          │ 范围：选中对象       │
│ 减仓   │                                                  │                     │
│ 止损   │                                                  │ 我认为这里回踩确认… │
│ 止盈   │                                                  │ [发送给 Codex]       │
└────────┴──────────────────────────────────────────────────┴─────────────────────┘
```

Chat 输入框上方增加“上下文托盘”。每个对象显示为可移除、可定位、可展开检查的
Chip，例如 `趋势线 T3`、`多头开仓 E1 @ 64,250`、`止损 SL1`。点击 Chip 时图表
高亮对象及其关联 K 线；悬停显示精确时间、价格和来源。

上下文范围有三档：

1. **选中对象**：默认，只发送用户明确选择的对象。
2. **当前可见图层**：发送当前视口内未隐藏的对象。
3. **整个计划组**：发送同一计划组中的开仓、止损、止盈、失效条件及注释。

“所有工具都可以输入上下文”不等于每次把整张图全部发送。默认显式选择可以减少
噪声、token 消耗和 AI 对用户指代的误解。

## 3. 支持的图表对象

### 3.1 分析绘图

- 趋势线、射线、水平线、垂直线
- 平行通道、价格通道
- 矩形区域、供需区、支撑阻力区
- 斐波那契回撤与扩展
- 价格/时间测量、风险收益测量
- 文字、标签、自由路径
- Swing High / Swing Low、突破、回踩、假突破等语义标记

### 3.2 交易计划标记

- 计划开仓、多空方向、计划价格或价格区间
- 加仓、减仓、计划平仓
- 止损、止盈、保本移动、追踪止损
- 失效点、触发条件、观察点
- 风险收益框、仓位数量、杠杆、预计风险

计划对象可组成 `plan_group_id`。例如开仓 E1、止损 SL1、目标 TP1 和趋势线 T3
属于同一计划组，用户只需把 E1 加入 Chat，即可选择“一并带入整个计划”。

### 3.3 系统证据

- 真实或模拟订单、成交、撤单、拒单
- 当前仓位、爆仓价、保证金和杠杆
- 锁定的交易计划和 Playbook 规则
- AI 提议标注及其接受、拒绝、修改状态

系统证据不可伪装成用户绘图。计划开仓是意图，真实成交是事实，两者在图标、图层
和 TutorContext 中必须分开。

## 4. 通用对象契约

不要继续用一个只有 `shape + points + label` 的模型承载所有语义。改为判别联合：

```json
{
  "object_id": "chartobj_...",
  "object_revision": 3,
  "session_id": "session_...",
  "frame_id": "frame_...",
  "source": "user",
  "tool": "planned_entry",
  "semantic_role": "entry",
  "geometry": {
    "type": "marker",
    "anchors": [
      {"time": "2026-01-05T02:31:00Z", "price": "64250.0"}
    ]
  },
  "trade_intent": {
    "side": "long",
    "quantity": "0.02",
    "leverage": "5",
    "order_type": "LIMIT"
  },
  "label": "回踩确认后开多",
  "note": "低点不破，成交量缩小",
  "plan_group_id": "plan_...",
  "related_object_ids": ["chartobj_stop_...", "chartobj_target_..."],
  "created_at_frame_id": "frame_...",
  "visible_until": null
}
```

不同工具使用不同的 `geometry` 和业务字段：

- 线/射线：两个锚点、延伸方向、斜率。
- 区域：时间上下界、价格上下界。
- 通道：基准线锚点和宽度锚点。
- Fibonacci：起终点、方向和启用的比率。
- 开仓/加减仓：方向、价格、数量、杠杆、订单类型。
- 止损/止盈：触发价、关联开仓、风险金额或预期收益。
- 文字：锚点、正文和用户定义的语义标签。

所有工具通过 `ChartToolRegistry` 注册：

```text
tool name
→ geometry validator
→ context serializer
→ evidence resolver
→ chart renderer
→ AI instruction renderer
```

因此未来新增 Elliott Wave、成交量分布或自定义策略工具时，不需要修改 Chat 主流程。

## 5. Context Bundle

Chat 不直接接收客户端拼出的完整行情，也不只接收图片。发送消息前先创建不可变的
`ChartContextBundle`：

```json
{
  "context_bundle_id": "ctx_...",
  "session_id": "session_...",
  "frame_id": "frame_...",
  "visible_at": "2026-01-05T02:31:00Z",
  "timeframe": "5m",
  "selection_mode": "selected",
  "object_refs": [
    {"object_id": "chartobj_T3", "object_revision": 1},
    {"object_id": "chartobj_E1", "object_revision": 3}
  ],
  "resolved_evidence_ids": [
    "bar_100_130",
    "plan_...",
    "rule_breakout_retest_2"
  ],
  "derived_facts": {
    "entry_to_stop_pct": "0.82",
    "planned_rr": "2.15",
    "trendline_touch_count": 3
  }
}
```

服务端根据对象坐标解析相关 K 线。区域对象读取区域内已可见 K 线；趋势线读取锚点、
触碰和突破附近的 K 线；开仓对象读取入场前环境、入场位置、关联止损目标与策略规则。
派生数值由确定性模块计算，Codex 只解释。

每条 Chat 消息绑定 `context_bundle_id`。之后用户移动趋势线，也不会悄悄改变旧回答的
依据；新位置会生成新的对象 revision 和新的 Context Bundle。

可附带一张裁剪后的图表缩略图帮助 AI 理解视觉布局，但缩略图只作辅助。时间、价格、
订单和规则结论以结构化证据为准。

## 6. 对话交互

### 6.1 添加上下文

- 单击对象后按 `Ask AI`，对象进入上下文托盘并聚焦 Chat。
- `Shift + 单击` 多选多个图形。
- 框选工具完成后浮出 `保存`、`加入对话`、`保存并询问`。
- 输入框支持 `@趋势线T3`、`@开仓E1`、`@当前仓位`。
- 开启“新标注自动加入本轮对话”后，新绘图自动成为下一条消息的上下文。
- 清空 Chat 上下文不会删除图表对象。

### 6.2 AI 回答

回答固定为：

1. **我理解的计划**：复述图形关系，先验证 AI 是否理解正确。
2. **可验证事实**：位置、K 线、斜率、风险收益、订单与规则结果。
3. **判断**：哪些合理、哪些与策略冲突，明确置信度。
4. **缺失条件**：例如没有失效点、开仓与止损未关联、趋势线触点不足。
5. **建议图层**：可选地画出替代趋势线、风险区或关键证据。
6. **下一问**：要求用户补充计划，而不是代替用户做交易决定。

回答中的 `趋势线 T3`、`第 118 根 K 线`、`止损 SL1` 都是可点击证据。点击后图表定位、
闪烁高亮，底部订单表和 Inspector 同步选中。

### 6.3 AI 回写

AI 不能直接修改用户对象。它只能：

- 指向现有对象；
- 返回独立 `proposed` 图层的新对象；
- 建议移动或重构某个对象；
- 建议把若干对象组成计划组。

用户对每条建议执行接受、拒绝或修改。接受也保留原始 AI 提议和处置历史。

## 7. 反前视和权限边界

- 客户端只提交 `frame_id` 和对象 ID，不能提交任意 `visible_at`。
- 服务端重新解析对象 revision、市场帧和可见 K 线。
- 任一锚点晚于 `visible_at` 时拒绝创建 Context Bundle。
- 回放中隐藏未来订单、成交、最终盈亏、MFE/MAE 和事后标注。
- 对象若关联未来成交，只返回当前帧已经发生的部分。
- AI 输出不能提交、修改或取消订单，不能改账本和行情。
- 旧消息使用不可变 Context Bundle，保证回答可审计和可复现。

## 8. 对现有代码的改动

当前限制：

- `ChartAnnotation.shape` 只有 `line / zone / marker / label`。
- `AnnotationPoint` 只有时间和价格。
- `TutorRequest` 只有 `question + stage`。
- `DrawingTool` 只有 `select / line / zone / marker`。
- Tutor 还不能接收用户选择的图表对象。

建议新增：

```text
contracts:
  ChartContextObject (discriminated union)
  ChartObjectRevision
  ChartContextSelection
  ChartContextBundle
  TutorRequest.context_bundle_id

backend:
  ChartObjectService
  ChartToolRegistry
  ChartContextBuilder
  ChartEvidenceResolver

frontend:
  ChartSelectionController
  ChartContextTray
  ChartObjectInspector
  ChatEvidenceLink
```

原 `session_annotation` 可以迁移为通用图表对象的基础表，也可以保留为兼容层；
对象修改继续使用 append-only revision/event，不原地覆盖。

## 9. 分阶段实现

### P0：形成完整闭环

- 趋势线、水平线、区域、文字、计划开仓、止损、止盈、风险收益框。
- 单选/多选、上下文托盘、计划组。
- 不可变 Context Bundle 和 Tutor 请求绑定。
- Codex 读取结构化对象并返回证据链接。
- 回答点击回跳图表；AI 建议进入 proposed 图层。

### P1：补齐专业绘图

- 射线、通道、Fibonacci、测量、加仓、减仓、追踪止损。
- 当前视口/当前图层选择模式。
- `@对象` 输入和对象关系编辑。

### P2：提高智能程度

- 自动检测触点、突破、回踩、偏离和风险收益。
- 自动提示缺失的止损、失效条件或计划关联。
- 多周期 Context Bundle，但仍分别受各自可见帧裁剪。

## 10. 验收标准

1. 任意已注册图表工具都能生成可校验的上下文对象。
2. 用户可以明确看到下一条消息会带入哪些对象。
3. AI 能区分计划开仓、真实订单和真实成交。
4. AI 能引用具体对象和 K 线，点击引用可回跳并高亮。
5. 移动对象后旧消息的证据不改变。
6. 任意超过 `visible_at` 的坐标、行情或成交均无法进入 TutorContext。
7. AI 建议不会覆盖用户图层，也不会修改订单或账本。
8. Context Bundle 可在日志中重建，回答可审计复现。
