"""Add immutable market data catalog and import staging tables."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0002_market_data"
down_revision: str | Sequence[str] | None = "0001_m0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "instrument",
        sa.Column("instrument_id", sa.String(40), primary_key=True),
        sa.Column("canonical_symbol", sa.String(32), nullable=False),
        sa.Column("display_name", sa.String(128), nullable=False),
        sa.Column("asset_class", sa.String(32), nullable=False),
        sa.Column("market", sa.String(16), nullable=False),
        sa.Column("venue", sa.String(32), nullable=False),
        sa.Column("base_currency", sa.String(16), nullable=False),
        sa.Column("quote_currency", sa.String(16), nullable=False),
        sa.Column("timezone", sa.String(64), nullable=False),
        sa.Column("tick_size", sa.String(64), nullable=False),
        sa.Column("lot_size", sa.String(64), nullable=False),
        sa.Column("price_scale", sa.Integer(), nullable=False),
        sa.Column("market_rule_set_id", sa.String(64), nullable=False),
        sa.UniqueConstraint("market", "venue", "canonical_symbol"),
    )
    op.create_table(
        "data_snapshot",
        sa.Column("snapshot_id", sa.String(40), primary_key=True),
        sa.Column(
            "instrument_id",
            sa.String(40),
            sa.ForeignKey("instrument.instrument_id"),
            nullable=False,
        ),
        sa.Column("timeframe", sa.String(8), nullable=False),
        sa.Column("source_id", sa.String(128), nullable=False),
        sa.Column("source_kind", sa.String(32), nullable=False),
        sa.Column("coverage_start", sa.String(40), nullable=False),
        sa.Column("coverage_end", sa.String(40), nullable=False),
        sa.Column("created_at", sa.String(40), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("manifest_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("manifest_path", sa.Text(), nullable=False),
        sa.Column("quality_json", sa.Text(), nullable=False),
        sa.Column("derived_timeframes_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("status", sa.String(16), nullable=False),
        sa.CheckConstraint("status IN ('ready', 'failed')"),
    )
    op.create_table(
        "data_import",
        sa.Column("import_id", sa.String(40), primary_key=True),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("staged_path", sa.Text(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("detected_columns_json", sa.Text(), nullable=False),
        sa.Column("sample_rows_json", sa.Text(), nullable=False),
        sa.Column("quality_json", sa.Text(), nullable=False),
        sa.Column("error", sa.Text()),
        sa.Column("snapshot_id", sa.String(40), sa.ForeignKey("data_snapshot.snapshot_id")),
        sa.Column("created_at", sa.String(40), nullable=False),
    )
    op.create_index("ix_data_snapshot_instrument", "data_snapshot", ["instrument_id"])


def downgrade() -> None:
    op.drop_index("ix_data_snapshot_instrument", table_name="data_snapshot")
    op.drop_table("data_import")
    op.drop_table("data_snapshot")
    op.drop_table("instrument")
