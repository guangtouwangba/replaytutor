from __future__ import annotations

import hashlib
import json
import subprocess
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal, cast

from replaytutor.adapters.agents import CodexAdapter
from replaytutor.config import Settings
from replaytutor.contracts import (
    PlaybookEvaluation,
    TutorRequest,
    TutorResponse,
    TutorRuleCheck,
    TutorRun,
)
from replaytutor.ids import new_id
from replaytutor.modules.annotations import persist_ai_annotations
from replaytutor.modules.chart_context import ChartContextBuilder
from replaytutor.modules.evidence_review import EvidenceReviewService
from replaytutor.modules.indicators import IndicatorService
from replaytutor.modules.local_system import LocalSystemService
from replaytutor.modules.market_data.service import utc_text
from replaytutor.modules.playbook import PlaybookEvaluator
from replaytutor.modules.training_session.service import TrainingSessionService, parse_utc
from replaytutor.modules.tutor.context import build_tutor_context
from replaytutor.modules.tutor.validation import (
    sanitize_evidence,
    strict_output_schema,
    validate_evidence,
)
from replaytutor.storage.database import connect_database

_processes: dict[str, subprocess.Popen[str]] = {}
_process_lock = threading.Lock()

INSTRUCTIONS = """# ReplayTutor Codex Tutor

You are a read-only trading-process coach. Use only tutor_context.json.
Separate observations from inferences. Never invent prices, fills, rules, or evidence ids.
Only cite ids listed in allowed_evidence_ids. Do not calculate or alter orders or account state.
deterministic_rule_checks is read-only. Never change its status, reason, or evidence.
Chart annotations are optional. Use only line, zone, marker, or label; every annotation
must cite allowed evidence ids and every point must be at or before visible_at.
chart_context contains chart objects explicitly selected by the user. First restate the
relationship between those objects, then assess the user's question from cited evidence.
indicators contains deterministic, server-evaluated values explicitly selected by the user.
Treat calculation_version and parameters as fixed facts; cite their source bar ids, never
recalculate them or infer values for missing warmup points.
The market is hidden after visible_at. Treat forbidden_fields as unavailable, not unknown files.
Use the locale declared in tutor_context.json for all explanatory prose and match
tutor_response.schema.json exactly. Preserve evidence ids, rule ids, and structured values.
"""


class TutorRunNotFoundError(RuntimeError):
    pass


class TutorRuntime:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.sessions = TrainingSessionService(settings)
        self.adapter = CodexAdapter()

    def start(self, session_id: str, request: TutorRequest) -> TutorRun:
        if LocalSystemService(self.settings).get_preferences().ai_mode == "off":
            raise ValueError("Codex Tutor is disabled in local preferences")
        delta = self.sessions.get(session_id)
        if delta.session.status == "completed" and request.stage != "after_action":
            raise ValueError("Completed sessions require after_action Tutor mode")
        if delta.session.status != "completed" and request.stage == "after_action":
            raise ValueError("after_action Tutor is available only after completion")
        if delta.session.status == "stopped":
            raise ValueError("Stopped sessions cannot start Tutor")
        review = (
            EvidenceReviewService(self.settings).get(session_id)
            if request.stage == "after_action"
            else None
        )
        playbook_evaluation = PlaybookEvaluator(self.settings).evaluate(session_id)
        chart_context = ChartContextBuilder(self.settings).build(
            delta,
            request.context_annotation_ids,
        )
        indicator_service = IndicatorService()
        indicator_evidence = [
            indicator_service.evaluate(
                delta.session.frame,
                spec,
                self.sessions.visible_bars(session_id, spec.timeframe).bars,
            )
            for spec in request.context_indicators
        ]
        context, evidence_ids = build_tutor_context(
            delta,
            request,
            review,
            playbook_evaluation,
            chart_context,
            indicator_evidence,
        )
        run_id = new_id("run")
        workspace = self.settings.resolved_data_dir / "runtime" / "agent-runs" / run_id
        workspace.mkdir(parents=True, exist_ok=False)
        self._write_workspace(workspace, context)
        now = datetime.now(UTC)
        run = TutorRun(
            run_id=run_id,
            session_id=session_id,
            frame_id=delta.session.frame.frame_id,
            status="running",
            question=request.question,
            stage=request.stage,
            context_bundle_id=(
                chart_context.context_bundle_id if chart_context is not None else None
            ),
            created_at=now,
        )
        with connect_database(self.settings.database_path) as connection:
            connection.execute(
                """INSERT INTO tutor_run (
                    run_id, session_id, frame_id, status, question, stage,
                    context_bundle_id, workspace_path, created_at
                ) VALUES (?, ?, ?, 'running', ?, ?, ?, ?, ?)""",
                (
                    run_id,
                    session_id,
                    run.frame_id,
                    request.question,
                    request.stage,
                    run.context_bundle_id,
                    str(workspace),
                    utc_text(now),
                ),
            )
        thread = threading.Thread(
            target=self._execute,
            args=(run_id, workspace, evidence_ids, playbook_evaluation),
            daemon=True,
            name=f"tutor-{run_id}",
        )
        thread.start()
        return run

    def get(self, run_id: str) -> TutorRun:
        with connect_database(self.settings.database_path) as connection:
            row = connection.execute(
                "SELECT * FROM tutor_run WHERE run_id = ?",
                (run_id,),
            ).fetchone()
        if row is None:
            raise TutorRunNotFoundError("Tutor run not found")
        response = (
            TutorResponse.model_validate_json(row["response_json"])
            if row["response_json"]
            else None
        )
        return TutorRun(
            run_id=str(row["run_id"]),
            session_id=str(row["session_id"]),
            frame_id=str(row["frame_id"]),
            status=cast(
                Literal["running", "completed", "failed", "cancelled", "timed_out"],
                str(row["status"]),
            ),
            question=str(row["question"]),
            stage=cast(
                Literal["environment", "plan", "position", "exit", "after_action"],
                str(row["stage"]),
            ),
            context_bundle_id=(
                str(row["context_bundle_id"]) if row["context_bundle_id"] else None
            ),
            response=response,
            error=str(row["error"]) if row["error"] else None,
            created_at=parse_utc(str(row["created_at"])),
            completed_at=(parse_utc(str(row["completed_at"])) if row["completed_at"] else None),
        )

    def cancel(self, run_id: str) -> TutorRun:
        run = self.get(run_id)
        if run.status != "running":
            return run
        with _process_lock:
            process = _processes.get(run_id)
            if process is not None:
                process.terminate()
        self._finish(run_id, status="cancelled", error="Cancelled by user")
        return self.get(run_id)

    def _execute(
        self,
        run_id: str,
        workspace: Path,
        evidence_ids: set[str],
        playbook_evaluation: PlaybookEvaluation,
    ) -> None:
        try:
            if self.get(run_id).status != "running":
                return

            def register(process: subprocess.Popen[str]) -> None:
                with _process_lock:
                    _processes[run_id] = process

            response = self.adapter.run(
                workspace,
                timeout_seconds=self.settings.codex_timeout_seconds,
                on_process=register,
            )
            response = validate_evidence(
                sanitize_evidence(response, evidence_ids),
                evidence_ids,
            )
            response = response.model_copy(
                update={
                    "rule_checks": [
                        TutorRuleCheck(
                            rule_id=check.rule_id,
                            status=check.status,
                            reason=check.summary,
                            evidence_ids=check.evidence_ids,
                        )
                        for check in playbook_evaluation.checks
                    ]
                }
            )
            if self.get(run_id).status == "running":
                self._finish(run_id, status="completed", response=response)
        except TimeoutError as error:
            self._finish(run_id, status="timed_out", error=str(error))
        except BaseException as error:
            if self.get(run_id).status == "running":
                self._finish(run_id, status="failed", error=str(error))
        finally:
            with _process_lock:
                _processes.pop(run_id, None)

    def _finish(
        self,
        run_id: str,
        *,
        status: Literal["completed", "failed", "cancelled", "timed_out"],
        response: TutorResponse | None = None,
        error: str | None = None,
    ) -> None:
        now = datetime.now(UTC)
        with connect_database(self.settings.database_path) as connection:
            if status == "completed" and response is not None:
                run = connection.execute(
                    "SELECT session_id, frame_id FROM tutor_run WHERE run_id = ?",
                    (run_id,),
                ).fetchone()
                if run is None:
                    raise TutorRunNotFoundError("Tutor run not found")
                persist_ai_annotations(
                    connection,
                    run_id=run_id,
                    session_id=str(run["session_id"]),
                    frame_id=str(run["frame_id"]),
                    instructions=response.annotations,
                )
            connection.execute(
                """UPDATE tutor_run
                SET status = ?, response_json = ?, error = ?, completed_at = ?
                WHERE run_id = ? AND status = 'running'""",
                (
                    status,
                    response.model_dump_json() if response is not None else None,
                    error,
                    utc_text(now),
                    run_id,
                ),
            )

    @staticmethod
    def _write_workspace(workspace: Path, context: dict[str, object]) -> None:
        context_text = json.dumps(
            context,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        schema_text = json.dumps(
            strict_output_schema(TutorResponse.model_json_schema()),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        locale = str(context.get("locale", "en-US"))
        locale_instruction = (
            "Write concise Simplified Chinese."
            if locale == "zh-CN"
            else "Write concise English."
        )
        (workspace / "TUTOR_INSTRUCTIONS.md").write_text(
            f"{INSTRUCTIONS}\n{locale_instruction}\n",
            encoding="utf-8",
        )
        (workspace / "tutor_context.json").write_text(
            context_text,
            encoding="utf-8",
        )
        (workspace / "tutor_response.schema.json").write_text(
            schema_text,
            encoding="utf-8",
        )
        manifest = {
            "schema_version": "1.0",
            "adapter": "codex-local",
            "context_sha256": hashlib.sha256(context_text.encode()).hexdigest(),
            "schema_sha256": hashlib.sha256(schema_text.encode()).hexdigest(),
            "permissions": {
                "sandbox": "read-only",
                "ephemeral": True,
                "user_config": "ignored",
                "project_rules": "ignored",
            },
        }
        (workspace / "manifest.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True),
            encoding="utf-8",
        )
