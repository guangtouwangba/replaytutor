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
    ChartGeometry,
    ChartObjectStyle,
    ChartSemanticRole,
    ChartTool,
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
    points = [
        AnnotationPoint.model_validate(item) for item in json.loads(str(values["points_json"]))
    ]
    geometry_payload = values.get("geometry_json")
    geometry = (
        ChartGeometry.model_validate(json.loads(str(geometry_payload)))
        if geometry_payload
        else ChartGeometry(
            kind=(
                "risk_reward"
                if str(values.get("tool")) in {"long_position", "short_position", "risk_reward"}
                else "region"
                if str(values["shape"]) == "zone"
                else "point"
                if str(values["shape"]) in {"marker", "label"}
                else "line"
            ),
            anchors=points,
        )
    )
    return ChartAnnotation(
        annotation_id=str(values["annotation_id"]),
        session_id=str(values["session_id"]),
        frame_id=str(values["frame_id"]),
        layer=cast(Literal["user", "ai"], str(values["layer"])),
        shape=cast(
            Literal["line", "zone", "marker", "label"],
            str(values["shape"]),
        ),
        tool=cast(ChartTool, str(values.get("tool", "note_marker"))),
        semantic_role=cast(
            ChartSemanticRole,
            str(values.get("semantic_role", "note")),
        ),
        label=str(values["label"]),
        points=points,
        metadata=json.loads(str(values.get("metadata_json", "{}"))),
        tool_version=int(values.get("tool_version", 1)),
        geometry=geometry,
        style=ChartObjectStyle.model_validate(json.loads(str(values.get("style_json") or "{}"))),
        properties=json.loads(str(values.get("properties_json") or "{}")),
        derived_facts=json.loads(str(values.get("derived_facts_json") or "{}")),
        algorithm_version=str(values.get("algorithm_version") or "1"),
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
    effective_metadata = annotation.metadata
    effective_geometry = annotation.geometry or ChartGeometry(
        kind="line", anchors=annotation.points
    )
    effective_style = annotation.style
    effective_properties = annotation.properties
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
            replacement_metadata = event.get("replacement_metadata_json")
            if replacement_metadata is not None:
                effective_metadata = {
                    str(key): str(value)
                    for key, value in json.loads(str(replacement_metadata)).items()
                }
            replacement_geometry = event.get("replacement_geometry_json")
            if replacement_geometry is not None:
                effective_geometry = ChartGeometry.model_validate(
                    json.loads(str(replacement_geometry))
                )
            else:
                effective_geometry = effective_geometry.model_copy(
                    update={"anchors": effective_points}
                )
            replacement_style = event.get("replacement_style_json")
            if replacement_style is not None:
                effective_style = ChartObjectStyle.model_validate(
                    json.loads(str(replacement_style))
                )
            replacement_properties = event.get("replacement_properties_json")
            if replacement_properties is not None:
                effective_properties = json.loads(str(replacement_properties))
    return AnnotationDisposition(
        annotation_id=annotation.annotation_id,
        state=state,
        effective_label=effective_label,
        effective_points=effective_points,
        effective_metadata=effective_metadata,
        effective_geometry=effective_geometry,
        effective_style=effective_style,
        effective_properties=effective_properties,
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
                tool=request.tool,
                semantic_role=request.semantic_role,
                label=request.label,
                points=request.points,
                metadata=request.metadata,
                tool_version=request.tool_version,
                geometry=request.geometry
                or ChartGeometry(
                    kind=(
                        "risk_reward"
                        if request.tool in {"long_position", "short_position", "risk_reward"}
                        else "region"
                        if request.shape == "zone"
                        else "point"
                        if request.shape in {"marker", "label"}
                        else "line"
                    ),
                    anchors=request.points,
                ),
                style=request.style,
                properties=request.properties,
                derived_facts=request.derived_facts,
                algorithm_version=request.algorithm_version,
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
            replacement_metadata_json: str | None = None
            replacement_geometry_json: str | None = None
            replacement_style_json: str | None = None
            replacement_properties_json: str | None = None
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
                current = _disposition(
                    annotation,
                    [
                        dict(event)
                        for event in connection.execute(
                            """
                            SELECT * FROM session_annotation_event
                            WHERE annotation_id = ? ORDER BY rowid
                            """,
                            (annotation_id,),
                        ).fetchall()
                    ],
                )
                replacement_metadata_json = json.dumps(
                    request.metadata
                    if request.metadata is not None
                    else current.effective_metadata,
                    separators=(",", ":"),
                    sort_keys=True,
                )
                replacement_geometry_json = json.dumps(
                    (
                        request.geometry
                        or current.effective_geometry.model_copy(update={"anchors": request.points})
                    ).model_dump(mode="json"),
                    separators=(",", ":"),
                    sort_keys=True,
                )
                replacement_style_json = json.dumps(
                    (request.style or current.effective_style).model_dump(mode="json"),
                    separators=(",", ":"),
                    sort_keys=True,
                )
                replacement_properties_json = json.dumps(
                    request.properties
                    if request.properties is not None
                    else current.effective_properties,
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
                    replacement_metadata_json, replacement_geometry_json,
                    replacement_style_json, replacement_properties_json,
                    command_id, actor, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'user', ?)
                """,
                (
                    event_id,
                    annotation_id,
                    session_id,
                    request.expected_revision,
                    request.action,
                    replacement_label,
                    replacement_points_json,
                    replacement_metadata_json,
                    replacement_geometry_json,
                    replacement_style_json,
                    replacement_properties_json,
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
            tool="ai_suggestion",
            semantic_role="analysis",
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
            annotation_id, session_id, frame_id, layer, shape, tool,
            semantic_role, label, points_json, metadata_json,
            tool_version, geometry_json, style_json, properties_json,
            derived_facts_json, algorithm_version,
            provenance_run_id, command_id, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            annotation.annotation_id,
            annotation.session_id,
            annotation.frame_id,
            annotation.layer,
            annotation.shape,
            annotation.tool,
            annotation.semantic_role,
            annotation.label,
            json.dumps(
                [point.model_dump(mode="json") for point in annotation.points],
                separators=(",", ":"),
                sort_keys=True,
            ),
            json.dumps(annotation.metadata, separators=(",", ":"), sort_keys=True),
            annotation.tool_version,
            json.dumps(
                (
                    annotation.geometry or ChartGeometry(kind="line", anchors=annotation.points)
                ).model_dump(mode="json"),
                separators=(",", ":"),
                sort_keys=True,
            ),
            json.dumps(
                annotation.style.model_dump(mode="json"), separators=(",", ":"), sort_keys=True
            ),
            json.dumps(annotation.properties, separators=(",", ":"), sort_keys=True),
            json.dumps(annotation.derived_facts, separators=(",", ":"), sort_keys=True),
            annotation.algorithm_version,
            annotation.provenance_run_id,
            command_id,
            utc_text(annotation.created_at),
        ),
    )
