from __future__ import annotations

from fastapi.testclient import TestClient

from replaytutor.ids import new_id


def create_session(client: TestClient) -> dict:
    snapshot = client.post("/api/v1/datasets/golden", json={}).json()
    return client.post(
        "/api/v1/sessions",
        json={
            "snapshot_id": snapshot["snapshot_id"],
            "warmup_bars": 20,
            "initial_cash": "100000",
        },
    ).json()


def test_review_is_hidden_until_finish_then_stable_and_evidence_backed(
    client: TestClient,
) -> None:
    created = create_session(client)
    session = created["session"]
    session_id = session["session_id"]
    hidden = client.get(f"/api/v1/sessions/{session_id}/review")
    assert hidden.status_code == 409

    plan = client.post(
        f"/api/v1/sessions/{session_id}/plan",
        json={
            "command_id": new_id("cmd"),
            "expected_revision": 0,
            "side": "BUY",
            "thesis": "结构上方回调完成后跟随",
            "invalidation": "跌破结构低点则判断失效",
            "risk_amount": "100",
        },
    )
    assert plan.status_code == 200
    order = client.post(
        f"/api/v1/sessions/{session_id}/orders",
        json={
            "command_id": new_id("cmd"),
            "expected_revision": 0,
            "side": "BUY",
            "order_type": "MARKET",
            "quantity": "0.01",
        },
    )
    assert order.status_code == 200
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
    finished = client.post(
        f"/api/v1/sessions/{session_id}/finish",
        json={"command_id": new_id("cmd"), "expected_revision": 1},
    )
    assert finished.status_code == 200

    review = client.get(f"/api/v1/sessions/{session_id}/review")
    replayed = client.get(f"/api/v1/sessions/{session_id}/review")
    assert review.status_code == replayed.status_code == 200
    body = review.json()
    assert body["review_hash"] == replayed.json()["review_hash"]
    assert body["process_outcome"].startswith("good_process_")
    assert {item["kind"] for item in body["evidence"]} >= {"plan", "order", "fill"}
    assert {item["key"] for item in body["metrics"]} == {
        "net_pnl",
        "realized_pnl",
        "fees",
        "ending_equity",
        "trade_count",
        "win_rate",
        "mfe",
        "mae",
        "r_multiple",
        "max_drawdown",
        "exit_efficiency",
    }
    assert all(item["evidence_id"] for item in body["evidence"])
    aggregate = client.get("/api/v1/training-reviews")
    assert aggregate.status_code == 200
    assert aggregate.json()["reviews"][0]["review_id"] == body["review_id"]
    assert all(
        item["status"] == "insufficient"
        and item["score"] is None
        and item["sample_count"] == 1
        for item in aggregate.json()["dimensions"]
    )
