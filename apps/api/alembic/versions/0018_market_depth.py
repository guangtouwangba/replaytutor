"""Store point-in-time L2 order book snapshots for replay."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0018_market_depth"
down_revision: str | Sequence[str] | None = "0017_chart_objects_v2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    if "market_depth_snapshot" not in sa.inspect(op.get_bind()).get_table_names():
        op.create_table(
            "market_depth_snapshot",
            sa.Column("depth_id", sa.String(40), primary_key=True),
            sa.Column("snapshot_id", sa.String(40), nullable=False),
            sa.Column("instrument_id", sa.String(40), nullable=False),
            sa.Column("captured_at", sa.String(40), nullable=False),
            sa.Column("source_kind", sa.String(32), nullable=False),
            sa.Column("last_update_id", sa.BigInteger()),
            sa.Column("bids_json", sa.Text(), nullable=False),
            sa.Column("asks_json", sa.Text(), nullable=False),
            sa.Column("created_at", sa.String(40), nullable=False),
            sa.ForeignKeyConstraint(["snapshot_id"], ["data_snapshot.snapshot_id"]),
            sa.ForeignKeyConstraint(["instrument_id"], ["instrument.instrument_id"]),
        )
        op.create_index(
            "idx_market_depth_snapshot_visible",
            "market_depth_snapshot",
            ["snapshot_id", "captured_at"],
        )


def downgrade() -> None:
    if "market_depth_snapshot" in sa.inspect(op.get_bind()).get_table_names():
        op.drop_index("idx_market_depth_snapshot_visible", table_name="market_depth_snapshot")
        op.drop_table("market_depth_snapshot")
