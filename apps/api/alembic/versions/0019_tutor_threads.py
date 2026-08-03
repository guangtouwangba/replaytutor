"""Add durable Tutor conversation threads."""

from collections.abc import Sequence
from datetime import UTC, datetime

import sqlalchemy as sa

from alembic import op
from replaytutor.ids import stable_id

revision: str = "0019_tutor_threads"
down_revision: str | Sequence[str] | None = "0018_market_depth"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "tutor_thread" not in inspector.get_table_names():
        op.create_table(
            "tutor_thread",
            sa.Column("thread_id", sa.String(40), primary_key=True),
            sa.Column("session_id", sa.String(40), nullable=False),
            sa.Column("title", sa.String(80), nullable=False),
            sa.Column("title_locked", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("created_at", sa.String(40), nullable=False),
            sa.Column("updated_at", sa.String(40), nullable=False),
            sa.Column("deleted_at", sa.String(40)),
            sa.ForeignKeyConstraint(["session_id"], ["replay_session.session_id"]),
        )
        op.create_index(
            "ix_tutor_thread_session_updated",
            "tutor_thread",
            ["session_id", "deleted_at", "updated_at"],
        )

    tutor_columns = {column["name"] for column in inspector.get_columns("tutor_run")}
    if "thread_id" not in tutor_columns:
        op.add_column("tutor_run", sa.Column("thread_id", sa.String(40)))
    if "sequence" not in tutor_columns:
        op.add_column("tutor_run", sa.Column("sequence", sa.Integer()))

    connection = op.get_bind()
    session_rows = connection.execute(
        sa.text(
            """SELECT session_id, MIN(created_at) AS created_at, MAX(created_at) AS updated_at
            FROM tutor_run GROUP BY session_id"""
        )
    ).mappings()
    fallback_now = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    for row in session_rows:
        session_id = str(row["session_id"])
        thread_id = stable_id("thr", "replaytutor:tutor-thread-migration", session_id)
        connection.execute(
            sa.text(
                """INSERT OR IGNORE INTO tutor_thread (
                    thread_id, session_id, title, title_locked, created_at, updated_at
                ) VALUES (
                    :thread_id, :session_id, '历史 Tutor 对话', 0, :created_at, :updated_at
                )"""
            ),
            {
                "thread_id": thread_id,
                "session_id": session_id,
                "created_at": row["created_at"] or fallback_now,
                "updated_at": row["updated_at"] or fallback_now,
            },
        )
        run_rows = connection.execute(
            sa.text(
                """SELECT run_id FROM tutor_run
                WHERE session_id = :session_id ORDER BY created_at, run_id"""
            ),
            {"session_id": session_id},
        ).mappings()
        for sequence, run in enumerate(run_rows, start=1):
            connection.execute(
                sa.text(
                    """UPDATE tutor_run SET thread_id = :thread_id, sequence = :sequence
                    WHERE run_id = :run_id"""
                ),
                {"thread_id": thread_id, "sequence": sequence, "run_id": run["run_id"]},
            )

    with op.batch_alter_table("tutor_run") as batch:
        batch.alter_column("thread_id", existing_type=sa.String(40), nullable=False)
        batch.alter_column("sequence", existing_type=sa.Integer(), nullable=False)
        batch.create_foreign_key(
            "fk_tutor_run_thread_id",
            "tutor_thread",
            ["thread_id"],
            ["thread_id"],
        )
        batch.create_unique_constraint("uq_tutor_run_thread_sequence", ["thread_id", "sequence"])


def downgrade() -> None:
    with op.batch_alter_table("tutor_run") as batch:
        batch.drop_constraint("uq_tutor_run_thread_sequence", type_="unique")
        batch.drop_constraint("fk_tutor_run_thread_id", type_="foreignkey")
        batch.drop_column("sequence")
        batch.drop_column("thread_id")
    op.drop_index("ix_tutor_thread_session_updated", table_name="tutor_thread")
    op.drop_table("tutor_thread")
