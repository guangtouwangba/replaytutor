# ReplayTutor Chrome Companion

本目录用于 ReplayTutor 的 Chrome Manifest V3 Side Panel Companion。

当前状态：文档与架构阶段，尚未建立可运行扩展工程。

正式需求与架构：

- [Chrome Companion PRD](../../docs/chrome-companion-prd.md)
- [Chrome Companion Architecture](../../docs/CHROME_COMPANION_ARCHITECTURE.md)

## 固定边界

- 插件是 ReplayTutor 的可选 UI Adapter，不实现回放、撮合、账本、指标或规则计算。
- 发布版通过受限 Native Messaging Connector 连接本机 ReplayTutor 和 Codex Runtime。
- 不读取 TradingView DOM、Canvas、网络、Cookie、页面存储、截图、指标或交易数据。
- 不包含 content script、页面注入、自动交易或 TradingView 图表 Overlay。
- 所有 Tutor 上下文由后端按 Session 的 `frame_id` 与 `visible_at` 重新构建并校验。

## 计划目录

```text
apps/chrome-extension/
  manifest/
  public/icons/
  src/background/
  src/sidepanel/
  src/transport/
  src/api/
  src/state/
  src/styles/
  native-host/
  tests/e2e/
```

在 PRD 和协议 v1 获得批准前，不添加 TradingView host permission 或页面读取能力。
