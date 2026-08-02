"""Create the M0 system metadata table."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0001_m0"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Recover safely from an interrupted initial migration where SQLite committed
    # the DDL but Alembic had not yet recorded the revision.
    inspector = sa.inspect(op.get_bind())
    if inspector.has_table("system_meta"):
        column_names = {column["name"] for column in inspector.get_columns("system_meta")}
        primary_key = set(
            inspector.get_pk_constraint("system_meta").get("constrained_columns") or []
        )
        if column_names != {"key", "value", "updated_at"} or primary_key != {"key"}:
            raise RuntimeError("Existing system_meta table does not match the M0 schema")
    else:
        op.create_table(
            "system_meta",
            sa.Column("key", sa.String(length=128), primary_key=True),
            sa.Column("value", sa.Text(), nullable=False),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
        )


def downgrade() -> None:
    if sa.inspect(op.get_bind()).has_table("system_meta"):
        op.drop_table("system_meta")
