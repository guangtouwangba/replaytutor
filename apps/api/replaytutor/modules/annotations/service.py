from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from typing import Any, Literal, cast

from replaytutor.config import Settings
from replaytutor.contracts import (
    AnnotationActionRequest,
    AnnotationDisposition,
    AnnotationPoint,
    ChartAnnotation,
    CreateAnnotationRequest,
    TutorChartInstruction,
)
from replaytutor.ids import stable_id
from replaytutor.modules.market_data.service import utc_text
from replaytutor.modules.training_session.service import (
    SessionConflictError,
    SessionNotFoundError,
    TrainingSessionError,
    parse_utc,
)
from replaytutor.storage.database import connect_database


def _annotation_from_row(row: sqlite3.Row | dict[str, Any]) -> ChartAnnotation:
    values = dict(row)
    return ChartAnnotation(
        annotation_id=str(values["annotation_id"]),
        session_id=str(values["session_id"]),
        frame_id=str(values["frame_id"]),
        layer=cast(Literal["user", "ai"], str(values["layer"])),
        shape=cast(
            Literal["line", "zone", "marker", "label"],
            str(values["shape"]),
        ),
        label=str(values["label"]),
        points=[
            AnnotationPoint.model_validate(item) for item in json.loads(str(values["points_json"]))
        ],
        provenance_run_id=(
            str(values["provenance_run_id"]) if values["provenance_run_id"] is not None else None
        ),
        created_at=parse_utc(str(values["created_at"])),
    )


def load_annotations(
    connection: sqlite3.Connection,
    session_id: str,
) -> list[ChartAnnotation]:
    rows = connection.execute(
        """
        SELECT * FROM session_annotation
        WHERE session_id = ?
        ORDER BY created_at, annotation_id
        """,
        (session_id,),
    ).fetchall()
    return [_annotation_from_row(row) for row in rows]


def load_dispositions(
    connection: sqlite3.Connection,
    session_id: str,
) -> list[AnnotationDisposition]:
    annotations = load_annotations(connection, session_id)
    rows = connection.execute(
        """
        SELECT * FROM session_annotation_event
        WHERE session_id = ?
        ORDER BY rowid
        """,
        (session_id,),
    ).fetchall()
    events_by_annotation: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        events_by_annotation.setdefault(str(row["annotation_id"]), []).append(dict(row))
    return [
        _disposition(annotation, events_by_annotation.get(annotation.annotation_id, []))
        for annotation in annotations
    ]


def _disposition(
    annotation: ChartAnnotation,
    events: list[dict[str, Any]],
) -> AnnotationDisposition:
    state: Literal["active", "proposed", "accepted", "rejected", "deleted"] = (
        "active" if annotation.layer == "user" else "proposed"
    )
    effective_label = annotation.label
    effective_points = annotation.points
    latest_event_id = None
    for event in events:
        action = str(event["action"])
        latest_event_id = str(event["event_id"])
        if action == "rejected":
            state = "rejected"
        elif action == "deleted":
            state = "deleted"
        elif action == "accepted":
            state = "accepted"
        elif action == "revised":
            state = "active" if annotation.layer == "user" else "accepted"
            effective_label = str(event["replacement_label"])
            effective_points = [
                AnnotationPoint.model_validate(item)
                for item in json.loads(str(event["replacement_points_json"]))
            ]
    return AnnotationDisposition(
        annotation_id=annotation.annotation_id,
        state=state,
        effective_label=effective_label,
        effective_points=effective_points,
        original_annotation=annotation,
        latest_event_id=latest_event_id,
    )


def _validate_points(
    points: list[AnnotationPoint],
    *,
    visible_at: datetime,
) -> None:
    if any(point.time > visible_at for point in points):
        raise TrainingSessionError("Annotation point cannot reference market data after visible_at")


class AnnotationService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def create(
        self,
        session_id: str,
        request: CreateAnnotationRequest,
    ) -> ChartAnnotation:
        connection = connect_database(self.settings.database_path)
        try:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                "SELECT * FROM session_annotation WHERE command_id = ?",
                (request.command_id,),
            ).fetchone()
            if existing is not None:
                if str(existing["session_id"]) != session_id:
                    raise TrainingSessionError("Command id was already used by another session")
                connection.rollback()
                return _annotation_from_row(existing)
            row = connection.execute(
                "SELECT revision FROM replay_session WHERE session_id = ?",
                (session_id,),
            ).fetchone()
            if row is None:
                raise SessionNotFoundError("Session not found")
            if int(row["revision"]) != request.expected_revision:
                raise SessionConflictError(int(row["revision"]))
            frame = connection.execute(
                """
                SELECT frame_id, visible_at FROM replay_frame
                WHERE session_id = ? ORDER BY revision DESC LIMIT 1
                """,
                (session_id,),
            ).fetchone()
            if frame is None:
                raise TrainingSessionError("Session has no replay frame")
            _validate_points(
                request.points,
                visible_at=parse_utc(str(frame["visible_at"])),
            )
            now = datetime.now(UTC)
            annotation = ChartAnnotation(
                annotation_id=stable_id(
                    "ann",
                    "replaytutor:user-annotation",
                    request.command_id,
                ),
                session_id=session_id,
                frame_id=str(frame["frame_id"]),
                layer="user",
                shape=request.shape,
                label=request.label,
                points=request.points,
                created_at=now,
            )
            _insert(
                connection,
                annotation,
                command_id=request.command_id,
            )
            connection.commit()
            return annotation
        except BaseException:
            if connection.in_transaction:
                connection.rollback()
            raise
        finally:
            connection.close()

    def list_dispositions(self, session_id: str) -> list[AnnotationDisposition]:
        connection = connect_database(self.settings.database_path)
        try:
            row = connection.execute(
                "SELECT 1 FROM replay_session WHERE session_id = ?",
                (session_id,),
            ).fetchone()
            if row is None:
                raise SessionNotFoundError("Session not found")
            return load_dispositions(connection, session_id)
        finally:
            connection.close()

    def act(
        self,
        session_id: str,
        annotation_id: str,
        request: AnnotationActionRequest,
    ) -> AnnotationDisposition:
        connection = connect_database(self.settings.database_path)
        try:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                """
                SELECT rowid AS event_rowid, * FROM session_annotation_event
                WHERE command_id = ?
                """,
                (request.command_id,),
            ).fetchone()
            if existing is not None:
                if (
                    str(existing["session_id"]) != session_id
                    or str(existing["annotation_id"]) != annotation_id
                ):
                    raise TrainingSessionError("Command id was already used by another annotation")
                annotation_row = connection.execute(
                    "SELECT * FROM session_annotation WHERE annotation_id = ?",
                    (annotation_id,),
                ).fetchone()
                if annotation_row is None:
                    raise TrainingSessionError("Annotation not found")
                events = connection.execute(
                    """
                    SELECT * FROM session_annotation_event
                    WHERE annotation_id = ? AND rowid <= ?
                    ORDER BY rowid
                    """,
                    (annotation_id, existing["event_rowid"]),
                ).fetchall()
                connection.rollback()
                return _disposition(
                    _annotation_from_row(annotation_row),
                    [dict(event) for event in events],
                )
            session = connection.execute(
                "SELECT revision FROM replay_session WHERE session_id = ?",
                (session_id,),
            ).fetchone()
            if session is None:
                raise SessionNotFoundError("Session not found")
            current_revision = int(session["revision"])
            if current_revision != request.expected_revision:
                raise SessionConflictError(current_revision)
            annotation_row = connection.execute(
                """
                SELECT * FROM session_annotation
                WHERE annotation_id = ? AND session_id = ?
                """,
                (annotation_id, session_id),
            ).fetchone()
            if annotation_row is None:
                raise TrainingSessionError("Annotation not found in session")
            annotation = _annotation_from_row(annotation_row)
            if request.action in {"accepted", "rejected"} and annotation.layer != "ai":
                raise TrainingSessionError("Only AI annotations can be accepted or rejected")
            replacement_label: str | None = None
            replacement_points_json: str | None = None
            if request.action == "revised":
                if request.label is None or request.points is None:
                    raise TrainingSessionError("Revised annotations require label and points")
                frame = connection.execute(
                    """
                    SELECT visible_at FROM replay_frame
                    WHERE session_id = ? ORDER BY revision DESC LIMIT 1
                    """,
                    (session_id,),
                ).fetchone()
                if frame is None:
                    raise TrainingSessionError("Session has no replay frame")
                _validate_points(
                    request.points,
                    visible_at=parse_utc(str(frame["visible_at"])),
                )
                replacement_label = request.label
                replacement_points_json = json.dumps(
                    [point.model_dump(mode="json") for point in request.points],
                    separators=(",", ":"),
                    sort_keys=True,
                )
            now = datetime.now(UTC)
            event_id = stable_id(
                "ane",
                "replaytutor:annotation-event",
                request.command_id,
            )
            connection.execute(
                """
                INSERT INTO session_annotation_event (
                    event_id, annotation_id, session_id, expected_revision,
                    action, replacement_label, replacement_points_json,
                    command_id, actor, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'user', ?)
                """,
                (
                    event_id,
                    annotation_id,
                    session_id,
                    request.expected_revision,
                    request.action,
                    replacement_label,
                    replacement_points_json,
                    request.command_id,
                    utc_text(now),
                ),
            )
            events = connection.execute(
                """
                SELECT * FROM session_annotation_event
                WHERE annotation_id = ?
                ORDER BY rowid
                """,
                (annotation_id,),
            ).fetchall()
            connection.commit()
            return _disposition(annotation, [dict(event) for event in events])
        except BaseException:
            if connection.in_transaction:
                connection.rollback()
            raise
        finally:
            connection.close()


def persist_ai_annotations(
    connection: sqlite3.Connection,
    *,
    run_id: str,
    session_id: str,
    frame_id: str,
    instructions: list[TutorChartInstruction],
) -> list[ChartAnnotation]:
    if not instructions:
        return []
    frame = connection.execute(
        """
        SELECT visible_at FROM replay_frame
        WHERE session_id = ? AND frame_id = ?
        """,
        (session_id, frame_id),
    ).fetchone()
    if frame is None:
        raise TrainingSessionError("Tutor frame no longer exists")
    visible_at = parse_utc(str(frame["visible_at"]))
    now = datetime.now(UTC)
    annotations: list[ChartAnnotation] = []
    for index, instruction in enumerate(instructions):
        _validate_points(instruction.points, visible_at=visible_at)
        annotation = ChartAnnotation(
            annotation_id=stable_id(
                "ann",
                "replaytutor:ai-annotation",
                f"{run_id}:{index}",
            ),
            session_id=session_id,
            frame_id=frame_id,
            layer="ai",
            shape=instruction.shape,
            label=instruction.label,
            points=instruction.points,
            provenance_run_id=run_id,
            created_at=now,
        )
        _insert(connection, annotation, command_id=None)
        annotations.append(annotation)
    return annotations


def _insert(
    connection: sqlite3.Connection,
    annotation: ChartAnnotation,
    *,
    command_id: str | None,
) -> None:
    connection.execute(
        """
        INSERT INTO session_annotation (
            annotation_id, session_id, frame_id, layer, shape, label,
            points_json, provenance_run_id, command_id, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            annotation.annotation_id,
            annotation.session_id,
            annotation.frame_id,
            annotation.layer,
            annotation.shape,
            annotation.label,
            json.dumps(
                [point.model_dump(mode="json") for point in annotation.points],
                separators=(",", ":"),
                sort_keys=True,
            ),
            annotation.provenance_run_id,
            command_id,
            utc_text(annotation.created_at),
        ),
    )
