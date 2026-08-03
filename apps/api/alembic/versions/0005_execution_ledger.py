"""Add locked trade plans, paper orders, fills, and balanced journals."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005_execution_ledger"
down_revision: str | Sequence[str] | None = "0004_training_session"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "trade_plan",
        sa.Column("plan_id", sa.String(40), primary_key=True),
        sa.Column(
            "session_id", sa.String(40), sa.ForeignKey("replay_session.session_id"), nullable=False
        ),
        sa.Column(
            "frame_id", sa.String(40), sa.ForeignKey("replay_frame.frame_id"), nullable=False
        ),
        sa.Column("side", sa.String(4), nullable=False),
        sa.Column("thesis", sa.Text(), nullable=False),
        sa.Column("invalidation", sa.Text(), nullable=False),
        sa.Column("entry_price", sa.String(64)),
        sa.Column("stop_price", sa.String(64)),
        sa.Column("target_price", sa.String(64)),
        sa.Column("risk_amount", sa.String(64), nullable=False),
        sa.Column("created_at", sa.String(40), nullable=False),
        sa.CheckConstraint("side IN ('BUY', 'SELL')"),
    )
    op.create_index("ix_trade_plan_session", "trade_plan", ["session_id", "created_at"])
    op.create_table(
        "paper_order",
        sa.Column("order_id", sa.String(40), primary_key=True),
        sa.Column(
            "session_id", sa.String(40), sa.ForeignKey("replay_session.session_id"), nullable=False
        ),
        sa.Column("plan_id", sa.String(40), sa.ForeignKey("trade_plan.plan_id"), nullable=False),
        sa.Column(
            "submitted_frame_id",
            sa.String(40),
            sa.ForeignKey("replay_frame.frame_id"),
            nullable=False,
        ),
        sa.Column("side", sa.String(4), nullable=False),
        sa.Column("order_type", sa.String(16), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("quantity", sa.String(64), nullable=False),
        sa.Column("limit_price", sa.String(64)),
        sa.Column("stop_price", sa.String(64)),
        sa.Column("activate_index", sa.Integer(), nullable=False),
        sa.Column("submitted_at", sa.String(40), nullable=False),
        sa.Column("filled_at", sa.String(40)),
        sa.CheckConstraint("side IN ('BUY', 'SELL')"),
        sa.CheckConstraint("order_type IN ('MARKET', 'LIMIT', 'STOP_MARKET')"),
        sa.CheckConstraint("status IN ('PENDING', 'FILLED', 'CANCELLED', 'REJECTED')"),
    )
    op.create_index("ix_paper_order_session", "paper_order", ["session_id", "submitted_at"])
    op.create_table(
        "paper_fill",
        sa.Column("fill_id", sa.String(40), primary_key=True),
        sa.Column(
            "order_id",
            sa.String(40),
            sa.ForeignKey("paper_order.order_id"),
            nullable=False,
            unique=True,
        ),
        sa.Column(
            "session_id", sa.String(40), sa.ForeignKey("replay_session.session_id"), nullable=False
        ),
        sa.Column(
            "frame_id", sa.String(40), sa.ForeignKey("replay_frame.frame_id"), nullable=False
        ),
        sa.Column("side", sa.String(4), nullable=False),
        sa.Column("price", sa.String(64), nullable=False),
        sa.Column("quantity", sa.String(64), nullable=False),
        sa.Column("quote_amount", sa.String(64), nullable=False),
        sa.Column("fee", sa.String(64), nullable=False),
        sa.Column("executed_at", sa.String(40), nullable=False),
    )
    op.create_index("ix_paper_fill_session", "paper_fill", ["session_id", "executed_at"])
    op.create_table(
        "ledger_journal",
        sa.Column("journal_id", sa.String(40), primary_key=True),
        sa.Column("fill_id", sa.String(40), sa.ForeignKey("paper_fill.fill_id"), nullable=False),
        sa.Column("account", sa.String(32), nullable=False),
        sa.Column("debit", sa.String(64), nullable=False),
        sa.Column("credit", sa.String(64), nullable=False),
        sa.Column("created_at", sa.String(40), nullable=False),
    )
    op.create_index("ix_ledger_journal_fill", "ledger_journal", ["fill_id"])


def downgrade() -> None:
    op.drop_index("ix_ledger_journal_fill", table_name="ledger_journal")
    op.drop_table("ledger_journal")
    op.drop_index("ix_paper_fill_session", table_name="paper_fill")
    op.drop_table("paper_fill")
    op.drop_index("ix_paper_order_session", table_name="paper_order")
    op.drop_table("paper_order")
    op.drop_index("ix_trade_plan_session", table_name="trade_plan")
    op.drop_table("trade_plan")
