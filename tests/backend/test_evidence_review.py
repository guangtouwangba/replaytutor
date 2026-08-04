from __future__ import annotations

from fastapi.testclient import TestClient

from replaytutor.config import Settings
from replaytutor.contracts import AnnotationPoint, TutorChartInstruction
from replaytutor.ids import new_id
from replaytutor.modules.annotations import persist_ai_annotations
from replaytutor.storage.database import connect_database


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
    settings: Settings,
) -> None:
    created = create_session(client)
    session = created["session"]
    session_id = session["session_id"]
    hidden = client.get(f"/api/v1/sessions/{session_id}/review")
    assert hidden.status_code == 409
    user_annotation = client.post(
        f"/api/v1/sessions/{session_id}/annotations",
        json={
            "command_id": new_id("cmd"),
            "expected_revision": 0,
            "shape": "marker",
            "label": "用户证据",
            "points": [
                {
                    "time": created["bars"][-1]["close_time"],
                    "price": created["bars"][-1]["raw"]["close"],
                }
            ],
        },
    )
    assert user_annotation.status_code == 200

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
    advanced_body = advanced.json()
    ai_point = advanced_body["bars"][-1]
    with connect_database(settings.database_path) as connection:
        ai_annotations = persist_ai_annotations(
            connection,
            run_id=new_id("run"),
            session_id=session_id,
            frame_id=advanced_body["session"]["frame"]["frame_id"],
            instructions=[
                TutorChartInstruction(
                    tool="horizontal_line",
                    purpose="support",
                    timeframe="1m",
                    shape="line",
                    label="AI 证据",
                    evidence_ids=[ai_point["bar_id"]],
                    points=[
                        AnnotationPoint(
                            time=ai_point["close_time"],
                            price=ai_point["raw"]["close"],
                        )
                    ],
                )
            ],
        )
        connection.commit()
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
    assert {item["kind"] for item in body["evidence"]} >= {
        "plan",
        "order",
        "fill",
        "user_annotation",
        "ai_annotation",
    }
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
    assert body["equity_curve"]
    assert (
        body["equity_curve"][-1]["occurred_at"]
        == advanced_body["bars"][-1]["close_time"]
    )
    assert body["timeline"][-1]["kind"] == "session_completed"
    assert {item["key"] for item in body["dimension_observations"]} == {
        "environment",
        "plan",
        "risk",
        "execution",
        "management",
    }
    targets = {
        item["kind"]: client.get(
            f"/api/v1/sessions/{session_id}/evidence/{item['evidence_id']}"
        )
        for item in body["evidence"]
    }
    assert all(response.status_code == 200 for response in targets.values())
    assert (
        targets["plan"].json()["frame_id"]
        == plan.json()["execution"]["plan"]["frame_id"]
    )
    assert targets["order"].json()["order_id"] == order.json()["order"]["order_id"]
    assert (
        targets["fill"].json()["fill_id"]
        == advanced_body["execution"]["fills"][0]["fill_id"]
    )
    assert targets["user_annotation"].json()["layer"] == "user"
    assert (
        targets["ai_annotation"].json()["annotation_id"]
        == ai_annotations[0].annotation_id
    )
    bar_target = client.get(
        f"/api/v1/sessions/{session_id}/evidence/{ai_point['bar_id']}"
    )
    assert bar_target.status_code == 200
    assert bar_target.json()["kind"] == "bar"
    assert bar_target.json()["occurred_at"] == ai_point["close_time"]
    aggregate = client.get("/api/v1/training-reviews")
    assert aggregate.status_code == 200
    assert aggregate.json()["reviews"][0]["review_id"] == body["review_id"]
    dimensions = {item["key"]: item for item in aggregate.json()["dimensions"]}
    assert all(item["status"] == "insufficient" for item in dimensions.values())
    assert dimensions["environment"]["sample_count"] == 1
    assert dimensions["environment"]["passed_count"] == 1
    assert dimensions["plan"]["sample_count"] == 0
    assert aggregate.json()["recommendation"]["status"] == "insufficient"

    other = create_session(client)
    cross_session = client.get(
        f"/api/v1/sessions/{other['session']['session_id']}/evidence/"
        f"{user_annotation.json()['annotation_id']}"
    )
    unknown = client.get(f"/api/v1/sessions/{session_id}/evidence/{new_id('ann')}")
    assert cross_session.status_code == unknown.status_code == 404


def test_five_session_scores_and_recommendation_use_rules_not_profit(
    client: TestClient,
) -> None:
    snapshot = client.post("/api/v1/datasets/golden", json={}).json()
    playbooks = client.get("/api/v1/playbooks").json()["playbooks"]
    trend = next(
        item
        for item in playbooks
        if item["slug"] == "trend-pullback" and item["version"] == 2
    )
    breakout = next(
        item
        for item in playbooks
        if item["slug"] == "breakout-retest" and item["version"] == 2
    )
    session_ids: list[str] = []
    for index in range(5):
        playbook = trend if index < 3 else breakout
        created = client.post(
            "/api/v1/sessions",
            json={
                "snapshot_id": snapshot["snapshot_id"],
                "warmup_bars": 20,
                "playbook_id": playbook["playbook_id"],
            },
        ).json()
        session_id = created["session"]["session_id"]
        session_ids.append(session_id)
        annotated = client.post(
            f"/api/v1/sessions/{session_id}/annotations",
            json={
                "command_id": new_id("cmd"),
                "expected_revision": 0,
                "shape": "marker",
                "label": f"环境观察 {index}",
                "points": [
                    {
                        "time": created["bars"][-1]["close_time"],
                        "price": created["bars"][-1]["raw"]["close"],
                    }
                ],
            },
        )
        assert annotated.status_code == 200
        locked = client.post(
            f"/api/v1/sessions/{session_id}/plan",
            json={
                "command_id": new_id("cmd"),
                "expected_revision": 0,
                "side": "BUY",
                "thesis": "结构确认后执行",
                "invalidation": "结构失效退出",
                "risk_amount": "150",
            },
        )
        assert locked.status_code == 200
        ordered = client.post(
            f"/api/v1/sessions/{session_id}/orders",
            json={
                "command_id": new_id("cmd"),
                "expected_revision": 0,
                "side": "BUY",
                "order_type": "MARKET",
                "quantity": "0.01",
            },
        )
        assert ordered.status_code == 200
        finished = client.post(
            f"/api/v1/sessions/{session_id}/finish",
            json={"command_id": new_id("cmd"), "expected_revision": 0},
        )
        assert finished.status_code == 200

    aggregate = client.get("/api/v1/training-reviews").json()
    dimensions = {item["key"]: item for item in aggregate["dimensions"]}
    assert all(item["status"] == "ready" for item in dimensions.values())
    assert dimensions["environment"]["score"] == "100"
    assert dimensions["plan"]["score"] == "100"
    assert dimensions["risk"]["score"] == "0"
    assert dimensions["execution"]["score"] == "100"
    assert dimensions["management"]["score"] == "0"
    assert dimensions["risk"]["passed_count"] == 0
    assert dimensions["risk"]["evaluated_count"] == 10
    assert aggregate["recommendation"]["dimension"] == "risk"
    assert aggregate["recommendation"]["playbook_id"] == trend["playbook_id"]
    assert "不使用盈利排名" in aggregate["recommendation"]["reason"]

    deleted = client.delete(f"/api/v1/sessions/{session_ids[0]}")
    assert deleted.status_code == 200
    recomputed = client.get("/api/v1/training-reviews").json()
    assert all(
        item["status"] == "insufficient" and item["sample_count"] == 4
        for item in recomputed["dimensions"]
    )
    assert recomputed["recommendation"]["status"] == "insufficient"
