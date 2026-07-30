"""Add bracket and OCO relationships to paper orders."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0005_order_management"
down_revision: str | Sequence[str] | None = "0005_execution_ledger"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("paper_order") as batch:
        batch.add_column(sa.Column("parent_order_id", sa.String(40)))
        batch.add_column(sa.Column("oco_group_id", sa.String(80)))
        batch.create_foreign_key(
            "fk_paper_order_parent",
            "paper_order",
            ["parent_order_id"],
            ["order_id"],
        )
    op.create_index(
        "ix_paper_order_oco",
        "paper_order",
        ["session_id", "oco_group_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_paper_order_oco", table_name="paper_order")
    with op.batch_alter_table("paper_order") as batch:
        batch.drop_constraint("fk_paper_order_parent", type_="foreignkey")
        batch.drop_column("oco_group_id")
        batch.drop_column("parent_order_id")
