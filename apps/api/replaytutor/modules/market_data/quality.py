from __future__ import annotations

from collections import Counter
from datetime import timedelta
from itertools import pairwise

from replaytutor.contracts import DataQuality
from replaytutor.modules.market_data.models import NormalizedBar


def inspect_bars(bars: list[NormalizedBar], *, continuous: bool) -> DataQuality:
    duplicate_count = sum(
        count - 1 for count in Counter(bar.open_time for bar in bars).values() if count > 1
    )
    invalid_ohlc_count = sum(
        1
        for bar in bars
        if not (
            bar.low <= bar.open <= bar.high
            and bar.low <= bar.close <= bar.high
            and bar.volume >= 0
            and bar.open_time < bar.close_time
        )
    )
    ordered = sorted({bar.open_time for bar in bars})
    gap_count = 0
    if continuous:
        gap_count = sum(
            max(0, int((current - previous) / timedelta(minutes=1)) - 1)
            for previous, current in pairwise(ordered)
        )
    flags: list[str] = []
    if duplicate_count:
        flags.append("duplicate_open_time")
    if gap_count:
        flags.append("missing_1m_bar")
    if invalid_ohlc_count:
        flags.append("invalid_ohlc")
    if not bars:
        flags.append("empty_dataset")
    status = "failed" if duplicate_count or invalid_ohlc_count or not bars else "passed"
    if status == "passed" and gap_count:
        status = "warning"
    return DataQuality(
        status=status,
        row_count=len(bars),
        duplicate_count=duplicate_count,
        gap_count=gap_count,
        invalid_ohlc_count=invalid_ohlc_count,
        flags=flags,
    )
