from __future__ import annotations

import json
import time
from pathlib import Path

from fastapi.testclient import TestClient

from replaytutor.adapters.agents import CodexAdapter
from replaytutor.config import Settings
from replaytutor.contracts import (
    AnnotationPoint,
    TutorChartInstruction,
    TutorObservation,
    TutorResponse,
)


def create_session(client: TestClient) -> dict:
    snapshot = client.post("/api/v1/datasets/golden", json={}).json()
    return client.post(
        "/api/v1/sessions",
        json={"snapshot_id": snapshot["snapshot_id"], "warmup_bars": 20},
    ).json()


def response(evidence_id: str) -> TutorResponse:
    return TutorResponse(
        summary="当前结构仍需用户先定义失效条件。",
        observations=[
            TutorObservation(
                text="当前可见柱已经收盘。",
                evidence_ids=[evidence_id],
            )
        ],
        inferences=[],
        risks_and_unknowns=["未来行情不可见。"],
        rule_checks=[],
        next_questions=["你的失效条件是什么？"],
        disclaimer="仅用于回放训练，不构成交易建议。",
    )


def wait_for_run(client: TestClient, run_id: str) -> dict:
    for _ in range(100):
        run = client.get(f"/api/v1/tutor/runs/{run_id}").json()
        if run["status"] != "running":
            return run
        time.sleep(0.01)
    raise AssertionError("Tutor run did not finish")


def test_tutor_context_is_future_safe_and_fake_run_is_persisted(
    client: TestClient,
    settings: Settings,
    monkeypatch,
) -> None:
    created = create_session(client)
    visible_bar_id = created["bars"][-1]["bar_id"]

    def fake_run(self, workspace, *, timeout_seconds, on_process):
        del self, timeout_seconds, on_process
        context = json.loads((workspace / "tutor_context.json").read_text())
        assert context["perspective"] == "in_replay"
        assert (
            context["visible_bars"][-1]["close_time"]
            == created["session"]["frame"]["visible_at"]
        )
        assert all(
            bar["close_time"] <= context["visible_at"]
            for bar in context["visible_bars"]
        )
        assert set(context["forbidden_fields"]) == {
            "future_bars",
            "final_pnl",
            "mfe",
            "mae",
            "later_orders",
            "later_fills",
        }
        return response(visible_bar_id)

    monkeypatch.setattr(CodexAdapter, "run", fake_run)
    started = client.post(
        f"/api/v1/sessions/{created['session']['session_id']}/tutor",
        json={"question": "当前环境是否支持我的计划？", "stage": "environment"},
    )
    assert started.status_code == 200
    run = wait_for_run(client, started.json()["run_id"])
    assert run["status"] == "completed", run["error"]
    assert run["response"]["observations"][0]["evidence_ids"] == [visible_bar_id]

    workspace = settings.resolved_data_dir / "runtime" / "agent-runs" / run["run_id"]
    assert workspace.is_dir()
    assert not any(path.is_symlink() for path in workspace.rglob("*"))
    assert not any(path.suffix == ".db" for path in workspace.rglob("*"))
    assert (workspace / "manifest.json").is_file()


def test_invalid_evidence_fails_run_without_blocking_replay(
    client: TestClient,
    monkeypatch,
) -> None:
    created = create_session(client)

    def fake_invalid(self, workspace, *, timeout_seconds, on_process):
        del self, workspace, timeout_seconds, on_process
        return response("bar_future-not-allowed")

    monkeypatch.setattr(CodexAdapter, "run", fake_invalid)
    started = client.post(
        f"/api/v1/sessions/{created['session']['session_id']}/tutor",
        json={"question": "检查证据", "stage": "plan"},
    ).json()
    run = wait_for_run(client, started["run_id"])
    assert run["status"] == "failed"
    assert "outside the current frame" in run["error"]

    advanced = client.post(
        f"/api/v1/sessions/{created['session']['session_id']}/commands",
        json={
            "command_id": "cmd_00000000-0000-4000-8000-000000000001",
            "expected_revision": 0,
            "kind": "advance",
            "bars": 1,
        },
    )
    assert advanced.status_code == 200


def test_after_action_codex_uses_review_and_persists_ai_layer(
    client: TestClient,
    monkeypatch,
) -> None:
    created = create_session(client)
    session_id = created["session"]["session_id"]
    visible = created["bars"][-1]
    finished = client.post(
        f"/api/v1/sessions/{session_id}/finish",
        json={
            "command_id": "cmd_00000000-0000-4000-8000-000000000010",
            "expected_revision": 0,
        },
    )
    assert finished.status_code == 200

    def fake_after_action(self, workspace, *, timeout_seconds, on_process):
        del self, timeout_seconds, on_process
        context = json.loads((workspace / "tutor_context.json").read_text())
        assert context["perspective"] == "after_action"
        assert context["forbidden_fields"] == []
        assert context["deterministic_review"]["process_outcome"] == (
            "insufficient_evidence"
        )
        result = response(visible["bar_id"])
        return result.model_copy(
            update={
                "annotations": [
                    TutorChartInstruction(
                        shape="marker",
                        label="回放终点",
                        evidence_ids=[visible["bar_id"]],
                        points=[
                            AnnotationPoint(
                                time=visible["close_time"],
                                price=visible["raw"]["close"],
                            )
                        ],
                    )
                ]
            }
        )

    monkeypatch.setattr(CodexAdapter, "run", fake_after_action)
    started = client.post(
        f"/api/v1/sessions/{session_id}/tutor",
        json={"question": "审查完整会话", "stage": "after_action"},
    )
    assert started.status_code == 200
    run = wait_for_run(client, started.json()["run_id"])
    assert run["status"] == "completed", run["error"]
    restored = client.get(f"/api/v1/sessions/{session_id}").json()
    ai = [item for item in restored["annotations"] if item["layer"] == "ai"]
    assert len(ai) == 1
    assert ai[0]["provenance_run_id"] == run["run_id"]


def test_codex_adapter_never_uses_bypass_flags() -> None:
    source = (
        Path(__file__).resolve().parents[2]
        / "apps/api/replaytutor/adapters/agents/codex.py"
    ).read_text()
    assert '"read-only"' in source
    assert '"--ephemeral"' in source
    assert '"--ignore-user-config"' in source
    assert '"--ignore-rules"' in source
    assert "dangerously-bypass" not in source
