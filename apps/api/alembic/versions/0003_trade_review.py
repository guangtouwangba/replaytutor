"""Add Binance execution imports, reconstructed episodes, and review artifacts."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_trade_review"
down_revision: str | Sequence[str] | None = "0002_market_data"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "trade_sync",
        sa.Column("sync_id", sa.String(40), primary_key=True),
        sa.Column("market_type", sa.String(24), nullable=False),
        sa.Column("coverage_start", sa.String(40), nullable=False),
        sa.Column("coverage_end", sa.String(40), nullable=False),
        sa.Column("coverage_status", sa.String(24), nullable=False),
        sa.Column("fill_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("order_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("income_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("diagnostics_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("created_at", sa.String(40), nullable=False),
        sa.CheckConstraint(
            "coverage_status IN ('complete', 'partial', 'quota_blocked', 'failed')"
        ),
    )
    op.create_table(
        "execution_fill",
        sa.Column("fill_id", sa.String(40), primary_key=True),
        sa.Column("market_type", sa.String(24), nullable=False),
        sa.Column("symbol", sa.String(32), nullable=False),
        sa.Column("trade_id", sa.String(64), nullable=False),
        sa.Column("order_id", sa.String(64), nullable=False),
        sa.Column("side", sa.String(8), nullable=False),
        sa.Column("position_side", sa.String(8), nullable=False),
        sa.Column("price", sa.String(64), nullable=False),
        sa.Column("qty", sa.String(64), nullable=False),
        sa.Column("quote_qty", sa.String(64), nullable=False),
        sa.Column("commission", sa.String(64), nullable=False),
        sa.Column("commission_asset", sa.String(16), nullable=False),
        sa.Column("realized_pnl", sa.String(64), nullable=False),
        sa.Column("executed_at", sa.String(40), nullable=False),
        sa.Column("is_buyer", sa.Boolean(), nullable=False),
        sa.Column("is_maker", sa.Boolean(), nullable=False),
        sa.Column("raw_json", sa.Text(), nullable=False),
        sa.UniqueConstraint("market_type", "symbol", "trade_id"),
    )
    op.create_index("ix_execution_fill_time", "execution_fill", ["executed_at"])
    op.create_index("ix_execution_fill_symbol", "execution_fill", ["symbol"])
    op.create_table(
        "trade_order",
        sa.Column("market_type", sa.String(24), nullable=False),
        sa.Column("symbol", sa.String(32), nullable=False),
        sa.Column("order_id", sa.String(64), nullable=False),
        sa.Column("order_type", sa.String(32), nullable=False),
        sa.Column("side", sa.String(8), nullable=False),
        sa.Column("position_side", sa.String(8), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("price", sa.String(64), nullable=False),
        sa.Column("stop_price", sa.String(64), nullable=False),
        sa.Column("avg_price", sa.String(64), nullable=False),
        sa.Column("orig_qty", sa.String(64), nullable=False),
        sa.Column("executed_qty", sa.String(64), nullable=False),
        sa.Column("reduce_only", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.String(40), nullable=False),
        sa.Column("updated_at", sa.String(40), nullable=False),
        sa.Column("raw_json", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("market_type", "symbol", "order_id"),
    )
    op.create_table(
        "trade_income",
        sa.Column("market_type", sa.String(24), nullable=False),
        sa.Column("transaction_id", sa.String(64), nullable=False),
        sa.Column("symbol", sa.String(32), nullable=False),
        sa.Column("income_type", sa.String(32), nullable=False),
        sa.Column("income", sa.String(64), nullable=False),
        sa.Column("asset", sa.String(16), nullable=False),
        sa.Column("occurred_at", sa.String(40), nullable=False),
        sa.Column("raw_json", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("market_type", "transaction_id"),
    )
    op.create_table(
        "trade_episode",
        sa.Column("episode_id", sa.String(40), primary_key=True),
        sa.Column("market_type", sa.String(24), nullable=False),
        sa.Column("symbol", sa.String(32), nullable=False),
        sa.Column("direction", sa.String(8), nullable=False),
        sa.Column("position_side", sa.String(8), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("opened_at", sa.String(40), nullable=False),
        sa.Column("closed_at", sa.String(40)),
        sa.Column("entry_price", sa.String(64), nullable=False),
        sa.Column("exit_price", sa.String(64)),
        sa.Column("peak_qty", sa.String(64), nullable=False),
        sa.Column("realized_pnl", sa.String(64), nullable=False),
        sa.Column("commission", sa.String(64), nullable=False),
        sa.Column("allocations_json", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.String(40), nullable=False),
        sa.CheckConstraint("direction IN ('long', 'short')"),
        sa.CheckConstraint("status IN ('open', 'closed')"),
    )
    op.create_index("ix_trade_episode_closed", "trade_episode", ["closed_at"])
    op.create_index("ix_trade_episode_symbol", "trade_episode", ["symbol"])
    op.create_table(
        "trade_journal",
        sa.Column(
            "episode_id",
            sa.String(40),
            sa.ForeignKey("trade_episode.episode_id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("plan_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("updated_at", sa.String(40), nullable=False),
    )
    op.create_table(
        "trade_review",
        sa.Column("review_id", sa.String(40), primary_key=True),
        sa.Column("scope_kind", sa.String(16), nullable=False),
        sa.Column("scope_value", sa.String(128), nullable=False),
        sa.Column("episode_ids_json", sa.Text(), nullable=False),
        sa.Column("summary_json", sa.Text(), nullable=False),
        sa.Column("report_json_path", sa.Text(), nullable=False),
        sa.Column("report_html_path", sa.Text(), nullable=False),
        sa.Column("created_at", sa.String(40), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("trade_review")
    op.drop_table("trade_journal")
    op.drop_index("ix_trade_episode_symbol", table_name="trade_episode")
    op.drop_index("ix_trade_episode_closed", table_name="trade_episode")
    op.drop_table("trade_episode")
    op.drop_table("trade_income")
    op.drop_table("trade_order")
    op.drop_index("ix_execution_fill_symbol", table_name="execution_fill")
    op.drop_index("ix_execution_fill_time", table_name="execution_fill")
    op.drop_table("execution_fill")
    op.drop_table("trade_sync")
