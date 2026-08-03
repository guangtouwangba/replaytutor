"""Add semantic chart tools and immutable Tutor context bundles."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0014_chart_context"
down_revision: str | Sequence[str] | None = "0013_derivatives_execution"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    annotation_columns = {
        column["name"] for column in inspector.get_columns("session_annotation")
    }
    if "tool" not in annotation_columns:
        op.add_column(
            "session_annotation",
            sa.Column("tool", sa.String(32), nullable=False, server_default="note_marker"),
        )
    if "semantic_role" not in annotation_columns:
        op.add_column(
            "session_annotation",
            sa.Column("semantic_role", sa.String(32), nullable=False, server_default="note"),
        )
    if "metadata_json" not in annotation_columns:
        op.add_column(
            "session_annotation",
            sa.Column("metadata_json", sa.Text(), nullable=False, server_default="{}"),
        )
    op.execute(
        """
        UPDATE session_annotation
        SET tool = CASE shape
            WHEN 'line' THEN 'trend_line'
            WHEN 'zone' THEN 'zone'
            WHEN 'label' THEN 'text'
            ELSE 'note_marker'
        END,
        semantic_role = CASE WHEN shape IN ('label', 'marker') THEN 'note' ELSE 'analysis' END
        WHERE tool = 'note_marker' AND semantic_role = 'note'
        """
    )

    tutor_columns = {column["name"] for column in inspector.get_columns("tutor_run")}
    if "context_bundle_id" not in tutor_columns:
        op.add_column("tutor_run", sa.Column("context_bundle_id", sa.String(40)))

    if "chart_context_bundle" not in inspector.get_table_names():
        op.create_table(
            "chart_context_bundle",
            sa.Column("context_bundle_id", sa.String(40), primary_key=True),
            sa.Column(
                "session_id",
                sa.String(40),
                sa.ForeignKey("replay_session.session_id"),
                nullable=False,
            ),
            sa.Column("frame_id", sa.String(40), nullable=False),
            sa.Column("visible_at", sa.String(40), nullable=False),
            sa.Column("selection_mode", sa.String(16), nullable=False),
            sa.Column("objects_json", sa.Text(), nullable=False),
            sa.Column("evidence_ids_json", sa.Text(), nullable=False),
            sa.Column("derived_facts_json", sa.Text(), nullable=False),
            sa.Column("created_at", sa.String(40), nullable=False),
            sa.CheckConstraint("selection_mode = 'selected'"),
        )
        op.create_index(
            "ix_chart_context_bundle_session",
            "chart_context_bundle",
            ["session_id", "created_at"],
        )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "chart_context_bundle" in inspector.get_table_names():
        op.drop_index(
            "ix_chart_context_bundle_session",
            table_name="chart_context_bundle",
        )
        op.drop_table("chart_context_bundle")
    tutor_columns = {column["name"] for column in inspector.get_columns("tutor_run")}
    if "context_bundle_id" in tutor_columns:
        op.drop_column("tutor_run", "context_bundle_id")
    annotation_columns = {
        column["name"] for column in inspector.get_columns("session_annotation")
    }
    for column in ("metadata_json", "semantic_role", "tool"):
        if column in annotation_columns:
            op.drop_column("session_annotation", column)
