"""Add deterministic completed-session reviews."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006_training_review"
down_revision: str | Sequence[str] | None = "0005_order_management"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "training_review",
        sa.Column("review_id", sa.String(40), primary_key=True),
        sa.Column(
            "session_id",
            sa.String(40),
            sa.ForeignKey("replay_session.session_id"),
            nullable=False,
            unique=True,
        ),
        sa.Column("review_hash", sa.String(64), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.String(40), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("training_review")
