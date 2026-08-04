from __future__ import annotations

from fastapi.testclient import TestClient


def companion(client: TestClient, request_id: str, method: str, params: dict) -> dict:
    response = client.post(
        "/api/v1/companion",
        json={
            "protocol_version": "1.0",
            "request_id": request_id,
            "method": method,
            "params": params,
        },
    )
    assert response.status_code == 200
    return response.json()


def create_session(client: TestClient) -> dict:
    snapshot = client.post("/api/v1/datasets/golden", json={}).json()
    created = client.post(
        "/api/v1/sessions",
        json={
            "snapshot_id": snapshot["snapshot_id"],
            "warmup_bars": 20,
        },
    )
    assert created.status_code == 200
    return created.json()["session"]


def test_companion_bootstrap_and_health_do_not_expose_local_paths(client: TestClient) -> None:
    bootstrap = companion(
        client,
        "req_bootstrap-0001",
        "system.bootstrap",
        {"extension_version": "0.1.0", "locale": "zh-CN"},
    )
    assert bootstrap["ok"] is True
    assert bootstrap["result"]["compatible_protocols"] == ["1.0"]
    assert "tutor.run" in bootstrap["result"]["capabilities"]

    health = companion(client, "req_health-0001", "system.health", {})
    assert health["ok"] is True
    assert health["result"]["status"] == "healthy"
    assert "path" not in health["result"]


def test_companion_rejects_unknown_methods_and_arbitrary_proxy_params(
    client: TestClient,
) -> None:
    forbidden = companion(
        client,
        "req_forbidden-0001",
        "orders.submit",
        {"url": "http://127.0.0.1:8788/api/v1/sessions/arbitrary/orders"},
    )
    assert forbidden == {
        "protocol_version": "1.0",
        "request_id": "req_forbidden-0001",
        "ok": False,
        "result": None,
        "error": {
            "code": "method_not_allowed",
            "message": "Companion method is not allowed",
            "retryable": False,
        },
    }

    invalid = companion(
        client,
        "req_invalid-0001",
        "system.health",
        {"url": "http://127.0.0.1:8788/api/v1/health"},
    )
    assert invalid["ok"] is False
    assert invalid["error"]["code"] == "payload_invalid"


def test_companion_fails_closed_for_protocol_drift_and_oversized_payloads(
    client: TestClient,
) -> None:
    incompatible = client.post(
        "/api/v1/companion",
        json={
            "protocol_version": "2.0",
            "request_id": "req_protocol-0001",
            "method": "system.health",
            "params": {},
        },
    ).json()
    assert incompatible["ok"] is False
    assert incompatible["error"]["code"] == "protocol_incompatible"

    oversized = client.post(
        "/api/v1/companion",
        json={
            "protocol_version": "1.0",
            "request_id": "req_oversized-0001",
            "method": "system.health",
            "params": {"padding": "x" * (512 * 1024)},
        },
    ).json()
    assert oversized["ok"] is False
    assert oversized["error"]["code"] == "payload_too_large"


def test_companion_returns_only_session_summary_and_safe_navigation(
    client: TestClient,
) -> None:
    session = create_session(client)
    listed = companion(client, "req_sessions-0001", "session.list", {"limit": 10})
    assert listed["ok"] is True
    summary = listed["result"]["sessions"][0]
    assert summary["session_id"] == session["session_id"]
    assert summary["frame_id"] == session["frame"]["frame_id"]
    assert summary["visible_at"] == session["frame"]["visible_at"]
    assert "initial_cash" not in summary
    assert "fingerprint" not in summary

    target = companion(
        client,
        "req_navigation-0001",
        "navigation.open_replaytutor",
        {"session_id": session["session_id"], "mode": "review"},
    )
    assert target["ok"] is True
    assert target["result"]["path"] == f"/sessions/{session['session_id']}?mode=replay"
