from fastapi.testclient import TestClient

from replaytutor.ids import new_id


def test_official_playbooks_and_immutable_user_versions_bind_to_session(
    client: TestClient,
) -> None:
    listed = client.get("/api/v1/playbooks")
    assert listed.status_code == 200
    official = listed.json()["playbooks"]
    assert {item["slug"] for item in official} == {
        "trend-pullback",
        "breakout-retest",
        "range-reversal",
    }
    latest_official = [
        item for item in official if item["official"] and item["version"] == 2
    ]
    assert len(latest_official) == 3
    assert all(item["evaluator_version"] == "1.0" for item in latest_official)
    assert all(len(item["rule_definitions"]) == 6 for item in latest_official)
    assert all(
        definition["evaluator_kind"] != "free_text"
        for item in latest_official
        for definition in item["rule_definitions"]
    )
    legacy = [item for item in official if item["official"] and item["version"] == 1]
    assert all(item["evaluator_version"] == "legacy" for item in legacy)
    assert all(
        definition["evaluator_kind"] == "free_text"
        for item in legacy
        for definition in item["rule_definitions"]
    )
    payload = {
        "slug": "my-pullback",
        "name": "我的回调",
        "description": "个人规则",
        "rules": ["只在趋势上方", "必须定义失效"],
    }
    first = client.post("/api/v1/playbooks", json=payload)
    second = client.post("/api/v1/playbooks", json=payload)
    assert first.status_code == second.status_code == 200
    assert first.json()["version"] == 1
    assert second.json()["version"] == 2
    assert first.json()["playbook_id"] != second.json()["playbook_id"]

    snapshot = client.post("/api/v1/datasets/golden", json={}).json()
    session = client.post(
        "/api/v1/sessions",
        json={
            "snapshot_id": snapshot["snapshot_id"],
            "warmup_bars": 20,
            "playbook_id": first.json()["playbook_id"],
        },
    )
    assert session.status_code == 200
    assert session.json()["session"]["playbook_id"] == first.json()["playbook_id"]
    custom_checks = client.get(
        f"/api/v1/sessions/{session.json()['session']['session_id']}/playbook-checks"
    )
    assert custom_checks.status_code == 200
    assert {check["status"] for check in custom_checks.json()["checks"]} == {"unknown"}


def test_deterministic_playbook_checks_are_versioned_and_evidence_backed(
    client: TestClient,
) -> None:
    playbooks = client.get("/api/v1/playbooks").json()["playbooks"]
    playbook = next(
        item
        for item in playbooks
        if item["slug"] == "trend-pullback" and item["version"] == 2
    )
    snapshot = client.post("/api/v1/datasets/golden", json={}).json()
    created = client.post(
        "/api/v1/sessions",
        json={
            "snapshot_id": snapshot["snapshot_id"],
            "warmup_bars": 20,
            "playbook_id": playbook["playbook_id"],
        },
    ).json()
    session_id = created["session"]["session_id"]
    locked = client.post(
        f"/api/v1/sessions/{session_id}/plan",
        json={
            "command_id": new_id("cmd"),
            "expected_revision": 0,
            "side": "BUY",
            "thesis": "趋势结构保持完整",
            "invalidation": "跌破回调低点",
            "risk_amount": "150",
        },
    )
    assert locked.status_code == 200
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
    assert submitted.status_code == 200, submitted.json()

    first = client.get(f"/api/v1/sessions/{session_id}/playbook-checks")
    second = client.get(f"/api/v1/sessions/{session_id}/playbook-checks")
    assert first.status_code == second.status_code == 200
    assert first.json() == second.json()
    active = {check["rule_id"]: check for check in first.json()["checks"]}
    assert active["plan_locked_before_first_order"]["status"] == "passed"
    assert active["order_activated_on_next_bar"]["status"] == "passed"
    assert active["risk_amount_within_limit"]["status"] == "failed"
    assert active["protective_stop_present"]["status"] == "passed"
    assert active["no_order_after_session_complete"]["status"] == "unknown"
    assert active["entry_side_matches_locked_plan"]["status"] == "passed"

    finished = client.post(
        f"/api/v1/sessions/{session_id}/finish",
        json={
            "command_id": new_id("cmd"),
            "expected_revision": 0,
        },
    )
    assert finished.status_code == 200
    completed = client.get(f"/api/v1/sessions/{session_id}/playbook-checks").json()
    assert completed["playbook_id"] == playbook["playbook_id"]
    assert completed["evaluator_version"] == "1.0"
    checks = {check["rule_id"]: check for check in completed["checks"]}
    assert checks["no_order_after_session_complete"]["status"] == "passed"
    for check in completed["checks"]:
        if check["status"] in {"passed", "failed"}:
            assert check["evidence_ids"]
            for evidence_id in check["evidence_ids"]:
                resolved = client.get(
                    f"/api/v1/sessions/{session_id}/evidence/{evidence_id}"
                )
                assert resolved.status_code == 200

    review_one = client.get(f"/api/v1/sessions/{session_id}/review").json()
    review_two = client.get(f"/api/v1/sessions/{session_id}/review").json()
    assert review_one["review_hash"] == review_two["review_hash"]
    assert review_one["rule_checks"] == completed["checks"]
    assert review_one["playbook_evaluator_version"] == "1.0"
