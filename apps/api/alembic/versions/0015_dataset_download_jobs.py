"""Add durable background jobs for market-data downloads."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0015_dataset_download_jobs"
down_revision: str | Sequence[str] | None = "0014_chart_context"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "dataset_download_job" in inspector.get_table_names():
        return
    op.create_table(
        "dataset_download_job",
        sa.Column("job_id", sa.String(40), primary_key=True),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("market_type", sa.String(24), nullable=False),
        sa.Column("timeframe", sa.String(8), nullable=False),
        sa.Column("start_time", sa.String(40), nullable=False),
        sa.Column("end_time", sa.String(40), nullable=False),
        sa.Column("completed_bars", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_bars", sa.Integer(), nullable=False),
        sa.Column("snapshot_id", sa.String(40), sa.ForeignKey("data_snapshot.snapshot_id")),
        sa.Column("error", sa.Text()),
        sa.Column("created_at", sa.String(40), nullable=False),
        sa.Column("started_at", sa.String(40)),
        sa.Column("finished_at", sa.String(40)),
        sa.CheckConstraint("status IN ('queued', 'running', 'succeeded', 'failed')"),
        sa.CheckConstraint("market_type IN ('SPOT', 'USDT_PERPETUAL')"),
        sa.CheckConstraint("completed_bars >= 0"),
        sa.CheckConstraint("total_bars > 0"),
    )
    op.create_index(
        "ix_dataset_download_job_status_created",
        "dataset_download_job",
        ["status", "created_at"],
    )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "dataset_download_job" in inspector.get_table_names():
        op.drop_index(
            "ix_dataset_download_job_status_created",
            table_name="dataset_download_job",
        )
        op.drop_table("dataset_download_job")
