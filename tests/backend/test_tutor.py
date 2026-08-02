from __future__ import annotations

import json
import subprocess
import sys
import threading
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
    TutorRuleCheck,
)
from replaytutor.ids import new_id
from replaytutor.storage.database import connect_database


def create_session(client: TestClient) -> dict:
    snapshot = client.post("/api/v1/datasets/golden", json={}).json()
    playbook = next(
        item
        for item in client.get("/api/v1/playbooks").json()["playbooks"]
        if item["slug"] == "trend-pullback" and item["version"] == 2
    )
    return client.post(
        "/api/v1/sessions",
        json={
            "snapshot_id": snapshot["snapshot_id"],
            "warmup_bars": 20,
            "playbook_id": playbook["playbook_id"],
        },
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
        assert context["deterministic_rule_checks"]["evaluator_version"] == "1.0"
        assert len(context["deterministic_rule_checks"]["checks"]) == 6
        result = response(visible_bar_id)
        return result.model_copy(
            update={
                "rule_checks": [
                    TutorRuleCheck(
                        rule_id="risk_amount_within_limit",
                        status="passed",
                        reason="模型尝试覆盖确定性状态",
                        evidence_ids=[visible_bar_id],
                    )
                ]
            }
        )

    monkeypatch.setattr(CodexAdapter, "run", fake_run)
    started = client.post(
        f"/api/v1/sessions/{created['session']['session_id']}/tutor",
        json={"question": "当前环境是否支持我的计划？", "stage": "environment"},
    )
    assert started.status_code == 200
    run = wait_for_run(client, started.json()["run_id"])
    assert run["status"] == "completed", run["error"]
    assert run["response"]["observations"][0]["evidence_ids"] == [visible_bar_id]
    assert len(run["response"]["rule_checks"]) == 6
    assert all(check["status"] == "unknown" for check in run["response"]["rule_checks"])
    assert all(
        check["reason"] != "模型尝试覆盖确定性状态"
        for check in run["response"]["rule_checks"]
    )

    workspace = settings.resolved_data_dir / "runtime" / "agent-runs" / run["run_id"]
    assert workspace.is_dir()
    assert not any(path.is_symlink() for path in workspace.rglob("*"))
    assert not any(path.suffix == ".db" for path in workspace.rglob("*"))
    assert (workspace / "manifest.json").is_file()


def test_selected_chart_objects_are_snapshotted_into_tutor_context(
    client: TestClient,
    settings: Settings,
    monkeypatch,
) -> None:
    created = create_session(client)
    session = created["session"]
    first = created["bars"][-4]
    last = created["bars"][-1]
    annotation = client.post(
        f"/api/v1/sessions/{session['session_id']}/annotations",
        json={
            "command_id": new_id("cmd"),
            "expected_revision": session["revision"],
            "shape": "line",
            "tool": "trend_line",
            "semantic_role": "analysis",
            "label": "回调趋势线",
            "points": [
                {"time": first["close_time"], "price": first["raw"]["low"]},
                {"time": last["close_time"], "price": last["raw"]["low"]},
            ],
            "metadata": {"side": "long"},
        },
    ).json()
    revised = client.post(
        f"/api/v1/sessions/{session['session_id']}/annotations/"
        f"{annotation['annotation_id']}/actions",
        json={
            "command_id": new_id("cmd"),
            "expected_revision": session["revision"],
            "action": "revised",
            "label": "修订回调趋势线",
            "points": [
                {"time": first["close_time"], "price": first["raw"]["low"]},
                {"time": last["close_time"], "price": last["raw"]["high"]},
            ],
            "metadata": {"side": "short", "drawing_kind": "parallel_channel"},
        },
    )
    assert revised.status_code == 200

    def fake_run(self, workspace, *, timeout_seconds, on_process):
        del self, timeout_seconds, on_process
        context = json.loads((workspace / "tutor_context.json").read_text())
        bundle = context["chart_context"]
        assert bundle["frame_id"] == session["frame"]["frame_id"]
        assert bundle["objects"][0]["object_id"] == annotation["annotation_id"]
        assert bundle["objects"][0]["tool"] == "trend_line"
        assert bundle["objects"][0]["label"] == "修订回调趋势线"
        assert bundle["objects"][0]["metadata"] == {
            "side": "short",
            "drawing_kind": "parallel_channel",
        }
        assert annotation["annotation_id"] in context["allowed_evidence_ids"]
        assert all(
            evidence_id in context["allowed_evidence_ids"]
            for evidence_id in bundle["evidence_ids"]
        )
        return response(annotation["annotation_id"])

    monkeypatch.setattr(CodexAdapter, "run", fake_run)
    started = client.post(
        f"/api/v1/sessions/{session['session_id']}/tutor",
        json={
            "question": "这条趋势线是否支持我的开仓想法？",
            "stage": "plan",
            "context_annotation_ids": [annotation["annotation_id"]],
        },
    )
    assert started.status_code == 200
    assert started.json()["context_bundle_id"].startswith("ctx_")
    run = wait_for_run(client, started.json()["run_id"])
    assert run["status"] == "completed", run["error"]
    with connect_database(settings.database_path) as connection:
        stored = connection.execute(
            "SELECT objects_json FROM chart_context_bundle WHERE context_bundle_id = ?",
            (run["context_bundle_id"],),
        ).fetchone()
    assert stored is not None
    assert json.loads(stored["objects_json"])[0]["label"] == "修订回调趋势线"


def test_chart_context_rejects_cross_session_annotation(client: TestClient) -> None:
    first = create_session(client)
    second = create_session(client)
    point = first["bars"][-1]
    annotation = client.post(
        f"/api/v1/sessions/{first['session']['session_id']}/annotations",
        json={
            "command_id": new_id("cmd"),
            "expected_revision": 0,
            "shape": "marker",
            "tool": "planned_entry",
            "semantic_role": "entry",
            "label": "计划开仓",
            "points": [{"time": point["close_time"], "price": point["raw"]["close"]}],
        },
    ).json()
    rejected = client.post(
        f"/api/v1/sessions/{second['session']['session_id']}/tutor",
        json={
            "question": "检查这个开仓",
            "stage": "plan",
            "context_annotation_ids": [annotation["annotation_id"]],
        },
    )
    assert rejected.status_code == 409
    assert "not found" in rejected.json()["error"]["message"]


def test_invalid_evidence_is_removed_without_blocking_replay(
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
    assert run["status"] == "completed"
    assert run["response"]["observations"][0]["evidence_ids"] == []
    assert any(
        "宿主已删除 1 个" in item
        for item in run["response"]["risks_and_unknowns"]
    )

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


def test_tutor_timeout_crash_and_cancel_are_terminal_and_clean_up_process(
    client: TestClient,
    monkeypatch,
) -> None:
    created = create_session(client)
    session_id = created["session"]["session_id"]

    def timeout_run(self, workspace, *, timeout_seconds, on_process):
        del self, workspace, timeout_seconds, on_process
        raise TimeoutError("deterministic timeout")

    monkeypatch.setattr(CodexAdapter, "run", timeout_run)
    timed_out = client.post(
        f"/api/v1/sessions/{session_id}/tutor",
        json={"question": "触发超时", "stage": "environment"},
    ).json()
    timed_out_run = wait_for_run(client, timed_out["run_id"])
    assert timed_out_run["status"] == "timed_out"
    assert timed_out_run["error"] == "deterministic timeout"

    def crash_run(self, workspace, *, timeout_seconds, on_process):
        del self, workspace, timeout_seconds, on_process
        raise RuntimeError("deterministic adapter crash")

    monkeypatch.setattr(CodexAdapter, "run", crash_run)
    crashed = client.post(
        f"/api/v1/sessions/{session_id}/tutor",
        json={"question": "触发崩溃", "stage": "environment"},
    ).json()
    crashed_run = wait_for_run(client, crashed["run_id"])
    assert crashed_run["status"] == "failed"
    assert crashed_run["error"] == "deterministic adapter crash"

    process_started = threading.Event()
    child: subprocess.Popen[str] | None = None

    def blocking_run(self, workspace, *, timeout_seconds, on_process):
        nonlocal child
        del self, workspace, timeout_seconds
        child = subprocess.Popen(
            [sys.executable, "-c", "import time; time.sleep(30)"],
            text=True,
        )
        on_process(child)
        process_started.set()
        child.wait(timeout=5)
        raise RuntimeError("cancelled child exited")

    monkeypatch.setattr(CodexAdapter, "run", blocking_run)
    cancellable = client.post(
        f"/api/v1/sessions/{session_id}/tutor",
        json={"question": "触发取消", "stage": "environment"},
    ).json()
    assert process_started.wait(timeout=2)
    cancelled = client.post(f"/api/v1/tutor/runs/{cancellable['run_id']}/cancel")
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"
    deadline = time.monotonic() + 2
    while child is not None and child.poll() is None and time.monotonic() < deadline:
        time.sleep(0.01)
    assert child is not None
    assert child.poll() is not None
    assert wait_for_run(client, cancellable["run_id"])["status"] == "cancelled"
