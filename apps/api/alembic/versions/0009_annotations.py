"""Add immutable user and AI chart annotations."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0009_annotations"
down_revision: str | Sequence[str] | None = "0008_playbook"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "session_annotation" in inspector.get_table_names():
        return
    op.create_table(
        "session_annotation",
        sa.Column("annotation_id", sa.String(40), primary_key=True),
        sa.Column(
            "session_id",
            sa.String(40),
            sa.ForeignKey("replay_session.session_id"),
            nullable=False,
        ),
        sa.Column("frame_id", sa.String(40), nullable=False),
        sa.Column("layer", sa.String(8), nullable=False),
        sa.Column("shape", sa.String(16), nullable=False),
        sa.Column("label", sa.String(200), nullable=False),
        sa.Column("points_json", sa.Text(), nullable=False),
        sa.Column("provenance_run_id", sa.String(40)),
        sa.Column("command_id", sa.String(40), unique=True),
        sa.Column("created_at", sa.String(40), nullable=False),
        sa.CheckConstraint("layer IN ('user', 'ai')"),
        sa.CheckConstraint("shape IN ('line', 'zone', 'marker', 'label')"),
    )
    op.create_index(
        "ix_session_annotation_session",
        "session_annotation",
        ["session_id", "created_at"],
    )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "session_annotation" not in inspector.get_table_names():
        return
    op.drop_index(
        "ix_session_annotation_session",
        table_name="session_annotation",
    )
    op.drop_table("session_annotation")
