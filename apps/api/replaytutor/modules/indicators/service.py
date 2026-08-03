from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from replaytutor.contracts import (
    Bar,
    IndicatorEvidence,
    IndicatorEvidencePoint,
    IndicatorSpec,
    ReplayFrame,
)
from replaytutor.ids import new_id

CALCULATION_VERSION = "indicator-core-v1"


def _decimal(value: float) -> Decimal:
    return Decimal(str(value))


def _render(value: Decimal) -> str:
    rendered = format(value.normalize(), "f")
    return "0" if rendered in {"-0", ""} else rendered


def _true_range(current: Bar, previous: Bar | None) -> Decimal:
    high = Decimal(current.raw.high)
    low = Decimal(current.raw.low)
    if previous is None:
        return high - low
    previous_close = Decimal(previous.raw.close)
    return max(high - low, abs(high - previous_close), abs(low - previous_close))


def _atr(bars: list[Bar], period: int) -> list[Decimal | None]:
    period = max(1, period)
    result: list[Decimal | None] = []
    running = Decimal(0)
    previous_atr: Decimal | None = None
    for index, bar in enumerate(bars):
        value = _true_range(bar, bars[index - 1] if index else None)
        if index < period:
            running += value
        if index < period - 1:
            result.append(None)
        elif index == period - 1:
            previous_atr = running / Decimal(period)
            result.append(previous_atr)
        else:
            previous_atr = (
                (previous_atr or value) * Decimal(period - 1) + value
            ) / Decimal(period)
            result.append(previous_atr)
    return result


def _ma(bars: list[Bar], periods: list[int]) -> list[dict[str, str]]:
    periods = [max(1, period) for period in periods]
    closes = [Decimal(bar.raw.close) for bar in bars]
    result: list[dict[str, str]] = [{} for _ in bars]
    for parameter_index, period in enumerate(periods):
        running = Decimal(0)
        key = f"ma{parameter_index + 1}"
        for index, close in enumerate(closes):
            running += close
            if index >= period:
                running -= closes[index - period]
            if index >= period - 1:
                result[index][key] = _render(running / Decimal(period))
    return result


def _ema(bars: list[Bar], periods: list[int]) -> list[dict[str, str]]:
    closes = [Decimal(bar.raw.close) for bar in bars]
    result: list[dict[str, str]] = [{} for _ in bars]
    for parameter_index, raw_period in enumerate(periods):
        period = max(1, raw_period)
        current: Decimal | None = None
        key = f"ema{parameter_index + 1}"
        for index, close in enumerate(closes):
            if index < period - 1:
                continue
            if current is None:
                current = sum(closes[:period], Decimal(0)) / Decimal(period)
            else:
                current = (
                    Decimal(2) * close + Decimal(period - 1) * current
                ) / Decimal(period + 1)
            result[index][key] = _render(current)
    return result


def _volume(bars: list[Bar], periods: list[int]) -> list[dict[str, str]]:
    volumes = [Decimal(bar.raw.volume) for bar in bars]
    result = [{"volume": _render(volume)} for volume in volumes]
    for parameter_index, raw_period in enumerate(periods):
        period = max(1, raw_period)
        running = Decimal(0)
        key = f"ma{parameter_index + 1}"
        for index, volume in enumerate(volumes):
            running += volume
            if index >= period:
                running -= volumes[index - period]
            if index >= period - 1:
                result[index][key] = _render(running / Decimal(period))
    return result


def _obv(bars: list[Bar], period: int) -> list[dict[str, str]]:
    period = max(1, period)
    total = Decimal(0)
    running = Decimal(0)
    history: list[Decimal] = []
    result: list[dict[str, str]] = []
    for index, bar in enumerate(bars):
        if index:
            close = Decimal(bar.raw.close)
            previous = Decimal(bars[index - 1].raw.close)
            volume = Decimal(bar.raw.volume)
            if close > previous:
                total += volume
            elif close < previous:
                total -= volume
        history.append(total)
        running += total
        values = {"obv": _render(total)}
        if index >= period - 1:
            values["maObv"] = _render(running / Decimal(period))
            running -= history[index - (period - 1)]
        result.append(values)
    return result


def _vwap(bars: list[Bar]) -> list[dict[str, str]]:
    volume_total = Decimal(0)
    price_volume = Decimal(0)
    result: list[dict[str, str]] = []
    for bar in bars:
        volume = max(Decimal(0), Decimal(bar.raw.volume))
        typical = (
            Decimal(bar.raw.high) + Decimal(bar.raw.low) + Decimal(bar.raw.close)
        ) / Decimal(3)
        volume_total += volume
        price_volume += typical * volume
        result.append(
            {"vwap": _render(price_volume / volume_total)} if volume_total else {}
        )
    return result


@dataclass
class _Zone:
    top: Decimal
    bottom: Decimal
    confirmed_at: int
    mitigated: bool = False
    invalidated: bool = False


def _pivot_high(bars: list[Bar], index: int, radius: int) -> bool:
    target = Decimal(bars[index].raw.high)
    return all(
        candidate == index or Decimal(bars[candidate].raw.high) < target
        for candidate in range(index - radius, index + radius + 1)
    )


def _pivot_low(bars: list[Bar], index: int, radius: int) -> bool:
    target = Decimal(bars[index].raw.low)
    return all(
        candidate == index or Decimal(bars[candidate].raw.low) > target
        for candidate in range(index - radius, index + radius + 1)
    )


def _last_opposite(bars: list[Bar], before: int, bullish: bool) -> Bar | None:
    for index in range(before, max(-1, before - 20), -1):
        open_ = Decimal(bars[index].raw.open)
        close = Decimal(bars[index].raw.close)
        if (bullish and close < open_) or (not bullish and close > open_):
            return bars[index]
    return None


def _order_blocks(
    bars: list[Bar], atr_period: int, radius: int, multiplier: Decimal
) -> list[dict[str, str]]:
    atr = _atr(bars, atr_period)
    swing_high: tuple[int, Decimal] | None = None
    swing_low: tuple[int, Decimal] | None = None
    consumed_high = -1
    consumed_low = -1
    bull: _Zone | None = None
    bear: _Zone | None = None
    result: list[dict[str, str]] = []
    for index, bar in enumerate(bars):
        confirmed = index - radius
        if confirmed >= radius:
            if _pivot_high(bars, confirmed, radius):
                swing_high = (confirmed, Decimal(bars[confirmed].raw.high))
            if _pivot_low(bars, confirmed, radius):
                swing_low = (confirmed, Decimal(bars[confirmed].raw.low))
        current_atr = atr[index]
        threshold = current_atr * multiplier if current_atr is not None else None
        displacement = threshold is not None and _true_range(
            bar, bars[index - 1] if index else None
        ) >= threshold
        close = Decimal(bar.raw.close)
        if displacement and swing_high and swing_high[0] > consumed_high and close > swing_high[1]:
            source = _last_opposite(bars, index - 1, True)
            if source:
                bull = _Zone(
                    top=Decimal(source.raw.high),
                    bottom=Decimal(source.raw.low),
                    confirmed_at=index,
                )
                consumed_high = swing_high[0]
        if displacement and swing_low and swing_low[0] > consumed_low and close < swing_low[1]:
            source = _last_opposite(bars, index - 1, False)
            if source:
                bear = _Zone(
                    top=Decimal(source.raw.high),
                    bottom=Decimal(source.raw.low),
                    confirmed_at=index,
                )
                consumed_low = swing_low[0]
        high = Decimal(bar.raw.high)
        low = Decimal(bar.raw.low)
        if bull and index > bull.confirmed_at:
            if close < bull.bottom:
                bull.invalidated = True
            elif low <= bull.top and high >= bull.bottom:
                bull.mitigated = True
        if bear and index > bear.confirmed_at:
            if close > bear.top:
                bear.invalidated = True
            elif low <= bear.top and high >= bear.bottom:
                bear.mitigated = True
        values: dict[str, str] = {}
        if bull and not bull.invalidated:
            values.update(
                bull_top=_render(bull.top),
                bull_bottom=_render(bull.bottom),
                bull_status="mitigated" if bull.mitigated else "active",
            )
        if bear and not bear.invalidated:
            values.update(
                bear_top=_render(bear.top),
                bear_bottom=_render(bear.bottom),
                bear_status="mitigated" if bear.mitigated else "active",
            )
        result.append(values)
    return result


class IndicatorService:
    """Deterministically evaluate explicitly selected indicators for one signed frame."""

    def evaluate(
        self,
        frame: ReplayFrame,
        spec: IndicatorSpec,
        bars: list[Bar],
    ) -> IndicatorEvidence:
        if any(bar.close_time > frame.visible_at for bar in bars):
            raise ValueError("Indicator input extends beyond visible_at")
        if any(bar.timeframe != spec.timeframe for bar in bars):
            raise ValueError("Indicator input timeframe does not match the selected instance")
        params = spec.params
        if spec.definition_id == "MA":
            values = _ma(bars, [int(value) for value in params] if params else [5, 10, 30, 60])
        elif spec.definition_id == "EMA":
            values = _ema(bars, [int(value) for value in params] if params else [6, 12, 20])
        elif spec.definition_id == "VOL":
            values = _volume(bars, [int(value) for value in params] if params else [5, 10, 20])
        elif spec.definition_id == "OBV":
            values = _obv(bars, int(params[0]) if params else 30)
        elif spec.definition_id == "VWAP":
            values = _vwap(bars)
        elif spec.definition_id == "ATR":
            period = int(params[0]) if params else 14
            values = [
                {"atr": _render(item)} if item is not None else {}
                for item in _atr(bars, period)
            ]
        elif spec.definition_id == "BAR_COUNT":
            values = [{"count": str(index + 1)} for index in range(len(bars))]
        else:
            values = _order_blocks(
                bars,
                max(1, int(params[0])) if params else 14,
                max(1, int(params[1])) if len(params) > 1 else 3,
                _decimal(params[2]) if len(params) > 2 else Decimal("1.5"),
            )
        points = [
            IndicatorEvidencePoint(bar_id=bar.bar_id, time=bar.close_time, values=value)
            for bar, value in zip(bars, values, strict=True)
            if value
        ][-50:]
        return IndicatorEvidence(
            evidence_id=new_id("iev"),
            frame_id=frame.frame_id,
            visible_at=frame.visible_at,
            instance_id=spec.instance_id,
            definition_id=spec.definition_id,
            timeframe=spec.timeframe,
            params=params,
            status="ready" if points else "insufficient_data",
            calculation_version=CALCULATION_VERSION,
            points=points,
        )
