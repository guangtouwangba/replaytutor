from __future__ import annotations

from decimal import Decimal

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


def test_session_can_start_from_a_user_selected_snapshot_time(
    client: TestClient,
) -> None:
    snapshot = client.post("/api/v1/datasets/golden", json={})
    assert snapshot.status_code == 200

    response = client.post(
        "/api/v1/sessions",
        json={
            "snapshot_id": snapshot.json()["snapshot_id"],
            "start_mode": "specific",
            "start_time": "2025-01-02T00:00:00Z",
            "seed": 7,
            "warmup_bars": 120,
            "initial_cash": "100000",
            "hidden_real_date": False,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["session"]["frame"]["current_index"] == 1440
    assert body["session"]["frame"]["visible_at"] == "2025-01-02T00:00:59.999000Z"
    assert len(body["bars"]) >= 120
    assert body["bars"][-1]["open_time"] == "2025-01-02T00:00:00Z"
    assert all(
        bar["close_time"] <= body["session"]["frame"]["visible_at"]
        for bar in body["bars"]
    )


def test_specific_session_start_enforces_warmup_and_future_boundaries(
    client: TestClient,
) -> None:
    snapshot_id = client.post("/api/v1/datasets/golden", json={}).json()["snapshot_id"]
    for start_time, expected_message in (
        ("2025-01-01T00:00:00Z", "enough warm-up bars"),
        ("2025-02-01T00:00:00Z", "at least one future bar"),
    ):
        response = client.post(
            "/api/v1/sessions",
            json={
                "snapshot_id": snapshot_id,
                "start_mode": "specific",
                "start_time": start_time,
                "warmup_bars": 120,
                "hidden_real_date": False,
            },
        )
        assert response.status_code == 422
        assert expected_message in response.json()["error"]["message"]


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


def test_session_chart_timeframes_are_aggregated_without_future_data(
    client: TestClient,
) -> None:
    created = create_golden_session(client)
    session = created["session"]
    visible_at = session["frame"]["visible_at"]

    expected_counts = {
        "1m": 20,
        "5m": 4,
        "15m": 2,
        "1h": 1,
        "4h": 1,
        "1d": 1,
    }
    responses: dict[str, dict] = {}
    for timeframe, count in expected_counts.items():
        response = client.get(
            f"/api/v1/sessions/{session['session_id']}/bars",
            params={"timeframe": timeframe},
        )
        assert response.status_code == 200
        payload = response.json()
        responses[timeframe] = payload
        assert payload["timeframe"] == timeframe
        assert len(payload["bars"]) == count
        assert all(bar["timeframe"] == timeframe for bar in payload["bars"])
        assert all(bar["close_time"] <= visible_at for bar in payload["bars"])
        assert payload["bars"][-1]["close_time"] == visible_at

    source = created["bars"][:5]
    first_5m = responses["5m"]["bars"][0]
    assert first_5m["raw"]["open"] == source[0]["raw"]["open"]
    assert first_5m["raw"]["close"] == source[-1]["raw"]["close"]
    assert Decimal(first_5m["raw"]["high"]) == max(
        Decimal(bar["raw"]["high"]) for bar in source
    )
    assert Decimal(first_5m["raw"]["low"]) == min(
        Decimal(bar["raw"]["low"]) for bar in source
    )
    assert Decimal(first_5m["raw"]["volume"]) == sum(
        Decimal(bar["raw"]["volume"]) for bar in source
    )
