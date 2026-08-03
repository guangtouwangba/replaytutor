from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from replaytutor.config import Settings
from replaytutor.contracts import (
    AnnotationPoint,
    TutorChartInstruction,
    TutorResponse,
)
from replaytutor.ids import new_id
from replaytutor.modules.annotations import persist_ai_annotations
from replaytutor.modules.tutor.validation import TutorValidationError, validate_evidence
from replaytutor.storage.database import connect_database


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
            "points": [
                {
                    "time": (
                        datetime.fromisoformat(session["frame"]["visible_at"])
                        + timedelta(minutes=1)
                    ).isoformat(),
                    "price": point["raw"]["close"],
                }
            ],
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


def test_user_annotation_revision_and_delete_are_append_only(
    client: TestClient,
    settings: Settings,
) -> None:
    created = _session(client)
    session = created["session"]
    point = created["bars"][-1]
    annotation = client.post(
        f"/api/v1/sessions/{session['session_id']}/annotations",
        json={
            "command_id": new_id("cmd"),
            "expected_revision": 0,
            "shape": "line",
            "label": "原始趋势线",
            "metadata": {"drawing_kind": "measure", "percent_change": "1.00"},
            "points": [
                {
                    "time": created["bars"][-2]["close_time"],
                    "price": created["bars"][-2]["raw"]["close"],
                },
                {"time": point["close_time"], "price": point["raw"]["close"]},
            ],
        },
    ).json()
    action_url = (
        f"/api/v1/sessions/{session['session_id']}/annotations/"
        f"{annotation['annotation_id']}/actions"
    )
    command_id = new_id("cmd")
    revision_payload = {
        "command_id": command_id,
        "expected_revision": 0,
        "action": "revised",
        "label": "修订趋势线",
        "points": [{"time": point["close_time"], "price": point["raw"]["close"]}],
        "metadata": {"drawing_kind": "measure", "percent_change": "2.50"},
        "style": {"line_color": "#ffcc00", "line_width": 3, "line_dash": "dashed"},
        "properties": {"locked": True, "hidden": False, "z_index": 2},
    }
    revised = client.post(action_url, json=revision_payload)
    replayed = client.post(action_url, json=revision_payload)
    assert revised.status_code == replayed.status_code == 200
    assert revised.json() == replayed.json()
    assert revised.json()["state"] == "active"
    assert revised.json()["effective_label"] == "修订趋势线"
    assert revised.json()["effective_metadata"]["percent_change"] == "2.50"
    assert revised.json()["effective_style"]["line_color"] == "#ffcc00"
    assert revised.json()["effective_style"]["line_width"] == 3
    assert revised.json()["effective_properties"]["locked"] is True
    assert revised.json()["original_annotation"]["label"] == "原始趋势线"
    assert revised.json()["original_annotation"]["metadata"]["percent_change"] == "1.00"

    deleted = client.post(
        action_url,
        json={
            "command_id": new_id("cmd"),
            "expected_revision": 0,
            "action": "deleted",
        },
    )
    assert deleted.status_code == 200
    assert deleted.json()["state"] == "deleted"
    assert deleted.json()["effective_label"] == "修订趋势线"
    restored = client.get(
        f"/api/v1/sessions/{session['session_id']}/annotations/dispositions"
    ).json()
    assert restored["dispositions"][0]["state"] == "deleted"
    assert restored["dispositions"][0]["effective_label"] == "修订趋势线"
    with connect_database(settings.database_path) as connection:
        original = connection.execute(
            "SELECT label FROM session_annotation WHERE annotation_id = ?",
            (annotation["annotation_id"],),
        ).fetchone()
        event_count = connection.execute(
            "SELECT COUNT(*) FROM session_annotation_event WHERE annotation_id = ?",
            (annotation["annotation_id"],),
        ).fetchone()[0]
        replacement_metadata = connection.execute(
            """
            SELECT replacement_metadata_json FROM session_annotation_event
            WHERE annotation_id = ? AND action = 'revised'
            """,
            (annotation["annotation_id"],),
        ).fetchone()[0]
    assert original["label"] == "原始趋势线"
    assert event_count == 2
    assert '"percent_change":"2.50"' in replacement_metadata


def test_ai_annotation_can_be_accepted_or_rejected(
    client: TestClient,
    settings: Settings,
) -> None:
    created = _session(client)
    session = created["session"]
    point = created["bars"][-1]
    with connect_database(settings.database_path) as connection:
        annotations = persist_ai_annotations(
            connection,
            run_id=new_id("run"),
            session_id=session["session_id"],
            frame_id=session["frame"]["frame_id"],
            instructions=[
                TutorChartInstruction(
                    shape="marker",
                    label="AI 候选标注",
                    evidence_ids=[point["bar_id"]],
                    points=[
                        AnnotationPoint(
                            time=datetime.fromisoformat(point["close_time"]),
                            price=point["raw"]["close"],
                        )
                    ],
                )
            ],
        )
        connection.commit()
    annotation = annotations[0]
    endpoint = (
        f"/api/v1/sessions/{session['session_id']}/annotations/"
        f"{annotation.annotation_id}/actions"
    )
    accepted = client.post(
        endpoint,
        json={
            "command_id": new_id("cmd"),
            "expected_revision": 0,
            "action": "accepted",
        },
    )
    assert accepted.status_code == 200
    assert accepted.json()["state"] == "accepted"
    assert accepted.json()["original_annotation"]["layer"] == "ai"

    rejected = client.post(
        endpoint,
        json={
            "command_id": new_id("cmd"),
            "expected_revision": 0,
            "action": "rejected",
        },
    )
    assert rejected.status_code == 200
    assert rejected.json()["state"] == "rejected"


def test_annotation_actions_reject_future_cross_session_and_stale_revision(
    client: TestClient,
) -> None:
    first = _session(client)
    second = _session(client)
    point = first["bars"][-1]
    annotation = client.post(
        f"/api/v1/sessions/{first['session']['session_id']}/annotations",
        json={
            "command_id": new_id("cmd"),
            "expected_revision": 0,
            "shape": "marker",
            "label": "边界测试",
            "points": [{"time": point["close_time"], "price": point["raw"]["close"]}],
        },
    ).json()
    wrong_session_url = (
        f"/api/v1/sessions/{second['session']['session_id']}/annotations/"
        f"{annotation['annotation_id']}/actions"
    )
    wrong_session = client.post(
        wrong_session_url,
        json={
            "command_id": new_id("cmd"),
            "expected_revision": 0,
            "action": "deleted",
        },
    )
    assert wrong_session.status_code == 422

    endpoint = (
        f"/api/v1/sessions/{first['session']['session_id']}/annotations/"
        f"{annotation['annotation_id']}/actions"
    )
    stale = client.post(
        endpoint,
        json={
            "command_id": new_id("cmd"),
            "expected_revision": 1,
            "action": "deleted",
        },
    )
    assert stale.status_code == 409
    future = client.post(
        endpoint,
        json={
            "command_id": new_id("cmd"),
            "expected_revision": 0,
            "action": "revised",
            "label": "未来点",
            "points": [
                {
                    "time": (
                        datetime.fromisoformat(first["session"]["frame"]["visible_at"])
                        + timedelta(minutes=1)
                    ).isoformat(),
                    "price": point["raw"]["close"],
                }
            ],
        },
    )
    assert future.status_code == 422
