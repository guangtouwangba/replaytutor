export type DemoLocale = "en-US" | "zh-CN";

export const copy = {
  "en-US": {
    intro: "Train decisions, not hindsight.",
    introDetail: "A local-first market replay and evidence-linked AI Tutor",
    data: "Choose BTCUSDT perpetual. Reuse local data or fill the missing range.",
    replay: "Future bars stay hidden behind the server-issued visible_at boundary.",
    execution: "Orders, fills, fees, and the ledger are deterministic.",
    tutor: "Tutor cites the current frame. It cannot rewrite trading state.",
    outro: "ReplayTutor",
    outroDetail: "Replay the market. Audit the decision.",
  },
  "zh-CN": {
    intro: "训练决策，而不是事后诸葛。",
    introDetail: "本地优先的行情回放与证据化 AI Tutor",
    data: "选择 BTCUSDT 永续合约。本地优先，缺失区间自动补齐。",
    replay: "未来 K 线始终隐藏在服务端签发的 visible_at 边界之后。",
    execution: "订单、成交、费用和账本全部由确定性模块计算。",
    tutor: "Tutor 只能引用当前 frame，不能改写交易状态。",
    outro: "ReplayTutor",
    outroDetail: "重放行情，核验决策。",
  },
} as const;
