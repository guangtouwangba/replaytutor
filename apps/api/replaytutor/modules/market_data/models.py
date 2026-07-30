from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass(frozen=True)
class NormalizedBar:
    open_time: datetime
    close_time: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
    source_row_id: str
    quality_flags: tuple[str, ...] = ()


@dataclass(frozen=True)
class NormalizedInstrument:
    symbol: str
    display_name: str
    market: str
    asset_class: str
    venue: str
    base_currency: str
    quote_currency: str
    timezone: str
    tick_size: Decimal
    lot_size: Decimal
    price_scale: int
    market_rule_set_id: str
