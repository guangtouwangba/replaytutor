# ReplayTutor Chrome Companion PRD

状态：Draft for approval v0.1
更新时间：2026-08-03
产品形态：Chrome Manifest V3 Side Panel Extension
实施目录：`apps/chrome-extension/`
正式架构：[Chrome Companion 架构](CHROME_COMPANION_ARCHITECTURE.md)

实施进度（2026-08-03）：Phase 1 基础批次已完成协议 v1 生成契约、后端受限
Companion Facade、单入口 dispatcher，以及 Web/Extension 共用的 `TutorClient` seam。
Side Panel 工程、开发 transport 和纵向 UI 切片进入下一批。

## 1. 决策摘要

ReplayTutor Chrome Companion 是运行在 Chrome 原生侧边栏中的本地优先 Tutor 入口。
用户可以在 TradingView 页面旁选择 ReplayTutor 回放会话、查看受控上下文、与本机 Codex
对话并跳转到 ReplayTutor 的证据位置。

本插件不是 TradingView 数据采集器、自动交易插件或 TradingView 图表增强脚本。
MVP 不读取 TradingView DOM、Canvas、网络请求、Cookie、Local Storage、截图、指标值、
订单或账户信息；不会把 TradingView 页面内容发送给 ReplayTutor、Codex 或任何远端服务。

所有进入 Codex 的事实仍由 ReplayTutor 后端根据 `session_id`、服务端签发的 `frame_id` 和
`visible_at` 重新构建。回放、撮合、费用、盈亏、指标、规则检查、证据引用和 AI 输出校验
继续由现有确定性模块负责。

## 2. 背景与问题

ReplayTutor 已经具备完整的图表工作台、回放、虚拟交易、复盘和 Codex Tutor，但用户在
TradingView 看盘时需要切换页面才能提问或查看训练上下文。切换成本会中断观察过程，也降低
Tutor 在日常看盘中的使用频率。

将完整产品迁入 TradingView 页面并不可取：

1. TradingView 页面状态不是 ReplayTutor 可依赖的稳定契约。
2. 页面中的回放游标无法证明与 ReplayTutor `visible_at` 一致。
3. DOM、Canvas 或网络提取无法形成版本化、可重放的行情证据。
4. 页面采集和机器处理涉及 TradingView 数据使用条款与 Chrome Web Store 隐私披露风险。
5. 注入式实现会把 ReplayTutor 的核心能力绑定到第三方页面结构和发布节奏。

因此，本产品采用“独立核心 + 同屏 Companion”模式：TradingView 只作为用户正在查看的网页，
ReplayTutor 侧边栏只消费 ReplayTutor 自己的数据与会话。

## 3. 产品目标

### 3.1 用户目标

- 在 TradingView 看盘时无需离开当前标签页即可打开 ReplayTutor Tutor。
- 明确知道本轮 AI 使用的是哪个 ReplayTutor Session、品种、周期和 `visible_at`。
- 使用现有本机 Codex 登录态，不购买或配置第二套模型 API。
- 从回答中的证据一键打开 ReplayTutor，并定位到对应 K 线、订单、成交、规则或标注。
- 本地服务或 Codex 不可用时获得可操作的诊断，不影响 TradingView 本身。

### 3.2 业务与项目目标

- 提高 Tutor 在日常看盘场景中的可达性和使用频率。
- 复用现有 FastAPI、SQLite、Parquet、Agent Runtime 和统一契约，不形成第二套核心。
- 将插件保持为可撤销的产品面；停用或卸载插件不影响 ReplayTutor 数据和 Web 工作台。
- 为后续桌面 Companion 或其他浏览器表面验证一套受限的本地连接协议。

### 3.3 成功指标

MVP 验收以本地、可测试指标为准，不默认上传遥测：

| 指标 | 目标 |
|---|---|
| 用户从点击扩展按钮到看到连接状态 | 本地服务正常时 P95 小于 1 秒 |
| 从侧边栏完成 Session 选择并提交第一问 | 不超过 3 个显式动作 |
| Tutor 上下文来源标识 | 100% 回合展示 Session、品种、周期、`visible_at` |
| 未来数据门禁 | 诱饵数据、响应扫描和现有 no-future 测试全部通过 |
| AI 证据引用 | 正式回答中的 evidence ID 100% 通过服务端白名单校验 |
| TradingView 页面读取 | MVP 构建中 content script、页面注入和页面采集能力为 0 |
| 本地核心回归 | Web 工作台、回放、撮合、账本和 Tutor 现有测试不退化 |
| 扩展发布门禁 | 无远程托管可执行代码，权限清单与批准快照一致 |

## 4. 目标用户与核心场景

### 4.1 目标用户

- 已经使用 TradingView 看盘，同时在本机运行 ReplayTutor 的个人交易者。
- 已经登录 Codex CLI，希望复用本机能力进行训练和复盘的用户。
- 重视证据、数据时点和交易纪律，不接受无来源聊天建议的用户。

### 4.2 核心场景

#### 场景 A：同屏询问回放环境

用户在 TradingView 页面打开 ReplayTutor 侧边栏，选择一个进行中的 ReplayTutor Session。
侧边栏显示 `BTCUSDT · 4h · REPLAY · visible to 14:00`。用户询问当前环境，后端只使用该
Session 当前 frame 内的证据，返回观察、推断、风险和证据链接。

#### 场景 B：继续已有 Tutor 对话

用户重新打开 Chrome 后，侧边栏恢复最近选择的 Session 和该 Session 最近活动的 Tutor
线程。恢复只使用本地标识重新向后端读取真值；不会把扩展缓存当成线程或运行状态真源。

#### 场景 C：证据回跳

用户点击回答中的 `bar_*`、`execution_*` 或 `rule_*`。插件打开 ReplayTutor Web 工作台的
只读深链接，由 ReplayTutor 自己解析 evidence ID 并定位。插件不尝试操作 TradingView 图表。

#### 场景 D：本地服务不可用

侧边栏显示“ReplayTutor 未运行”，提供复制启动命令、打开安装说明和重新检测。插件不得反复
后台唤醒、静默下载安装程序或向远端发送错误日志。

#### 场景 E：上下文不一致

TradingView 页面可能正在显示其他品种或周期。MVP 不自动读取它。侧边栏始终突出显示
ReplayTutor 上下文来源；用户必须主动切换 Session 或分析周期。不得暗示 AI 已看见当前网页。

## 5. 产品范围

### 5.1 MVP 必须提供

#### CMP-FR-001 侧边栏入口

- 使用 Chrome Side Panel，而不是覆盖网页的浮窗或注入式 iframe。
- 用户点击扩展 action 后打开侧边栏。
- 最低支持 Chrome 116；低版本显示不兼容说明，不提供隐式降级注入。
- 默认允许在普通标签页打开，但产品文案以 TradingView 同屏使用为主要场景。

#### CMP-FR-002 本地连接状态

- 状态固定为：`not_installed`、`stopped`、`connecting`、`ready`、`incompatible`、`error`。
- `ready` 必须同时包含 Connector 协议版本、ReplayTutor 版本和 API 健康状态。
- Codex 状态独立展示：`unavailable`、`auth_unknown`、`verified`、`failed`、`available`。
- Codex 不可用时仍可浏览 Session、历史回答和证据链接。

#### CMP-FR-003 Session 选择

- 默认展示未完成 Session，其次展示最近完成 Session。
- 每项显示市场、品种、状态、`visible_at`、Snapshot 简称和最近活动时间。
- 选择结果只在本地保存 `session_id`；每次打开都重新请求 Session 真值。
- Session 被软删除、完成或不存在时显示明确状态，不自动替换成另一个 Session。

#### CMP-FR-004 受控上下文头

- Chat 顶部常驻显示：来源 `ReplayTutor`、Session、品种、模式、frame、`visible_at`、分析周期。
- `frame_id` 和 `visible_at` 只能来自后端响应，扩展不得自行构造或修改。
- 上下文与 TradingView 当前页面不一致时不显示错误匹配结论，只显示 ReplayTutor 真值。
- 未选择 Session 时禁止发送需要市场上下文的 Tutor 请求。

#### CMP-FR-005 Codex Tutor Chat

- 支持读取当前线程、新建线程、提交问题、查看运行状态和取消运行。
- 回答结构与 Web 工作台一致：结论、观察、推断、风险/未知、规则检查、下一问、免责声明。
- 正式回答必须已通过现有 JSON Schema 和 evidence ID 校验。
- 失败、取消、超时和未校验原始输出不得混入后续对话上下文。
- 同一线程最近 12 个成功回合的上下文限制继续由后端执行。
- 插件不得直接调用 Codex CLI，也不得保存 Codex token 或复制用户 Codex 配置。

#### CMP-FR-006 证据链接

- 每个 evidence ID 可请求后端解析为只读目标。
- 点击后打开 ReplayTutor 深链接：
  `/sessions/{session_id}?mode=review&evidence={evidence_id}`。
- 回放进行中需要保持时间安全时，打开对应 Session 当前允许的工作台状态；不得通过深链接
  绕过 `visible_at` 查看未来数据。
- 无效或已不可用证据显示错误，不尝试在 TradingView 中寻找相似时间或价格。

#### CMP-FR-007 本地化与可访问性

- 支持 `zh-CN` 和 `en-US`，英文为 fallback。
- 键盘可完成打开、Session 选择、输入、发送、取消和证据打开。
- 侧边栏在 320–600px 宽度无水平溢出；主要控件满足可访问名称和焦点可见性。
- 红绿不作为唯一状态表达。

#### CMP-FR-008 隐私与权限说明

- 首次使用明确说明：插件连接本机 ReplayTutor，不读取 TradingView 页面内容。
- 设置页展示已授予权限、本机连接方式、数据保留位置和隐私策略链接。
- 默认无远程遥测、广告、第三方分析 SDK 或云端账号。
- 本地错误日志遵循现有路径与 secret 脱敏规则。

### 5.2 MVP 明确不做

- 不读取或解析 TradingView DOM、Canvas、URL 参数、页面文本、选择内容或浏览历史。
- 不注册 TradingView content script，不使用 `webRequest`、`debugger`、Cookie 或页面存储权限。
- 不截图、不 OCR、不抓取 K 线、指标、绘图、告警、订单或经纪商数据。
- 不同步 TradingView Replay 游标，不声称知道网页当前 `visible_at`。
- 不向 TradingView 图表注入 AI 标注、下单线、按钮、Logo 或 Overlay。
- 不提供真实下单、自动交易、订单验证、价格引用或智能路由。
- 不在插件中实现回放引擎、撮合、账本、指标或规则计算。
- 不通过远程脚本、CDN JavaScript、远程 WASM 或动态代码执行扩展功能。
- 不在 MVP 发布包内支持 Firefox、Safari 或移动浏览器。

### 5.3 Post-MVP 候选

只有在独立法律/条款审查、数据授权和威胁建模通过后，才能评估：

- 用户显式触发的网页上下文桥接。
- 获授权的 TradingView 官方集成或数据接口。
- 用户手动提供截图后的视觉分析。
- 其他网站或浏览器支持。

这些能力必须作为独立权限和独立发布门，不得通过普通插件升级静默加入。

## 6. 信息架构与交互

侧边栏固定为单栏，不复制 ReplayTutor 完整工作台：

```text
┌──────────────────────────────┐
│ ReplayTutor   Local ●  Codex ●│
├──────────────────────────────┤
│ Session ▼                    │
│ BTCUSDT · REPLAY · 4h        │
│ Visible to 2025-01-08 14:00  │
├──────────────────────────────┤
│                              │
│ 当前 Tutor 对话              │
│ 结论 / 观察 / 推断 / 风险     │
│ evidence links               │
│                              │
├──────────────────────────────┤
│ [阶段] 询问当前 frame…        │
│                    [发送]     │
└──────────────────────────────┘
```

### 6.1 顶部状态区

- 品牌使用 ReplayTutor 自有标识，不使用 TradingView 品牌、Logo 或近似图标。
- Local 与 Codex 分开显示；Local 错误不能伪装成 Codex 错误。
- 点击状态打开诊断详情，不跳转到外部网站。

### 6.2 Session 区

- Session 选择器是上下文切换的唯一入口。
- 切换 Session 时未发送输入保留在原 Session 的本地草稿中，并明确提示上下文已变化。
- 有运行中的 Tutor run 时不允许静默切换；用户需取消、等待或明确离开。

### 6.3 Chat 区

- 只展示当前对话，不增加第二条线程历史侧栏。
- 顶栏允许新建对话；线程管理仍由 ReplayTutor 后端按 Session 隔离。
- 回答中的事实观察和确定性规则必须保留证据跳转。
- 运行中使用轮询或 Connector 事件更新；UI 不依赖长存内存判断最终状态。

### 6.4 错误状态

| 错误 | 用户动作 | 禁止行为 |
|---|---|---|
| Connector 未安装 | 打开本地安装说明 | 静默下载可执行文件 |
| ReplayTutor 未运行 | 启动/重新检测 | 无限后台重试 |
| 协议不兼容 | 更新插件或本地应用 | 忽略版本继续调用 |
| Codex 未安装/未认证 | 打开 ReplayTutor 设置说明 | 读取或展示 token |
| Session 不存在 | 重新选择 Session | 自动选择其他 Session 并发送 |
| Tutor 超时 | 重试或编辑问题 | 把部分输出标为成功 |
| 证据失效 | 显示不可定位 | 猜测相似 K 线 |

## 7. 核心数据与契约要求

插件优先复用 `@replaytutor/contracts`，不得维护手写的 TutorResponse 影子类型。

新增的 Companion 协议只描述传输，不复制业务模型：

```json
{
  "protocol_version": "1.0",
  "request_id": "req_...",
  "method": "tutor.start",
  "params": {}
}
```

```json
{
  "protocol_version": "1.0",
  "request_id": "req_...",
  "ok": true,
  "result": {}
}
```

允许的 MVP 方法固定为：

- `system.bootstrap`
- `system.health`
- `agent.codex.discover`
- `session.list`
- `session.get`
- `tutor.thread.list`
- `tutor.thread.create`
- `tutor.thread.get`
- `tutor.run.start`
- `tutor.run.get`
- `tutor.run.cancel`
- `evidence.resolve`
- `navigation.open_replaytutor`

协议中不得出现通用 URL、任意 HTTP method、SQL、文件路径、shell command 或 Codex 参数。

## 8. 安全、隐私与合规需求

### 8.1 权限最小化

发布版初始权限目标：

```json
{
  "permissions": ["sidePanel", "storage", "nativeMessaging"],
  "host_permissions": []
}
```

- 不使用 `externally_connectable`。
- 不使用 `<all_urls>`、`tabs`、`scripting`、`webRequest`、`cookies` 或 `debugger`。
- Incognito 默认禁用且不承诺支持。
- 开发版 direct HTTP transport 可以使用仅限 `http://127.0.0.1:8788/*` 的本地构建 manifest，
  但不得进入 Web Store 发布包。

### 8.2 本地连接

- 发布版使用 Chrome Native Messaging，并在 native host manifest 中固定允许的扩展 origin。
- Connector 只代理方法白名单，不是通用 localhost 反向代理。
- Connector 不把数据库、Parquet、Codex 配置或用户主目录路径返回插件。
- 单条消息限制在 512 KiB；禁止通过协议传输 bars、截图、数据库文件或 Agent 运行目录。
- 所有请求携带协议版本和 request ID，参数与响应均通过共享 Schema 校验。

### 8.3 Agent 边界

- 插件不能选择可执行文件、修改 Codex 参数或扩大 sandbox。
- Agent 仍由现有 Tutor Runtime 创建物理裁剪的证据包并启动。
- `ai_mode=off` 时在创建 Agent run 目录前拒绝请求。
- Agent 失败不影响 Session、回放、订单、成交或账本。

### 8.4 第三方页面边界

- TradingView 页面不能向扩展发送消息，扩展也不向页面注入对象。
- 插件不得把“与 TradingView 同屏”表述成“读取、同步或分析 TradingView 数据”。
- Chrome Web Store 商品页、首次使用说明和隐私政策必须与实际权限及行为一致。

## 9. 非功能需求

### 9.1 性能

- Side Panel 首屏 JavaScript 压缩后目标小于 350 KiB，不打包 KLineChart。
- 空闲时不轮询 Tutor；仅在面板可见且存在 running run 时查询状态。
- Session 列表默认最多返回 50 项，使用后端排序和裁剪。
- 扩展 service worker 可随时终止；所有必要状态保存在后端或 `chrome.storage`。

### 9.2 可靠性

- Connector 断开后指数退避，最大间隔 30 秒；用户点击重试立即触发一次检测。
- 每个 Tutor 提交必须有 request ID；重复提交由后端幂等或返回现有 run。
- 插件更新、Chrome 重启或 service worker 重启不能把运行中的 run 标记为失败。
- 协议版本不兼容时 fail closed。

### 9.3 可维护性

- 插件使用 TypeScript strict、React、Vite 和现有 contracts。
- 共享 Chat 展示组件与业务传输分离；Web 和 Extension 各自注入 transport adapter。
- 扩展包内所有可执行代码固定在构建产物中，构建扫描拒绝远程可执行代码和 `eval`。
- 发布构建可复现，产物记录 lockfile hash、协议版本和 ReplayTutor 兼容范围。

## 10. 方案比较与选择

| 方案 | 改动 | 优点 | 缺点 | 结论 |
|---|---|---|---|---|
| A. 侧边栏直接访问现有 HTTP API | 小 | 验证快、复用 REST | 需要扩展 CORS 和认证；本地网页攻击面更大 | 仅开发验证 |
| B. Side Panel + 受限 Native Connector | 中 | 权限和方法可控；不暴露通用 API；适合发布 | 需要本机安装/注册 | **MVP 发布方案** |
| C. Content script 深度集成 TradingView | 大 | 可尝试同步页面 | 条款、隐私、脆弱性和未来泄露风险 | 不采用 |

共享 UI 同样采用平衡方案：抽取 transport-agnostic Tutor UI 和 client interface，Web 与插件
分别提供 HTTP/Native adapter；不复制 Tutor 业务逻辑，也不把整个 Web 工作台打进插件。

## 11. 发布阶段

### Phase 0：文档与契约

- 批准本 PRD 和正式架构。
- 冻结 Companion MVP 方法白名单、权限清单和协议 v1。
- 确认 Chrome Web Store 发布主体与隐私政策位置。

### Phase 1：Unpacked 技术切片

- 建立 `apps/chrome-extension/` React + Vite + MV3 工程。
- 使用仅开发可用的 loopback HTTP transport。
- 完成健康检查、Session 选择、Chat、取消和证据深链接。
- 验证现有 Tutor Runtime 无需业务逻辑分叉。

### Phase 2：发布级 Connector

- 实现 Native Messaging host、安装/卸载和固定 extension origin。
- 将发布构建切换到 Native transport，移除 localhost host permission。
- 完成协议兼容、断线恢复、权限和构建产物扫描。

### Phase 3：商店与本地试用

- 完成隐私政策、显著披露、截图、说明和支持页面。
- 小范围本机试用，验证打开频率、连接失败和上下文误解问题。
- 通过发布清单后再提交 Chrome Web Store。

### Phase 4：授权集成评估

- 只有在独立条款与数据授权通过后，才创建新的 PRD 评估页面上下文桥接。

## 12. 验收计划

### 12.1 单元与契约测试

- Manifest 权限快照。
- Native 协议 request/response/event Schema。
- 版本协商、未知 method、超大消息和无效 payload 拒绝。
- Session 切换、草稿隔离、运行中切换门禁。
- TutorResponse 和 evidence ID 展示。
- service worker 重启后的状态恢复。

### 12.2 集成测试

- Extension → Connector → FastAPI → Tutor Runtime → fake Codex 完整链路。
- Connector 只能调用白名单方法，订单/数据集/维护接口全部拒绝。
- `ai_mode=off`、Codex 不可用、超时、取消和 orphan recovery。
- 当前 frame 与诱饵未来 bars 隔离。
- Deep link 不越过 Session 的时间权限。

### 12.3 浏览器 E2E

- 使用真实 Chrome 加载 unpacked extension。
- 打开 TradingView 页面与普通空白页，确认侧边栏不注入页面、不读取内容。
- 320、400、600px 侧边栏宽度和中英文布局。
- 键盘操作、axe 和焦点恢复。
- Chrome/Connector/ReplayTutor 分别重启后的恢复矩阵。

### 12.4 发布门禁

- 构建产物中无远程 JavaScript/WASM、`eval`、动态 script 注入或 source map 本机路径。
- Manifest 无未批准权限。
- 扩展 zip、Native host 和 ReplayTutor 版本兼容矩阵通过。
- 隐私政策与首次使用披露和实际行为一致。
- TradingView 商标、Logo、专有图标和页面截图不进入产品资产或商店素材。

## 13. 风险与缓解

| 风险 | 影响 | 缓解 |
|---|---|---|
| 用户误以为 AI 看见 TradingView 图表 | 错误决策与信任损失 | 常驻 ReplayTutor context badge；不自动匹配网页 |
| Native host 安装复杂 | 首次使用流失 | ReplayTutor 安装器统一注册；提供 doctor 和可恢复卸载 |
| Extension 与本地版本漂移 | 请求失败或语义错误 | 显式协议协商、兼容范围、fail closed |
| 侧边栏 service worker 被回收 | 运行状态丢失 | 后端为真源；storage 持久 ID；重连后重新读取 |
| 本地恶意页面探测 API | 数据或操作暴露 | 发布版不开放 HTTP；开发版固定 origin + 配对 token |
| 第三方条款变化 | 发布或功能风险 | MVP 零页面采集；发布前复核官方条款 |
| 共享 UI 抽取影响 Web | 核心回归 | 先建立 client interface 和现有行为测试，再迁移展示层 |

## 14. 上线与回滚

- 插件是可选应用，不进入 ReplayTutor 核心启动依赖。
- Connector 注册失败不得阻止 Web 工作台或 API 启动。
- 回滚时可禁用扩展发布、注销 native host；SQLite、Parquet、Session 和 Tutor 历史不迁移、
  不删除，也不需要降级。
- 协议升级至少保留一个稳定版本的兼容窗口；不兼容时显示更新要求，不猜测转换。

## 15. 待产品确认

以下不阻塞 Phase 1，默认值已给出：

1. 首发平台：默认 macOS + Chrome 116+；Windows 安装器进入后续批次。
2. 分发方式：Phase 1 unpacked，Phase 3 Chrome Web Store。
3. 遥测：默认关闭，只保留本地诊断；需要远程遥测时另行设计同意和数据最小化。
4. 页面集成：默认永久关闭，任何开启都需要新 PRD、权限审查和数据授权。
