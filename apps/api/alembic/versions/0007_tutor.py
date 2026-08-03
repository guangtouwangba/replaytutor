"""Add Codex tutor runs."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007_tutor"
down_revision: str | Sequence[str] | None = "0006_training_review"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "tutor_run",
        sa.Column("run_id", sa.String(40), primary_key=True),
        sa.Column(
            "session_id",
            sa.String(40),
            sa.ForeignKey("replay_session.session_id"),
            nullable=False,
        ),
        sa.Column("frame_id", sa.String(40), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("stage", sa.String(16), nullable=False),
        sa.Column("workspace_path", sa.Text(), nullable=False),
        sa.Column("response_json", sa.Text()),
        sa.Column("error", sa.Text()),
        sa.Column("created_at", sa.String(40), nullable=False),
        sa.Column("completed_at", sa.String(40)),
        sa.CheckConstraint(
            "status IN ('running', 'completed', 'failed', 'cancelled', 'timed_out')"
        ),
    )
    op.create_index("ix_tutor_run_session", "tutor_run", ["session_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_tutor_run_session", table_name="tutor_run")
    op.drop_table("tutor_run")
