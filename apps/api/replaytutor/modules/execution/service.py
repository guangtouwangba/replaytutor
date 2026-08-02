from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, Literal, cast

from replaytutor.contracts import (
    AmendOrderRequest,
    CancelOrderRequest,
    ExecutionSnapshot,
    LockTradePlanRequest,
    OrderResult,
    PaperFill,
    PaperOrder,
    PortfolioState,
    PositionState,
    SubmitOrderRequest,
    TradePlan,
    TradePlanResult,
)
from replaytutor.ids import new_id
from replaytutor.modules.execution.core import match_order
from replaytutor.modules.ledger import (
    FuturesLedgerState,
    LedgerState,
    apply_fill,
    apply_funding,
    apply_futures_fill,
    initial_margin,
    liquidate,
    liquidation_price,
    maintenance_margin,
    unrealized_pnl,
)
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

SPOT_FEE_RATE = Decimal("0.001")
BAR_PARTICIPATION_RATE = Decimal("0.10")


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
                if request.order_type in {"LIMIT", "STOP_LIMIT", "TAKE_PROFIT_LIMIT"}
                else None
            )
            stop_price = (
                rules.validate_price(request.stop_price, field="stop_price")
                if request.order_type
                in {
                    "STOP_MARKET",
                    "STOP_LIMIT",
                    "TAKE_PROFIT_MARKET",
                    "TAKE_PROFIT_LIMIT",
                }
                else None
            )
            activation_price = (
                rules.validate_price(request.activation_price, field="activation_price")
                if request.activation_price is not None
                else None
            )
            callback_rate = (
                Decimal(request.callback_rate) if request.callback_rate is not None else None
            )
            if request.order_type == "TRAILING_STOP_MARKET":
                if callback_rate is None:
                    raise RuleViolation("callback_rate is required for a trailing stop")
                if not Decimal("0.001") <= callback_rate <= Decimal("0.10"):
                    raise RuleViolation("callback_rate must be between 0.001 and 0.10")
            elif callback_rate is not None or activation_price is not None:
                raise RuleViolation("Trailing fields require TRAILING_STOP_MARKET")
            if request.time_in_force == "GTD":
                if request.good_till_index is None or request.good_till_index <= int(
                    row["current_index"]
                ):
                    raise RuleViolation("GTD requires a future good_till_index")
            elif request.good_till_index is not None:
                raise RuleViolation("good_till_index requires GTD")
            if request.post_only and request.order_type not in {
                "LIMIT",
                "STOP_LIMIT",
                "TAKE_PROFIT_LIMIT",
            }:
                raise RuleViolation("Post-only is only valid for limit orders")
            if str(row.get("position_mode", "ONEWAY")) == "ONEWAY":
                if request.position_side != "BOTH":
                    raise RuleViolation("One-way mode requires BOTH position side")
            elif request.position_side == "BOTH":
                raise RuleViolation("Hedge mode requires LONG or SHORT position side")
            if str(row.get("account_type", "SPOT")) == "SPOT" and (
                request.position_side != "BOTH" or request.reduce_only or request.close_position
            ):
                raise RuleViolation("Derivative position flags are unavailable in spot sessions")
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
            if (
                str(row.get("account_type", "SPOT")) == "SPOT"
                and (take_profit_price is not None or protective_stop_price is not None)
                and request.side != "BUY"
            ):
                raise RuleViolation("Spot bracket orders require a BUY parent")
            if str(row.get("account_type", "SPOT")) == "SPOT":
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
                filled_quantity="0",
                average_fill_price="0",
                limit_price=decimal_text(limit_price) if limit_price is not None else None,
                stop_price=decimal_text(stop_price) if stop_price is not None else None,
                activation_price=(
                    decimal_text(activation_price) if activation_price is not None else None
                ),
                callback_rate=(decimal_text(callback_rate) if callback_rate is not None else None),
                time_in_force=request.time_in_force,
                good_till_index=request.good_till_index,
                reduce_only=request.reduce_only or request.close_position,
                post_only=request.post_only,
                close_position=request.close_position,
                position_side=request.position_side,
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
                    activation_price, callback_rate, time_in_force,
                    good_till_index, reduce_only, post_only, close_position,
                    position_side, activate_index, submitted_at,
                    parent_order_id, oco_group_id
                ) VALUES (?, ?, ?, ?, ?, ?, 'PENDING', ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, NULL, NULL)""",
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
                    order.activation_price,
                    order.callback_rate,
                    order.time_in_force,
                    order.good_till_index,
                    order.reduce_only,
                    order.post_only,
                    order.close_position,
                    order.position_side,
                    order.activate_index,
                    utc_text(now),
                ),
            )
            if take_profit_price is not None or protective_stop_price is not None:
                oco_group_id = new_id("oco")
                exit_side = "SELL" if request.side == "BUY" else "BUY"
                children: list[tuple[str, Decimal | None, Decimal | None]] = []
                if take_profit_price is not None:
                    children.append(("LIMIT", take_profit_price, None))
                if protective_stop_price is not None:
                    children.append(("STOP_MARKET", None, protective_stop_price))
                for child_type, child_limit, child_stop in children:
                    connection.execute(
                        """INSERT INTO paper_order (
                            order_id, session_id, plan_id, submitted_frame_id,
                            side, order_type, status, quantity, limit_price,
                            stop_price, activate_index, submitted_at,
                            parent_order_id, oco_group_id, reduce_only,
                            close_position, position_side, time_in_force
                        ) VALUES (?, ?, ?, ?, ?, ?, 'PENDING', ?, ?, ?, ?, ?, ?, ?,
                            ?, 0, ?, 'GTC')""",
                        (
                            new_id("ord"),
                            session_id,
                            order.plan_id,
                            order.submitted_frame_id,
                            exit_side,
                            child_type,
                            order.quantity,
                            decimal_text(child_limit) if child_limit is not None else None,
                            decimal_text(child_stop) if child_stop is not None else None,
                            int(row["total_bars"]),
                            utc_text(now),
                            order.order_id,
                            oco_group_id,
                            str(row.get("account_type", "SPOT")) == "USDT_PERPETUAL",
                            order.position_side,
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
            if str(order_row["status"]) not in {
                "PENDING",
                "TRIGGERED",
                "PARTIALLY_FILLED",
            }:
                raise TrainingSessionError("Only active orders can be cancelled")
            connection.execute(
                """UPDATE paper_order SET status = 'CANCELLED'
                WHERE (order_id = ? OR parent_order_id = ?)
                  AND status IN ('PENDING', 'TRIGGERED', 'PARTIALLY_FILLED')""",
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

    def amend_order(self, session_id: str, request: AmendOrderRequest) -> OrderResult:
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
                    or str(existing["command_type"]) != "amend_order"
                ):
                    raise TrainingSessionError("Command id was already used by another operation")
                connection.rollback()
                stored = OrderResult.model_validate_json(existing["result_json"])
                return stored.model_copy(update={"idempotent_replay": True})
            row = self.sessions._session_row(connection, session_id)
            self._validate_active(row, request.expected_revision)
            order = connection.execute(
                "SELECT * FROM paper_order WHERE order_id = ? AND session_id = ?",
                (request.order_id, session_id),
            ).fetchone()
            if order is None:
                raise TrainingSessionError("Order not found")
            if str(order["status"]) not in {"PENDING", "TRIGGERED", "PARTIALLY_FILLED"}:
                raise TrainingSessionError("Only active orders can be amended")
            snapshot = self.sessions.market_data.get_snapshot(str(row["snapshot_id"]))
            rules = CryptoSpotRules(
                tick_size=snapshot.instrument.tick_size,
                lot_size=snapshot.instrument.lot_size,
            )
            updates: dict[str, object] = {}
            if request.quantity is not None:
                quantity = rules.validate_quantity(request.quantity)
                if quantity < Decimal(str(order["filled_quantity"])):
                    raise RuleViolation("Quantity cannot be below already filled quantity")
                updates["quantity"] = decimal_text(quantity)
            for field in ("limit_price", "stop_price", "activation_price"):
                value = getattr(request, field)
                if value is not None:
                    updates[field] = decimal_text(rules.validate_price(value, field=field))
            if request.callback_rate is not None:
                callback = Decimal(request.callback_rate)
                if not Decimal("0.001") <= callback <= Decimal("0.10"):
                    raise RuleViolation("callback_rate must be between 0.001 and 0.10")
                updates["callback_rate"] = decimal_text(callback)
            if request.good_till_index is not None:
                if request.good_till_index <= int(row["current_index"]):
                    raise RuleViolation("good_till_index must be in the future")
                updates["good_till_index"] = request.good_till_index
            if not updates:
                raise RuleViolation("At least one amendable field is required")
            updates.update(
                activate_index=int(row["current_index"]) + 1,
                triggered_at_index=None,
                trail_anchor_price=None,
                status=(
                    "PARTIALLY_FILLED" if Decimal(str(order["filled_quantity"])) > 0 else "PENDING"
                ),
            )
            assignments = ", ".join(f"{field} = ?" for field in updates)
            connection.execute(
                f"UPDATE paper_order SET {assignments} WHERE order_id = ?",
                (*updates.values(), request.order_id),
            )
            now = datetime.now(UTC)
            session = self.sessions._session_from_row(connection, row)
            execution = load_execution(connection, row)
            amended = next(item for item in execution.orders if item.order_id == request.order_id)
            result = OrderResult(session=session, order=amended, execution=execution)
            self._store_command(
                connection,
                request.command_id,
                session_id,
                "amend_order",
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
    account_type = str(row.get("account_type", "SPOT"))
    spot_state: LedgerState | None = None
    futures_state: FuturesLedgerState | None = None
    if account_type == "SPOT":
        spot_state = load_ledger(connection, row)
    else:
        futures_state = load_futures_ledger(connection, row)

    for index in range(from_index, to_index + 1):
        bar = market_data.query_snapshot_bar_slice(str(row["snapshot_id"]), offset=index, limit=1)[
            0
        ]
        mark_price = Decimal(bar.raw.close)
        if futures_state is not None:
            futures_state = _settle_funding(
                connection, row, frame_id, index, bar.open_time, mark_price, futures_state
            )
            futures_state = _settle_liquidation(
                connection, row, frame_id, index, bar.open_time, bar, futures_state
            )
            if futures_state.liquidated:
                connection.execute(
                    """UPDATE paper_order SET status = 'CANCELLED'
                    WHERE session_id = ?
                      AND status IN (
                        'PENDING', 'TRIGGERED', 'PARTIALLY_FILLED'
                      )""",
                    (row["session_id"],),
                )
                continue

        orders = connection.execute(
            """SELECT * FROM paper_order
            WHERE session_id = ?
              AND status IN ('PENDING', 'TRIGGERED', 'PARTIALLY_FILLED')
              AND activate_index <= ?
            ORDER BY submitted_at, order_id""",
            (row["session_id"], index),
        ).fetchall()
        for raw_order in orders:
            order = dict(raw_order)
            if (
                order["time_in_force"] == "GTD"
                and order["good_till_index"] is not None
                and index > int(order["good_till_index"])
            ):
                connection.execute(
                    "UPDATE paper_order SET status = 'EXPIRED' WHERE order_id = ?",
                    (order["order_id"],),
                )
                continue
            if bool(order["post_only"]) and _would_take_at_open(order, Decimal(bar.raw.open)):
                connection.execute(
                    "UPDATE paper_order SET status = 'REJECTED' WHERE order_id = ?",
                    (order["order_id"],),
                )
                continue
            match = match_order(
                side=cast(Literal["BUY", "SELL"], str(order["side"])),
                order_type=cast(Any, str(order["order_type"])),
                bar=bar,
                limit_price=_optional_decimal(order["limit_price"]),
                stop_price=_optional_decimal(order["stop_price"]),
                activation_price=_optional_decimal(order["activation_price"]),
                callback_rate=_optional_decimal(order["callback_rate"]),
                trail_anchor_price=_optional_decimal(order["trail_anchor_price"]),
                already_triggered=order["triggered_at_index"] is not None,
            )
            if match.triggered and order["triggered_at_index"] is None:
                connection.execute(
                    """UPDATE paper_order
                    SET status = 'TRIGGERED', triggered_at_index = ?,
                        trail_anchor_price = ?
                    WHERE order_id = ?""",
                    (
                        index,
                        (
                            decimal_text(match.trail_anchor_price)
                            if match.trail_anchor_price is not None
                            else None
                        ),
                        order["order_id"],
                    ),
                )
                if not match.filled:
                    continue
            elif match.trail_anchor_price is not None:
                connection.execute(
                    "UPDATE paper_order SET trail_anchor_price = ? WHERE order_id = ?",
                    (decimal_text(match.trail_anchor_price), order["order_id"]),
                )
            if not match.filled or match.price is None:
                if order["time_in_force"] in {"IOC", "FOK"}:
                    connection.execute(
                        "UPDATE paper_order SET status = 'EXPIRED' WHERE order_id = ?",
                        (order["order_id"],),
                    )
                continue
            remaining = Decimal(str(order["quantity"])) - Decimal(str(order["filled_quantity"]))
            if bool(order["close_position"]) and futures_state is not None:
                closes_long = str(order["position_side"]) == "LONG" or (
                    str(order["position_side"]) == "BOTH" and str(order["side"]) == "SELL"
                )
                remaining = (
                    futures_state.long.quantity if closes_long else futures_state.short.quantity
                )
                if remaining <= 0:
                    connection.execute(
                        "UPDATE paper_order SET status = 'REJECTED' WHERE order_id = ?",
                        (order["order_id"],),
                    )
                    continue
                connection.execute(
                    "UPDATE paper_order SET quantity = ? WHERE order_id = ?",
                    (decimal_text(remaining), order["order_id"]),
                )
            capacity = Decimal(bar.raw.volume) * BAR_PARTICIPATION_RATE
            fill_quantity = min(remaining, capacity)
            if order["time_in_force"] == "FOK" and fill_quantity < remaining:
                connection.execute(
                    "UPDATE paper_order SET status = 'EXPIRED' WHERE order_id = ?",
                    (order["order_id"],),
                )
                continue
            if fill_quantity <= 0:
                continue
            maker = str(order["order_type"]) in {
                "LIMIT",
                "STOP_LIMIT",
                "TAKE_PROFIT_LIMIT",
            }
            fee_rate = (
                SPOT_FEE_RATE
                if account_type == "SPOT"
                else Decimal(str(row["maker_fee_rate"] if maker else row["taker_fee_rate"]))
            )
            quote = match.price * fill_quantity
            fee = quote * fee_rate
            try:
                if spot_state is not None:
                    spot_state = apply_fill(
                        spot_state,
                        side=cast(Literal["BUY", "SELL"], str(order["side"])),
                        price=match.price,
                        quantity=fill_quantity,
                        fee=fee,
                    )
                else:
                    assert futures_state is not None
                    candidate = apply_futures_fill(
                        futures_state,
                        side=cast(Literal["BUY", "SELL"], str(order["side"])),
                        position_side=cast(Any, str(order["position_side"])),
                        position_mode=cast(Any, str(row["position_mode"])),
                        price=match.price,
                        quantity=fill_quantity,
                        fee=fee,
                        reduce_only=bool(order["reduce_only"]),
                    )
                    required = initial_margin(candidate, match.price, int(row["leverage"]))
                    if required > candidate.wallet_balance:
                        raise ValueError("Insufficient available margin")
                    futures_state = candidate
            except ValueError:
                connection.execute(
                    "UPDATE paper_order SET status = 'REJECTED' WHERE order_id = ?",
                    (order["order_id"],),
                )
                continue
            fill_id = new_id("fil")
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
                    decimal_text(fill_quantity),
                    decimal_text(quote),
                    decimal_text(fee),
                    utc_text(bar.open_time),
                ),
            )
            _insert_balanced_journal(
                connection, fill_id, str(order["side"]), quote, fee, bar.open_time
            )
            previous_filled = Decimal(str(order["filled_quantity"]))
            total_filled = previous_filled + fill_quantity
            previous_average = Decimal(str(order["average_fill_price"]))
            average = (
                previous_average * previous_filled + match.price * fill_quantity
            ) / total_filled
            completed = total_filled >= Decimal(str(order["quantity"]))
            status = "FILLED" if completed else "PARTIALLY_FILLED"
            if not completed and order["time_in_force"] == "IOC":
                status = "EXPIRED"
            connection.execute(
                """UPDATE paper_order
                SET status = ?, filled_quantity = ?, average_fill_price = ?,
                    filled_at = ?
                WHERE order_id = ?""",
                (
                    status,
                    decimal_text(total_filled),
                    decimal_text(average),
                    utc_text(bar.open_time) if completed else None,
                    order["order_id"],
                ),
            )
            if order["parent_order_id"] is None and completed:
                connection.execute(
                    """UPDATE paper_order SET activate_index = ?, quantity = ?
                    WHERE parent_order_id = ?
                      AND status IN ('PENDING', 'TRIGGERED')""",
                    (index + 1, decimal_text(total_filled), order["order_id"]),
                )
            elif order["oco_group_id"] is not None:
                connection.execute(
                    """UPDATE paper_order SET status = 'CANCELLED'
                    WHERE oco_group_id = ? AND order_id != ?
                      AND status IN ('PENDING', 'TRIGGERED', 'PARTIALLY_FILLED')""",
                    (order["oco_group_id"], order["order_id"]),
                )


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


def load_futures_ledger(
    connection: sqlite3.Connection,
    row: dict[str, Any],
) -> FuturesLedgerState:
    state = FuturesLedgerState(wallet_balance=Decimal(str(row["initial_cash"])))
    fills = connection.execute(
        """SELECT f.side, f.price, f.quantity, f.fee,
            o.position_side, o.reduce_only
        FROM paper_fill f
        JOIN paper_order o ON o.order_id = f.order_id
        WHERE f.session_id = ?
        ORDER BY f.executed_at, f.fill_id""",
        (row["session_id"],),
    ).fetchall()
    for fill in fills:
        state = apply_futures_fill(
            state,
            side=cast(Literal["BUY", "SELL"], str(fill["side"])),
            position_side=cast(Any, str(fill["position_side"])),
            position_mode=cast(Any, str(row["position_mode"])),
            price=Decimal(str(fill["price"])),
            quantity=Decimal(str(fill["quantity"])),
            fee=Decimal(str(fill["fee"])),
            reduce_only=bool(fill["reduce_only"]),
        )
    funding_rows = connection.execute(
        """SELECT amount
        FROM account_event
        WHERE session_id = ? AND event_type = 'FUNDING'""",
        (row["session_id"],),
    ).fetchall()
    funding_paid = sum(
        (Decimal(str(item["amount"])) for item in funding_rows),
        start=Decimal("0"),
    )
    state = FuturesLedgerState(
        wallet_balance=state.wallet_balance - funding_paid,
        long=state.long,
        short=state.short,
        realized_pnl=state.realized_pnl,
        fees=state.fees,
        funding_paid=funding_paid,
        liquidated=False,
    )
    liquidation = connection.execute(
        """SELECT details_json FROM account_event
        WHERE session_id = ? AND event_type = 'LIQUIDATION'
        ORDER BY bar_index DESC LIMIT 1""",
        (row["session_id"],),
    ).fetchone()
    if liquidation is not None:
        details = json.loads(str(liquidation["details_json"]))
        return FuturesLedgerState(
            wallet_balance=Decimal(str(details["wallet_balance"])),
            realized_pnl=Decimal(str(details["realized_pnl"])),
            fees=state.fees,
            funding_paid=state.funding_paid,
            liquidated=True,
        )
    return state


def _optional_decimal(value: object) -> Decimal | None:
    return None if value is None else Decimal(str(value))


def _would_take_at_open(order: dict[str, Any], open_price: Decimal) -> bool:
    if str(order["order_type"]) not in {
        "LIMIT",
        "STOP_LIMIT",
        "TAKE_PROFIT_LIMIT",
    }:
        return False
    if str(order["order_type"]) != "LIMIT" and order["triggered_at_index"] is None:
        return False
    limit_price = _optional_decimal(order["limit_price"])
    if limit_price is None:
        return False
    return limit_price >= open_price if str(order["side"]) == "BUY" else limit_price <= open_price


def _settle_funding(
    connection: sqlite3.Connection,
    row: dict[str, Any],
    frame_id: str,
    index: int,
    occurred_at: datetime,
    mark_price: Decimal,
    state: FuturesLedgerState,
) -> FuturesLedgerState:
    interval = int(row["funding_interval_bars"])
    if index <= int(row["start_index"]) or (index - int(row["start_index"])) % interval:
        return state
    existing = connection.execute(
        """SELECT 1 FROM account_event
        WHERE session_id = ? AND event_type = 'FUNDING' AND bar_index = ?""",
        (row["session_id"], index),
    ).fetchone()
    if existing is not None:
        return state
    updated, amount = apply_funding(
        state,
        mark_price=mark_price,
        funding_rate=Decimal(str(row["funding_rate"])),
    )
    connection.execute(
        """INSERT INTO account_event (
            account_event_id, session_id, frame_id, event_type, bar_index,
            amount, mark_price, details_json, occurred_at
        ) VALUES (?, ?, ?, 'FUNDING', ?, ?, ?, ?, ?)""",
        (
            new_id("ace"),
            row["session_id"],
            frame_id,
            index,
            decimal_text(amount),
            decimal_text(mark_price),
            json.dumps({"funding_rate": str(row["funding_rate"])}, sort_keys=True),
            utc_text(occurred_at),
        ),
    )
    return updated


def _settle_liquidation(
    connection: sqlite3.Connection,
    row: dict[str, Any],
    frame_id: str,
    index: int,
    occurred_at: datetime,
    bar: Any,
    state: FuturesLedgerState,
) -> FuturesLedgerState:
    if state.liquidated or (not state.long.quantity and not state.short.quantity):
        return state
    maintenance_rate = Decimal(str(row["maintenance_margin_rate"]))
    long_liquidation = liquidation_price(
        state,
        direction="LONG",
        margin_mode=cast(Any, str(row["margin_mode"])),
        leverage=int(row["leverage"]),
        maintenance_margin_rate=maintenance_rate,
    )
    short_liquidation = liquidation_price(
        state,
        direction="SHORT",
        margin_mode=cast(Any, str(row["margin_mode"])),
        leverage=int(row["leverage"]),
        maintenance_margin_rate=maintenance_rate,
    )
    trigger_price = (
        long_liquidation
        if long_liquidation is not None and Decimal(bar.raw.low) <= long_liquidation
        else short_liquidation
        if short_liquidation is not None and Decimal(bar.raw.high) >= short_liquidation
        else None
    )
    if trigger_price is None:
        return state
    updated = liquidate(state, mark_price=trigger_price)
    loss = state.wallet_balance - updated.wallet_balance
    connection.execute(
        """INSERT INTO account_event (
            account_event_id, session_id, frame_id, event_type, bar_index,
            amount, mark_price, details_json, occurred_at
        ) VALUES (?, ?, ?, 'LIQUIDATION', ?, ?, ?, ?, ?)""",
        (
            new_id("ace"),
            row["session_id"],
            frame_id,
            index,
            decimal_text(loss),
            decimal_text(trigger_price),
            json.dumps(
                {
                    "wallet_balance": decimal_text(updated.wallet_balance),
                    "realized_pnl": decimal_text(updated.realized_pnl),
                },
                sort_keys=True,
            ),
            utc_text(occurred_at),
        ),
    )
    return updated


def load_execution(
    connection: sqlite3.Connection,
    row: dict[str, Any],
    *,
    mark_price: Decimal | None = None,
) -> ExecutionSnapshot:
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
                Any,
                str(item["order_type"]),
            ),
            status=cast(
                Any,
                str(item["status"]),
            ),
            quantity=str(item["quantity"]),
            filled_quantity=str(item["filled_quantity"]),
            average_fill_price=str(item["average_fill_price"]),
            limit_price=item["limit_price"],
            stop_price=item["stop_price"],
            activation_price=item["activation_price"],
            callback_rate=item["callback_rate"],
            trail_anchor_price=item["trail_anchor_price"],
            time_in_force=cast(Any, str(item["time_in_force"])),
            good_till_index=(
                int(item["good_till_index"]) if item["good_till_index"] is not None else None
            ),
            reduce_only=bool(item["reduce_only"]),
            post_only=bool(item["post_only"]),
            close_position=bool(item["close_position"]),
            position_side=cast(Any, str(item["position_side"])),
            triggered_at_index=(
                int(item["triggered_at_index"]) if item["triggered_at_index"] is not None else None
            ),
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
    if str(row.get("account_type", "SPOT")) == "USDT_PERPETUAL":
        futures = load_futures_ledger(connection, row)
        mark = mark_price or (
            futures.long.average_entry
            if futures.long.quantity
            else futures.short.average_entry
            if futures.short.quantity
            else Decimal("0")
        )
        unrealized = unrealized_pnl(futures, mark)
        used_margin = initial_margin(futures, mark, int(row["leverage"]))
        maintenance = maintenance_margin(
            futures, mark, Decimal(str(row["maintenance_margin_rate"]))
        )
        positions: list[PositionState] = []
        for side, position in (("LONG", futures.long), ("SHORT", futures.short)):
            if not position.quantity:
                continue
            notional = position.quantity * mark
            positions.append(
                PositionState(
                    position_side=cast(Any, side),
                    quantity=decimal_text(position.quantity),
                    average_entry_price=decimal_text(position.average_entry),
                    mark_price=decimal_text(mark),
                    notional=decimal_text(notional),
                    initial_margin=decimal_text(notional / Decimal(int(row["leverage"]))),
                    maintenance_margin=decimal_text(
                        notional * Decimal(str(row["maintenance_margin_rate"]))
                    ),
                    unrealized_pnl=decimal_text(
                        (mark - position.average_entry) * position.quantity
                        if side == "LONG"
                        else (position.average_entry - mark) * position.quantity
                    ),
                    liquidation_price=(
                        decimal_text(value)
                        if (
                            value := liquidation_price(
                                futures,
                                direction=cast(Any, side),
                                margin_mode=cast(Any, str(row["margin_mode"])),
                                leverage=int(row["leverage"]),
                                maintenance_margin_rate=Decimal(
                                    str(row["maintenance_margin_rate"])
                                ),
                            )
                        )
                        is not None
                        else None
                    ),
                    leverage=int(row["leverage"]),
                )
            )
        signed_quantity = futures.long.quantity - futures.short.quantity
        average_entry = (
            futures.long.average_entry if futures.long.quantity else futures.short.average_entry
        )
        margin_balance = futures.wallet_balance + unrealized
        return ExecutionSnapshot(
            plan=plan,
            orders=orders,
            fills=fills,
            portfolio=PortfolioState(
                cash=decimal_text(futures.wallet_balance),
                position_quantity=decimal_text(signed_quantity),
                average_entry_price=decimal_text(average_entry),
                realized_pnl=decimal_text(futures.realized_pnl),
                fees_paid=decimal_text(futures.fees),
                account_type="USDT_PERPETUAL",
                wallet_balance=decimal_text(futures.wallet_balance),
                available_balance=decimal_text(
                    max(Decimal("0"), futures.wallet_balance - used_margin)
                ),
                margin_balance=decimal_text(margin_balance),
                used_initial_margin=decimal_text(used_margin),
                maintenance_margin=decimal_text(maintenance),
                unrealized_pnl=decimal_text(unrealized),
                funding_paid=decimal_text(futures.funding_paid),
                liquidated=futures.liquidated,
                positions=positions,
            ),
        )
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
            account_type="SPOT",
            wallet_balance=decimal_text(state.cash),
            available_balance=decimal_text(state.cash),
            margin_balance=decimal_text(state.cash),
        ),
    )
