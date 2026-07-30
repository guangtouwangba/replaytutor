from __future__ import annotations

from decimal import Decimal

from fastapi.testclient import TestClient

from replaytutor.config import Settings
from replaytutor.ids import new_id
from replaytutor.modules.market_data.service import MarketDataService
from replaytutor.storage.database import connect_database


def create_golden_session(client: TestClient) -> dict:
    snapshot = client.post("/api/v1/datasets/golden", json={})
    assert snapshot.status_code == 200
    response = client.post(
        "/api/v1/sessions",
        json={
            "snapshot_id": snapshot.json()["snapshot_id"],
            "start_mode": "beginning",
            "seed": 7,
            "warmup_bars": 20,
            "initial_cash": "100000",
            "hidden_real_date": True,
        },
    )
    assert response.status_code == 200
    return response.json()


def test_plan_is_server_gate_and_market_order_fills_on_next_bar(
    client: TestClient,
    settings: Settings,
) -> None:
    created = create_golden_session(client)
    session = created["session"]
    session_id = session["session_id"]
    order_payload = {
        "command_id": new_id("cmd"),
        "expected_revision": 0,
        "side": "BUY",
        "order_type": "MARKET",
        "quantity": "0.01",
    }
    blocked = client.post(f"/api/v1/sessions/{session_id}/orders", json=order_payload)
    assert blocked.status_code == 422
    assert "locked trade plan" in blocked.json()["error"]["message"]

    plan_payload = {
        "command_id": new_id("cmd"),
        "expected_revision": 0,
        "side": "BUY",
        "thesis": "趋势回调后重新转强",
        "invalidation": "跌破当前结构低点",
        "risk_amount": "100",
    }
    locked = client.post(f"/api/v1/sessions/{session_id}/plan", json=plan_payload)
    assert locked.status_code == 200
    assert locked.json()["execution"]["plan"]["status"] == "locked"

    submitted = client.post(f"/api/v1/sessions/{session_id}/orders", json=order_payload)
    assert submitted.status_code == 200
    order = submitted.json()["order"]
    assert order["status"] == "PENDING"
    assert order["activate_index"] == session["frame"]["current_index"] + 1
    assert submitted.json()["execution"]["fills"] == []

    next_bar = MarketDataService(settings).query_snapshot_bar_slice(
        session["snapshot_id"],
        offset=order["activate_index"],
        limit=1,
    )[0]
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
    execution = advanced.json()["execution"]
    assert execution["orders"][0]["status"] == "FILLED"
    assert execution["fills"][0]["price"] == next_bar.raw.open
    assert execution["portfolio"]["position_quantity"] == "0.01"
    assert Decimal(execution["portfolio"]["cash"]) < Decimal(session["initial_cash"])

    with connect_database(settings.database_path) as connection:
        journal = connection.execute(
            "SELECT debit, credit FROM ledger_journal WHERE fill_id = ?",
            (execution["fills"][0]["fill_id"],),
        ).fetchall()
    assert sum(Decimal(row["debit"]) for row in journal) == sum(
        Decimal(row["credit"]) for row in journal
    )


def test_plan_and_order_command_ids_are_idempotent(client: TestClient) -> None:
    created = create_golden_session(client)
    session = created["session"]
    session_id = session["session_id"]
    plan_payload = {
        "command_id": new_id("cmd"),
        "expected_revision": 0,
        "side": "BUY",
        "thesis": "价格保持在结构上方",
        "invalidation": "收盘跌回结构下方",
        "risk_amount": "50",
    }
    first_plan = client.post(f"/api/v1/sessions/{session_id}/plan", json=plan_payload)
    replayed_plan = client.post(
        f"/api/v1/sessions/{session_id}/plan", json=plan_payload
    )
    assert first_plan.status_code == replayed_plan.status_code == 200
    assert replayed_plan.json()["idempotent_replay"]
    assert (
        replayed_plan.json()["execution"]["plan"]["plan_id"]
        == first_plan.json()["execution"]["plan"]["plan_id"]
    )


def test_bracket_children_wait_for_parent_and_oco_cancels_sibling(
    client: TestClient,
) -> None:
    created = create_golden_session(client)
    session = created["session"]
    session_id = session["session_id"]
    plan = client.post(
        f"/api/v1/sessions/{session_id}/plan",
        json={
            "command_id": new_id("cmd"),
            "expected_revision": 0,
            "side": "BUY",
            "thesis": "突破后跟随并使用保护性退出",
            "invalidation": "保护性止损被触发",
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
            "order_type": "MARKET",
            "quantity": "0.01",
            "take_profit_price": "1.00",
            "protective_stop_price": "1.00",
        },
    )
    assert submitted.status_code == 200
    orders = submitted.json()["execution"]["orders"]
    assert len(orders) == 3
    parent = next(order for order in orders if order["parent_order_id"] is None)
    children = [
        order for order in orders if order["parent_order_id"] == parent["order_id"]
    ]
    assert all(
        order["activate_index"] == session["frame"]["total_bars"] for order in children
    )

    parent_fill = client.post(
        f"/api/v1/sessions/{session_id}/commands",
        json={
            "command_id": new_id("cmd"),
            "expected_revision": 0,
            "kind": "advance",
            "bars": 1,
        },
    )
    assert parent_fill.status_code == 200
    after_parent = parent_fill.json()["execution"]
    assert len(after_parent["fills"]) == 1
    assert all(
        order["activate_index"] == session["frame"]["current_index"] + 2
        for order in after_parent["orders"]
        if order["parent_order_id"] is not None
    )

    child_fill = client.post(
        f"/api/v1/sessions/{session_id}/commands",
        json={
            "command_id": new_id("cmd"),
            "expected_revision": 1,
            "kind": "advance",
            "bars": 1,
        },
    )
    assert child_fill.status_code == 200
    after_child = child_fill.json()["execution"]
    assert len(after_child["fills"]) == 2
    child_statuses = {
        order["status"]
        for order in after_child["orders"]
        if order["parent_order_id"] is not None
    }
    assert child_statuses == {"FILLED", "CANCELLED"}
    assert after_child["portfolio"]["position_quantity"] == "0"


def test_pending_order_can_be_cancelled_idempotently(client: TestClient) -> None:
    created = create_golden_session(client)
    session = created["session"]
    session_id = session["session_id"]
    client.post(
        f"/api/v1/sessions/{session_id}/plan",
        json={
            "command_id": new_id("cmd"),
            "expected_revision": 0,
            "side": "BUY",
            "thesis": "等待更深回调的限价机会",
            "invalidation": "市场结构不再支持回调",
            "risk_amount": "50",
        },
    )
    submitted = client.post(
        f"/api/v1/sessions/{session_id}/orders",
        json={
            "command_id": new_id("cmd"),
            "expected_revision": 0,
            "side": "BUY",
            "order_type": "LIMIT",
            "quantity": "0.01",
            "limit_price": "1.00",
        },
    )
    order_id = submitted.json()["order"]["order_id"]
    cancel_payload = {
        "command_id": new_id("cmd"),
        "expected_revision": 0,
        "order_id": order_id,
    }
    cancelled = client.post(
        f"/api/v1/sessions/{session_id}/orders/cancel",
        json=cancel_payload,
    )
    replayed = client.post(
        f"/api/v1/sessions/{session_id}/orders/cancel",
        json=cancel_payload,
    )
    assert cancelled.status_code == replayed.status_code == 200
    assert cancelled.json()["order"]["status"] == "CANCELLED"
    assert replayed.json()["idempotent_replay"]
