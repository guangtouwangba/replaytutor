from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import UTC, datetime

# ruff: noqa: RUF001
from itertools import pairwise
from statistics import fmean

from replaytutor.contracts import (
    AnnotationPoint,
    PriceActionAnnotation,
    ReviewDimension,
)

TIMEFRAME_MINUTES = {"5m": 5, "15m": 15, "1h": 60, "2h": 120, "4h": 240}


@dataclass(frozen=True)
class ReviewBar:
    open_ms: int
    close_ms: int
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass(frozen=True)
class TimeframeRead:
    timeframe: str
    bars: tuple[dict[str, object], ...]
    annotations: tuple[PriceActionAnnotation, ...]
    environment: str
    always_in: str
    location: float
    atr: float
    ema: float
    slope_atr: float
    overlap: float
    breakout: str
    pullback_signal: str | None
    climax: bool
    entry_index: int


def bars_from_binance(rows: list[list[object]]) -> list[ReviewBar]:
    return [
        ReviewBar(
            open_ms=int(str(row[0])),
            open=float(str(row[1])),
            high=float(str(row[2])),
            low=float(str(row[3])),
            close=float(str(row[4])),
            volume=float(str(row[5])),
            close_ms=int(str(row[6])),
        )
        for row in rows
    ]


def resample_bars(bars: list[ReviewBar], timeframe: str) -> list[ReviewBar]:
    interval_ms = TIMEFRAME_MINUTES[timeframe] * 60_000
    buckets: dict[int, list[ReviewBar]] = {}
    for bar in bars:
        bucket = bar.open_ms // interval_ms * interval_ms
        buckets.setdefault(bucket, []).append(bar)
    result: list[ReviewBar] = []
    for bucket, group in sorted(buckets.items()):
        ordered = sorted(group, key=lambda item: item.open_ms)
        result.append(
            ReviewBar(
                open_ms=bucket,
                close_ms=bucket + interval_ms - 1,
                open=ordered[0].open,
                high=max(item.high for item in ordered),
                low=min(item.low for item in ordered),
                close=ordered[-1].close,
                volume=sum(item.volume for item in ordered),
            )
        )
    return result


def analyze_timeframe(
    source: list[ReviewBar],
    timeframe: str,
    entry_ms: int,
    exit_ms: int,
    entry_price: float,
    direction: str,
) -> TimeframeRead:
    all_bars = resample_bars(source, timeframe)
    decision = [bar for bar in all_bars if bar.close_ms <= entry_ms]
    if len(decision) < 25:
        return insufficient_read(all_bars, timeframe, entry_ms)

    decision_entry = len(decision) - 1
    start = max(0, decision_entry - 119)
    final_ms = max(entry_ms, exit_ms)
    after = [index for index, bar in enumerate(all_bars) if bar.open_ms <= final_ms]
    end_base = after[-1] if after else decision_entry
    end = min(len(all_bars), end_base + 61)
    visible = all_bars[start:end]
    entry_index = decision_entry - start

    closes = [bar.close for bar in decision]
    ema_values = ema_series(closes, 20)
    atr_values = atr_series(decision, 14)
    atr = max(atr_values[-1], 1e-12)
    recent = decision[-40:]
    slope = regression_slope([bar.close for bar in recent])
    slope_atr = slope / atr
    overlap = overlap_ratio(recent)
    ema = ema_values[-1]
    above = sum(bar.close > ema_values[-len(recent) + i] for i, bar in enumerate(recent))
    directional = above / len(recent)
    if slope_atr > 0.06 and directional >= 0.62 and overlap < 0.62:
        environment, always_in = "trend", "long"
    elif slope_atr < -0.06 and directional <= 0.38 and overlap < 0.62:
        environment, always_in = "trend", "short"
    elif abs(slope_atr) < 0.08 and overlap >= 0.42:
        environment, always_in = "range", "neutral"
    else:
        environment = "transition"
        always_in = "long" if slope_atr > 0.04 else "short" if slope_atr < -0.04 else "neutral"

    range_high = max(bar.high for bar in recent)
    range_low = min(bar.low for bar in recent)
    location = (entry_price - range_low) / max(range_high - range_low, 1e-12)
    breakout = breakout_state(decision, atr)
    pullback = pullback_signal(decision, environment, always_in)
    climax = climax_state(decision, atr)
    annotations = build_annotations(
        timeframe,
        decision,
        entry_price,
        range_low,
        range_high,
        environment,
        always_in,
        location,
        breakout,
        pullback,
        climax,
        direction,
    )

    display_ema = ema_series([bar.close for bar in visible], 20)
    chart_bars = tuple(
        {
            "t": bar.open_ms,
            "ct": bar.close_ms,
            "o": bar.open,
            "h": bar.high,
            "l": bar.low,
            "c": bar.close,
            "v": bar.volume,
            "ema20": display_ema[index],
        }
        for index, bar in enumerate(visible)
    )
    return TimeframeRead(
        timeframe=timeframe,
        bars=chart_bars,
        annotations=tuple(annotations),
        environment=environment,
        always_in=always_in,
        location=location,
        atr=atr,
        ema=ema,
        slope_atr=slope_atr,
        overlap=overlap,
        breakout=breakout,
        pullback_signal=pullback,
        climax=climax,
        entry_index=entry_index,
    )


def insufficient_read(
    bars: list[ReviewBar],
    timeframe: str,
    entry_ms: int,
) -> TimeframeRead:
    visible = bars[-180:]
    return TimeframeRead(
        timeframe=timeframe,
        bars=tuple(
            {
                "t": bar.open_ms,
                "ct": bar.close_ms,
                "o": bar.open,
                "h": bar.high,
                "l": bar.low,
                "c": bar.close,
                "v": bar.volume,
                "ema20": None,
            }
            for bar in visible
        ),
        annotations=(
            annotation(
                timeframe,
                "background",
                "label",
                "数据不足，无法确认背景",
                "入场前已收盘 K 线少于 25 根",
                "price-action-coach:insufficient-evidence",
                1,
                "decision_time",
                "unknown",
                [(entry_ms, visible[-1].close if visible else 0)],
            ),
        ),
        environment="unknown",
        always_in="neutral",
        location=0.5,
        atr=0,
        ema=0,
        slope_atr=0,
        overlap=0,
        breakout="unknown",
        pullback_signal=None,
        climax=False,
        entry_index=max(0, len(visible) - 1),
    )


def build_annotations(
    timeframe: str,
    decision: list[ReviewBar],
    entry_price: float,
    range_low: float,
    range_high: float,
    environment: str,
    always_in: str,
    location: float,
    breakout: str,
    pullback: str | None,
    climax: bool,
    direction: str,
) -> list[PriceActionAnnotation]:
    recent = decision[-40:]
    start_ms, end_ms = recent[0].open_ms, recent[-1].close_ms
    result = [
        annotation(
            timeframe,
            "background",
            "label",
            f"{environment_label(environment)} · Always-In {always_in.upper()}",
            "基于最近 40 根已收盘 K 线的斜率、EMA20 与重叠度",
            "price-action-thinking:context-over-signal",
            0.78 if environment != "transition" else 0.58,
            "decision_time",
            (
                "correct"
                if always_in == direction
                else "improve"
                if always_in != "neutral"
                else "neutral"
            ),
            [(end_ms, entry_price)],
        ),
        annotation(
            timeframe,
            "location",
            "zone",
            "背景观察区间",
            "最近 40 根已收盘 K 线的可见高低边界",
            "price-action-trading-ranges:boundaries",
            0.82,
            "decision_time",
            "neutral",
            [(start_ms, range_low), (end_ms, range_high)],
        ),
        annotation(
            timeframe,
            "location",
            "line",
            "区间中轴 / 价值区",
            f"入场位于观察区间的 {location:.0%}",
            "price-action-trading-ranges:range-midpoint",
            0.8,
            "decision_time",
            "improve" if environment == "range" and 0.35 <= location <= 0.65 else "neutral",
            [(start_ms, (range_low + range_high) / 2), (end_ms, (range_low + range_high) / 2)],
        ),
    ]
    for kind, index, price in swing_points(decision)[-8:]:
        result.append(
            annotation(
                timeframe,
                "background",
                "marker",
                kind,
                "仅使用入场前已形成的局部波段",
                "price-action-coach:swing-sequence",
                0.72,
                "decision_time",
                "neutral",
                [(decision[index].open_ms, price)],
            )
        )
    if breakout != "none":
        result.append(
            annotation(
                timeframe,
                "setup",
                "marker",
                breakout_label(breakout),
                "突破幅度、收盘位置与可见跟随共同判定",
                "price-action-trading-ranges:breakout-follow-through",
                0.7,
                "decision_time",
                "neutral",
                [(end_ms, decision[-1].close)],
            )
        )
    if pullback:
        result.append(
            annotation(
                timeframe,
                "setup",
                "marker",
                pullback,
                "按趋势背景中的恢复尝试计数；区间内不机械使用",
                "price-action-trading-ranges:bar-counting",
                0.62,
                "decision_time",
                (
                    "correct"
                    if (
                        (pullback.startswith("H") and direction == "long")
                        or (pullback.startswith("L") and direction == "short")
                    )
                    else "neutral"
                ),
                [(end_ms, decision[-1].close)],
            )
        )
    if climax:
        result.append(
            annotation(
                timeframe,
                "execution",
                "label",
                "高潮/过度延伸风险",
                "入场前出现相对 ATR 明显放大的晚期趋势 K 线",
                "price-action-thinking:climax",
                0.7,
                "decision_time",
                "improve",
                [(end_ms, entry_price)],
            )
        )
    return result


def context_evidence(read: TimeframeRead) -> str:
    return (
        f"{read.timeframe}: {environment_label(read.environment)}，"
        f"Always-In {read.always_in}，斜率 {read.slope_atr:.2f} ATR/Bar，"
        f"重叠度 {read.overlap:.0%}"
    )


def review_dimensions(
    reads: dict[str, TimeframeRead],
    direction: str,
    entry_price: float,
    realized_pnl: float,
    status: str,
    mfe: float,
    mae: float,
    exit_efficiency: float | None,
) -> tuple[list[ReviewDimension], list[str], list[str], list[str], str]:
    positives: list[str] = []
    improvements: list[str] = []
    missing: list[str] = []
    dimensions: list[ReviewDimension] = []
    context_reads = [reads[item] for item in ("4h", "2h") if item in reads]
    aligned = sum(read.always_in == direction for read in context_reads)
    opposed = sum(read.always_in not in {direction, "neutral"} for read in context_reads)
    if aligned:
        evidence = [context_evidence(read) for read in context_reads]
        positives.append("交易方向至少得到一个高周期 Always-In 支持")
        dimensions.append(dimension("background", "correct", "高周期方向有支持", evidence))
    elif opposed:
        evidence = [context_evidence(read) for read in context_reads]
        improvements.append("交易方向与高周期 Always-In 背景相反")
        dimensions.append(dimension("background", "improve", "逆高周期背景", evidence))
    else:
        dimensions.append(
            dimension(
                "background",
                "unknown",
                "高周期没有方向优势",
                [
                    *[context_evidence(read) for read in context_reads],
                    "这不是行情数据缺失；含义是高周期处于区间/过渡，不能把交易当成高胜率顺势单",
                ],
            )
        )

    primary = reads.get("15m") or reads.get("1h")
    primary_breakout_direction = (
        "long"
        if primary and primary.breakout == "strong_bull"
        else "short"
        if primary and primary.breakout == "strong_bear"
        else None
    )
    if primary and primary_breakout_direction == direction:
        positives.append("中周期出现同向强突破并获得跟随")
        dimensions.append(
            dimension(
                "location",
                "correct",
                "强突破正在脱离原价值区",
                [
                    f"{primary.timeframe}: {primary.breakout}，位置 {primary.location:.0%}",
                    "此时不能机械套用区间边缘规则；关键是突破后的连续收盘与跟随",
                ],
            )
        )
    elif primary and primary_breakout_direction not in {None, direction}:
        improvements.append("中周期强突破方向与交易方向相反")
        dimensions.append(
            dimension(
                "location",
                "improve",
                "逆强突破方向入场",
                [f"{primary.timeframe}: {primary.breakout}"],
            )
        )
    elif primary and primary.environment == "range" and 0.35 <= primary.location <= 0.65:
        improvements.append("在交易区间中部入场，位置缺少边缘")
        dimensions.append(
            dimension(
                "location",
                "improve",
                "区间中部入场",
                [f"{primary.timeframe} 区间位置 {primary.location:.0%}"],
            )
        )
    elif primary and (
        (direction == "long" and primary.location <= 0.35)
        or (direction == "short" and primary.location >= 0.65)
    ):
        positives.append("入场位置靠近对交易方向有利的观察区间边缘")
        dimensions.append(
            dimension(
                "location",
                "correct",
                "入场位置具有区间边缘",
                [f"{primary.timeframe} 区间位置 {primary.location:.0%}"],
            )
        )
    elif primary and primary.environment == "trend" and primary.always_in == direction:
        positives.append("中周期处于同向趋势，入场不依赖区间边缘")
        dimensions.append(
            dimension(
                "location",
                "correct",
                "同向趋势中的位置可接受",
                [
                    f"{primary.timeframe}: {context_evidence(primary)}",
                    f"观察窗口位置 {primary.location:.0%}；趋势交易主要看回调结构而非机械买低卖高",
                ],
            )
        )
    elif primary and primary.environment in {"range", "transition"}:
        outside_range = primary.location < 0 or primary.location > 1
        improvement = (
            "价格已经冲出观察区间，但突破没有得到足够确认"
            if outside_range
            else "中周期处于区间或过渡，但入场没有位于有利边缘"
        )
        improvements.append(improvement)
        dimensions.append(
            dimension(
                "location",
                "improve",
                ("区间外追价，但突破质量不足" if outside_range else "区间/过渡中的位置没有优势"),
                [
                    (
                        f"{primary.timeframe}: {primary.environment}，"
                        f"观察窗口位置 {primary.location:.0%}"
                    ),
                    (
                        "成交价已在观察区间之外，但没有同向强突破+跟随，属于追逐未确认行情"
                        if outside_range
                        else "既不是明确的低买/高卖边缘，也没有强突破证明市场正在离开价值区"
                    ),
                ],
            )
        )
    elif primary and primary.environment == "trend":
        improvements.append("中周期趋势方向与交易方向相反")
        dimensions.append(
            dimension(
                "location",
                "improve",
                "逆中周期趋势入场",
                [context_evidence(primary)],
            )
        )
    else:
        dimensions.append(
            dimension(
                "location",
                "unknown",
                "位置数据不可用",
                ["对应周期入场前已收盘 K 线不足，无法计算区间位置"],
            )
        )

    setup = reads.get("15m")
    pullback_matches = bool(
        setup
        and setup.pullback_signal
        and (
            (setup.pullback_signal.startswith("H") and direction == "long")
            or (setup.pullback_signal.startswith("L") and direction == "short")
        )
    )
    if setup and pullback_matches:
        positives.append(f"入场前出现可识别的 {setup.pullback_signal} 恢复尝试")
        dimensions.append(
            dimension(
                "setup",
                "correct",
                f"存在 {setup.pullback_signal} 结构",
                ["信号基于入场前已收盘 K 线计数"],
            )
        )
    elif setup and setup.pullback_signal:
        improvements.append(f"{setup.pullback_signal} 恢复尝试方向与实际交易方向相反")
        dimensions.append(
            dimension(
                "setup",
                "improve",
                f"{setup.pullback_signal} 不是本次交易方向的 Setup",
                [
                    f"15m Always-In {setup.always_in}，实际方向 {direction}",
                    "不能只因为出现 H1/H2/L1/L2 名称就把它当成有效入场结构",
                ],
            )
        )
    elif setup and setup.breakout.startswith("weak"):
        improvements.append("突破缺乏跟随，Setup 质量需要降级")
        dimensions.append(
            dimension(
                "setup",
                "improve",
                "弱突破或失败突破",
                [
                    f"15m 突破状态 {setup.breakout}",
                    "突破没有连续收盘跟随，应等待回调确认或按失败突破处理",
                ],
            )
        )
    elif setup and setup.breakout.startswith("failed"):
        fade_direction = "short" if setup.breakout == "failed_bull" else "long"
        verdict = "correct" if direction == fade_direction else "improve"
        message = (
            "交易方向利用了失败突破后的反向机会"
            if verdict == "correct"
            else "交易方向仍在追逐已经失败的突破"
        )
        (positives if verdict == "correct" else improvements).append(message)
        dimensions.append(
            dimension(
                "setup",
                verdict,
                ("失败突破反向 Setup 成立" if verdict == "correct" else "追逐失败突破"),
                [
                    f"15m 突破状态 {setup.breakout}，实际方向 {direction}",
                    "价格返回原区间后，原突破方向的交易者更可能被困",
                ],
            )
        )
    elif setup and setup.breakout.startswith("strong"):
        breakout_direction = "long" if setup.breakout.endswith("bull") else "short"
        verdict = "correct" if breakout_direction == direction else "improve"
        message = "强突破方向与交易一致" if verdict == "correct" else "强突破方向与实际交易相反"
        (positives if verdict == "correct" else improvements).append(message)
        dimensions.append(
            dimension(
                "setup",
                verdict,
                message,
                [f"15m 突破状态 {setup.breakout}"],
            )
        )
    elif setup and setup.atr > 0:
        improvements.append("入场前没有识别到可验证的价格行为 Setup")
        dimensions.append(
            dimension(
                "setup",
                "improve",
                "结构依据偏弱：没有可验证 Setup",
                [
                    f"15m 为 {setup.environment}，breakout={setup.breakout}，未形成 H1/H2/L1/L2",
                    "这不代表一定亏损；它表示入场缺少可复述、可重复训练的结构理由",
                ],
            )
        )
    else:
        dimensions.append(
            dimension(
                "setup",
                "unknown",
                "Setup 数据不可用",
                ["15m 入场前已收盘 K 线不足，不强行套形态"],
            )
        )

    missing.append("仅凭成交时间无法证明是否等待信号 K 收盘")
    dimensions.append(dimension("trigger", "unknown", "触发纪律无法完全验证", missing[-1:]))

    trigger = reads.get("5m")
    if trigger and trigger.climax and abs(entry_price - trigger.ema) > 1.8 * trigger.atr:
        improvements.append("入场距离 EMA20 过远且处于高潮延伸，存在追价证据")
        dimensions.append(
            dimension(
                "execution",
                "improve",
                "高潮延伸后追价",
                [f"距 5m EMA20 {abs(entry_price - trigger.ema) / max(trigger.atr, 1e-12):.2f} ATR"],
            )
        )
    elif trigger and trigger.always_in == direction:
        positives.append("5 分钟执行方向与局部控制方向一致")
        dimensions.append(
            dimension("execution", "correct", "执行方向有局部结构支持", ["5m Always-In 同向"])
        )
    elif trigger and trigger.atr > 0:
        improvements.append("入场时 5 分钟没有同向控制优势")
        dimensions.append(
            dimension(
                "execution",
                "improve",
                "低周期执行缺少同向控制",
                [
                    context_evidence(trigger),
                    "若这是区间边缘限价单，需要交易计划证明；否则属于在低周期无确认时猜方向",
                ],
            )
        )
    else:
        dimensions.append(
            dimension(
                "execution",
                "unknown",
                "执行数据不可用",
                ["5m 入场前已收盘 K 线不足"],
            )
        )

    if status == "open":
        dimensions.append(
            dimension("management", "unknown", "交易仍在进行", ["不对未完成交易下最终结论"])
        )
        dimensions.append(dimension("outcome", "unknown", "结果尚未形成", ["open episode"]))
        return dimensions, positives, improvements, missing, "open_trade"

    if exit_efficiency is not None and mfe > 0:
        if exit_efficiency >= 0.65:
            positives.append("离场保留了大部分可实现顺向波动")
            dimensions.append(
                dimension(
                    "management",
                    "correct",
                    "离场效率较高",
                    [f"保留约 {exit_efficiency:.0%} 的 MFE"],
                )
            )
        elif exit_efficiency <= 0.2 and mae < mfe:
            improvements.append("大部分 MFE 被回吐，管理层需要复盘")
            dimensions.append(
                dimension(
                    "management",
                    "improve",
                    "顺向波动回吐明显",
                    [f"仅保留约 {exit_efficiency:.0%} 的 MFE"],
                )
            )
        else:
            dimensions.append(
                dimension("management", "unknown", "管理结果中性", [f"MFE {mfe:.4f}"])
            )
    else:
        dimensions.append(
            dimension("management", "unknown", "缺少可比较的管理路径", ["MFE 不为正或行情不完整"])
        )

    complete_market_evidence = all(
        timeframe in reads and reads[timeframe].atr > 0
        for timeframe in ("5m", "15m", "1h", "2h", "4h")
    )
    decisive_dimensions = [
        item
        for item in dimensions
        if item.dimension in {"background", "location", "setup", "execution", "management"}
    ]
    process_bad = any(item.verdict == "improve" for item in decisive_dimensions)
    process_good = (
        complete_market_evidence
        and not process_bad
        and any(item.verdict == "correct" for item in decisive_dimensions)
    )
    profitable = realized_pnl > 0
    if not complete_market_evidence:
        outcome = "insufficient_evidence"
    elif process_good:
        outcome = "good_trade_profit" if profitable else "good_trade_loss"
    elif process_bad:
        outcome = "bad_trade_profit" if profitable else "bad_trade_loss"
    else:
        outcome = "bad_trade_profit" if profitable else "bad_trade_loss"
        improvements.append("完整行情存在，但没有识别到足以支持入场的结构优势")
    dimensions.append(
        dimension(
            "outcome",
            (
                "correct"
                if outcome.startswith("good")
                else "improve"
                if outcome.startswith("bad")
                else "unknown"
            ),
            outcome_label(outcome),
            ["盈亏与过程质量分开评价"],
        )
    )
    return dimensions, positives, improvements, missing, outcome


def dimension(
    name: str,
    verdict: str,
    title: str,
    evidence: list[str],
) -> ReviewDimension:
    return ReviewDimension.model_validate(
        {
            "dimension": name,
            "verdict": verdict,
            "title": title,
            "evidence": evidence,
        }
    )


def annotation(
    timeframe: str,
    layer: str,
    shape: str,
    label: str,
    evidence: str,
    rule_id: str,
    confidence: float,
    perspective: str,
    verdict: str,
    points: list[tuple[int, float]],
) -> PriceActionAnnotation:
    key = f"{timeframe}:{layer}:{rule_id}:{points[0][0] if points else 0}"
    return PriceActionAnnotation.model_validate(
        {
            "annotation_id": hash_id(key),
            "timeframe": timeframe,
            "layer": layer,
            "shape": shape,
            "label": label,
            "evidence": evidence,
            "rule_id": rule_id,
            "confidence": confidence,
            "perspective": perspective,
            "points": [
                AnnotationPoint(
                    time=datetime.fromtimestamp(stamp / 1000, tz=UTC),
                    price=decimal_string(price),
                )
                for stamp, price in points
            ],
            "verdict": verdict,
        }
    )


def ema_series(values: list[float], period: int) -> list[float]:
    if not values:
        return []
    alpha = 2 / (period + 1)
    result = [values[0]]
    for value in values[1:]:
        result.append(alpha * value + (1 - alpha) * result[-1])
    return result


def atr_series(bars: list[ReviewBar], period: int) -> list[float]:
    if not bars:
        return []
    true_ranges = [bars[0].high - bars[0].low]
    for previous, current in pairwise(bars):
        true_ranges.append(
            max(
                current.high - current.low,
                abs(current.high - previous.close),
                abs(current.low - previous.close),
            )
        )
    return ema_series(true_ranges, period)


def regression_slope(values: list[float]) -> float:
    if len(values) < 2:
        return 0
    x_mean = (len(values) - 1) / 2
    y_mean = fmean(values)
    numerator = sum((index - x_mean) * (value - y_mean) for index, value in enumerate(values))
    denominator = sum((index - x_mean) ** 2 for index in range(len(values)))
    return numerator / denominator if denominator else 0


def overlap_ratio(bars: list[ReviewBar]) -> float:
    values: list[float] = []
    for left, right in pairwise(bars):
        overlap = max(0.0, min(left.high, right.high) - max(left.low, right.low))
        union = max(left.high, right.high) - min(left.low, right.low)
        values.append(overlap / union if union else 1)
    return fmean(values) if values else 0


def swing_points(bars: list[ReviewBar]) -> list[tuple[str, int, float]]:
    points: list[tuple[str, int, float]] = []
    for index in range(2, len(bars) - 2):
        current = bars[index]
        window = bars[index - 2 : index + 3]
        if current.high == max(item.high for item in window):
            previous_highs = [price for kind, _, price in points if kind in {"HH", "LH"}]
            kind = "HH" if not previous_highs or current.high > previous_highs[-1] else "LH"
            points.append((kind, index, current.high))
        if current.low == min(item.low for item in window):
            previous_lows = [price for kind, _, price in points if kind in {"HL", "LL"}]
            kind = "HL" if not previous_lows or current.low > previous_lows[-1] else "LL"
            points.append((kind, index, current.low))
    return points


def breakout_state(bars: list[ReviewBar], atr: float) -> str:
    if len(bars) < 23:
        return "none"
    signal = bars[-3]
    prior = bars[-23:-3]
    high, low = max(item.high for item in prior), min(item.low for item in prior)
    body = abs(signal.close - signal.open)
    span = max(signal.high - signal.low, 1e-12)
    follow = bars[-2:]
    if signal.close > high:
        strong = body / span >= 0.6 and all(item.close >= high for item in follow)
        return "strong_bull" if strong else "weak_bull"
    if signal.close < low:
        strong = body / span >= 0.6 and all(item.close <= low for item in follow)
        return "strong_bear" if strong else "weak_bear"
    if max(item.high for item in bars[-3:]) > high + 0.1 * atr:
        return "failed_bull"
    if min(item.low for item in bars[-3:]) < low - 0.1 * atr:
        return "failed_bear"
    return "none"


def pullback_signal(bars: list[ReviewBar], environment: str, always_in: str) -> str | None:
    if environment != "trend" or len(bars) < 12:
        return None
    recent = bars[-12:]
    if always_in == "long":
        attempts = sum(
            recent[index].high > recent[index - 1].high for index in range(1, len(recent))
        )
        return "H2" if attempts >= 2 else "H1" if attempts == 1 else None
    if always_in == "short":
        attempts = sum(recent[index].low < recent[index - 1].low for index in range(1, len(recent)))
        return "L2" if attempts >= 2 else "L1" if attempts == 1 else None
    return None


def climax_state(bars: list[ReviewBar], atr: float) -> bool:
    if len(bars) < 8 or atr <= 0:
        return False
    last = bars[-1]
    large = abs(last.close - last.open) >= 1.4 * atr
    direction = math.copysign(1, last.close - last.open or 1)
    pushes = sum(math.copysign(1, bar.close - bar.open or 1) == direction for bar in bars[-5:])
    return large and pushes >= 4


def environment_label(value: str) -> str:
    return {"trend": "趋势", "range": "交易区间", "transition": "过渡"}.get(value, "未知")


def breakout_label(value: str) -> str:
    return {
        "strong_bull": "强多头突破并有跟随",
        "strong_bear": "强空头突破并有跟随",
        "weak_bull": "多头突破但跟随不足",
        "weak_bear": "空头突破但跟随不足",
        "failed_bull": "上破失败",
        "failed_bear": "下破失败",
    }.get(value, value)


def outcome_label(value: str) -> str:
    return {
        "good_trade_profit": "好交易盈利",
        "good_trade_loss": "好交易亏损",
        "bad_trade_profit": "坏交易盈利",
        "bad_trade_loss": "坏交易亏损",
        "insufficient_evidence": "证据不足",
    }.get(value, value)


def decimal_string(value: float) -> str:
    return format(value, ".12f").rstrip("0").rstrip(".") or "0"


def hash_id(value: str) -> str:
    import hashlib

    return hashlib.sha256(value.encode()).hexdigest()[:20]
