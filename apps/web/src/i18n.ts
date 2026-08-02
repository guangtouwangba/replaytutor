import i18n from "i18next";
import LanguageDetector from "i18next-browser-languagedetector";
import { initReactI18next } from "react-i18next";

export const supportedLocales = ["en-US", "zh-CN"] as const;
export type AppLocale = (typeof supportedLocales)[number];
export type LocalePreference = AppLocale | "system";

const resources = {
  "en-US": { translation: {
    "app.loading": "Loading page…",
    "app.skip": "Skip to main content",
    "app.environment": "LOCAL · ALPHA",
    "api.connecting": "Connecting to local API",
    "api.incompatible": "Incompatible API · {{version}}",
    "api.unavailable": "API unavailable · retry",
    "nav.home": "Today", "nav.academy": "Academy", "nav.workbench": "Workbench",
    "nav.reviews": "Reviews", "nav.playbooks": "Playbooks", "nav.sessions": "Sessions",
    "nav.data": "Data", "nav.settings": "Settings", "nav.primary": "Primary navigation",
    "home.onboardingLabel": "First-time ReplayTutor setup",
    "home.onboardingTitle": "Complete one verifiable session with the bundled market snapshot",
    "home.step1": "Choose a playbook and market data", "home.step2": "Lock the trading plan", "home.step3": "Finish and review the evidence",
    "home.dismiss": "Got it", "home.startFixed": "Start demo session", "home.loadSample": "Load sample data",
    "home.hero": "Train the decision with only what was visible then.",
    "home.subhero": "Market data, orders, ledger, and Tutor share one time boundary. Every result can be replayed and audited.",
    "home.continue": "Continue training", "home.create": "Create replay", "home.prepare": "Prepare market data",
    "home.snapshots": "Available snapshots", "home.none": "No market data loaded",
    "home.discipline": "Data discipline", "home.immutable": "Immutable",
    "home.sessions": "Training sessions", "home.resumable": "A resumable session is available",
    "home.resume": "Resume {{symbol}} training", "home.revision": "Safely saved at revision {{revision}} with the same visible-time boundary.",
    "home.back": "Back to workbench", "home.focus": "Focus next: {{dimension}}", "home.moreSamples": "Keep collecting usable sessions",
    "home.samples": "{{count}} usable sessions", "home.startRecommended": "Start recommended session", "home.next": "Complete next session", "home.sampleReason": "Each skill dimension needs at least 5 usable sessions before ReplayTutor ranks weaknesses.",
    "home.marketSnapshots": "Market snapshots", "home.manage": "Manage data",
    "home.dataError": "Could not read the data center: {{message}}",
    "home.empty": "No fabricated default chart. Load the real bundled BTCUSDT snapshot first.",
    "home.coverage": "Coverage", "home.quality": "Quality", "home.hash": "Content hash",
    "demo.kicker": "SEE REPLAYTUTOR IN 40 SECONDS", "demo.title": "Train decisions, not hindsight.",
    "demo.body": "Watch a deterministic BTCUSDT session move from a hidden-future replay to an evidence-linked Tutor review.",
    "demo.play": "Play ReplayTutor demo", "demo.transcript": "Read transcript", "demo.unavailable": "Video unavailable. Follow the transcript below.",
    "demo.scene1": "Choose BTCUSDT perpetual and reuse local data—or fill the missing range.",
    "demo.scene2": "Replay reveals only the bars visible at that frame.",
    "demo.scene3": "Orders, fills, and the ledger are computed deterministically.",
    "demo.scene4": "Tutor cites chart evidence without changing trading state.",
    "setup.title": "Training setup", "setup.description": "Choose an instrument to begin. ReplayTutor uses local data first and fills missing ranges from Binance.",
    "setup.stepsLabel": "Create training session steps", "setup.chooseInstrument": "Choose instrument", "setup.localFirst": "Local first, fill gaps automatically", "setup.bindPlaybook": "Bind playbook", "setup.defineConstraints": "Define this session's constraints", "setup.startTraining": "Start training", "setup.noLookaheadWorkbench": "Enter the no-look-ahead workbench",
    "setup.instrumentData": "Instrument and market data", "setup.trainingInstrument": "Training instrument", "setup.marketType": "Market type", "setup.usdtPerpetual": "USDT perpetual", "setup.spot": "Spot", "setup.historyRange": "Auto-download range", "setup.default30": "Used only when local data is missing", "setup.range30": "30 days", "setup.range365": "1 year", "setup.bars30": "About 43,200 bars", "setup.bars365": "About 525,600 bars",
    "setup.checkingLocal": "Checking local data", "setup.readingIndex": "Reading snapshot index and quality status…", "setup.localError": "Could not read local market data: {{message}}", "setup.localHit": "Selected local data", "setup.localCoverage": "{{count}} 1m bars · {{start}} to {{end}}", "setup.snapshotVersion": "Choose a dataset Snapshot", "setup.snapshotCreated": "created {{date}}", "setup.snapshotNoCoverage": "Choose an available version or download the requested range", "setup.snapshotRecommended": "Recommended", "setup.selectSnapshotHint": "Review coverage and version, then explicitly choose one.", "setup.selectSnapshotRequired": "Choose a dataset first", "setup.selectSnapshotBeforeConfig": "Account, replay start, strategy, and session creation unlock after you confirm a Snapshot.", "setup.configurationLocked": "The remaining setup is locked", "setup.downloading": "Downloading market data in the background", "setup.localMissing": "No local data covers this range yet", "setup.downloadingHint": "{{progress}}% complete. You can leave this page and return when the download finishes.", "setup.downloadHint": "Download the latest {{range}} of Binance 1m bars in the background. No API key required.",
    "setup.accountRisk": "Account and risk engine", "setup.initialEquity": "Initial equity", "setup.accountType": "Account type", "setup.leverage": "Leverage", "setup.isolated": "Isolated", "setup.cross": "Cross", "setup.oneway": "One-way", "setup.hedge": "Hedge mode", "setup.deterministicRisk": "The deterministic engine computes margin, funding, and liquidation. AI cannot change these results.", "setup.startBlind": "Replay starting point", "setup.fromBeginning": "From data start", "setup.specificTime": "Choose date", "setup.randomSegment": "Random segment", "setup.replayStartTime": "Replay start (UTC)", "setup.replayStartHint": "Available after warm-up: {{start}} to {{end}} UTC", "setup.replayStart": "Replay starts", "setup.hideDate": "Hide real dates", "setup.hideDateHint": "Reveal the full coverage only after the session ends.",
    "setup.constraints": "Training constraints", "setup.playbook": "Playbook", "setup.loading": "Loading", "setup.initialCapital": "Initial capital", "setup.warmup": "Warm-up window", "setup.aiMode": "AI mode", "setup.codexConnected": "Codex · connected", "setup.contractHint": "The selected snapshot, start point, and rules are locked at creation. The server signs replay progress so future data stays hidden.", "setup.market": "Market", "setup.data": "Data", "setup.rules": "Rules", "setup.quality": "Quality", "setup.binancePerpetual": "Binance USDT perpetual", "setup.binanceSpot": "Binance spot", "setup.localSnapshot": "{{start}} to {{end}}", "setup.autoDownload": "Auto-download · {{range}}", "setup.verifyAfterDownload": "Verify after download",
    "setup.creating": "Creating session…", "setup.startLocal": "Start with local data", "setup.downloadingProgress": "Downloading · {{progress}}%", "setup.submitting": "Submitting job…", "setup.downloadAction": "Download market data", "setup.prepareFailed": "Could not prepare training: {{message}}",
    "settings.kicker": "PREFERENCES & SAFETY", "settings.title": "Local settings and recovery",
    "settings.executable": "Executable", "settings.version": "Version", "settings.status": "Status", "settings.permissions": "Permissions",
    "settings.notFound": "Not found", "settings.available": "Available", "settings.unavailable": "Unavailable",
    "settings.system": "Deterministic system", "settings.database": "Database", "settings.migration": "Migration", "settings.dataDir": "Market data directory", "settings.binding": "Network binding",
    "settings.training": "TRAINING PREFERENCES", "settings.trainingPrivacy": "Training and privacy",
    "settings.language": "Language", "settings.systemLanguage": "System language", "settings.english": "English", "settings.chinese": "简体中文",
    "settings.aiMode": "AI mode", "settings.aiOff": "AI off", "settings.retention": "Keep Agent run directories (days)",
    "settings.confirm": "Confirm before finishing a session", "settings.savedLocal": "Preferences are stored in local SQLite.",
    "settings.privacy": "Privacy mode is fixed to local_only. Settings, market data, account state, and Tutor evidence are not uploaded by the application.",
    "settings.save": "Save local preferences", "settings.maintenance": "RECOVERABLE MAINTENANCE", "settings.backupCleanup": "Backup and cleanup",
    "settings.createBackup": "Create database backup", "settings.recoveryNote": "A fresh backup is created before restore. Agent cleanup only moves files to the local trash directory.",
    "settings.restore": "Restore", "settings.restoreConfirm": "Restoring replaces the current database. Continue?", "settings.noBackups": "No local backups yet.",
    "settings.cleanup": "Clean expired Agent run directories", "settings.cleaned": "Moved {{count}} directories to trash.",
    "settings.aiBoundary": "Codex never participates in matching, ledger updates, or deterministic metrics. Replay and paper trading stay available if it fails."
  }},
  "zh-CN": { translation: {
    "app.loading": "正在载入页面…", "app.skip": "跳到主要内容", "app.environment": "本地 · ALPHA",
    "api.connecting": "正在连接本地 API", "api.incompatible": "API 版本不兼容 · {{version}}", "api.unavailable": "API 不可用 · 重试",
    "nav.home": "今日", "nav.academy": "学院", "nav.workbench": "工作台", "nav.reviews": "复盘", "nav.playbooks": "策略", "nav.sessions": "会话", "nav.data": "数据", "nav.settings": "设置", "nav.primary": "主要导航",
    "home.onboardingLabel": "首次使用 ReplayTutor", "home.onboardingTitle": "先用固定片段完成一场可核验训练",
    "home.step1": "选择策略与行情", "home.step2": "锁定交易计划", "home.step3": "完成并复盘证据", "home.dismiss": "我已了解", "home.startFixed": "开始固定训练", "home.loadSample": "载入示例数据",
    "home.hero": "用当时可见的信息，重新训练一次决策。", "home.subhero": "行情、订单、账本和 Tutor 共享同一时间边界。所有结果都能重放和核对。",
    "home.continue": "继续训练", "home.create": "创建回放", "home.prepare": "准备真实数据", "home.snapshots": "可用快照", "home.none": "尚未载入行情",
    "home.discipline": "数据纪律", "home.immutable": "不可变", "home.sessions": "训练会话", "home.resumable": "存在可继续会话",
    "home.resume": "继续 {{symbol}} 训练", "home.revision": "已安全保存至 revision {{revision}}，恢复后仍从同一可见时间边界继续。", "home.back": "回到工作台",
    "home.focus": "重点训练：{{dimension}}", "home.moreSamples": "继续积累可解析样本", "home.samples": "{{count}} 个可解析会话", "home.startRecommended": "开始推荐训练", "home.next": "完成下一场", "home.sampleReason": "每个能力维度至少需要 5 个可解析会话，当前不生成弱项排名。",
    "home.marketSnapshots": "行情快照", "home.manage": "管理数据", "home.dataError": "无法读取数据中心：{{message}}", "home.empty": "没有伪造的默认行情。先去数据中心载入真实 BTCUSDT Snapshot。",
    "home.coverage": "覆盖区间", "home.quality": "质量", "home.hash": "内容哈希",
    "demo.kicker": "40 秒了解 REPLAYTUTOR", "demo.title": "训练决策，而不是事后诸葛。", "demo.body": "观看一场确定性 BTCUSDT 训练：从隐藏未来的回放，到带证据引用的 Tutor 复盘。",
    "demo.play": "播放 ReplayTutor 演示", "demo.transcript": "阅读文字版", "demo.unavailable": "视频暂不可用，请查看下方文字步骤。",
    "demo.scene1": "选择 BTCUSDT 永续合约，优先复用本地数据，缺口自动补齐。", "demo.scene2": "回放只揭示当前 frame 当时可见的 K 线。",
    "demo.scene3": "订单、成交和账本由确定性模块计算。", "demo.scene4": "Tutor 引用图表证据，但不能修改交易状态。",
    "setup.title": "训练配置", "setup.description": "选择品种即可开始；系统优先使用本地行情，缺失时自动从 Binance 拉取。", "setup.stepsLabel": "创建训练会话步骤", "setup.chooseInstrument": "选择品种", "setup.localFirst": "本地优先，自动补数", "setup.bindPlaybook": "绑定策略", "setup.defineConstraints": "明确本次训练约束", "setup.startTraining": "开始训练", "setup.noLookaheadWorkbench": "进入无未来数据工作台",
    "setup.instrumentData": "品种与行情", "setup.trainingInstrument": "训练品种", "setup.marketType": "市场类型", "setup.usdtPerpetual": "U 本位永续", "setup.spot": "现货", "setup.historyRange": "自动补数范围", "setup.default30": "仅在本地无可用数据时使用", "setup.range30": "30 天", "setup.range365": "1 年", "setup.bars30": "约 43,200 根", "setup.bars365": "约 525,600 根", "setup.checkingLocal": "正在检查本地数据", "setup.readingIndex": "读取 Snapshot 索引与质量状态…", "setup.localError": "无法读取本地行情：{{message}}", "setup.localHit": "已选择本地数据", "setup.localCoverage": "{{count}} 根 1m K 线 · {{start}} 至 {{end}}", "setup.snapshotVersion": "选择数据集 Snapshot", "setup.snapshotCreated": "创建于 {{date}}", "setup.snapshotNoCoverage": "选择已有版本，或下载所需范围", "setup.snapshotRecommended": "推荐", "setup.selectSnapshotHint": "确认覆盖区间和版本后，由你明确选择。", "setup.selectSnapshotRequired": "请先选择数据集", "setup.selectSnapshotBeforeConfig": "确认 Snapshot 后才会展开账户、回放起点、策略和创建会话设置。", "setup.configurationLocked": "后续配置尚未展开", "setup.downloading": "行情正在后台下载", "setup.localMissing": "本地暂无满足范围的行情", "setup.downloadingHint": "当前 {{progress}}%，可以切换到其他页面，完成后再回来开始训练。", "setup.downloadHint": "点击后在后台下载 Binance 最近 {{range}}完整 1m K 线；不需要 API Key。",
    "setup.accountRisk": "账户与风险引擎", "setup.initialEquity": "初始权益", "setup.accountType": "账户类型", "setup.leverage": "杠杆", "setup.isolated": "逐仓", "setup.cross": "全仓", "setup.oneway": "单向持仓", "setup.hedge": "双向持仓", "setup.deterministicRisk": "撮合会计算开仓保证金、维持保证金、资金费率与强平；AI 无权修改这些结果。", "setup.startBlind": "回放起点", "setup.fromBeginning": "从数据开头", "setup.specificTime": "选择日期", "setup.randomSegment": "随机片段", "setup.replayStartTime": "回放开始时间（UTC）", "setup.replayStartHint": "扣除预热窗口后可选：{{start}} 至 {{end}} UTC", "setup.replayStart": "回放起点", "setup.hideDate": "隐藏真实日期", "setup.hideDateHint": "结束会话后才揭示完整覆盖区间。", "setup.constraints": "本次训练约束", "setup.playbook": "策略", "setup.loading": "载入中", "setup.initialCapital": "初始资金", "setup.warmup": "预热窗口", "setup.aiMode": "AI 模式", "setup.codexConnected": "Codex · 已接入", "setup.contractHint": "创建后锁定所选 Snapshot、回放起点与规则；进度始终由服务端签发，防止看到未来数据。", "setup.market": "市场", "setup.data": "数据", "setup.rules": "规则", "setup.quality": "质量", "setup.binancePerpetual": "Binance U 本位永续", "setup.binanceSpot": "Binance 现货", "setup.localSnapshot": "{{start}} 至 {{end}}", "setup.autoDownload": "自动下载 {{range}}", "setup.verifyAfterDownload": "下载后校验", "setup.creating": "正在创建训练…", "setup.startLocal": "使用所选数据开始", "setup.downloadingProgress": "后台下载中 · {{progress}}%", "setup.submitting": "正在提交任务…", "setup.downloadAction": "后台下载行情", "setup.prepareFailed": "准备训练失败：{{message}}",
    "settings.kicker": "偏好与安全", "settings.title": "本地设置与恢复", "settings.executable": "可执行文件", "settings.version": "版本", "settings.status": "状态", "settings.permissions": "权限",
    "settings.notFound": "未找到", "settings.available": "可运行", "settings.unavailable": "不可用", "settings.system": "确定性系统", "settings.database": "数据库", "settings.migration": "迁移", "settings.dataDir": "行情目录", "settings.binding": "网络绑定",
    "settings.training": "训练偏好", "settings.trainingPrivacy": "训练与隐私", "settings.language": "语言", "settings.systemLanguage": "跟随系统", "settings.english": "English", "settings.chinese": "简体中文",
    "settings.aiMode": "AI 模式", "settings.aiOff": "关闭 AI", "settings.retention": "Agent 运行目录保留天数", "settings.confirm": "结束会话前确认", "settings.savedLocal": "偏好保存在本地 SQLite。",
    "settings.privacy": "隐私模式固定为 local_only；设置、行情、账户和 Tutor 证据不会由应用上传。", "settings.save": "保存本地偏好",
    "settings.maintenance": "可恢复维护", "settings.backupCleanup": "备份与清理", "settings.createBackup": "创建数据库备份", "settings.recoveryNote": "恢复前会自动再创建一份备份。Agent 清理只移动到本地回收目录。",
    "settings.restore": "恢复", "settings.restoreConfirm": "恢复会替换当前数据库，继续吗？", "settings.noBackups": "还没有本地备份。", "settings.cleanup": "清理过期 Agent 运行目录", "settings.cleaned": "已移动 {{count}} 个目录到回收站。",
    "settings.aiBoundary": "Codex 不参与撮合、账本或确定性指标。失败时回放和模拟交易继续可用。"
  }}
} as const;

function normalizeLanguage(value?: string): AppLocale {
  return value?.toLowerCase().startsWith("zh") ? "zh-CN" : "en-US";
}

void i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources,
    fallbackLng: "en-US",
    supportedLngs: [...supportedLocales],
    load: "currentOnly",
    interpolation: { escapeValue: false },
    detection: {
      order: ["localStorage", "navigator"],
      lookupLocalStorage: "replaytutor:locale",
      caches: ["localStorage"],
    },
  });

export function resolveLocale(preference: LocalePreference): AppLocale {
  return preference === "system" ? normalizeLanguage(window.navigator.language) : preference;
}

export async function applyLocale(preference: LocalePreference): Promise<AppLocale> {
  const locale = resolveLocale(preference);
  window.localStorage.setItem("replaytutor:locale-preference", preference);
  window.localStorage.setItem("replaytutor:locale", locale);
  document.documentElement.lang = locale;
  await i18n.changeLanguage(locale);
  return locale;
}

export function currentLocale(): AppLocale {
  return normalizeLanguage(i18n.resolvedLanguage);
}

document.documentElement.lang = normalizeLanguage(i18n.resolvedLanguage);

export default i18n;
