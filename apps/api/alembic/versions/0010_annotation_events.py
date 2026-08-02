"""Add append-only annotation disposition events."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0010_annotation_events"
down_revision: str | Sequence[str] | None = "0009_annotations"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "session_annotation_event" in inspector.get_table_names():
        return
    op.create_table(
        "session_annotation_event",
        sa.Column("event_id", sa.String(40), primary_key=True),
        sa.Column(
            "annotation_id",
            sa.String(40),
            sa.ForeignKey("session_annotation.annotation_id"),
            nullable=False,
        ),
        sa.Column(
            "session_id",
            sa.String(40),
            sa.ForeignKey("replay_session.session_id"),
            nullable=False,
        ),
        sa.Column("expected_revision", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(16), nullable=False),
        sa.Column("replacement_label", sa.String(200)),
        sa.Column("replacement_points_json", sa.Text()),
        sa.Column("command_id", sa.String(40), nullable=False, unique=True),
        sa.Column("actor", sa.String(8), nullable=False, server_default="user"),
        sa.Column("created_at", sa.String(40), nullable=False),
        sa.CheckConstraint("action IN ('accepted', 'rejected', 'revised', 'deleted')"),
        sa.CheckConstraint("actor = 'user'"),
    )
    op.create_index(
        "ix_annotation_event_annotation",
        "session_annotation_event",
        ["annotation_id", "created_at"],
    )
    op.create_index(
        "ix_annotation_event_session",
        "session_annotation_event",
        ["session_id", "created_at"],
    )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "session_annotation_event" not in inspector.get_table_names():
        return
    op.drop_index(
        "ix_annotation_event_session",
        table_name="session_annotation_event",
    )
    op.drop_index(
        "ix_annotation_event_annotation",
        table_name="session_annotation_event",
    )
    op.drop_table("session_annotation_event")
