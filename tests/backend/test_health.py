from __future__ import annotations

from fastapi.testclient import TestClient


def test_health_reports_local_runtime(client: TestClient) -> None:
    response = client.get("/api/v1/health", headers={"X-Request-ID": "test-request"})

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "test-request"
    payload = response.json()
    assert payload["schema_version"] == "1.0"
    assert payload["status"] == "healthy"
    assert payload["request_id"] == "test-request"
    assert payload["api"] == {"status": "healthy", "version": "0.1.0", "detail": None}
    assert payload["database"]["journal_mode"] == "wal"
    assert payload["database"]["foreign_keys"] is True
    assert payload["database"]["migration_current"] == "0012_local_hardening"
    assert payload["database"]["migration_head"] == "0012_local_hardening"
    assert [agent["agent_id"] for agent in payload["agents"]] == ["codex-local"]
    assert all(agent["authentication"] == "not_checked" for agent in payload["agents"])


def test_not_found_uses_error_envelope(client: TestClient) -> None:
    response = client.get("/api/v1/does-not-exist", headers={"X-Request-ID": "missing"})

    assert response.status_code == 404
    assert response.json() == {
        "error": {
            "code": "not_found",
            "message": "Not Found",
            "retryable": False,
            "request_id": "missing",
            "details": {},
        }
    }


def test_cors_allows_only_configured_origin(client: TestClient) -> None:
    allowed = client.options(
        "/api/v1/health",
        headers={
            "Origin": "http://127.0.0.1:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    denied = client.options(
        "/api/v1/health",
        headers={
            "Origin": "http://192.168.1.10:5173",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert allowed.status_code == 200
    assert allowed.headers["access-control-allow-origin"] == "http://127.0.0.1:5173"
    assert denied.status_code == 400
    assert "access-control-allow-origin" not in denied.headers
