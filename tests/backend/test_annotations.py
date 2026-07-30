from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from replaytutor.contracts import (
    AnnotationPoint,
    TutorChartInstruction,
    TutorResponse,
)
from replaytutor.ids import new_id
from replaytutor.modules.tutor.validation import TutorValidationError, validate_evidence


def _session(client: TestClient) -> dict:
    snapshot = client.post("/api/v1/datasets/golden", json={}).json()
    response = client.post(
        "/api/v1/sessions",
        json={
            "snapshot_id": snapshot["snapshot_id"],
            "warmup_bars": 20,
            "initial_cash": "100000",
        },
    )
    assert response.status_code == 200
    return response.json()


def test_user_annotation_is_idempotent_and_frame_bounded(client: TestClient) -> None:
    created = _session(client)
    session = created["session"]
    point = created["bars"][-1]
    command_id = new_id("cmd")
    payload = {
        "command_id": command_id,
        "expected_revision": 0,
        "shape": "marker",
        "label": "我的入场观察",
        "points": [{"time": point["close_time"], "price": point["raw"]["close"]}],
    }
    endpoint = f"/api/v1/sessions/{session['session_id']}/annotations"
    first = client.post(endpoint, json=payload)
    replayed = client.post(endpoint, json=payload)
    assert first.status_code == replayed.status_code == 200
    assert first.json()["annotation_id"] == replayed.json()["annotation_id"]
    assert first.json()["layer"] == "user"
    restored = client.get(f"/api/v1/sessions/{session['session_id']}").json()
    assert [item["annotation_id"] for item in restored["annotations"]] == [
        first.json()["annotation_id"]
    ]

    future = client.post(
        endpoint,
        json={
            **payload,
            "command_id": new_id("cmd"),
            "points": [{
                "time": (
                    datetime.fromisoformat(session["frame"]["visible_at"])
                    + timedelta(minutes=1)
                ).isoformat(),
                "price": point["raw"]["close"],
            }],
        },
    )
    assert future.status_code == 422


def test_ai_annotation_evidence_is_whitelisted() -> None:
    response = TutorResponse(
        summary="结构测试",
        annotations=[
            TutorChartInstruction(
                shape="marker",
                label="潜在触发",
                evidence_ids=["bar_future"],
                points=[
                    AnnotationPoint(
                        time=datetime.now(UTC),
                        price="100",
                    )
                ],
            )
        ],
        disclaimer="仅用于训练",
    )
    try:
        validate_evidence(response, {"bar_visible"})
    except TutorValidationError as error:
        assert "bar_future" in str(error)
    else:
        raise AssertionError("Invalid annotation evidence must be rejected")
