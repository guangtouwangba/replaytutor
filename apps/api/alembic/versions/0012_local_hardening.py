"""Add recoverable session deletion and local preferences."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0012_local_hardening"
down_revision: str | Sequence[str] | None = "0011_playbook_rules"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    columns = {column["name"] for column in inspector.get_columns("replay_session")}
    with op.batch_alter_table("replay_session") as batch:
        if "deleted_at" not in columns:
            batch.add_column(sa.Column("deleted_at", sa.String(40)))
    if not inspector.has_table("app_preference"):
        op.create_table(
            "app_preference",
            sa.Column("preference_key", sa.String(64), primary_key=True),
            sa.Column("payload_json", sa.Text(), nullable=False),
            sa.Column("updated_at", sa.String(40), nullable=False),
        )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if inspector.has_table("app_preference"):
        op.drop_table("app_preference")
    columns = {column["name"] for column in inspector.get_columns("replay_session")}
    with op.batch_alter_table("replay_session") as batch:
        if "deleted_at" in columns:
            batch.drop_column("deleted_at")
