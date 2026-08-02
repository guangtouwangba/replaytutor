from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from replaytutor.adapters.binance_private import BinanceReadOnlyClient
from replaytutor.modules.trade_review.episodes import FillRecord, reconstruct_episodes
from replaytutor.modules.trade_review.price_action import (
    ReviewBar,
    TimeframeRead,
    analyze_timeframe,
    resample_bars,
    review_dimensions,
)
from replaytutor.modules.trade_review.render import render_review_html


def fill(
    trade_id: int,
    side: str,
    qty: str,
    price: str,
    *,
    pnl: str = "0",
    position_side: str = "BOTH",
) -> FillRecord:
    return FillRecord(
        fill_id=f"fil_00000000-0000-7000-8000-{trade_id:012d}",
        symbol="BTCUSDT",
        trade_id=str(trade_id),
        order_id=str(1000 + trade_id),
        side=side,
        position_side=position_side,
        price=Decimal(price),
        qty=Decimal(qty),
        commission=Decimal("0.1"),
        realized_pnl=Decimal(pnl),
        executed_at=datetime(2026, 7, 27, tzinfo=UTC) + timedelta(minutes=trade_id),
        is_maker=False,
    )


def test_episode_reconstruction_handles_add_reduce_and_close() -> None:
    episodes = reconstruct_episodes(
        [
            fill(1, "BUY", "1", "100"),
            fill(2, "BUY", "1", "110"),
            fill(3, "SELL", "0.5", "120", pnl="7.5"),
            fill(4, "SELL", "1.5", "130", pnl="37.5"),
        ]
    )
    assert len(episodes) == 1
    episode = episodes[0]
    assert episode.status == "closed"
    assert episode.direction == "long"
    assert episode.entry_price == Decimal("105")
    assert episode.exit_price == Decimal("127.5")
    assert episode.peak_qty == Decimal("2")
    assert episode.realized_pnl == Decimal("45")
    assert [item["role"] for item in episode.allocations] == [
        "open",
        "add",
        "reduce",
        "close",
    ]


def test_episode_reconstruction_splits_reversal_without_losing_residual() -> None:
    episodes = reconstruct_episodes(
        [
            fill(1, "BUY", "1", "100"),
            fill(2, "SELL", "2", "90", pnl="-10"),
            fill(3, "BUY", "1", "80", pnl="10"),
        ]
    )
    assert [(item.direction, item.status) for item in episodes] == [
        ("long", "closed"),
        ("short", "closed"),
    ]
    assert episodes[0].peak_qty == Decimal("1")
    assert episodes[1].entry_price == Decimal("90")
    assert episodes[1].exit_price == Decimal("80")


def test_hedge_mode_keeps_long_and_short_episodes_separate() -> None:
    episodes = reconstruct_episodes(
        [
            fill(1, "BUY", "1", "100", position_side="LONG"),
            fill(2, "SELL", "1", "101", position_side="SHORT"),
            fill(3, "SELL", "1", "110", pnl="10", position_side="LONG"),
            fill(4, "BUY", "1", "90", pnl="11", position_side="SHORT"),
        ]
    )
    assert {(item.position_side, item.direction) for item in episodes} == {
        ("LONG", "long"),
        ("SHORT", "short"),
    }
    assert all(item.status == "closed" for item in episodes)


def synthetic_bars(count: int = 800) -> list[ReviewBar]:
    start = int(datetime(2026, 7, 1, tzinfo=UTC).timestamp() * 1000)
    bars: list[ReviewBar] = []
    price = 100.0
    for index in range(count):
        open_price = price
        price += 0.04
        bars.append(
            ReviewBar(
                open_ms=start + index * 60_000,
                close_ms=start + (index + 1) * 60_000 - 1,
                open=open_price,
                high=price + 0.03,
                low=open_price - 0.02,
                close=price,
                volume=100 + index,
            )
        )
    return bars


def test_resample_uses_utc_aligned_boundaries() -> None:
    bars = synthetic_bars(20)
    aggregated = resample_bars(bars, "5m")
    assert len(aggregated) == 4
    assert aggregated[0].open_ms % (5 * 60_000) == 0
    assert aggregated[0].open == bars[0].open
    assert aggregated[0].close == bars[4].close
    assert aggregated[0].volume == sum(item.volume for item in bars[:5])


def test_decision_time_analysis_ignores_future_bait() -> None:
    original = synthetic_bars()
    entry = original[599].close_ms
    baseline = analyze_timeframe(
        original, "15m", entry, original[-1].close_ms, 124, "long"
    )
    baited = list(original[:600])
    for index, bar in enumerate(original[600:], start=600):
        baited.append(
            ReviewBar(
                open_ms=bar.open_ms,
                close_ms=bar.close_ms,
                open=50 - index,
                high=51 - index,
                low=40 - index,
                close=41 - index,
                volume=999_999,
            )
        )
    bait = analyze_timeframe(baited, "15m", entry, baited[-1].close_ms, 124, "long")
    assert baseline.environment == bait.environment
    assert baseline.always_in == bait.always_in
    assert baseline.location == bait.location
    assert [item.model_dump() for item in baseline.annotations] == [
        item.model_dump() for item in bait.annotations
    ]


def timeframe_read(
    timeframe: str,
    *,
    environment: str = "range",
    always_in: str = "neutral",
    location: float = 0.5,
    atr: float = 1,
    breakout: str = "none",
) -> TimeframeRead:
    return TimeframeRead(
        timeframe=timeframe,
        bars=(),
        annotations=(),
        environment=environment,
        always_in=always_in,
        location=location,
        atr=atr,
        ema=100,
        slope_atr=0,
        overlap=0.6,
        breakout=breakout,
        pullback_signal=None,
        climax=False,
        entry_index=0,
    )


def test_complete_range_trade_is_critiqued_instead_of_marked_insufficient() -> None:
    reads = {
        timeframe: timeframe_read(timeframe)
        for timeframe in ("5m", "15m", "1h", "2h", "4h")
    }
    dimensions, _, improvements, _, outcome = review_dimensions(
        reads,
        "long",
        100,
        1,
        "closed",
        3,
        1,
        0.4,
    )

    assert outcome == "bad_trade_profit"
    assert "在交易区间中部入场，位置缺少边缘" in improvements
    assert "入场前没有识别到可验证的价格行为 Setup" in improvements
    assert any(
        item.dimension == "execution" and item.verdict == "improve"
        for item in dimensions
    )


def test_insufficient_outcome_is_reserved_for_missing_market_history() -> None:
    reads = {
        timeframe: timeframe_read(timeframe, environment="unknown", atr=0)
        for timeframe in ("5m", "15m", "1h", "2h", "4h")
    }
    _, _, _, _, outcome = review_dimensions(
        reads,
        "short",
        100,
        -1,
        "closed",
        0,
        1,
        None,
    )

    assert outcome == "insufficient_evidence"


def test_review_html_exposes_interactive_chart_viewport_and_label_layout() -> None:
    html = render_review_html({"title": "复盘交互测试"})

    assert 'data-chart-zoom="in"' in html
    assert "data-chart-reset" in html
    assert 'addEventListener("wheel"' in html
    assert 'addEventListener("pointerdown"' in html
    assert "function drawPointAnnotations" in html
    assert "function boxesOverlap" in html


def test_confirmed_breakout_is_not_penalized_for_leaving_range() -> None:
    reads = {
        timeframe: timeframe_read(timeframe)
        for timeframe in ("5m", "15m", "1h", "2h", "4h")
    }
    reads["5m"] = timeframe_read(
        "5m",
        environment="trend",
        always_in="short",
        location=-0.1,
    )
    reads["15m"] = timeframe_read(
        "15m",
        environment="transition",
        always_in="short",
        location=-0.1,
        breakout="strong_bear",
    )
    dimensions, positives, improvements, _, outcome = review_dimensions(
        reads,
        "short",
        100,
        1,
        "closed",
        3,
        1,
        0.7,
    )

    assert outcome == "good_trade_profit"
    assert "中周期出现同向强突破并获得跟随" in positives
    assert not any("区间" in item and "没有" in item for item in improvements)
    assert any(
        item.dimension == "location"
        and item.title == "强突破正在脱离原价值区"
        and item.verdict == "correct"
        for item in dimensions
    )


def test_review_routes_start_empty(client: TestClient) -> None:
    response = client.get("/api/v1/reviews")
    assert response.status_code == 200
    assert response.json() == {"schema_version": "1.0", "reviews": []}


@pytest.mark.asyncio
async def test_signed_get_resigns_after_timestamp_error(tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "binance": {
                    "api_key": "test-key",
                    "api_secret": "test-secret",
                    "testnet": False,
                }
            }
        ),
        encoding="utf-8",
    )
    signed_attempts = 0
    server_times = iter((1000, 2000))

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal signed_attempts
        if request.url.path == "/fapi/v1/time":
            return httpx.Response(200, json={"serverTime": next(server_times)})
        signed_attempts += 1
        if signed_attempts == 1:
            return httpx.Response(
                400,
                json={"code": -1021, "msg": "Timestamp outside recvWindow"},
            )
        assert request.url.params["timestamp"] == "2000"
        return httpx.Response(200, json=[])

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        client = BinanceReadOnlyClient(config_path, http)
        result = await client.user_trades(1, 2)

    assert result == []
    assert signed_attempts == 2
