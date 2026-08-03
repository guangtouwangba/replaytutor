"""Add deterministic training session and replay event tables."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004_training_session"
down_revision: str | Sequence[str] | None = "0003_trade_review"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "replay_session",
        sa.Column("session_id", sa.String(40), primary_key=True),
        sa.Column(
            "snapshot_id",
            sa.String(40),
            sa.ForeignKey("data_snapshot.snapshot_id"),
            nullable=False,
        ),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("current_index", sa.Integer(), nullable=False),
        sa.Column("start_index", sa.Integer(), nullable=False),
        sa.Column("total_bars", sa.Integer(), nullable=False),
        sa.Column("warmup_bars", sa.Integer(), nullable=False),
        sa.Column("seed", sa.Integer(), nullable=False),
        sa.Column("initial_cash", sa.String(64), nullable=False),
        sa.Column("hidden_real_date", sa.Boolean(), nullable=False),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("created_at", sa.String(40), nullable=False),
        sa.Column("updated_at", sa.String(40), nullable=False),
        sa.Column("completed_at", sa.String(40)),
        sa.CheckConstraint("status IN ('ready', 'paused', 'completed', 'stopped')"),
        sa.CheckConstraint("revision >= 0"),
        sa.CheckConstraint("current_index >= start_index"),
        sa.CheckConstraint("total_bars > current_index"),
    )
    op.create_index(
        "ix_replay_session_snapshot",
        "replay_session",
        ["snapshot_id", "created_at"],
    )
    op.create_table(
        "session_command",
        sa.Column("command_id", sa.String(40), primary_key=True),
        sa.Column(
            "session_id",
            sa.String(40),
            sa.ForeignKey("replay_session.session_id"),
            nullable=False,
        ),
        sa.Column("command_type", sa.String(32), nullable=False),
        sa.Column("expected_revision", sa.Integer(), nullable=False),
        sa.Column("request_json", sa.Text(), nullable=False),
        sa.Column("result_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.String(40), nullable=False),
    )
    op.create_index(
        "ix_session_command_session",
        "session_command",
        ["session_id", "created_at"],
    )
    op.create_table(
        "session_event",
        sa.Column("event_id", sa.String(40), primary_key=True),
        sa.Column(
            "session_id",
            sa.String(40),
            sa.ForeignKey("replay_session.session_id"),
            nullable=False,
        ),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(32), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("occurred_at", sa.String(40), nullable=False),
        sa.UniqueConstraint("session_id", "sequence"),
    )
    op.create_table(
        "replay_frame",
        sa.Column("frame_id", sa.String(40), primary_key=True),
        sa.Column(
            "session_id",
            sa.String(40),
            sa.ForeignKey("replay_session.session_id"),
            nullable=False,
        ),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("current_index", sa.Integer(), nullable=False),
        sa.Column("visible_at", sa.String(40), nullable=False),
        sa.Column("created_at", sa.String(40), nullable=False),
        sa.UniqueConstraint("session_id", "revision"),
    )
    op.create_index(
        "ix_replay_frame_session",
        "replay_frame",
        ["session_id", "revision"],
    )


def downgrade() -> None:
    op.drop_index("ix_replay_frame_session", table_name="replay_frame")
    op.drop_table("replay_frame")
    op.drop_table("session_event")
    op.drop_index("ix_session_command_session", table_name="session_command")
    op.drop_table("session_command")
    op.drop_index("ix_replay_session_snapshot", table_name="replay_session")
    op.drop_table("replay_session")
