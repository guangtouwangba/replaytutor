"""Add versioned chart object geometry, styling and tool preferences."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0017_chart_objects_v2"
down_revision: str | Sequence[str] | None = "0016_annotation_metadata_events"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _columns(table: str) -> set[str]:
    return {column["name"] for column in sa.inspect(op.get_bind()).get_columns(table)}


def upgrade() -> None:
    annotation_columns = _columns("session_annotation")
    for name, column in (
        (
            "tool_version",
            sa.Column("tool_version", sa.Integer(), nullable=False, server_default="1"),
        ),
        ("geometry_json", sa.Column("geometry_json", sa.Text())),
        ("style_json", sa.Column("style_json", sa.Text(), nullable=False, server_default="{}")),
        (
            "properties_json",
            sa.Column("properties_json", sa.Text(), nullable=False, server_default="{}"),
        ),
        (
            "derived_facts_json",
            sa.Column("derived_facts_json", sa.Text(), nullable=False, server_default="{}"),
        ),
        (
            "algorithm_version",
            sa.Column("algorithm_version", sa.String(32), nullable=False, server_default="1"),
        ),
    ):
        if name not in annotation_columns:
            op.add_column("session_annotation", column)

    event_columns = _columns("session_annotation_event")
    for name in (
        "replacement_geometry_json",
        "replacement_style_json",
        "replacement_properties_json",
    ):
        if name not in event_columns:
            op.add_column("session_annotation_event", sa.Column(name, sa.Text()))

    inspector = sa.inspect(op.get_bind())
    if "chart_tool_template" not in inspector.get_table_names():
        op.create_table(
            "chart_tool_template",
            sa.Column("template_id", sa.String(40), primary_key=True),
            sa.Column("tool", sa.String(40), nullable=False),
            sa.Column("tool_version", sa.Integer(), nullable=False),
            sa.Column("name", sa.String(100), nullable=False),
            sa.Column("style_json", sa.Text(), nullable=False),
            sa.Column("properties_json", sa.Text(), nullable=False),
            sa.Column("created_at", sa.String(40), nullable=False),
            sa.Column("updated_at", sa.String(40), nullable=False),
        )
    if "chart_tool_preference" not in inspector.get_table_names():
        op.create_table(
            "chart_tool_preference",
            sa.Column("tool", sa.String(40), primary_key=True),
            sa.Column("favorite", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("recent_rank", sa.Integer()),
            sa.Column("continuous", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("default_template_id", sa.String(40)),
            sa.Column("updated_at", sa.String(40), nullable=False),
        )

    op.execute(
        """
        UPDATE session_annotation
        SET geometry_json = json_object(
            'kind', CASE
                WHEN tool IN ('long_position', 'short_position', 'risk_reward') THEN 'risk_reward'
                WHEN shape = 'zone' THEN 'region'
                WHEN shape IN ('marker', 'label') THEN 'point'
                ELSE 'line'
            END,
            'anchors', json(points_json)
        )
        WHERE geometry_json IS NULL
        """
    )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    for table in ("chart_tool_preference", "chart_tool_template"):
        if table in inspector.get_table_names():
            op.drop_table(table)
    for name in (
        "replacement_properties_json",
        "replacement_style_json",
        "replacement_geometry_json",
    ):
        if name in _columns("session_annotation_event"):
            op.drop_column("session_annotation_event", name)
    for name in (
        "algorithm_version",
        "derived_facts_json",
        "properties_json",
        "style_json",
        "geometry_json",
        "tool_version",
    ):
        if name in _columns("session_annotation"):
            op.drop_column("session_annotation", name)
