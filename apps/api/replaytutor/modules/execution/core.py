from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

from replaytutor.contracts import Bar


@dataclass(frozen=True)
class MatchResult:
    filled: bool
    price: Decimal | None = None


def match_order(
    *,
    side: Literal["BUY", "SELL"],
    order_type: Literal["MARKET", "LIMIT", "STOP_MARKET"],
    bar: Bar,
    limit_price: Decimal | None = None,
    stop_price: Decimal | None = None,
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
    if stop_price is None:
        raise ValueError("Stop price is required")
    touched = high >= stop_price if side == "BUY" else low <= stop_price
    if not touched:
        return MatchResult(False)
    return MatchResult(
        True, max(open_price, stop_price) if side == "BUY" else min(open_price, stop_price)
    )
