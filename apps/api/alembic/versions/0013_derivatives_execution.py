"""Add derivatives accounts and the complete replay order lifecycle."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0013_derivatives_execution"
down_revision: str | Sequence[str] | None = "0012_local_hardening"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


ORDER_TYPES = (
    "'MARKET', 'LIMIT', 'STOP_MARKET', 'STOP_LIMIT', "
    "'TAKE_PROFIT_MARKET', 'TAKE_PROFIT_LIMIT', 'TRAILING_STOP_MARKET'"
)
ORDER_STATUSES = (
    "'PENDING', 'TRIGGERED', 'PARTIALLY_FILLED', 'FILLED', 'CANCELLED', 'EXPIRED', 'REJECTED'"
)


def _create_order_table(name: str) -> None:
    op.create_table(
        name,
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
        sa.Column("order_type", sa.String(32), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("quantity", sa.String(64), nullable=False),
        sa.Column("filled_quantity", sa.String(64), nullable=False, server_default="0"),
        sa.Column("average_fill_price", sa.String(64), nullable=False, server_default="0"),
        sa.Column("limit_price", sa.String(64)),
        sa.Column("stop_price", sa.String(64)),
        sa.Column("activation_price", sa.String(64)),
        sa.Column("callback_rate", sa.String(64)),
        sa.Column("trail_anchor_price", sa.String(64)),
        sa.Column("time_in_force", sa.String(4), nullable=False, server_default="GTC"),
        sa.Column("good_till_index", sa.Integer()),
        sa.Column("reduce_only", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("post_only", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("close_position", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("position_side", sa.String(8), nullable=False, server_default="BOTH"),
        sa.Column("triggered_at_index", sa.Integer()),
        sa.Column("activate_index", sa.Integer(), nullable=False),
        sa.Column("submitted_at", sa.String(40), nullable=False),
        sa.Column("filled_at", sa.String(40)),
        sa.Column("parent_order_id", sa.String(40), sa.ForeignKey(f"{name}.order_id")),
        sa.Column("oco_group_id", sa.String(40)),
        sa.CheckConstraint("side IN ('BUY', 'SELL')"),
        sa.CheckConstraint(f"order_type IN ({ORDER_TYPES})"),
        sa.CheckConstraint(f"status IN ({ORDER_STATUSES})"),
        sa.CheckConstraint("time_in_force IN ('GTC', 'IOC', 'FOK', 'GTD')"),
        sa.CheckConstraint("position_side IN ('BOTH', 'LONG', 'SHORT')"),
    )


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    existing_columns = {
        column["name"] for column in inspector.get_columns("replay_session")
    }
    with op.batch_alter_table("replay_session") as batch:
        columns = (
            ("account_type", sa.String(24), "SPOT"),
            ("margin_mode", sa.String(16), "ISOLATED"),
            ("position_mode", sa.String(16), "ONEWAY"),
            ("leverage", sa.Integer(), "1"),
            ("maker_fee_rate", sa.String(64), "0.0002"),
            ("taker_fee_rate", sa.String(64), "0.0005"),
            ("maintenance_margin_rate", sa.String(64), "0.005"),
            ("funding_rate", sa.String(64), "0"),
            ("funding_interval_bars", sa.Integer(), "480"),
        )
        for name, data_type, default in columns:
            if name not in existing_columns:
                batch.add_column(
                    sa.Column(
                        name,
                        data_type,
                        nullable=False,
                        server_default=default,
                    )
                )

    inspector = sa.inspect(op.get_bind())
    order_columns = {
        column["name"] for column in inspector.get_columns("paper_order")
    }
    if "filled_quantity" in order_columns:
        if not inspector.has_table("account_event"):
            _create_account_event()
        return

    _create_order_table("paper_order_v2")
    op.execute(
        """
        INSERT INTO paper_order_v2 (
            order_id, session_id, plan_id, submitted_frame_id, side, order_type,
            status, quantity, limit_price, stop_price, activate_index,
            submitted_at, filled_at, parent_order_id, oco_group_id
        )
        SELECT order_id, session_id, plan_id, submitted_frame_id, side,
            order_type, status, quantity, limit_price, stop_price,
            activate_index, submitted_at, filled_at, parent_order_id, oco_group_id
        FROM paper_order
        """
    )
    op.create_table(
        "paper_fill_v2",
        sa.Column("fill_id", sa.String(40), primary_key=True),
        sa.Column(
            "order_id",
            sa.String(40),
            sa.ForeignKey("paper_order_v2.order_id"),
            nullable=False,
        ),
        sa.Column(
            "session_id",
            sa.String(40),
            sa.ForeignKey("replay_session.session_id"),
            nullable=False,
        ),
        sa.Column(
            "frame_id",
            sa.String(40),
            sa.ForeignKey("replay_frame.frame_id"),
            nullable=False,
        ),
        sa.Column("side", sa.String(4), nullable=False),
        sa.Column("price", sa.String(64), nullable=False),
        sa.Column("quantity", sa.String(64), nullable=False),
        sa.Column("quote_amount", sa.String(64), nullable=False),
        sa.Column("fee", sa.String(64), nullable=False),
        sa.Column("executed_at", sa.String(40), nullable=False),
    )
    op.execute("INSERT INTO paper_fill_v2 SELECT * FROM paper_fill")
    op.create_table(
        "ledger_journal_v2",
        sa.Column("journal_id", sa.String(40), primary_key=True),
        sa.Column(
            "fill_id",
            sa.String(40),
            sa.ForeignKey("paper_fill_v2.fill_id"),
            nullable=False,
        ),
        sa.Column("account", sa.String(32), nullable=False),
        sa.Column("debit", sa.String(64), nullable=False),
        sa.Column("credit", sa.String(64), nullable=False),
        sa.Column("created_at", sa.String(40), nullable=False),
    )
    op.execute("INSERT INTO ledger_journal_v2 SELECT * FROM ledger_journal")
    op.drop_table("ledger_journal")
    op.drop_table("paper_fill")
    op.drop_table("paper_order")
    op.rename_table("paper_order_v2", "paper_order")
    op.rename_table("paper_fill_v2", "paper_fill")
    op.rename_table("ledger_journal_v2", "ledger_journal")
    op.create_index(
        "ix_paper_order_session",
        "paper_order",
        ["session_id", "submitted_at"],
    )
    op.create_index("ix_paper_order_oco", "paper_order", ["oco_group_id"])
    op.create_index(
        "ix_paper_fill_session",
        "paper_fill",
        ["session_id", "executed_at"],
    )
    op.create_index("ix_ledger_journal_fill", "ledger_journal", ["fill_id"])
    _create_account_event()


def _create_account_event() -> None:
    op.create_table(
        "account_event",
        sa.Column("account_event_id", sa.String(40), primary_key=True),
        sa.Column(
            "session_id",
            sa.String(40),
            sa.ForeignKey("replay_session.session_id"),
            nullable=False,
        ),
        sa.Column(
            "frame_id",
            sa.String(40),
            sa.ForeignKey("replay_frame.frame_id"),
            nullable=False,
        ),
        sa.Column("event_type", sa.String(24), nullable=False),
        sa.Column("bar_index", sa.Integer(), nullable=False),
        sa.Column("amount", sa.String(64), nullable=False),
        sa.Column("mark_price", sa.String(64), nullable=False),
        sa.Column("details_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("occurred_at", sa.String(40), nullable=False),
        sa.UniqueConstraint("session_id", "event_type", "bar_index"),
    )
    op.create_index(
        "ix_account_event_session",
        "account_event",
        ["session_id", "bar_index"],
    )


def downgrade() -> None:
    # Keep the additive schema when walking the revision marker backward. This
    # preserves fills and permits the recovery path to re-run idempotently.
    pass
