from fastapi.testclient import TestClient


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
