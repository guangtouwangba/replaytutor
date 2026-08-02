from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal

from replaytutor.config import Settings
from replaytutor.contracts import (
    ChartContextBundle,
    ChartContextObject,
    SessionDelta,
)
from replaytutor.ids import new_id
from replaytutor.modules.annotations import load_dispositions
from replaytutor.modules.market_data.service import utc_text
from replaytutor.storage.database import connect_database


class ChartContextBuilder:
    """Resolve selected chart objects into one immutable, future-safe Tutor snapshot."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def build(
        self,
        delta: SessionDelta,
        annotation_ids: list[str],
    ) -> ChartContextBundle | None:
        selected_ids = list(dict.fromkeys(annotation_ids))
        if not selected_ids:
            return None

        with connect_database(self.settings.database_path) as connection:
            dispositions = {
                item.annotation_id: item
                for item in load_dispositions(connection, delta.session.session_id)
            }
            objects: list[ChartContextObject] = []
            for annotation_id in selected_ids:
                disposition = dispositions.get(annotation_id)
                if disposition is None:
                    raise ValueError(f"Chart context object not found: {annotation_id}")
                if disposition.state in {"rejected", "deleted"}:
                    raise ValueError(f"Chart context object is not active: {annotation_id}")
                annotation = disposition.original_annotation
                if any(
                    point.time > delta.session.frame.visible_at
                    for point in disposition.effective_points
                ):
                    raise ValueError("Chart context object extends beyond visible_at")
                objects.append(
                    ChartContextObject(
                        object_id=annotation.annotation_id,
                        revision_id=disposition.latest_event_id,
                        layer=annotation.layer,
                        shape=annotation.shape,
                        tool=annotation.tool,
                        semantic_role=annotation.semantic_role,
                        label=disposition.effective_label,
                        points=disposition.effective_points,
                        metadata=disposition.effective_metadata,
                        tool_version=annotation.tool_version,
                        geometry=disposition.effective_geometry,
                        style=disposition.effective_style,
                        properties=disposition.effective_properties,
                        algorithm_version=annotation.algorithm_version,
                        derived_facts=annotation.derived_facts,
                    )
                )

            evidence_ids = self._evidence_ids(delta, objects)
            now = datetime.now(UTC)
            bundle = ChartContextBundle(
                context_bundle_id=new_id("ctx"),
                session_id=delta.session.session_id,
                frame_id=delta.session.frame.frame_id,
                visible_at=delta.session.frame.visible_at,
                objects=objects,
                evidence_ids=evidence_ids,
                derived_facts=self._derived_facts(objects),
                created_at=now,
            )
            connection.execute(
                """
                INSERT INTO chart_context_bundle (
                    context_bundle_id, session_id, frame_id, visible_at,
                    selection_mode, objects_json, evidence_ids_json,
                    derived_facts_json, created_at
                ) VALUES (?, ?, ?, ?, 'selected', ?, ?, ?, ?)
                """,
                (
                    bundle.context_bundle_id,
                    bundle.session_id,
                    bundle.frame_id,
                    utc_text(bundle.visible_at),
                    json.dumps(
                        [item.model_dump(mode="json") for item in bundle.objects],
                        ensure_ascii=False,
                        separators=(",", ":"),
                        sort_keys=True,
                    ),
                    json.dumps(bundle.evidence_ids, separators=(",", ":"), sort_keys=True),
                    json.dumps(
                        bundle.derived_facts,
                        ensure_ascii=False,
                        separators=(",", ":"),
                        sort_keys=True,
                    ),
                    utc_text(now),
                ),
            )
        return bundle

    @staticmethod
    def _evidence_ids(
        delta: SessionDelta,
        objects: list[ChartContextObject],
    ) -> list[str]:
        evidence_ids = {item.object_id for item in objects}
        for item in objects:
            start = min(point.time for point in item.points)
            end = max(point.time for point in item.points)
            in_range = [bar for bar in delta.bars if start <= bar.close_time <= end]
            if not in_range:
                closest = next(
                    (bar for bar in reversed(delta.bars) if bar.close_time <= end),
                    None,
                )
                if closest is not None:
                    evidence_ids.add(closest.bar_id)
            else:
                evidence_ids.update(bar.bar_id for bar in in_range)
        return sorted(evidence_ids)

    @staticmethod
    def _derived_facts(objects: list[ChartContextObject]) -> dict[str, str]:
        prices = [Decimal(point.price) for item in objects for point in item.points]
        times = [point.time for item in objects for point in item.points]
        return {
            "selected_object_count": str(len(objects)),
            "anchor_count": str(sum(len(item.points) for item in objects)),
            "price_low": str(min(prices)),
            "price_high": str(max(prices)),
            "time_start": min(times).isoformat(),
            "time_end": max(times).isoformat(),
        }
