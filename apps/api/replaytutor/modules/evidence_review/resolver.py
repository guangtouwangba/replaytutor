from __future__ import annotations

import sqlite3
from typing import Any, Literal, cast

from replaytutor.config import Settings
from replaytutor.contracts import Bar, EvidenceTarget
from replaytutor.modules.annotations import load_dispositions
from replaytutor.modules.market_data.service import MarketDataService, utc_text
from replaytutor.modules.training_session.service import SessionNotFoundError, parse_utc
from replaytutor.storage.database import connect_database


class EvidenceResolver:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.market_data = MarketDataService(settings)

    def resolve(self, session_id: str, evidence_id: str) -> EvidenceTarget:
        with connect_database(self.settings.database_path) as connection:
            session = connection.execute(
                "SELECT * FROM replay_session WHERE session_id = ?",
                (session_id,),
            ).fetchone()
            if session is None:
                raise SessionNotFoundError("Session not found")

            plan = connection.execute(
                "SELECT * FROM trade_plan WHERE plan_id = ? AND session_id = ?",
                (evidence_id, session_id),
            ).fetchone()
            if plan is not None:
                return self._target_from_frame(
                    connection,
                    session_id=session_id,
                    evidence_id=evidence_id,
                    kind="plan",
                    frame_id=str(plan["frame_id"]),
                    price=cast(str | None, plan["entry_price"]),
                )

            order = connection.execute(
                "SELECT * FROM paper_order WHERE order_id = ? AND session_id = ?",
                (evidence_id, session_id),
            ).fetchone()
            if order is not None:
                return self._target_from_frame(
                    connection,
                    session_id=session_id,
                    evidence_id=evidence_id,
                    kind="order",
                    frame_id=str(order["submitted_frame_id"]),
                    price=cast(
                        str | None,
                        order["limit_price"] or order["stop_price"],
                    ),
                    order_id=evidence_id,
                )

            fill = connection.execute(
                "SELECT * FROM paper_fill WHERE fill_id = ? AND session_id = ?",
                (evidence_id, session_id),
            ).fetchone()
            if fill is not None:
                return self._target_from_frame(
                    connection,
                    session_id=session_id,
                    evidence_id=evidence_id,
                    kind="fill",
                    frame_id=str(fill["frame_id"]),
                    price=str(fill["price"]),
                    occurred_at=parse_utc(str(fill["executed_at"])),
                    fill_id=evidence_id,
                )

            dispositions = load_dispositions(connection, session_id)
            disposition = next(
                (item for item in dispositions if item.annotation_id == evidence_id),
                None,
            )
            if disposition is not None:
                annotation = disposition.original_annotation
                latest_event = connection.execute(
                    """
                    SELECT expected_revision FROM session_annotation_event
                    WHERE annotation_id = ?
                    ORDER BY rowid DESC LIMIT 1
                    """,
                    (evidence_id,),
                ).fetchone()
                frame_id = annotation.frame_id
                if latest_event is not None:
                    event_frame = connection.execute(
                        """
                        SELECT frame_id FROM replay_frame
                        WHERE session_id = ? AND revision = ?
                        """,
                        (session_id, int(latest_event["expected_revision"])),
                    ).fetchone()
                    if event_frame is not None:
                        frame_id = str(event_frame["frame_id"])
                point = disposition.effective_points[0]
                return self._target_from_frame(
                    connection,
                    session_id=session_id,
                    evidence_id=evidence_id,
                    kind=("user_annotation" if annotation.layer == "user" else "ai_annotation"),
                    frame_id=frame_id,
                    price=point.price,
                    occurred_at=point.time,
                    layer=annotation.layer,
                    annotation_id=evidence_id,
                )

            bar = self._visible_bar(dict(session), evidence_id)
            if bar is not None:
                frame = connection.execute(
                    """
                    SELECT frame_id FROM replay_frame
                    WHERE session_id = ? AND visible_at >= ?
                    ORDER BY revision LIMIT 1
                    """,
                    (session_id, utc_text(bar.close_time)),
                ).fetchone()
                return EvidenceTarget(
                    evidence_id=evidence_id,
                    session_id=session_id,
                    kind="bar",
                    frame_id=str(frame["frame_id"]) if frame is not None else None,
                    occurred_at=bar.close_time,
                    price=bar.raw.close,
                )

        raise SessionNotFoundError("Evidence not found in session")

    @staticmethod
    def _target_from_frame(
        connection: sqlite3.Connection,
        *,
        session_id: str,
        evidence_id: str,
        kind: Literal[
            "plan",
            "order",
            "fill",
            "user_annotation",
            "ai_annotation",
        ],
        frame_id: str,
        price: str | None,
        occurred_at: Any | None = None,
        layer: Literal["user", "ai"] | None = None,
        annotation_id: str | None = None,
        order_id: str | None = None,
        fill_id: str | None = None,
    ) -> EvidenceTarget:
        frame = connection.execute(
            """
            SELECT visible_at FROM replay_frame
            WHERE session_id = ? AND frame_id = ?
            """,
            (session_id, frame_id),
        ).fetchone()
        if frame is None:
            raise SessionNotFoundError("Evidence frame not found in session")
        return EvidenceTarget(
            evidence_id=evidence_id,
            session_id=session_id,
            kind=kind,
            frame_id=frame_id,
            occurred_at=occurred_at or parse_utc(str(frame["visible_at"])),
            price=price,
            layer=layer,
            annotation_id=annotation_id,
            order_id=order_id,
            fill_id=fill_id,
        )

    def _visible_bar(
        self,
        session: dict[str, Any],
        evidence_id: str,
    ) -> Bar | None:
        current_index = int(session["current_index"])
        offset = max(0, current_index - 499)
        bars = self.market_data.query_snapshot_bar_slice(
            str(session["snapshot_id"]),
            offset=offset,
            limit=current_index - offset + 1,
        )
        return next((bar for bar in bars if bar.bar_id == evidence_id), None)
