from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from typing import Any, cast

from replaytutor.config import Settings
from replaytutor.contracts import (
    ChartTool,
    ChartToolManifest,
    ChartToolManifestListResponse,
    ChartToolPreference,
    ChartToolPreferenceListResponse,
    ChartToolTemplate,
    ChartToolTemplateListResponse,
    CreateChartToolTemplateRequest,
    UpdateChartToolPreferenceRequest,
)
from replaytutor.ids import new_id
from replaytutor.modules.market_data.service import utc_text
from replaytutor.storage.database import connect_database

TOOL_GROUPS: dict[str, tuple[str, ...]] = {
    "analysis": (
        "trend_line",
        "trend_ray",
        "extended_line",
        "price_line",
        "horizontal_ray",
        "vertical_line",
        "parallel_channel",
        "price_channel",
        "info_line",
        "trend_angle",
        "cross_line",
        "regression_trend",
        "flat_top_bottom",
        "disjoint_channel",
        "anchored_vwap",
        "horizontal_line",
    ),
    "fibonacci": (
        "fibonacci_retracement",
        "fibonacci_extension",
        "fibonacci_channel",
        "fibonacci_time_zone",
        "pitchfork",
    ),
    "measure": ("measure", "price_range", "date_range"),
    "shapes": ("zone", "brush", "polyline", "head_shoulders", "triangle_pattern"),
    "notes": ("text", "note_marker"),
    "trade": (
        "planned_entry",
        "add_position",
        "reduce_position",
        "planned_exit",
        "stop_loss",
        "take_profit",
    ),
    "position": ("long_position", "short_position", "risk_reward"),
}

ANCHOR_COUNTS: dict[str, int] = {
    "price_line": 1,
    "vertical_line": 1,
    "cross_line": 1,
    "horizontal_line": 1,
    "text": 1,
    "note_marker": 1,
    "planned_entry": 1,
    "add_position": 1,
    "reduce_position": 1,
    "planned_exit": 1,
    "stop_loss": 1,
    "take_profit": 1,
    "parallel_channel": 3,
    "price_channel": 3,
    "flat_top_bottom": 3,
    "fibonacci_extension": 3,
    "fibonacci_channel": 3,
    "pitchfork": 3,
    "long_position": 3,
    "short_position": 3,
    "risk_reward": 3,
    "disjoint_channel": 4,
    "brush": 4,
    "polyline": 4,
    "head_shoulders": 4,
    "triangle_pattern": 4,
}


def _geometry(tool: str) -> str:
    if tool in {"long_position", "short_position", "risk_reward"}:
        return "risk_reward"
    if tool == "anchored_vwap":
        return "anchored_series"
    if tool in {"head_shoulders", "triangle_pattern"}:
        return "pattern"
    if tool in {"brush", "polyline", "disjoint_channel"}:
        return "polyline"
    if tool.startswith("fibonacci_") or tool == "pitchfork":
        return "levels"
    if tool in {"measure", "price_range", "date_range", "info_line", "trend_angle"}:
        return "measurement"
    if tool in {"parallel_channel", "price_channel", "regression_trend", "flat_top_bottom"}:
        return "channel"
    if ANCHOR_COUNTS.get(tool) == 1:
        return "point"
    if tool == "zone":
        return "region"
    return "line"


class ChartToolService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def manifests(self) -> ChartToolManifestListResponse:
        tools: list[ChartToolManifest] = []
        for group, ids in TOOL_GROUPS.items():
            for tool in ids:
                count = ANCHOR_COUNTS.get(tool, 2)
                tools.append(
                    ChartToolManifest(
                        tool_id=tool,  # type: ignore[arg-type]
                        group=group,  # type: ignore[arg-type]
                        geometry_kind=_geometry(tool),  # type: ignore[arg-type]
                        min_anchors=count,
                        max_anchors=16 if tool in {"brush", "polyline"} else count,
                        tutor_semantic=tool,
                    )
                )
        if len(tools) != 40 or len({item.tool_id for item in tools}) != 40:
            raise RuntimeError("Professional drawing registry must contain exactly 40 unique tools")
        return ChartToolManifestListResponse(tools=tools)

    def list_templates(self) -> ChartToolTemplateListResponse:
        with connect_database(self.settings.database_path) as connection:
            rows = connection.execute(
                "SELECT * FROM chart_tool_template ORDER BY updated_at DESC, template_id"
            ).fetchall()
        return ChartToolTemplateListResponse(templates=[self._template(row) for row in rows])

    def create_template(self, request: CreateChartToolTemplateRequest) -> ChartToolTemplate:
        now = datetime.now(UTC)
        template = ChartToolTemplate(
            template_id=new_id("tpl"),
            tool=request.tool,
            tool_version=request.tool_version,
            name=request.name,
            style=request.style,
            properties=request.properties,
            created_at=now,
            updated_at=now,
        )
        with connect_database(self.settings.database_path) as connection:
            connection.execute(
                """
                INSERT INTO chart_tool_template (
                    template_id, tool, tool_version, name, style_json,
                    properties_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    template.template_id,
                    template.tool,
                    template.tool_version,
                    template.name,
                    json.dumps(
                        template.style.model_dump(mode="json"),
                        separators=(",", ":"),
                        sort_keys=True,
                    ),
                    json.dumps(template.properties, separators=(",", ":"), sort_keys=True),
                    utc_text(now),
                    utc_text(now),
                ),
            )
            connection.commit()
        return template

    def delete_template(self, template_id: str) -> None:
        with connect_database(self.settings.database_path) as connection:
            connection.execute(
                "UPDATE chart_tool_preference SET default_template_id = NULL "
                "WHERE default_template_id = ?",
                (template_id,),
            )
            deleted = connection.execute(
                "DELETE FROM chart_tool_template WHERE template_id = ?", (template_id,)
            ).rowcount
            connection.commit()
        if not deleted:
            raise ValueError("Chart tool template not found")

    def list_preferences(self) -> ChartToolPreferenceListResponse:
        with connect_database(self.settings.database_path) as connection:
            rows = connection.execute(
                "SELECT * FROM chart_tool_preference ORDER BY favorite DESC, recent_rank, tool"
            ).fetchall()
        return ChartToolPreferenceListResponse(preferences=[self._preference(row) for row in rows])

    def update_preference(
        self,
        tool: ChartTool,
        request: UpdateChartToolPreferenceRequest,
    ) -> ChartToolPreference:
        if tool == "ai_suggestion":
            raise ValueError("AI suggestion is not a user drawing tool")
        now = datetime.now(UTC)
        with connect_database(self.settings.database_path) as connection:
            if request.default_template_id is not None:
                template = connection.execute(
                    "SELECT tool FROM chart_tool_template WHERE template_id = ?",
                    (request.default_template_id,),
                ).fetchone()
                if template is None or str(template["tool"]) != tool:
                    raise ValueError("Default template must exist and belong to the same tool")
            connection.execute(
                """
                INSERT INTO chart_tool_preference (
                    tool, favorite, recent_rank, continuous, default_template_id, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(tool) DO UPDATE SET
                    favorite=excluded.favorite,
                    recent_rank=excluded.recent_rank,
                    continuous=excluded.continuous,
                    default_template_id=excluded.default_template_id,
                    updated_at=excluded.updated_at
                """,
                (
                    tool,
                    request.favorite,
                    request.recent_rank,
                    request.continuous,
                    request.default_template_id,
                    utc_text(now),
                ),
            )
            row = connection.execute(
                "SELECT * FROM chart_tool_preference WHERE tool = ?", (tool,)
            ).fetchone()
            connection.commit()
        assert row is not None
        return self._preference(row)

    @staticmethod
    def _template(row: sqlite3.Row) -> ChartToolTemplate:
        values: dict[str, Any] = dict(row)
        return ChartToolTemplate(
            template_id=str(values["template_id"]),
            tool=cast(ChartTool, str(values["tool"])),
            tool_version=int(values["tool_version"]),
            name=str(values["name"]),
            style=json.loads(str(values["style_json"])),
            properties=json.loads(str(values["properties_json"])),
            created_at=datetime.fromisoformat(str(values["created_at"])),
            updated_at=datetime.fromisoformat(str(values["updated_at"])),
        )

    @staticmethod
    def _preference(row: sqlite3.Row) -> ChartToolPreference:
        values: dict[str, Any] = dict(row)
        return ChartToolPreference(
            tool=cast(ChartTool, str(values["tool"])),
            favorite=bool(values["favorite"]),
            recent_rank=int(values["recent_rank"]) if values["recent_rank"] is not None else None,
            continuous=bool(values["continuous"]),
            default_template_id=(
                str(values["default_template_id"])
                if values["default_template_id"] is not None
                else None
            ),
            updated_at=datetime.fromisoformat(str(values["updated_at"])),
        )
