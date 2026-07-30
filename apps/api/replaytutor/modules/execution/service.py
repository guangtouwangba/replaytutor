from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, Literal, cast

from replaytutor.contracts import (
    CancelOrderRequest,
    ExecutionSnapshot,
    LockTradePlanRequest,
    OrderResult,
    PaperFill,
    PaperOrder,
    PortfolioState,
    SubmitOrderRequest,
    TradePlan,
    TradePlanResult,
)
from replaytutor.ids import new_id
from replaytutor.modules.execution.core import match_order
from replaytutor.modules.ledger import LedgerState, apply_fill
from replaytutor.modules.market_data.service import MarketDataService, utc_text
from replaytutor.modules.market_rules import CryptoSpotRules, RuleViolation
from replaytutor.modules.training_session.service import (
    InvalidSessionStateError,
    SessionConflictError,
    TrainingSessionError,
    TrainingSessionService,
    parse_utc,
)
from replaytutor.storage.database import connect_database

FEE_RATE = Decimal("0.001")


def decimal_text(value: Decimal) -> str:
    rendered = format(value, "f")
    if "." in rendered:
        rendered = rendered.rstrip("0").rstrip(".")
    return rendered or "0"


class ExecutionService:
    def __init__(self, sessions: TrainingSessionService) -> None:
        self.sessions = sessions
        self.settings = sessions.settings

    def lock_plan(self, session_id: str, request: LockTradePlanRequest) -> TradePlanResult:
        connection = connect_database(self.settings.database_path)
        try:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                """SELECT session_id, command_type, result_json
                FROM session_command WHERE command_id = ?""",
                (request.command_id,),
            ).fetchone()
            if existing is not None:
                if (
                    str(existing["session_id"]) != session_id
                    or str(existing["command_type"]) != "lock_plan"
                ):
                    raise TrainingSessionError("Command id was already used by another operation")
                connection.rollback()
                stored = TradePlanResult.model_validate_json(existing["result_json"])
                return stored.model_copy(update={"idempotent_replay": True})
            row = self.sessions._session_row(connection, session_id)
            self._validate_active(row, request.expected_revision)
            if Decimal(request.risk_amount) <= 0:
                raise RuleViolation("Risk amount must be positive")
            frame = connection.execute(
                "SELECT frame_id FROM replay_frame WHERE session_id = ? AND revision = ?",
                (session_id, row["revision"]),
            ).fetchone()
            if frame is None:
                raise TrainingSessionError("Current replay frame is missing")
            now = datetime.now(UTC)
            plan = TradePlan(
                plan_id=new_id("pln"),
                session_id=session_id,
                frame_id=str(frame["frame_id"]),
                status="locked",
                side=request.side,
                thesis=request.thesis,
                invalidation=request.invalidation,
                entry_price=request.entry_price,
                stop_price=request.stop_price,
                target_price=request.target_price,
                risk_amount=request.risk_amount,
                created_at=now,
            )
            connection.execute(
                """INSERT INTO trade_plan (
                    plan_id, session_id, frame_id, side, thesis, invalidation,
                    entry_price, stop_price, target_price, risk_amount, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    plan.plan_id,
                    session_id,
                    plan.frame_id,
                    plan.side,
                    plan.thesis,
                    plan.invalidation,
                    plan.entry_price,
                    plan.stop_price,
                    plan.target_price,
                    plan.risk_amount,
                    utc_text(now),
                ),
            )
            session = self.sessions._session_from_row(connection, row)
            result = TradePlanResult(session=session, execution=load_execution(connection, row))
            self._store_command(
                connection,
                request.command_id,
                session_id,
                "lock_plan",
                request.expected_revision,
                request.model_dump_json(),
                result.model_dump_json(),
                now,
            )
            connection.commit()
            return result
        except BaseException:
            if connection.in_transaction:
                connection.rollback()
            raise
        finally:
            connection.close()

    def submit_order(self, session_id: str, request: SubmitOrderRequest) -> OrderResult:
        connection = connect_database(self.settings.database_path)
        try:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                """SELECT session_id, command_type, result_json
                FROM session_command WHERE command_id = ?""",
                (request.command_id,),
            ).fetchone()
            if existing is not None:
                if (
                    str(existing["session_id"]) != session_id
                    or str(existing["command_type"]) != "submit_order"
                ):
                    raise TrainingSessionError("Command id was already used by another operation")
                connection.rollback()
                stored = OrderResult.model_validate_json(existing["result_json"])
                return stored.model_copy(update={"idempotent_replay": True})
            row = self.sessions._session_row(connection, session_id)
            self._validate_active(row, request.expected_revision)
            plan_row = connection.execute(
                "SELECT * FROM trade_plan WHERE session_id = ? ORDER BY created_at DESC LIMIT 1",
                (session_id,),
            ).fetchone()
            if plan_row is None:
                raise TrainingSessionError("A locked trade plan is required before ordering")
            snapshot = self.sessions.market_data.get_snapshot(str(row["snapshot_id"]))
            rules = CryptoSpotRules(
                tick_size=snapshot.instrument.tick_size,
                lot_size=snapshot.instrument.lot_size,
            )
            quantity = rules.validate_quantity(request.quantity)
            limit_price = (
                rules.validate_price(request.limit_price, field="limit_price")
                if request.order_type == "LIMIT"
                else None
            )
            stop_price = (
                rules.validate_price(request.stop_price, field="stop_price")
                if request.order_type == "STOP_MARKET"
                else None
            )
            take_profit_price = (
                rules.validate_price(
                    request.take_profit_price,
                    field="take_profit_price",
                )
                if request.take_profit_price is not None
                else None
            )
            protective_stop_price = (
                rules.validate_price(
                    request.protective_stop_price,
                    field="protective_stop_price",
                )
                if request.protective_stop_price is not None
                else None
            )
            if (take_profit_price is None) != (protective_stop_price is None):
                raise RuleViolation("Bracket requires both take-profit and protective-stop prices")
            if take_profit_price is not None and request.side != "BUY":
                raise RuleViolation("MVP spot bracket orders require a BUY parent")
            portfolio = load_ledger(connection, row)
            if request.side == "SELL" and portfolio.quantity < quantity:
                raise RuleViolation("Insufficient position")
            frame = connection.execute(
                "SELECT frame_id FROM replay_frame WHERE session_id = ? AND revision = ?",
                (session_id, row["revision"]),
            ).fetchone()
            if frame is None:
                raise TrainingSessionError("Current replay frame is missing")
            now = datetime.now(UTC)
            order = PaperOrder(
                order_id=new_id("ord"),
                session_id=session_id,
                plan_id=str(plan_row["plan_id"]),
                submitted_frame_id=str(frame["frame_id"]),
                side=request.side,
                order_type=request.order_type,
                status="PENDING",
                quantity=decimal_text(quantity),
                limit_price=decimal_text(limit_price) if limit_price is not None else None,
                stop_price=decimal_text(stop_price) if stop_price is not None else None,
                parent_order_id=None,
                oco_group_id=None,
                activate_index=int(row["current_index"]) + 1,
                submitted_at=now,
            )
            if order.activate_index >= int(row["total_bars"]):
                raise TrainingSessionError("No next bar is available to activate the order")
            connection.execute(
                """INSERT INTO paper_order (
                    order_id, session_id, plan_id, submitted_frame_id, side,
                    order_type, status, quantity, limit_price, stop_price,
                    activate_index, submitted_at, parent_order_id, oco_group_id
                ) VALUES (?, ?, ?, ?, ?, ?, 'PENDING', ?, ?, ?, ?, ?, NULL, NULL)""",
                (
                    order.order_id,
                    session_id,
                    order.plan_id,
                    order.submitted_frame_id,
                    order.side,
                    order.order_type,
                    order.quantity,
                    order.limit_price,
                    order.stop_price,
                    order.activate_index,
                    utc_text(now),
                ),
            )
            if take_profit_price is not None and protective_stop_price is not None:
                oco_group_id = new_id("oco")
                for child_type, child_limit, child_stop in (
                    ("LIMIT", take_profit_price, None),
                    ("STOP_MARKET", None, protective_stop_price),
                ):
                    connection.execute(
                        """INSERT INTO paper_order (
                            order_id, session_id, plan_id, submitted_frame_id,
                            side, order_type, status, quantity, limit_price,
                            stop_price, activate_index, submitted_at,
                            parent_order_id, oco_group_id
                        ) VALUES (?, ?, ?, ?, 'SELL', ?, 'PENDING', ?, ?, ?, ?, ?, ?, ?)""",
                        (
                            new_id("ord"),
                            session_id,
                            order.plan_id,
                            order.submitted_frame_id,
                            child_type,
                            order.quantity,
                            decimal_text(child_limit) if child_limit is not None else None,
                            decimal_text(child_stop) if child_stop is not None else None,
                            int(row["total_bars"]),
                            utc_text(now),
                            order.order_id,
                            oco_group_id,
                        ),
                    )
            session = self.sessions._session_from_row(connection, row)
            result = OrderResult(
                session=session, order=order, execution=load_execution(connection, row)
            )
            self._store_command(
                connection,
                request.command_id,
                session_id,
                "submit_order",
                request.expected_revision,
                request.model_dump_json(),
                result.model_dump_json(),
                now,
            )
            connection.commit()
            return result
        except BaseException:
            if connection.in_transaction:
                connection.rollback()
            raise
        finally:
            connection.close()

    def cancel_order(
        self,
        session_id: str,
        request: CancelOrderRequest,
    ) -> OrderResult:
        connection = connect_database(self.settings.database_path)
        try:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                """SELECT session_id, command_type, result_json
                FROM session_command WHERE command_id = ?""",
                (request.command_id,),
            ).fetchone()
            if existing is not None:
                if (
                    str(existing["session_id"]) != session_id
                    or str(existing["command_type"]) != "cancel_order"
                ):
                    raise TrainingSessionError("Command id was already used by another operation")
                connection.rollback()
                stored = OrderResult.model_validate_json(existing["result_json"])
                return stored.model_copy(update={"idempotent_replay": True})
            row = self.sessions._session_row(connection, session_id)
            self._validate_active(row, request.expected_revision)
            order_row = connection.execute(
                "SELECT * FROM paper_order WHERE order_id = ? AND session_id = ?",
                (request.order_id, session_id),
            ).fetchone()
            if order_row is None:
                raise TrainingSessionError("Order not found")
            if str(order_row["status"]) != "PENDING":
                raise TrainingSessionError("Only pending orders can be cancelled")
            connection.execute(
                """UPDATE paper_order SET status = 'CANCELLED'
                WHERE (order_id = ? OR parent_order_id = ?) AND status = 'PENDING'""",
                (request.order_id, request.order_id),
            )
            now = datetime.now(UTC)
            refreshed = connection.execute(
                "SELECT * FROM paper_order WHERE order_id = ?",
                (request.order_id,),
            ).fetchone()
            assert refreshed is not None
            session = self.sessions._session_from_row(connection, row)
            execution = load_execution(connection, row)
            cancelled = next(item for item in execution.orders if item.order_id == request.order_id)
            result = OrderResult(
                session=session,
                order=cancelled,
                execution=execution,
            )
            self._store_command(
                connection,
                request.command_id,
                session_id,
                "cancel_order",
                request.expected_revision,
                request.model_dump_json(),
                result.model_dump_json(),
                now,
            )
            connection.commit()
            return result
        except BaseException:
            if connection.in_transaction:
                connection.rollback()
            raise
        finally:
            connection.close()

    @staticmethod
    def _validate_active(row: dict[str, Any], expected_revision: int) -> None:
        if row["status"] in {"completed", "stopped"}:
            raise InvalidSessionStateError(f"Cannot trade in a {row['status']} session")
        if int(row["revision"]) != expected_revision:
            raise SessionConflictError(int(row["revision"]))

    @staticmethod
    def _store_command(
        connection: sqlite3.Connection,
        command_id: str,
        session_id: str,
        kind: str,
        revision: int,
        request_json: str,
        result_json: str,
        now: datetime,
    ) -> None:
        connection.execute(
            """INSERT INTO session_command (
                command_id, session_id, command_type, expected_revision,
                request_json, result_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (command_id, session_id, kind, revision, request_json, result_json, utc_text(now)),
        )


def settle_pending_orders(
    connection: sqlite3.Connection,
    *,
    market_data: MarketDataService,
    row: dict[str, Any],
    from_index: int,
    to_index: int,
    frame_id: str,
) -> None:
    orders = connection.execute(
        """SELECT * FROM paper_order
        WHERE session_id = ? AND status = 'PENDING' AND activate_index <= ?
        ORDER BY submitted_at, order_id""",
        (row["session_id"], to_index),
    ).fetchall()
    state = load_ledger(connection, row)
    for raw_order in orders:
        order = dict(raw_order)
        live_status = connection.execute(
            "SELECT status FROM paper_order WHERE order_id = ?",
            (order["order_id"],),
        ).fetchone()
        if live_status is None or str(live_status["status"]) != "PENDING":
            continue
        first_index = max(from_index, int(order["activate_index"]))
        for index in range(first_index, to_index + 1):
            bar = market_data.query_snapshot_bar_slice(
                str(row["snapshot_id"]), offset=index, limit=1
            )[0]
            match = match_order(
                side=cast(Literal["BUY", "SELL"], str(order["side"])),
                order_type=cast(
                    Literal["MARKET", "LIMIT", "STOP_MARKET"], str(order["order_type"])
                ),
                bar=bar,
                limit_price=Decimal(str(order["limit_price"]))
                if order["limit_price"] is not None
                else None,
                stop_price=Decimal(str(order["stop_price"]))
                if order["stop_price"] is not None
                else None,
            )
            if not match.filled or match.price is None:
                continue
            quantity = Decimal(str(order["quantity"]))
            quote = match.price * quantity
            fee = quote * FEE_RATE
            try:
                new_state = apply_fill(
                    state,
                    side=cast(Literal["BUY", "SELL"], str(order["side"])),
                    price=match.price,
                    quantity=quantity,
                    fee=fee,
                )
            except ValueError:
                connection.execute(
                    "UPDATE paper_order SET status = 'REJECTED' WHERE order_id = ?",
                    (order["order_id"],),
                )
                break
            fill_id = new_id("fil")
            executed_at = bar.open_time
            connection.execute(
                """INSERT INTO paper_fill (
                    fill_id, order_id, session_id, frame_id, side, price,
                    quantity, quote_amount, fee, executed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    fill_id,
                    order["order_id"],
                    row["session_id"],
                    frame_id,
                    order["side"],
                    decimal_text(match.price),
                    decimal_text(quantity),
                    decimal_text(quote),
                    decimal_text(fee),
                    utc_text(executed_at),
                ),
            )
            _insert_balanced_journal(
                connection, fill_id, str(order["side"]), quote, fee, executed_at
            )
            connection.execute(
                "UPDATE paper_order SET status = 'FILLED', filled_at = ? WHERE order_id = ?",
                (utc_text(executed_at), order["order_id"]),
            )
            if order["parent_order_id"] is None:
                connection.execute(
                    """UPDATE paper_order SET activate_index = ?
                    WHERE parent_order_id = ? AND status = 'PENDING'""",
                    (index + 1, order["order_id"]),
                )
            elif order["oco_group_id"] is not None:
                connection.execute(
                    """UPDATE paper_order SET status = 'CANCELLED'
                    WHERE oco_group_id = ? AND order_id != ? AND status = 'PENDING'""",
                    (order["oco_group_id"], order["order_id"]),
                )
            state = new_state
            break


def _insert_balanced_journal(
    connection: sqlite3.Connection,
    fill_id: str,
    side: str,
    quote: Decimal,
    fee: Decimal,
    now: datetime,
) -> None:
    entries = (
        (
            ("inventory", quote, Decimal("0")),
            ("fee", fee, Decimal("0")),
            ("cash", Decimal("0"), quote + fee),
        )
        if side == "BUY"
        else (
            ("cash", quote - fee, Decimal("0")),
            ("fee", fee, Decimal("0")),
            ("inventory", Decimal("0"), quote),
        )
    )
    for account, debit, credit in entries:
        connection.execute(
            """INSERT INTO ledger_journal (
                journal_id, fill_id, account, debit, credit, created_at
            ) VALUES (?, ?, ?, ?, ?, ?)""",
            (
                new_id("jrn"),
                fill_id,
                account,
                decimal_text(debit),
                decimal_text(credit),
                utc_text(now),
            ),
        )


def load_ledger(connection: sqlite3.Connection, row: dict[str, Any]) -> LedgerState:
    state = LedgerState(cash=Decimal(str(row["initial_cash"])))
    fills = connection.execute(
        """SELECT side, price, quantity, fee
        FROM paper_fill WHERE session_id = ?
        ORDER BY executed_at, fill_id""",
        (row["session_id"],),
    ).fetchall()
    for fill in fills:
        state = apply_fill(
            state,
            side=cast(Literal["BUY", "SELL"], str(fill["side"])),
            price=Decimal(str(fill["price"])),
            quantity=Decimal(str(fill["quantity"])),
            fee=Decimal(str(fill["fee"])),
        )
    return state


def load_execution(connection: sqlite3.Connection, row: dict[str, Any]) -> ExecutionSnapshot:
    plan_row = connection.execute(
        "SELECT * FROM trade_plan WHERE session_id = ? ORDER BY created_at DESC LIMIT 1",
        (row["session_id"],),
    ).fetchone()
    plan = (
        None
        if plan_row is None
        else TradePlan(
            plan_id=str(plan_row["plan_id"]),
            session_id=str(plan_row["session_id"]),
            frame_id=str(plan_row["frame_id"]),
            status="locked",
            side=cast(Literal["BUY", "SELL"], str(plan_row["side"])),
            thesis=str(plan_row["thesis"]),
            invalidation=str(plan_row["invalidation"]),
            entry_price=plan_row["entry_price"],
            stop_price=plan_row["stop_price"],
            target_price=plan_row["target_price"],
            risk_amount=str(plan_row["risk_amount"]),
            created_at=parse_utc(str(plan_row["created_at"])),
        )
    )
    orders = [
        PaperOrder(
            order_id=str(item["order_id"]),
            session_id=str(item["session_id"]),
            plan_id=str(item["plan_id"]),
            submitted_frame_id=str(item["submitted_frame_id"]),
            side=cast(Literal["BUY", "SELL"], str(item["side"])),
            order_type=cast(
                Literal["MARKET", "LIMIT", "STOP_MARKET"],
                str(item["order_type"]),
            ),
            status=cast(
                Literal["PENDING", "FILLED", "CANCELLED", "REJECTED"],
                str(item["status"]),
            ),
            quantity=str(item["quantity"]),
            limit_price=item["limit_price"],
            stop_price=item["stop_price"],
            parent_order_id=item["parent_order_id"],
            oco_group_id=item["oco_group_id"],
            activate_index=int(item["activate_index"]),
            submitted_at=parse_utc(str(item["submitted_at"])),
            filled_at=parse_utc(str(item["filled_at"])) if item["filled_at"] else None,
        )
        for item in connection.execute(
            "SELECT * FROM paper_order WHERE session_id = ? ORDER BY submitted_at",
            (row["session_id"],),
        ).fetchall()
    ]
    fills = [
        PaperFill(
            fill_id=str(item["fill_id"]),
            order_id=str(item["order_id"]),
            session_id=str(item["session_id"]),
            frame_id=str(item["frame_id"]),
            side=cast(Literal["BUY", "SELL"], str(item["side"])),
            price=str(item["price"]),
            quantity=str(item["quantity"]),
            quote_amount=str(item["quote_amount"]),
            fee=str(item["fee"]),
            executed_at=parse_utc(str(item["executed_at"])),
        )
        for item in connection.execute(
            "SELECT * FROM paper_fill WHERE session_id = ? ORDER BY executed_at",
            (row["session_id"],),
        ).fetchall()
    ]
    state = load_ledger(connection, row)
    return ExecutionSnapshot(
        plan=plan,
        orders=orders,
        fills=fills,
        portfolio=PortfolioState(
            cash=decimal_text(state.cash),
            position_quantity=decimal_text(state.quantity),
            average_entry_price=decimal_text(state.average_entry),
            realized_pnl=decimal_text(state.realized_pnl),
            fees_paid=decimal_text(state.fees),
        ),
    )
