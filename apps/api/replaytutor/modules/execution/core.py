from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

from replaytutor.contracts import Bar


@dataclass(frozen=True)
class MatchResult:
    filled: bool
    price: Decimal | None = None
    triggered: bool = False
    trail_anchor_price: Decimal | None = None


def match_order(
    *,
    side: Literal["BUY", "SELL"],
    order_type: Literal[
        "MARKET",
        "LIMIT",
        "STOP_MARKET",
        "STOP_LIMIT",
        "TAKE_PROFIT_MARKET",
        "TAKE_PROFIT_LIMIT",
        "TRAILING_STOP_MARKET",
    ],
    bar: Bar,
    limit_price: Decimal | None = None,
    stop_price: Decimal | None = None,
    activation_price: Decimal | None = None,
    callback_rate: Decimal | None = None,
    trail_anchor_price: Decimal | None = None,
    already_triggered: bool = False,
) -> MatchResult:
    open_price = Decimal(bar.raw.open)
    high = Decimal(bar.raw.high)
    low = Decimal(bar.raw.low)
    if order_type == "MARKET":
        return MatchResult(True, open_price)
    if order_type == "LIMIT":
        if limit_price is None:
            raise ValueError("Limit price is required")
        touched = low <= limit_price if side == "BUY" else high >= limit_price
        if not touched:
            return MatchResult(False)
        return MatchResult(
            True, min(open_price, limit_price) if side == "BUY" else max(open_price, limit_price)
        )
    if order_type == "TRAILING_STOP_MARKET":
        if callback_rate is None or not Decimal("0.001") <= callback_rate <= Decimal("0.10"):
            raise ValueError("Callback rate must be between 0.001 and 0.10")
        if trail_anchor_price is None:
            activated = (
                activation_price is None
                or (low <= activation_price if side == "BUY" else high >= activation_price)
            )
            if not activated:
                return MatchResult(False)
            anchor = low if side == "BUY" else high
            return MatchResult(False, triggered=True, trail_anchor_price=anchor)
        trigger = (
            trail_anchor_price * (Decimal("1") + callback_rate)
            if side == "BUY"
            else trail_anchor_price * (Decimal("1") - callback_rate)
        )
        touched = high >= trigger if side == "BUY" else low <= trigger
        if touched:
            price = max(open_price, trigger) if side == "BUY" else min(open_price, trigger)
            return MatchResult(True, price, triggered=True, trail_anchor_price=trail_anchor_price)
        anchor = min(trail_anchor_price, low) if side == "BUY" else max(trail_anchor_price, high)
        return MatchResult(False, triggered=True, trail_anchor_price=anchor)

    if order_type in {
        "STOP_MARKET",
        "STOP_LIMIT",
        "TAKE_PROFIT_MARKET",
        "TAKE_PROFIT_LIMIT",
    }:
        if stop_price is None:
            raise ValueError("Stop price is required")
        take_profit = order_type.startswith("TAKE_PROFIT")
        touched = (
            (low <= stop_price if side == "BUY" else high >= stop_price)
            if take_profit
            else (high >= stop_price if side == "BUY" else low <= stop_price)
        )
        triggered = already_triggered or touched
        if not triggered:
            return MatchResult(False)
        if order_type in {"STOP_LIMIT", "TAKE_PROFIT_LIMIT"}:
            if limit_price is None:
                raise ValueError("Limit price is required")
            if not already_triggered:
                # OHLC bars do not reveal whether the limit was reachable after the
                # trigger. Activate on the next bar to avoid optimistic fill ordering.
                return MatchResult(False, triggered=True)
            limit_touched = low <= limit_price if side == "BUY" else high >= limit_price
            if not limit_touched:
                return MatchResult(False, triggered=True)
            price = (
                min(open_price, limit_price)
                if side == "BUY"
                else max(open_price, limit_price)
            )
            return MatchResult(True, price, triggered=True)
        price = max(open_price, stop_price) if side == "BUY" else min(open_price, stop_price)
        return MatchResult(True, price, triggered=True)
    raise ValueError(f"Unsupported order type: {order_type}")
