"""Add immutable playbook versions and session binding."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0008_playbook"
down_revision: str | Sequence[str] | None = "0007_tutor"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "playbook_version" not in inspector.get_table_names():
        op.create_table(
            "playbook_version",
            sa.Column("playbook_id", sa.String(40), primary_key=True),
            sa.Column("slug", sa.String(64), nullable=False),
            sa.Column("name", sa.String(100), nullable=False),
            sa.Column("version", sa.Integer(), nullable=False),
            sa.Column("description", sa.Text(), nullable=False),
            sa.Column("rules_json", sa.Text(), nullable=False),
            sa.Column("official", sa.Boolean(), nullable=False),
            sa.Column("created_at", sa.String(40), nullable=False),
            sa.UniqueConstraint("slug", "version"),
        )
    session_columns = {
        column["name"] for column in sa.inspect(op.get_bind()).get_columns("replay_session")
    }
    if "playbook_id" not in session_columns:
        # SQLite ALTER ADD COLUMN is atomic and recoverable. Application-level
        # validation enforces the immutable playbook reference.
        op.add_column(
            "replay_session",
            sa.Column("playbook_id", sa.String(40)),
        )


def downgrade() -> None:
    with op.batch_alter_table("replay_session") as batch:
        batch.drop_column("playbook_id")
    op.drop_table("playbook_version")
