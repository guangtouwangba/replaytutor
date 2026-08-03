from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient

from replaytutor.config import Settings
from replaytutor.contracts import Bar, PriceValues
from replaytutor.ids import new_id
from replaytutor.modules.execution.core import match_order
from replaytutor.modules.ledger import (
    FuturesLedgerState,
    apply_futures_fill,
    liquidation_price,
)
from replaytutor.storage.database import connect_database


def bar(*, open_: str, high: str, low: str, close: str) -> Bar:
    opened = datetime(2025, 1, 1, tzinfo=UTC)
    return Bar(
        bar_id=new_id("bar"),
        instrument_id=new_id("ins"),
        timeframe="1m",
        open_time=opened,
        close_time=opened + timedelta(minutes=1),
        raw=PriceValues(
            open=open_,
            high=high,
            low=low,
            close=close,
            volume="100",
        ),
    )


def test_stop_limit_waits_until_bar_after_trigger() -> None:
    trigger_bar = bar(open_="99", high="101", low="98", close="100")
    triggered = match_order(
        side="BUY",
        order_type="STOP_LIMIT",
        bar=trigger_bar,
        stop_price=Decimal("100"),
        limit_price=Decimal("99.5"),
    )
    assert triggered.triggered
    assert not triggered.filled
    next_bar = bar(open_="99.4", high="100", low="99", close="99.8")
    filled = match_order(
        side="BUY",
        order_type="STOP_LIMIT",
        bar=next_bar,
        stop_price=Decimal("100"),
        limit_price=Decimal("99.5"),
        already_triggered=True,
    )
    assert filled.filled
    assert filled.price == Decimal("99.4")


def test_trailing_stop_uses_prior_anchor_to_avoid_intrabar_lookahead() -> None:
    activated = match_order(
        side="SELL",
        order_type="TRAILING_STOP_MARKET",
        bar=bar(open_="100", high="105", low="99", close="104"),
        callback_rate=Decimal("0.01"),
    )
    assert activated.triggered
    assert activated.trail_anchor_price == Decimal("105")
    filled = match_order(
        side="SELL",
        order_type="TRAILING_STOP_MARKET",
        bar=bar(open_="104", high="104.5", low="103", close="103.5"),
        callback_rate=Decimal("0.01"),
        trail_anchor_price=Decimal("105"),
        already_triggered=True,
    )
    assert filled.filled
    assert filled.price == Decimal("103.95")


def test_hedge_ledger_keeps_long_and_short_independent() -> None:
    state = FuturesLedgerState(wallet_balance=Decimal("1000"))
    state = apply_futures_fill(
        state,
        side="BUY",
        position_side="LONG",
        position_mode="HEDGE",
        price=Decimal("100"),
        quantity=Decimal("2"),
        fee=Decimal("0.1"),
        reduce_only=False,
    )
    state = apply_futures_fill(
        state,
        side="SELL",
        position_side="SHORT",
        position_mode="HEDGE",
        price=Decimal("110"),
        quantity=Decimal("1"),
        fee=Decimal("0.05"),
        reduce_only=False,
    )
    assert state.long.quantity == Decimal("2")
    assert state.short.quantity == Decimal("1")
    assert liquidation_price(
        state,
        direction="LONG",
        margin_mode="ISOLATED",
        leverage=10,
        maintenance_margin_rate=Decimal("0.005"),
    ) == Decimal("90.45226130653266331658291457")


def test_usdt_perpetual_session_opens_leveraged_long(
    client: TestClient,
    settings: Settings,
) -> None:
    snapshot_response = client.post("/api/v1/datasets/golden", json={})
    snapshot = snapshot_response.json()
    with connect_database(settings.database_path) as connection:
        connection.execute(
            """UPDATE instrument SET asset_class = 'crypto_perpetual',
                venue = 'BINANCE_USDM',
                market_rule_set_id = 'binance_usdm_perpetual_v1'
            WHERE instrument_id = ?""",
            (snapshot["instrument"]["instrument_id"],),
        )
    created = client.post(
        "/api/v1/sessions",
        json={
            "snapshot_id": snapshot["snapshot_id"],
            "warmup_bars": 20,
            "account_type": "USDT_PERPETUAL",
            "margin_mode": "ISOLATED",
            "position_mode": "ONEWAY",
            "leverage": 10,
            "initial_cash": "10000",
        },
    )
    assert created.status_code == 200
    session = created.json()["session"]
    session_id = session["session_id"]
    plan = client.post(
        f"/api/v1/sessions/{session_id}/plan",
        json={
            "command_id": new_id("cmd"),
            "expected_revision": 0,
            "side": "BUY",
            "thesis": "永续合约趋势跟随开多",
            "invalidation": "跌破结构低点时失效",
            "risk_amount": "100",
        },
    )
    assert plan.status_code == 200
    submitted = client.post(
        f"/api/v1/sessions/{session_id}/orders",
        json={
            "command_id": new_id("cmd"),
            "expected_revision": 0,
            "side": "BUY",
            "position_side": "BOTH",
            "order_type": "MARKET",
            "quantity": "0.01",
        },
    )
    assert submitted.status_code == 200
    advanced = client.post(
        f"/api/v1/sessions/{session_id}/commands",
        json={
            "command_id": new_id("cmd"),
            "expected_revision": 0,
            "kind": "advance",
            "bars": 1,
        },
    )
    assert advanced.status_code == 200
    portfolio = advanced.json()["execution"]["portfolio"]
    assert portfolio["account_type"] == "USDT_PERPETUAL"
    assert portfolio["position_quantity"] == "0.01"
    assert portfolio["positions"][0]["position_side"] == "LONG"
    assert Decimal(portfolio["used_initial_margin"]) > 0
    assert Decimal(portfolio["available_balance"]) < Decimal("10000")
