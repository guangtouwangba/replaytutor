# ReplayTutor 本地试用发布清单

## Open-source Alpha gate

- [ ] Full Git history scanned with gitleaks or an equivalent secret scanner.
- [ ] Sample-data provenance and third-party licenses reviewed.
- [ ] English and Simplified Chinese homepage, settings, and core training flow checked.
- [ ] `make demo-video` reproduces both MP4 files without private data.
- [ ] GitHub private vulnerability reporting enabled before public visibility.
- [ ] Repository renamed to `replaytutor` only after merged release content is present.

状态：MVP 1A local hardening  
更新时间：2026-07-31

## 必过门禁

- `make verify`
- `make e2e`
- 1180、1440、1920 三种宽度无水平溢出
- WCAG 2 A/AA serious/critical axe violations 为 0
- 浏览器 console error 与 page error 为 0
- 失败 E2E 自动保存截图和 Playwright trace 到 `test-results/`
- 成功发布验收保留 `test-results/release-acceptance-*.png`、
  `test-results/release-acceptance-*.zip` 和
  `test-results/release-acceptance-summary.json`
- GitHub CI 始终上传 `release-acceptance-artifacts`，供发布复核下载
- `scripts/check-release-artifacts.sh` 确认前端产物和 Git 跟踪文件不包含
  本机路径、数据库、日志、凭据文件或 secret pattern

## 恢复演练

- 会话移入回收站后从 `/sessions` 恢复，订单、证据和复盘保持不变。
- 设置页创建 SQLite 在线备份；恢复前系统自动创建一份当前数据库备份。
- 备份恢复前执行 SQLite `integrity_check`。
- 应用重启时将遗留的 `running` Tutor run 标为 failed，不继续假装运行。
- 过期 Agent 目录只移动到 `data/trash/agent-runs`，不直接删除。

## 已知限制

- 当前训练与撮合仅支持 BTCUSDT 1m Crypto Spot；工作台可查看服务端派生的 5m、15m、1h、4h、1d 图表。A 股、美股和外汇未进入本版本。
- 个人自由文本 Playbook 没有注册 evaluator 时保持 `unknown`。
- 备份仅覆盖 SQLite 业务数据库；Parquet Snapshot 与导出文件需单独复制。
- AI 模式仅有 Codex 或关闭；真实 Codex smoke 不进入 CI。
- 水平线、自由文字、图层锁定和批量图层操作尚未开放。
- 本项目不提供真实下单、撤单、转账或提现能力。
