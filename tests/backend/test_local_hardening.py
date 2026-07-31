from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from replaytutor.config import Settings
from replaytutor.ids import new_id
from replaytutor.modules.local_system import LocalSystemService
from replaytutor.modules.market_data.service import utc_text
from replaytutor.storage.database import connect_database


def create_session(client: TestClient) -> dict:
    snapshot = client.post("/api/v1/datasets/golden", json={}).json()
    response = client.post(
        "/api/v1/sessions",
        json={"snapshot_id": snapshot["snapshot_id"], "warmup_bars": 20},
    )
    assert response.status_code == 200
    return response.json()


def test_session_delete_is_recoverable_and_excluded_from_indexes(
    client: TestClient,
) -> None:
    created = create_session(client)
    session_id = created["session"]["session_id"]
    deleted = client.delete(f"/api/v1/sessions/{session_id}")
    assert deleted.status_code == 200
    assert deleted.json()["deleted_at"] is not None
    assert client.get(f"/api/v1/sessions/{session_id}").status_code == 404
    assert client.get(f"/api/v1/sessions/{session_id}/review").status_code == 404
    assert (
        client.get(f"/api/v1/sessions/{session_id}/playbook-checks").status_code == 404
    )
    assert client.get("/api/v1/sessions").json()["sessions"] == []
    trash = client.get("/api/v1/sessions-trash").json()["sessions"]
    assert [item["session_id"] for item in trash] == [session_id]

    restored = client.post(f"/api/v1/sessions/{session_id}/restore")
    assert restored.status_code == 200
    assert restored.json()["deleted_at"] is None
    assert client.get(f"/api/v1/sessions/{session_id}").status_code == 200


def test_preferences_backup_restore_and_recoverable_cleanup(
    client: TestClient,
    settings: Settings,
) -> None:
    defaults = client.get("/api/v1/settings/preferences")
    assert defaults.status_code == 200
    assert defaults.json()["ai_mode"] == "codex"
    saved = client.put(
        "/api/v1/settings/preferences",
        json={
            **defaults.json(),
            "ai_mode": "off",
            "retain_agent_runs_days": 7,
        },
    )
    assert saved.status_code == 200
    assert saved.json()["ai_mode"] == "off"
    session = create_session(client)
    tutor = client.post(
        f"/api/v1/sessions/{session['session']['session_id']}/tutor",
        json={"question": "检查本地 AI 模式", "stage": "plan"},
    )
    assert tutor.status_code == 409
    assert "disabled" in tutor.json()["error"]["message"]

    backup = client.post("/api/v1/maintenance/backups")
    assert backup.status_code == 200
    backup_id = backup.json()["backup_id"]
    assert len(backup.json()["sha256"]) == 64
    client.put(
        "/api/v1/settings/preferences",
        json={**saved.json(), "ai_mode": "codex"},
    )
    restored = client.post(f"/api/v1/maintenance/backups/{backup_id}/restore")
    assert restored.status_code == 200
    assert client.get("/api/v1/settings/preferences").json()["ai_mode"] == "off"
    assert len(client.get("/api/v1/maintenance").json()["backups"]) == 2

    old_run = settings.resolved_data_dir / "runtime" / "agent-runs" / "run_old-test"
    old_run.mkdir(parents=True)
    old_timestamp = (datetime.now(UTC) - timedelta(days=10)).timestamp()
    os.utime(old_run, (old_timestamp, old_timestamp))
    cleanup = client.post("/api/v1/maintenance/cleanup-agent-runs")
    assert cleanup.status_code == 200
    assert cleanup.json()["moved_agent_runs"] == 1
    assert not old_run.exists()
    assert (
        settings.resolved_data_dir / "trash" / "agent-runs" / "run_old-test"
    ).is_dir()


def test_restart_recovery_marks_orphaned_tutor_run_failed(
    client: TestClient,
    settings: Settings,
) -> None:
    created = create_session(client)
    session = created["session"]
    run_id = new_id("run")
    now = datetime.now(UTC)
    with connect_database(settings.database_path) as connection:
        connection.execute(
            """INSERT INTO tutor_run (
                run_id, session_id, frame_id, status, question, stage,
                workspace_path, created_at
            ) VALUES (?, ?, ?, 'running', ?, 'plan', ?, ?)""",
            (
                run_id,
                session["session_id"],
                session["frame"]["frame_id"],
                "orphan",
                str(settings.resolved_data_dir / "runtime" / "agent-runs" / run_id),
                utc_text(now),
            ),
        )
    assert LocalSystemService(settings).recover_orphaned_tutor_runs() == 1
    run = client.get(f"/api/v1/tutor/runs/{run_id}").json()
    assert run["status"] == "failed"
    assert "application restart" in run["error"]
