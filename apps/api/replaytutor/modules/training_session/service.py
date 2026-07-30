from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from typing import Any, Literal, cast

from replaytutor.config import Settings
from replaytutor.contracts import (
    Bar,
    CompletedSession,
    CreateSessionSpec,
    FinishSessionRequest,
    ReplayFrame,
    ReplaySession,
    SessionCommand,
    SessionDelta,
    SessionEvent,
    SessionListResponse,
)
from replaytutor.ids import new_id, stable_id
from replaytutor.modules.market_data.service import MarketDataService, utc_text
from replaytutor.modules.replay import (
    ReplayState,
    advance,
    choose_start_index,
    replay_fingerprint,
)
from replaytutor.modules.replay.core import ReplayError
from replaytutor.storage.database import connect_database

VISIBLE_WINDOW_BARS = 500
SessionStatus = Literal["ready", "paused", "completed", "stopped"]


class TrainingSessionError(RuntimeError):
    pass


class SessionNotFoundError(TrainingSessionError):
    pass


class SessionConflictError(TrainingSessionError):
    def __init__(self, current_revision: int) -> None:
        super().__init__(
            f"Session revision conflict; current revision is {current_revision}"
        )
        self.current_revision = current_revision


class InvalidSessionStateError(TrainingSessionError):
    pass


class TrainingSessionService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.market_data = MarketDataService(settings)

    def create(self, spec: CreateSessionSpec) -> SessionDelta:
        snapshot = self.market_data.get_snapshot(spec.snapshot_id)
        if spec.playbook_id is not None:
            from replaytutor.modules.playbook import PlaybookService

            if not PlaybookService(self.settings).exists(spec.playbook_id):
                raise TrainingSessionError("Playbook version not found")
        if snapshot.timeframe != "1m":
            raise TrainingSessionError("MVP sessions require a 1m source snapshot")
        total_bars = self.market_data.snapshot_bar_count(spec.snapshot_id)
        try:
            start_index = choose_start_index(
                total_bars=total_bars,
                warmup_bars=spec.warmup_bars,
                start_mode=spec.start_mode,
                seed=spec.seed,
            )
        except ReplayError as error:
            raise TrainingSessionError(str(error)) from error
        current_bar = self._bar_at(spec.snapshot_id, start_index)
        now = datetime.now(UTC)
        session_id = new_id("ses")
        frame_id = self._frame_id(session_id, 0)
        fingerprint = replay_fingerprint(
            snapshot_hash=snapshot.content_hash,
            seed=spec.seed,
            start_index=start_index,
            warmup_bars=spec.warmup_bars,
        )
        event = SessionEvent(
            event_id=new_id("evt"),
            session_id=session_id,
            sequence=1,
            revision=0,
            event_type="session_created",
            occurred_at=now,
            payload={
                "snapshot_id": snapshot.snapshot_id,
                "start_index": start_index,
                "warmup_bars": spec.warmup_bars,
                "fingerprint": fingerprint,
            },
        )
        with connect_database(self.settings.database_path) as connection:
            connection.execute(
                """
                INSERT INTO replay_session (
                    session_id, snapshot_id, status, revision, current_index,
                    start_index, total_bars, warmup_bars, seed, initial_cash,
                    hidden_real_date, fingerprint, created_at, updated_at,
                    playbook_id
                ) VALUES (?, ?, 'ready', 0, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    snapshot.snapshot_id,
                    start_index,
                    start_index,
                    total_bars,
                    spec.warmup_bars,
                    spec.seed,
                    spec.initial_cash,
                    spec.hidden_real_date,
                    fingerprint,
                    utc_text(now),
                    utc_text(now),
                    spec.playbook_id,
                ),
            )
            connection.execute(
                """
                INSERT INTO replay_frame (
                    frame_id, session_id, revision, current_index, visible_at, created_at
                ) VALUES (?, ?, 0, ?, ?, ?)
                """,
                (
                    frame_id,
                    session_id,
                    start_index,
                    utc_text(current_bar.close_time),
                    utc_text(now),
                ),
            )
            self._insert_event(connection, event)
        return self.get(session_id, events=[event])

    def list(self) -> SessionListResponse:
        with connect_database(self.settings.database_path) as connection:
            rows = connection.execute(
                "SELECT * FROM replay_session ORDER BY created_at DESC"
            ).fetchall()
            sessions = [
                self._session_from_row(connection, dict(row))
                for row in rows
            ]
        return SessionListResponse(sessions=sessions)

    def get(
        self,
        session_id: str,
        *,
        events: list[SessionEvent] | None = None,
    ) -> SessionDelta:
        with connect_database(self.settings.database_path) as connection:
            row = self._session_row(connection, session_id)
            session = self._session_from_row(connection, row)
            from replaytutor.modules.annotations import load_annotations
            from replaytutor.modules.execution.service import load_execution

            execution = load_execution(connection, row)
            annotations = load_annotations(connection, session_id)
        bars = self._visible_bars(session)
        return SessionDelta(
            session=session,
            bars=bars,
            events=events or [],
            execution=execution,
            annotations=annotations,
        )

    def apply(self, session_id: str, command: SessionCommand) -> SessionDelta:
        connection = connect_database(self.settings.database_path)
        try:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                "SELECT session_id, result_json FROM session_command WHERE command_id = ?",
                (command.command_id,),
            ).fetchone()
            if existing is not None:
                if str(existing["session_id"]) != session_id:
                    raise TrainingSessionError(
                        "Command id was already used by another session"
                    )
                connection.rollback()
                stored = SessionDelta.model_validate_json(existing["result_json"])
                return stored.model_copy(update={"idempotent_replay": True})

            row = self._session_row(connection, session_id)
            if row["status"] in {"completed", "stopped"}:
                raise InvalidSessionStateError(
                    f"Cannot advance a {row['status']} session"
                )
            if int(row["revision"]) != command.expected_revision:
                raise SessionConflictError(int(row["revision"]))

            transition = advance(
                ReplayState(
                    current_index=int(row["current_index"]),
                    start_index=int(row["start_index"]),
                    total_bars=int(row["total_bars"]),
                ),
                command.bars,
            )
            if transition.advanced_bars == 0:
                raise InvalidSessionStateError("Replay is already at the final bar")
            revision = int(row["revision"]) + 1
            now = datetime.now(UTC)
            current_bar = self._bar_at(
                str(row["snapshot_id"]),
                transition.current.current_index,
            )
            frame_id = self._frame_id(session_id, revision)
            event = SessionEvent(
                event_id=new_id("evt"),
                session_id=session_id,
                sequence=self._next_sequence(connection, session_id),
                revision=revision,
                event_type="replay_advanced",
                occurred_at=now,
                payload={
                    "requested_bars": command.bars,
                    "advanced_bars": transition.advanced_bars,
                    "from_index": transition.previous.current_index,
                    "to_index": transition.current.current_index,
                    "reached_end": transition.reached_end,
                },
            )
            connection.execute(
                """
                UPDATE replay_session
                SET status = 'paused', revision = ?, current_index = ?, updated_at = ?
                WHERE session_id = ?
                """,
                (
                    revision,
                    transition.current.current_index,
                    utc_text(now),
                    session_id,
                ),
            )
            connection.execute(
                """
                INSERT INTO replay_frame (
                    frame_id, session_id, revision, current_index, visible_at, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    frame_id,
                    session_id,
                    revision,
                    transition.current.current_index,
                    utc_text(current_bar.close_time),
                    utc_text(now),
                ),
            )
            self._insert_event(connection, event)
            from replaytutor.modules.execution.service import (
                load_execution,
                settle_pending_orders,
            )

            updated_row = dict(row)
            updated_row.update(
                status="paused",
                revision=revision,
                current_index=transition.current.current_index,
                updated_at=utc_text(now),
            )
            settle_pending_orders(
                connection,
                market_data=self.market_data,
                row=updated_row,
                from_index=transition.previous.current_index + 1,
                to_index=transition.current.current_index,
                frame_id=frame_id,
            )
            session = self._session_from_values(
                updated_row,
                frame_id=frame_id,
                visible_at=current_bar.close_time,
            )
            result = SessionDelta(
                session=session,
                bars=self._visible_bars(session),
                events=[event],
                execution=load_execution(connection, updated_row),
                annotations=self._load_annotations(connection, session_id),
            )
            connection.execute(
                """
                INSERT INTO session_command (
                    command_id, session_id, command_type, expected_revision,
                    request_json, result_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    command.command_id,
                    session_id,
                    command.kind,
                    command.expected_revision,
                    command.model_dump_json(),
                    result.model_dump_json(),
                    utc_text(now),
                ),
            )
            connection.commit()
            return result
        except BaseException:
            if connection.in_transaction:
                connection.rollback()
            raise
        finally:
            connection.close()

    def finish(
        self,
        session_id: str,
        request: FinishSessionRequest,
    ) -> CompletedSession:
        connection = connect_database(self.settings.database_path)
        try:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                """
                SELECT session_id, command_type, result_json
                FROM session_command
                WHERE command_id = ?
                """,
                (request.command_id,),
            ).fetchone()
            if existing is not None:
                if (
                    str(existing["session_id"]) != session_id
                    or str(existing["command_type"]) != "finish"
                ):
                    raise TrainingSessionError(
                        "Command id was already used by another operation"
                    )
                connection.rollback()
                stored = CompletedSession.model_validate_json(existing["result_json"])
                return stored.model_copy(update={"idempotent_replay": True})

            row = self._session_row(connection, session_id)
            if int(row["revision"]) != request.expected_revision:
                raise SessionConflictError(int(row["revision"]))
            if row["status"] == "completed":
                raise InvalidSessionStateError(
                    "Completed session requires the original finish command id"
                )
            if row["status"] == "stopped":
                raise InvalidSessionStateError("Stopped session cannot be completed")

            revision = int(row["revision"]) + 1
            now = datetime.now(UTC)
            current_bar = self._bar_at(
                str(row["snapshot_id"]),
                int(row["current_index"]),
            )
            frame_id = self._frame_id(session_id, revision)
            event = SessionEvent(
                event_id=new_id("evt"),
                session_id=session_id,
                sequence=self._next_sequence(connection, session_id),
                revision=revision,
                event_type="session_completed",
                occurred_at=now,
                payload={"final_index": int(row["current_index"])},
            )
            connection.execute(
                """
                UPDATE replay_session
                SET status = 'completed', revision = ?, updated_at = ?, completed_at = ?
                WHERE session_id = ?
                """,
                (revision, utc_text(now), utc_text(now), session_id),
            )
            connection.execute(
                """
                INSERT INTO replay_frame (
                    frame_id, session_id, revision, current_index, visible_at, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    frame_id,
                    session_id,
                    revision,
                    int(row["current_index"]),
                    utc_text(current_bar.close_time),
                    utc_text(now),
                ),
            )
            self._insert_event(connection, event)
            updated_row = dict(row)
            updated_row.update(
                status="completed",
                revision=revision,
                updated_at=utc_text(now),
                completed_at=utc_text(now),
            )
            snapshot = self.market_data.get_snapshot(str(row["snapshot_id"]))
            result = CompletedSession(
                session=self._session_from_values(
                    updated_row,
                    frame_id=frame_id,
                    visible_at=current_bar.close_time,
                ),
                finished_at=now,
                revealed_coverage_start=snapshot.coverage_start,
                revealed_coverage_end=snapshot.coverage_end,
            )
            connection.execute(
                """
                INSERT INTO session_command (
                    command_id, session_id, command_type, expected_revision,
                    request_json, result_json, created_at
                ) VALUES (?, ?, 'finish', ?, ?, ?, ?)
                """,
                (
                    request.command_id,
                    session_id,
                    request.expected_revision,
                    request.model_dump_json(),
                    result.model_dump_json(),
                    utc_text(now),
                ),
            )
            connection.commit()
            return result
        except BaseException:
            if connection.in_transaction:
                connection.rollback()
            raise
        finally:
            connection.close()

    def _session_row(
        self,
        connection: sqlite3.Connection,
        session_id: str,
    ) -> dict[str, Any]:
        row = connection.execute(
            "SELECT * FROM replay_session WHERE session_id = ?",
            (session_id,),
        ).fetchone()
        if row is None:
            raise SessionNotFoundError("Session not found")
        return dict(row)

    def _session_from_row(
        self,
        connection: sqlite3.Connection,
        row: dict[str, Any],
    ) -> ReplaySession:
        frame = connection.execute(
            """
            SELECT * FROM replay_frame
            WHERE session_id = ?
            ORDER BY revision DESC
            LIMIT 1
            """,
            (row["session_id"],),
        ).fetchone()
        if frame is None:
            raise TrainingSessionError("Session has no replay frame")
        return self._session_from_values(
            row,
            frame_id=str(frame["frame_id"]),
            visible_at=parse_utc(str(frame["visible_at"])),
        )

    def _session_from_values(
        self,
        row: dict[str, Any],
        *,
        frame_id: str,
        visible_at: datetime,
    ) -> ReplaySession:
        snapshot = self.market_data.get_snapshot(str(row["snapshot_id"]))
        total_bars = int(row["total_bars"])
        current_index = int(row["current_index"])
        revision = int(row["revision"])
        frame = ReplayFrame(
            frame_id=frame_id,
            session_id=str(row["session_id"]),
            revision=revision,
            current_index=current_index,
            total_bars=total_bars,
            visible_at=visible_at,
            progress=current_index / (total_bars - 1),
        )
        return ReplaySession(
            session_id=str(row["session_id"]),
            snapshot_id=str(row["snapshot_id"]),
            instrument=snapshot.instrument,
            status=cast(SessionStatus, str(row["status"])),
            revision=revision,
            frame=frame,
            start_index=int(row["start_index"]),
            warmup_bars=int(row["warmup_bars"]),
            seed=int(row["seed"]),
            initial_cash=str(row["initial_cash"]),
            hidden_real_date=bool(row["hidden_real_date"]),
            playbook_id=(
                str(row["playbook_id"])
                if row.get("playbook_id") is not None
                else None
            ),
            fingerprint=str(row["fingerprint"]),
            created_at=parse_utc(str(row["created_at"])),
            updated_at=parse_utc(str(row["updated_at"])),
        )

    def _visible_bars(self, session: ReplaySession) -> list[Bar]:
        limit = min(VISIBLE_WINDOW_BARS, session.frame.current_index + 1)
        offset = session.frame.current_index - limit + 1
        bars = self.market_data.query_snapshot_bar_slice(
            session.snapshot_id,
            offset=offset,
            limit=limit,
        )
        if not bars or bars[-1].close_time != session.frame.visible_at:
            raise TrainingSessionError("Visible frame does not match market data")
        if any(bar.close_time > session.frame.visible_at for bar in bars):
            raise TrainingSessionError("Future market data escaped the replay boundary")
        return bars

    def _bar_at(self, snapshot_id: str, index: int) -> Bar:
        bars = self.market_data.query_snapshot_bar_slice(
            snapshot_id,
            offset=index,
            limit=1,
        )
        if len(bars) != 1:
            raise TrainingSessionError("Replay bar is missing from the snapshot")
        return bars[0]

    @staticmethod
    def _load_annotations(
        connection: sqlite3.Connection,
        session_id: str,
    ) -> list[Any]:
        from replaytutor.modules.annotations import load_annotations

        return load_annotations(connection, session_id)

    @staticmethod
    def _frame_id(session_id: str, revision: int) -> str:
        return stable_id(
            "frm",
            "replaytutor:frame",
            f"{session_id}:{revision}",
        )

    @staticmethod
    def _next_sequence(connection: sqlite3.Connection, session_id: str) -> int:
        row = connection.execute(
            "SELECT COALESCE(MAX(sequence), 0) + 1 FROM session_event WHERE session_id = ?",
            (session_id,),
        ).fetchone()
        return int(row[0])

    @staticmethod
    def _insert_event(
        connection: sqlite3.Connection,
        event: SessionEvent,
    ) -> None:
        connection.execute(
            """
            INSERT INTO session_event (
                event_id, session_id, sequence, revision, event_type,
                payload_json, occurred_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event.event_id,
                event.session_id,
                event.sequence,
                event.revision,
                event.event_type,
                json.dumps(event.payload, separators=(",", ":"), sort_keys=True),
                utc_text(event.occurred_at),
            ),
        )


def parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed.astimezone(UTC)
