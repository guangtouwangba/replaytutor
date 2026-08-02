# ReplayTutor

**训练决策，而不是事后诸葛。**

[English](README.md) · [架构](docs/ARCHITECTURE.md) · [安全](SECURITY.md) · [参与贡献](CONTRIBUTING.md)

> 当前为 Alpha。本项目用于本地研究和刻意训练，不是券商，不进行实盘下单，也不承诺交易收益。

[![ReplayTutor 中文演示](apps/web/public/media/replaytutor-demo-zh-readme.gif)](apps/web/public/media/replaytutor-demo-zh.mp4)

[观看中文演示（MP4）](apps/web/public/media/replaytutor-demo-zh.mp4) · [Watch the English demo (MP4)](apps/web/public/media/replaytutor-demo-en.mp4)

ReplayTutor 是本地优先的多市场交易回放与 AI 复盘工作台。它会隐藏未来行情，用确定性模块计算模拟成交，并让 AI Tutor 只读取与当前回放帧绑定的证据包。

## 为什么做 ReplayTutor

- 服务端统一签发 `frame_id` 和 `visible_at`，未来 K 线不会进入 UI 或 Tutor。
- 撮合、费用、盈亏、MFE/MAE 和账本均由确定性代码计算。
- Tutor 结论引用当前帧内的 K 线、订单、成交、笔记与图表标注。
- SQLite、Parquet、报告和 Agent 运行目录默认只保存在本机。
- 内置 BTCUSDT 1 分钟 Golden Dataset，无需 API Key 即可开始训练。

## 三分钟启动

需要 macOS 或 Linux、Node.js 24 + Corepack、Python 3.12、uv 和 GNU Make。WSL 暂为实验性支持。

```bash
git clone https://github.com/guangtouwangba/replaytutor.git
cd replaytutor
make setup
make doctor
make demo
```

打开 [http://127.0.0.1:5174](http://127.0.0.1:5174)。正常开发使用 `make dev`，地址为 5173 端口。

## 自动行情数据

训练配置支持 BTCUSDT、ETHUSDT 的现货和 USDT 永续合约。本地覆盖足够时会列出候选版本并标记推荐项，由用户明确确认用于本次训练的不可变 Snapshot；没有数据或覆盖不足时，通过 Binance 公共行情接口补齐。默认下载 30 天，也可选择一年。每次导入都会生成新的不可变 Parquet Snapshot。

Binance 私有成交复盘是可选的只读能力。不要向 ReplayTutor 提供交易、提现、杠杆或账户管理权限。

## 首页 Demo

首页按当前语言懒加载 Remotion 视频。视频工程位于 `apps/demo-video`，Playwright 会用隔离目录、固定 UTC 和内置数据自动准备录制。

- [中文演示](apps/web/public/media/replaytutor-demo-zh.mp4)：中文界面与中文字幕。
- [英文演示](apps/web/public/media/replaytutor-demo-en.mp4)：英文界面与英文字幕。

```bash
make demo-video
```

ReplayTutor 应用代码采用 Apache-2.0；Remotion 工具链适用独立的 [Remotion License](https://www.remotion.dev/license)。如果以公司主体使用视频工程，请先核对其适用条件。

## 验证

```bash
make verify
make e2e
```

当前 Alpha 聚焦“数据 → 隐藏未来的回放 → 模拟交易 → 带证据复盘”的可信闭环，不包含实盘交易、云账户、多人协作或收益承诺。

## 参与贡献与许可证

请先阅读 [CONTRIBUTING.md](CONTRIBUTING.md)、[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) 和 [SECURITY.md](SECURITY.md)。项目采用 [Apache-2.0](LICENSE)。
