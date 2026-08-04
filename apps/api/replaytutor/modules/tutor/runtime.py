from __future__ import annotations

import hashlib
import json
import subprocess
import threading
from datetime import UTC, datetime
from pathlib import Path
from sqlite3 import Row
from typing import Literal, cast

from replaytutor.adapters.agents import CodexAdapter
from replaytutor.config import Settings
from replaytutor.contracts import (
    CreateTutorThreadRequest,
    PlaybookEvaluation,
    TutorRequest,
    TutorResponse,
    TutorRuleCheck,
    TutorRun,
    TutorThreadDetail,
    TutorThreadListResponse,
    TutorThreadSummary,
    UpdateTutorThreadRequest,
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
    sanitize_chart_instructions,
    sanitize_evidence,
    strict_output_schema,
    validate_evidence,
)
from replaytutor.storage.database import connect_database

_processes: dict[str, subprocess.Popen[str]] = {}
_process_lock = threading.Lock()

INSTRUCTIONS = """# ReplayTutor Codex Tutor

You are a read-only trading-process coach. Use only tutor_context.json.
Answer the user's actual question directly in summary before adding coaching detail.
For market-environment or trend questions, use the visible bars and any supplied indicators;
do not require a trading plan, position, or completed session unless the question itself does.
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
Create annotations only when the user explicitly asks to draw, mark, or add chart objects.
For an unspecified count, propose only 3 to 5 high-confidence objects and never more than 8.
Supported tools are trend_line, horizontal_line, parallel_channel, and zone. Use the declared
analysis_timeframe exactly. Every point must use the close_time and an exact open, high, low,
or close price from a visible bar, and that bar id must appear in the annotation evidence_ids.
Use purpose trend for trend_line, support or resistance for horizontal_line and zone, and
channel for parallel_channel. Return no annotations for ordinary questions.
The market is hidden after visible_at. Treat forbidden_fields as unavailable, not unknown files.
conversation_history is prior application context. Prior evidence ids are provenance only and
cannot be cited unless allowed_evidence_ids also contains them for this turn. Prior inferences
must remain explicitly labelled as inferences and must never become deterministic facts.
Use the locale declared in tutor_context.json for all explanatory prose and match
tutor_response.schema.json exactly. Preserve evidence ids, rule ids, and structured values.
"""


class TutorRunNotFoundError(RuntimeError):
    pass


class TutorThreadNotFoundError(RuntimeError):
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
        thread_id = self._resolve_or_create_thread(session_id, request.thread_id)
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
        analysis_bars = self.sessions.visible_bars(
            session_id,
            request.analysis_timeframe,
        ).bars
        context, evidence_ids = build_tutor_context(
            delta,
            request,
            review,
            playbook_evaluation,
            chart_context,
            indicator_evidence,
            analysis_bars,
        )
        context["conversation_history"] = self._conversation_history(thread_id)
        context["conversation_history_policy"] = {
            "scope": "same_tutor_thread",
            "completed_turn_limit": 12,
            "character_budget": 24000,
            "provenance": "Prior agent inferences remain inferences, never deterministic facts.",
            "evidence": (
                "Prior evidence ids are not currently citable unless also allowed by this turn."
            ),
        }
        run_id = new_id("run")
        workspace = self.settings.resolved_data_dir / "runtime" / "agent-runs" / run_id
        now = datetime.now(UTC)
        with connect_database(self.settings.database_path) as connection:
            connection.execute("BEGIN IMMEDIATE")
            thread_row = connection.execute(
                """SELECT title, title_locked FROM tutor_thread
                WHERE thread_id = ? AND session_id = ? AND deleted_at IS NULL""",
                (thread_id, session_id),
            ).fetchone()
            if thread_row is None:
                raise TutorThreadNotFoundError("Tutor thread not found for this session")
            running = connection.execute(
                "SELECT 1 FROM tutor_run WHERE thread_id = ? AND status = 'running' LIMIT 1",
                (thread_id,),
            ).fetchone()
            if running is not None:
                raise ValueError("This Tutor conversation already has a running request")
            sequence = int(
                connection.execute(
                    "SELECT COALESCE(MAX(sequence), 0) + 1 FROM tutor_run WHERE thread_id = ?",
                    (thread_id,),
                ).fetchone()[0]
            )
            connection.execute(
                """INSERT INTO tutor_run (
                    run_id, thread_id, sequence, session_id, frame_id, status,
                    question, stage, context_bundle_id, workspace_path, created_at
                ) VALUES (?, ?, ?, ?, ?, 'running', ?, ?, ?, ?, ?)""",
                (
                    run_id,
                    thread_id,
                    sequence,
                    session_id,
                    delta.session.frame.frame_id,
                    request.question,
                    request.stage,
                    chart_context.context_bundle_id if chart_context is not None else None,
                    str(workspace),
                    utc_text(now),
                ),
            )
            title = str(thread_row["title"])
            if sequence == 1 and not bool(thread_row["title_locked"]):
                title = self._automatic_title(request.question)
            connection.execute(
                "UPDATE tutor_thread SET title = ?, updated_at = ? WHERE thread_id = ?",
                (title, utc_text(now), thread_id),
            )
            connection.commit()
        run = TutorRun(
            run_id=run_id,
            thread_id=thread_id,
            sequence=sequence,
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
        try:
            workspace.mkdir(parents=True, exist_ok=False)
            self._write_workspace(workspace, context)
        except BaseException as error:
            self._finish(run_id, status="failed", error=str(error))
            raise
        thread = threading.Thread(
            target=self._execute,
            args=(run_id, workspace, evidence_ids, playbook_evaluation),
            daemon=True,
            name=f"tutor-{run_id}",
        )
        thread.start()
        return run

    def list_threads(self, session_id: str) -> TutorThreadListResponse:
        self.sessions.get(session_id)
        with connect_database(self.settings.database_path) as connection:
            rows = connection.execute(
                """SELECT t.*,
                    COUNT(r.run_id) AS run_count,
                    (SELECT question FROM tutor_run lr WHERE lr.thread_id = t.thread_id
                     ORDER BY sequence DESC LIMIT 1) AS last_question,
                    (SELECT status FROM tutor_run lr WHERE lr.thread_id = t.thread_id
                     ORDER BY sequence DESC LIMIT 1) AS last_status
                FROM tutor_thread t
                LEFT JOIN tutor_run r ON r.thread_id = t.thread_id
                WHERE t.session_id = ? AND t.deleted_at IS NULL
                GROUP BY t.thread_id
                ORDER BY t.updated_at DESC, t.thread_id DESC""",
                (session_id,),
            ).fetchall()
        return TutorThreadListResponse(threads=[self._thread_summary(row) for row in rows])

    def create_thread(
        self,
        session_id: str,
        request: CreateTutorThreadRequest,
    ) -> TutorThreadDetail:
        self.sessions.get(session_id)
        thread_id = new_id("thr")
        now = datetime.now(UTC)
        title = request.title.strip() if request.title else "新对话"
        with connect_database(self.settings.database_path) as connection:
            connection.execute(
                """INSERT INTO tutor_thread (
                    thread_id, session_id, title, title_locked, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    thread_id,
                    session_id,
                    title,
                    request.title is not None,
                    utc_text(now),
                    utc_text(now),
                ),
            )
        return TutorThreadDetail(
            thread_id=thread_id,
            session_id=session_id,
            title=title,
            run_count=0,
            created_at=now,
            updated_at=now,
            runs=[],
        )

    def get_thread(self, thread_id: str) -> TutorThreadDetail:
        with connect_database(self.settings.database_path) as connection:
            row = connection.execute(
                """SELECT t.*, COUNT(r.run_id) AS run_count,
                    (SELECT question FROM tutor_run lr WHERE lr.thread_id = t.thread_id
                     ORDER BY sequence DESC LIMIT 1) AS last_question,
                    (SELECT status FROM tutor_run lr WHERE lr.thread_id = t.thread_id
                     ORDER BY sequence DESC LIMIT 1) AS last_status
                FROM tutor_thread t LEFT JOIN tutor_run r ON r.thread_id = t.thread_id
                WHERE t.thread_id = ? AND t.deleted_at IS NULL GROUP BY t.thread_id""",
                (thread_id,),
            ).fetchone()
            if row is None:
                raise TutorThreadNotFoundError("Tutor thread not found")
            run_rows = connection.execute(
                "SELECT * FROM tutor_run WHERE thread_id = ? ORDER BY sequence",
                (thread_id,),
            ).fetchall()
        summary = self._thread_summary(row)
        return TutorThreadDetail(
            **summary.model_dump(), runs=[self._run_from_row(item) for item in run_rows]
        )

    def update_thread(
        self,
        thread_id: str,
        request: UpdateTutorThreadRequest,
    ) -> TutorThreadDetail:
        title = request.title.strip()
        if not title:
            raise ValueError("Tutor thread title cannot be empty")
        with connect_database(self.settings.database_path) as connection:
            result = connection.execute(
                """UPDATE tutor_thread SET title = ?, title_locked = 1, updated_at = ?
                WHERE thread_id = ? AND deleted_at IS NULL""",
                (title, utc_text(datetime.now(UTC)), thread_id),
            )
        if result.rowcount == 0:
            raise TutorThreadNotFoundError("Tutor thread not found")
        return self.get_thread(thread_id)

    def delete_thread(self, thread_id: str) -> None:
        now = utc_text(datetime.now(UTC))
        with connect_database(self.settings.database_path) as connection:
            running = connection.execute(
                "SELECT 1 FROM tutor_run WHERE thread_id = ? AND status = 'running' LIMIT 1",
                (thread_id,),
            ).fetchone()
            if running is not None:
                raise ValueError(
                    "Cancel the running Tutor request before deleting this conversation"
                )
            result = connection.execute(
                """UPDATE tutor_thread SET deleted_at = ?, updated_at = ?
                WHERE thread_id = ? AND deleted_at IS NULL""",
                (now, now, thread_id),
            )
        if result.rowcount == 0:
            raise TutorThreadNotFoundError("Tutor thread not found")

    def get(self, run_id: str) -> TutorRun:
        with connect_database(self.settings.database_path) as connection:
            row = connection.execute(
                "SELECT * FROM tutor_run WHERE run_id = ?",
                (run_id,),
            ).fetchone()
        if row is None:
            raise TutorRunNotFoundError("Tutor run not found")
        return self._run_from_row(row)

    @staticmethod
    def _run_from_row(row: Row) -> TutorRun:
        response = (
            TutorResponse.model_validate_json(row["response_json"])
            if row["response_json"]
            else None
        )
        return TutorRun(
            run_id=str(row["run_id"]),
            thread_id=str(row["thread_id"]),
            sequence=int(row["sequence"]),
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
            context_bundle_id=(str(row["context_bundle_id"]) if row["context_bundle_id"] else None),
            response=response,
            error=str(row["error"]) if row["error"] else None,
            created_at=parse_utc(str(row["created_at"])),
            completed_at=(parse_utc(str(row["completed_at"])) if row["completed_at"] else None),
        )

    @staticmethod
    def _automatic_title(question: str) -> str:
        compact = " ".join(question.split())
        return compact[:40] + ("…" if len(compact) > 40 else "")

    def _resolve_or_create_thread(self, session_id: str, thread_id: str | None) -> str:
        if thread_id is not None:
            with connect_database(self.settings.database_path) as connection:
                row = connection.execute(
                    """SELECT 1 FROM tutor_thread
                    WHERE thread_id = ? AND session_id = ? AND deleted_at IS NULL""",
                    (thread_id, session_id),
                ).fetchone()
            if row is None:
                raise TutorThreadNotFoundError("Tutor thread not found for this session")
            return thread_id
        listed = self.list_threads(session_id).threads
        if listed:
            return listed[0].thread_id
        return self.create_thread(session_id, CreateTutorThreadRequest()).thread_id

    @staticmethod
    def _thread_summary(row: Row) -> TutorThreadSummary:
        return TutorThreadSummary(
            thread_id=str(row["thread_id"]),
            session_id=str(row["session_id"]),
            title=str(row["title"]),
            run_count=int(row["run_count"]),
            last_question=str(row["last_question"]) if row["last_question"] else None,
            last_status=cast(
                Literal["running", "completed", "failed", "cancelled", "timed_out"] | None,
                str(row["last_status"]) if row["last_status"] else None,
            ),
            created_at=parse_utc(str(row["created_at"])),
            updated_at=parse_utc(str(row["updated_at"])),
        )

    def _conversation_history(self, thread_id: str) -> list[dict[str, object]]:
        with connect_database(self.settings.database_path) as connection:
            rows = connection.execute(
                """SELECT question, response_json FROM tutor_run
                WHERE thread_id = ? AND status = 'completed' AND response_json IS NOT NULL
                ORDER BY sequence DESC LIMIT 12""",
                (thread_id,),
            ).fetchall()
        selected: list[dict[str, object]] = []
        used = 0
        for row in rows:
            response = TutorResponse.model_validate_json(row["response_json"])
            item: dict[str, object] = {
                "user_statement": str(row["question"]),
                "assistant_summary": response.summary,
                "deterministic_observations": [item.model_dump() for item in response.observations],
                "prior_agent_inferences": [item.model_dump() for item in response.inferences],
                "risks_and_unknowns": response.risks_and_unknowns,
            }
            size = len(json.dumps(item, ensure_ascii=False))
            if selected and used + size > 24000:
                break
            selected.append(item)
            used += size
        selected.reverse()
        return selected

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
            context = json.loads((workspace / "tutor_context.json").read_text(encoding="utf-8"))
            response = sanitize_chart_instructions(response, context)
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
                persisted_annotations = persist_ai_annotations(
                    connection,
                    run_id=run_id,
                    session_id=str(run["session_id"]),
                    frame_id=str(run["frame_id"]),
                    instructions=response.annotations,
                )
                response = response.model_copy(
                    update={
                        "annotations": [
                            instruction.model_copy(
                                update={"annotation_id": annotation.annotation_id}
                            )
                            for instruction, annotation in zip(
                                response.annotations,
                                persisted_annotations,
                                strict=True,
                            )
                        ]
                    }
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
            connection.execute(
                """UPDATE tutor_thread SET updated_at = ? WHERE thread_id = (
                    SELECT thread_id FROM tutor_run WHERE run_id = ?
                )""",
                (utc_text(now), run_id),
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
            "Write concise Simplified Chinese." if locale == "zh-CN" else "Write concise English."
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
