from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from replaytutor.contracts import (
    Bar,
    IndicatorSpec,
    PriceValues,
    ReplayFrame,
)
from replaytutor.ids import new_id
from replaytutor.modules.indicators import IndicatorService


def make_bars(
    rows: list[tuple[str, str, str, str, str]],
    *,
    start: datetime | None = None,
) -> list[Bar]:
    started = start or datetime(2025, 1, 1, tzinfo=UTC)
    return [
        Bar(
            bar_id=new_id("bar"),
            instrument_id=new_id("ins"),
            timeframe="1m",
            open_time=started + timedelta(minutes=index),
            close_time=started + timedelta(minutes=index + 1),
            raw=PriceValues(open=open_, high=high, low=low, close=close, volume=volume),
        )
        for index, (open_, high, low, close, volume) in enumerate(rows)
    ]


def frame_for(bars: list[Bar]) -> ReplayFrame:
    return ReplayFrame(
        frame_id=new_id("frm"),
        session_id=new_id("ses"),
        revision=0,
        current_index=len(bars) - 1,
        total_bars=len(bars),
        visible_at=bars[-1].close_time,
        progress=1,
    )


def test_selected_indicator_evidence_uses_signed_visible_bars() -> None:
    bars = make_bars(
        [
            ("10", "12", "9", "11", "2"),
            ("11", "13", "10", "12", "3"),
            ("12", "14", "11", "13", "4"),
        ]
    )
    evidence = IndicatorService().evaluate(
        frame_for(bars),
        IndicatorSpec(
            instance_id="indicator-ma-test",
            definition_id="MA",
            timeframe="1m",
            params=[2],
        ),
        bars,
    )
    assert evidence.status == "ready"
    assert evidence.frame_id
    assert evidence.visible_at == bars[-1].close_time
    assert evidence.calculation_version == "indicator-core-v1"
    assert [point.values["ma1"] for point in evidence.points] == ["11.5", "12.5"]
    assert all(point.time <= bars[-1].close_time for point in evidence.points)


def test_indicator_service_rejects_future_bait() -> None:
    bars = make_bars(
        [("10", "12", "9", "11", "2"), ("999", "1000", "1", "999", "999")]
    )
    safe_frame = frame_for(bars[:1])
    with pytest.raises(ValueError, match="visible_at"):
        IndicatorService().evaluate(
            safe_frame,
            IndicatorSpec(
                instance_id="indicator-vwap-test",
                definition_id="VWAP",
            ),
            bars,
        )


def test_order_block_prefix_does_not_repaint_when_future_bars_arrive() -> None:
    bars = make_bars(
        [
            ("100", "103", "99", "102", "10"),
            ("102", "105", "101", "104", "10"),
            ("104", "106", "102", "103", "10"),
            ("103", "104", "98", "99", "10"),
            ("99", "101", "96", "98", "10"),
            ("98", "100", "97", "99", "10"),
            ("99", "102", "98", "101", "10"),
            ("101", "104", "100", "103", "10"),
            ("103", "108", "102", "107", "10"),
            ("107", "114", "106", "113", "10"),
            ("113", "116", "111", "115", "10"),
            ("115", "118", "114", "117", "10"),
            ("117", "119", "112", "113", "10"),
            ("113", "114", "108", "109", "10"),
        ]
    )
    spec = IndicatorSpec(
        instance_id="indicator-order-block-test",
        definition_id="ORDER_BLOCK",
        params=[3, 2, 1],
    )
    service = IndicatorService()
    prefix = bars[:12]
    first = service.evaluate(frame_for(prefix), spec, prefix)
    extended = service.evaluate(frame_for(bars), spec, bars)
    first_by_time = {point.time: point.values for point in first.points}
    extended_prefix = {
        point.time: point.values
        for point in extended.points
        if point.time <= prefix[-1].close_time
    }
    assert extended_prefix == first_by_time
