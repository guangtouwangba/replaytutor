from __future__ import annotations

import sqlite3
from collections.abc import Callable
from decimal import Decimal, InvalidOperation
from typing import Any

from replaytutor.config import Settings
from replaytutor.contracts import (
    ExecutionSnapshot,
    PlaybookEvaluation,
    PlaybookRuleCheck,
    PlaybookRuleDefinition,
)
from replaytutor.modules.execution.service import load_execution
from replaytutor.modules.playbook.service import PlaybookService
from replaytutor.modules.training_session.service import SessionNotFoundError, parse_utc
from replaytutor.storage.database import connect_database


class PlaybookEvaluator:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def evaluate(self, session_id: str) -> PlaybookEvaluation:
        service = PlaybookService(self.settings)
        service._seed()
        with connect_database(self.settings.database_path) as connection:
            session_row = connection.execute(
                "SELECT * FROM replay_session WHERE session_id = ?",
                (session_id,),
            ).fetchone()
            if session_row is None:
                raise SessionNotFoundError("Session not found")
            session = dict(session_row)
            playbook_id = session.get("playbook_id")
            if playbook_id is None:
                return PlaybookEvaluation(
                    playbook_id=None,
                    evaluator_version="none",
                    checks=[],
                )
            playbook_row = connection.execute(
                "SELECT * FROM playbook_version WHERE playbook_id = ?",
                (str(playbook_id),),
            ).fetchone()
            if playbook_row is None:
                raise SessionNotFoundError("Bound Playbook version not found")
            playbook = service._from_row(playbook_row)
            execution = load_execution(connection, session)
            registry: dict[str, Callable[[PlaybookRuleDefinition], PlaybookRuleCheck]] = {
                "plan_locked_before_first_order": lambda definition: self._plan_before_order(
                    definition, execution
                ),
                "order_activated_on_next_bar": lambda definition: self._next_bar(
                    definition, execution, connection
                ),
                "risk_amount_within_limit": lambda definition: self._risk_limit(
                    definition, execution
                ),
                "protective_stop_present": lambda definition: self._protective_stop(
                    definition, execution
                ),
                "no_order_after_session_complete": lambda definition: self._no_late_order(
                    definition, execution, session
                ),
                "entry_side_matches_locked_plan": lambda definition: self._side_matches(
                    definition, execution
                ),
            }
            checks = []
            for definition in playbook.rule_definitions:
                evaluator = registry.get(definition.evaluator_kind)
                checks.append(
                    evaluator(definition)
                    if evaluator is not None
                    else self._unknown(
                        definition,
                        "unmapped_rule",
                        "自由文本或未知规则没有确定性映射。",
                    )
                )
            return PlaybookEvaluation(
                playbook_id=playbook.playbook_id,
                evaluator_version=playbook.evaluator_version,
                checks=checks,
            )

    @staticmethod
    def _check(
        definition: PlaybookRuleDefinition,
        *,
        passed: bool,
        reason_code: str,
        summary: str,
        evidence_ids: list[str],
    ) -> PlaybookRuleCheck:
        if not evidence_ids:
            return PlaybookEvaluator._unknown(
                definition,
                "insufficient_evidence",
                "没有足够证据执行该规则。",
            )
        return PlaybookRuleCheck(
            rule_id=definition.rule_id,
            status="passed" if passed else "failed",
            reason_code=reason_code,
            summary=summary,
            evidence_ids=evidence_ids,
        )

    @staticmethod
    def _unknown(
        definition: PlaybookRuleDefinition,
        reason_code: str,
        summary: str,
    ) -> PlaybookRuleCheck:
        return PlaybookRuleCheck(
            rule_id=definition.rule_id,
            status="unknown",
            reason_code=reason_code,
            summary=summary,
            evidence_ids=[],
        )

    def _plan_before_order(
        self,
        definition: PlaybookRuleDefinition,
        execution: ExecutionSnapshot,
    ) -> PlaybookRuleCheck:
        parent_orders = [order for order in execution.orders if order.parent_order_id is None]
        if execution.plan is None or not parent_orders:
            return self._unknown(
                definition,
                "plan_or_order_missing",
                "需要计划和至少一个入场订单才能判断。",
            )
        first_order = min(parent_orders, key=lambda order: order.submitted_at)
        passed = execution.plan.created_at <= first_order.submitted_at
        return self._check(
            definition,
            passed=passed,
            reason_code="plan_precedes_first_order" if passed else "plan_after_first_order",
            summary="计划在首笔订单前锁定。" if passed else "计划未在首笔订单前锁定。",
            evidence_ids=[execution.plan.plan_id, first_order.order_id],
        )

    def _next_bar(
        self,
        definition: PlaybookRuleDefinition,
        execution: ExecutionSnapshot,
        connection: sqlite3.Connection,
    ) -> PlaybookRuleCheck:
        parent_orders = [order for order in execution.orders if order.parent_order_id is None]
        if not parent_orders:
            return self._unknown(
                definition,
                "orders_missing",
                "没有入场订单可检查激活时点。",
            )
        passed = True
        for order in parent_orders:
            frame = connection.execute(
                "SELECT current_index FROM replay_frame WHERE frame_id = ?",
                (order.submitted_frame_id,),
            ).fetchone()
            if frame is None or order.activate_index != int(frame["current_index"]) + 1:
                passed = False
                break
        return self._check(
            definition,
            passed=passed,
            reason_code="next_bar_activation" if passed else "invalid_activation_index",
            summary="所有入场订单均在提交后的下一根激活。"
            if passed
            else "至少一个入场订单没有在下一根激活。",
            evidence_ids=[order.order_id for order in parent_orders],
        )

    def _risk_limit(
        self,
        definition: PlaybookRuleDefinition,
        execution: ExecutionSnapshot,
    ) -> PlaybookRuleCheck:
        if execution.plan is None:
            return self._unknown(
                definition,
                "plan_missing",
                "没有锁定计划, 无法检查风险金额。",
            )
        try:
            limit = Decimal(definition.params.get("max_risk_amount", "0"))
        except InvalidOperation:
            return self._unknown(
                definition,
                "invalid_rule_params",
                "规则风险上限参数无效。",
            )
        passed = limit > 0 and Decimal(execution.plan.risk_amount) <= limit
        return self._check(
            definition,
            passed=passed,
            reason_code="risk_within_limit" if passed else "risk_exceeds_limit",
            summary=(
                f"计划风险 {execution.plan.risk_amount} 未超过上限 {limit}。"
                if passed
                else f"计划风险 {execution.plan.risk_amount} 超过上限 {limit}。"
            ),
            evidence_ids=[execution.plan.plan_id],
        )

    def _protective_stop(
        self,
        definition: PlaybookRuleDefinition,
        execution: ExecutionSnapshot,
    ) -> PlaybookRuleCheck:
        parent_orders = [order for order in execution.orders if order.parent_order_id is None]
        if not parent_orders:
            return self._unknown(
                definition,
                "orders_missing",
                "没有入场订单可检查保护止损。",
            )
        stop_parents = {
            order.parent_order_id
            for order in execution.orders
            if order.parent_order_id is not None and order.order_type == "STOP_MARKET"
        }
        passed = all(order.order_id in stop_parents for order in parent_orders)
        evidence = [order.order_id for order in parent_orders]
        evidence.extend(
            order.order_id
            for order in execution.orders
            if order.parent_order_id in {parent.order_id for parent in parent_orders}
            and order.order_type == "STOP_MARKET"
        )
        return self._check(
            definition,
            passed=passed,
            reason_code="protective_stop_present" if passed else "protective_stop_missing",
            summary="每个入场订单都有保护止损。" if passed else "至少一个入场订单没有保护止损。",
            evidence_ids=evidence,
        )

    def _no_late_order(
        self,
        definition: PlaybookRuleDefinition,
        execution: ExecutionSnapshot,
        session: dict[str, Any],
    ) -> PlaybookRuleCheck:
        if str(session["status"]) != "completed":
            return self._unknown(
                definition,
                "session_active",
                "会话尚未完成, 不能做最终检查。",
            )
        if not execution.orders:
            return self._unknown(
                definition,
                "orders_missing",
                "没有订单证据可检查。",
            )
        completed_at = parse_utc(str(session["completed_at"]))
        passed = all(order.submitted_at <= completed_at for order in execution.orders)
        return self._check(
            definition,
            passed=passed,
            reason_code="no_late_order" if passed else "order_after_completion",
            summary="会话完成后没有新增订单。" if passed else "发现会话完成后的订单。",
            evidence_ids=[order.order_id for order in execution.orders],
        )

    def _side_matches(
        self,
        definition: PlaybookRuleDefinition,
        execution: ExecutionSnapshot,
    ) -> PlaybookRuleCheck:
        parent_orders = [order for order in execution.orders if order.parent_order_id is None]
        if execution.plan is None or not parent_orders:
            return self._unknown(
                definition,
                "plan_or_order_missing",
                "需要计划和入场订单才能检查方向。",
            )
        passed = all(order.side == execution.plan.side for order in parent_orders)
        return self._check(
            definition,
            passed=passed,
            reason_code="entry_side_matches" if passed else "entry_side_mismatch",
            summary="入场方向与计划一致。" if passed else "入场方向与计划不一致。",
            evidence_ids=[
                execution.plan.plan_id,
                *[order.order_id for order in parent_orders],
            ],
        )
