from __future__ import annotations

from fastapi.testclient import TestClient

from replaytutor.config import Settings
from replaytutor.ids import new_id
from replaytutor.modules.market_data.service import MarketDataService
from replaytutor.modules.training_session.service import TrainingSessionService


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


def test_session_replay_is_future_safe_idempotent_and_recoverable(
    client: TestClient,
    settings: Settings,
) -> None:
    created = create_golden_session(client)
    session = created["session"]
    assert session["revision"] == 0
    assert session["frame"]["current_index"] == 19
    assert len(created["bars"]) == 20
    assert created["bars"][-1]["close_time"] == session["frame"]["visible_at"]
    assert all(
        bar["close_time"] <= session["frame"]["visible_at"]
        for bar in created["bars"]
    )

    future_bar = MarketDataService(settings).query_snapshot_bar_slice(
        session["snapshot_id"],
        offset=20,
        limit=1,
    )[0]
    assert future_bar.bar_id not in {bar["bar_id"] for bar in created["bars"]}

    command_id = new_id("cmd")
    command = {
        "command_id": command_id,
        "expected_revision": 0,
        "kind": "advance",
        "bars": 3,
    }
    advanced = client.post(
        f"/api/v1/sessions/{session['session_id']}/commands",
        json=command,
    )
    assert advanced.status_code == 200
    delta = advanced.json()
    assert delta["session"]["revision"] == 1
    assert delta["session"]["frame"]["current_index"] == 22
    assert delta["events"][0]["payload"]["advanced_bars"] == 3
    assert not delta["idempotent_replay"]

    replayed = client.post(
        f"/api/v1/sessions/{session['session_id']}/commands",
        json=command,
    )
    assert replayed.status_code == 200
    assert replayed.json()["session"]["revision"] == 1
    assert replayed.json()["idempotent_replay"]

    stale = client.post(
        f"/api/v1/sessions/{session['session_id']}/commands",
        json={
            "command_id": new_id("cmd"),
            "expected_revision": 0,
            "kind": "advance",
            "bars": 1,
        },
    )
    assert stale.status_code == 409
    assert stale.json()["error"]["code"] == "session_revision_conflict"
    assert stale.json()["error"]["details"]["current_revision"] == 1

    recovered = TrainingSessionService(settings).get(session["session_id"])
    assert recovered.session.revision == 1
    assert recovered.session.frame.current_index == 22
    assert recovered.bars[-1].close_time == recovered.session.frame.visible_at


def test_session_finish_is_idempotent_and_blocks_further_replay(
    client: TestClient,
) -> None:
    created = create_golden_session(client)
    session = created["session"]
    finish_command = {
        "command_id": new_id("cmd"),
        "expected_revision": 0,
    }
    finished = client.post(
        f"/api/v1/sessions/{session['session_id']}/finish",
        json=finish_command,
    )
    assert finished.status_code == 200
    body = finished.json()
    assert body["session"]["status"] == "completed"
    assert body["session"]["revision"] == 1
    assert body["revealed_coverage_end"] > body["session"]["frame"]["visible_at"]

    replayed = client.post(
        f"/api/v1/sessions/{session['session_id']}/finish",
        json=finish_command,
    )
    assert replayed.status_code == 200
    assert replayed.json()["idempotent_replay"]

    rejected = client.post(
        f"/api/v1/sessions/{session['session_id']}/commands",
        json={
            "command_id": new_id("cmd"),
            "expected_revision": 1,
            "kind": "advance",
            "bars": 1,
        },
    )
    assert rejected.status_code == 409
    assert rejected.json()["error"]["code"] == "invalid_session_state"

    listed = client.get("/api/v1/sessions")
    assert listed.status_code == 200
    assert listed.json()["sessions"][0]["status"] == "completed"
