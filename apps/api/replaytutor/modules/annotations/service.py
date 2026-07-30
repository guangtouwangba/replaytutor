from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from typing import Any, Literal, cast

from replaytutor.config import Settings
from replaytutor.contracts import (
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
            AnnotationPoint.model_validate(item)
            for item in json.loads(str(values["points_json"]))
        ],
        provenance_run_id=(
            str(values["provenance_run_id"])
            if values["provenance_run_id"] is not None
            else None
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


def _validate_points(
    points: list[AnnotationPoint],
    *,
    visible_at: datetime,
) -> None:
    if any(point.time > visible_at for point in points):
        raise TrainingSessionError(
            "Annotation point cannot reference market data after visible_at"
        )


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
                    raise TrainingSessionError(
                        "Command id was already used by another session"
                    )
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
                [
                    point.model_dump(mode="json")
                    for point in annotation.points
                ],
                separators=(",", ":"),
                sort_keys=True,
            ),
            annotation.provenance_run_id,
            command_id,
            utc_text(annotation.created_at),
        ),
    )
