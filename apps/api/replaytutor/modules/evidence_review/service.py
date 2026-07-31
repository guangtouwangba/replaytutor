from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, Literal, cast

from replaytutor.config import Settings
from replaytutor.contracts import (
    AnnotationDisposition,
    CapabilityDimension,
    EvidenceRef,
    ReviewMetric,
    TrainingReview,
    TrainingReviewListResponse,
)
from replaytutor.ids import new_id
from replaytutor.modules.annotations import load_dispositions
from replaytutor.modules.execution.service import load_execution
from replaytutor.modules.market_data.service import MarketDataService, utc_text
from replaytutor.modules.playbook import PlaybookEvaluator
from replaytutor.modules.training_session.service import (
    InvalidSessionStateError,
    SessionNotFoundError,
)
from replaytutor.storage.database import connect_database


def text(value: Decimal) -> str:
    rendered = format(value, "f")
    return rendered.rstrip("0").rstrip(".") if "." in rendered else rendered


class EvidenceReviewService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.market_data = MarketDataService(settings)

    def get(self, session_id: str) -> TrainingReview:
        with connect_database(self.settings.database_path) as connection:
            stored = connection.execute(
                "SELECT payload_json FROM training_review WHERE session_id = ?",
                (session_id,),
            ).fetchone()
            if stored is not None:
                return TrainingReview.model_validate_json(stored["payload_json"])
            row = connection.execute(
                "SELECT * FROM replay_session WHERE session_id = ?",
                (session_id,),
            ).fetchone()
            if row is None:
                raise SessionNotFoundError("Session not found")
            values = dict(row)
            if str(values["status"]) != "completed":
                raise InvalidSessionStateError(
                    "Deterministic review is available only after session completion"
                )
            execution = load_execution(connection, values)
            final_bar = self.market_data.query_snapshot_bar_slice(
                str(values["snapshot_id"]),
                offset=int(values["current_index"]),
                limit=1,
            )[0]
            cash = Decimal(execution.portfolio.cash)
            quantity = Decimal(execution.portfolio.position_quantity)
            ending_equity = cash + quantity * Decimal(final_bar.raw.close)
            initial_cash = Decimal(str(values["initial_cash"]))
            net_pnl = ending_equity - initial_cash
            realized = Decimal(execution.portfolio.realized_pnl)
            fees = Decimal(execution.portfolio.fees_paid)
            sells = [fill for fill in execution.fills if fill.side == "SELL"]
            wins = sum(
                Decimal(fill.price) > Decimal(execution.portfolio.average_entry_price or "0")
                for fill in sells
            )
            win_rate = Decimal(wins) / Decimal(len(sells)) * 100 if sells else Decimal("0")
            excursion = self._excursion_metrics(values, execution)
            metrics = [
                ReviewMetric(
                    key="net_pnl",
                    label="净收益",
                    value=text(net_pnl),
                    unit=values.get("quote_currency") or "USDT",
                ),
                ReviewMetric(
                    key="realized_pnl", label="已实现收益", value=text(realized), unit="USDT"
                ),
                ReviewMetric(key="fees", label="手续费", value=text(fees), unit="USDT"),
                ReviewMetric(
                    key="ending_equity", label="结束权益", value=text(ending_equity), unit="USDT"
                ),
                ReviewMetric(key="trade_count", label="成交数", value=str(len(execution.fills))),
                ReviewMetric(key="win_rate", label="胜率", value=text(win_rate), unit="%"),
                ReviewMetric(
                    key="mfe",
                    label="最大有利波动",
                    value=text(excursion["mfe"]),
                    unit="USDT",
                ),
                ReviewMetric(
                    key="mae",
                    label="最大不利波动",
                    value=text(excursion["mae"]),
                    unit="USDT",
                ),
                ReviewMetric(
                    key="r_multiple",
                    label="R 倍数",
                    value=text(
                        net_pnl / Decimal(execution.plan.risk_amount)
                        if execution.plan is not None and Decimal(execution.plan.risk_amount) > 0
                        else Decimal("0")
                    ),
                    unit="R",
                ),
                ReviewMetric(
                    key="max_drawdown",
                    label="最大回撤",
                    value=text(excursion["max_drawdown"]),
                    unit="USDT",
                ),
                ReviewMetric(
                    key="exit_efficiency",
                    label="退出效率",
                    value=text(excursion["exit_efficiency"]),
                    unit="%",
                ),
            ]
            evidence = self._evidence(
                execution,
                load_dispositions(connection, session_id),
            )
            playbook_evaluation = PlaybookEvaluator(self.settings).evaluate(session_id)
            good_process = execution.plan is not None
            if not execution.fills:
                outcome: Literal[
                    "good_process_profit",
                    "good_process_loss",
                    "bad_process_profit",
                    "bad_process_loss",
                    "insufficient_evidence",
                ] = "insufficient_evidence"
            elif good_process and net_pnl >= 0:
                outcome = "good_process_profit"
            elif good_process:
                outcome = "good_process_loss"
            elif net_pnl >= 0:
                outcome = "bad_process_profit"
            else:
                outcome = "bad_process_loss"
            findings = [
                "交易前已锁定计划。" if good_process else "没有可验证的锁定计划。",
                f"共提交 {len(execution.orders)} 个订单, 产生 {len(execution.fills)} 笔成交。",
                "结果与过程分开评价; 盈亏不会覆盖计划纪律判断。",
            ]
            canonical: dict[str, Any] = {
                "session_id": session_id,
                "outcome": outcome,
                "metrics": [item.model_dump(mode="json") for item in metrics],
                "evidence": [item.model_dump(mode="json") for item in evidence],
                "playbook_id": playbook_evaluation.playbook_id,
                "playbook_evaluator_version": playbook_evaluation.evaluator_version,
                "rule_checks": [
                    item.model_dump(mode="json") for item in playbook_evaluation.checks
                ],
                "findings": findings,
            }
            review_hash = hashlib.sha256(
                json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest()
            now = datetime.now(UTC)
            review = TrainingReview(
                review_id=new_id("rev"),
                session_id=session_id,
                review_hash=review_hash,
                process_outcome=outcome,
                playbook_id=playbook_evaluation.playbook_id,
                playbook_evaluator_version=playbook_evaluation.evaluator_version,
                metrics=metrics,
                evidence=evidence,
                rule_checks=playbook_evaluation.checks,
                findings=findings,
                created_at=now,
            )
            connection.execute(
                """INSERT INTO training_review (
                    review_id, session_id, review_hash, payload_json, created_at
                ) VALUES (?, ?, ?, ?, ?)""",
                (
                    review.review_id,
                    session_id,
                    review_hash,
                    review.model_dump_json(),
                    utc_text(now),
                ),
            )
            return review

    def list(self) -> TrainingReviewListResponse:
        with connect_database(self.settings.database_path) as connection:
            rows = connection.execute(
                """
                SELECT session_id FROM replay_session
                WHERE status = 'completed'
                ORDER BY completed_at DESC, created_at DESC
                """
            ).fetchall()
        reviews = [self.get(str(row["session_id"])) for row in rows]
        sample_count = len(reviews)
        dimensions = [
            CapabilityDimension(
                key=cast(
                    Literal["environment", "plan", "risk", "execution", "management"],
                    key,
                ),
                label=label,
                sample_count=sample_count,
                status="insufficient",
                score=None,
            )
            for key, label in (
                ("environment", "环境识别"),
                ("plan", "计划纪律"),
                ("risk", "风险控制"),
                ("execution", "执行质量"),
                ("management", "持仓管理"),
            )
        ]
        return TrainingReviewListResponse(
            reviews=reviews,
            dimensions=dimensions,
        )

    def _excursion_metrics(
        self,
        session: dict[str, Any],
        execution: Any,
    ) -> dict[str, Decimal]:
        bars = self.market_data.query_snapshot_bar_slice(
            str(session["snapshot_id"]),
            offset=int(session["start_index"]),
            limit=int(session["current_index"]) - int(session["start_index"]) + 1,
        )
        fills = sorted(execution.fills, key=lambda item: item.executed_at)
        buys = [fill for fill in fills if fill.side == "BUY"]
        if not buys or not bars:
            return {
                "mfe": Decimal("0"),
                "mae": Decimal("0"),
                "max_drawdown": Decimal("0"),
                "exit_efficiency": Decimal("0"),
            }

        buy_quantity = sum((Decimal(fill.quantity) for fill in buys), Decimal("0"))
        entry_price = (
            sum(
                (Decimal(fill.price) * Decimal(fill.quantity) for fill in buys),
                Decimal("0"),
            )
            / buy_quantity
        )
        first_entry_at = min(fill.executed_at for fill in buys)
        active_bars = [bar for bar in bars if bar.close_time >= first_entry_at]
        if not active_bars:
            active_bars = [bars[-1]]
        max_high = max(Decimal(bar.raw.high) for bar in active_bars)
        min_low = min(Decimal(bar.raw.low) for bar in active_bars)
        mfe = max(Decimal("0"), (max_high - entry_price) * buy_quantity)
        mae = min(Decimal("0"), (min_low - entry_price) * buy_quantity)

        cash = Decimal(str(session["initial_cash"]))
        position = Decimal("0")
        fill_index = 0
        peak = cash
        max_drawdown = Decimal("0")
        for bar in bars:
            while fill_index < len(fills) and fills[fill_index].executed_at <= bar.close_time:
                fill = fills[fill_index]
                quantity = Decimal(fill.quantity)
                quote = Decimal(fill.quote_amount)
                fee = Decimal(fill.fee)
                if fill.side == "BUY":
                    cash -= quote + fee
                    position += quantity
                else:
                    cash += quote - fee
                    position -= quantity
                fill_index += 1
            equity = cash + position * Decimal(bar.raw.close)
            peak = max(peak, equity)
            max_drawdown = max(max_drawdown, peak - equity)

        sells = [fill for fill in fills if fill.side == "SELL"]
        if sells:
            sold_quantity = sum(
                (Decimal(fill.quantity) for fill in sells),
                Decimal("0"),
            )
            exit_price = (
                sum(
                    (Decimal(fill.price) * Decimal(fill.quantity) for fill in sells),
                    Decimal("0"),
                )
                / sold_quantity
            )
        else:
            exit_price = Decimal(bars[-1].raw.close)
        favorable_price_move = max_high - entry_price
        captured = exit_price - entry_price
        exit_efficiency = (
            captured / favorable_price_move * Decimal("100")
            if favorable_price_move > 0
            else Decimal("0")
        )
        return {
            "mfe": mfe,
            "mae": mae,
            "max_drawdown": max_drawdown,
            "exit_efficiency": exit_efficiency,
        }

    @staticmethod
    def _evidence(
        execution: Any,
        dispositions: list[AnnotationDisposition],
    ) -> list[EvidenceRef]:
        refs: list[EvidenceRef] = []
        if execution.plan is not None:
            refs.append(
                EvidenceRef(
                    evidence_id=execution.plan.plan_id,
                    kind="plan",
                    summary=execution.plan.thesis,
                    frame_id=execution.plan.frame_id,
                    occurred_at=execution.plan.created_at,
                )
            )
        refs.extend(
            EvidenceRef(
                evidence_id=order.order_id,
                kind="order",
                summary=f"{order.side} {order.order_type} {order.quantity}",
                frame_id=order.submitted_frame_id,
                occurred_at=order.submitted_at,
                price=order.limit_price or order.stop_price,
            )
            for order in execution.orders
        )
        refs.extend(
            EvidenceRef(
                evidence_id=fill.fill_id,
                kind="fill",
                summary=f"{fill.side} {fill.quantity} @ {fill.price}",
                frame_id=fill.frame_id,
                occurred_at=fill.executed_at,
                price=fill.price,
            )
            for fill in execution.fills
        )
        refs.extend(
            EvidenceRef(
                evidence_id=item.annotation_id,
                kind=(
                    "user_annotation"
                    if item.original_annotation.layer == "user"
                    else "ai_annotation"
                ),
                summary=f"{item.state}: {item.effective_label}",
                frame_id=item.original_annotation.frame_id,
                occurred_at=item.effective_points[0].time,
                price=item.effective_points[0].price,
            )
            for item in dispositions
        )
        return refs
