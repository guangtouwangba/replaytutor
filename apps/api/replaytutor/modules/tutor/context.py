from __future__ import annotations

from typing import Any

from replaytutor.contracts import (
    PlaybookEvaluation,
    SessionDelta,
    TrainingReview,
    TutorRequest,
)


def build_tutor_context(
    delta: SessionDelta,
    request: TutorRequest,
    review: TrainingReview | None = None,
    playbook_evaluation: PlaybookEvaluation | None = None,
) -> tuple[dict[str, Any], set[str]]:
    evidence_ids = {bar.bar_id for bar in delta.bars}
    execution = delta.execution
    if execution is not None:
        if execution.plan is not None:
            evidence_ids.add(execution.plan.plan_id)
        evidence_ids.update(order.order_id for order in execution.orders)
        evidence_ids.update(fill.fill_id for fill in execution.fills)
    if review is not None:
        evidence_ids.update(item.evidence_id for item in review.evidence)
    if playbook_evaluation is not None:
        for check in playbook_evaluation.checks:
            evidence_ids.update(check.evidence_ids)
    after_action = request.stage == "after_action"
    context = {
        "schema_version": "1.0",
        "perspective": "after_action" if after_action else "in_replay",
        "frame_id": delta.session.frame.frame_id,
        "visible_at": delta.session.frame.model_dump(mode="json")["visible_at"],
        "stage": request.stage,
        "question": request.question,
        "instrument": delta.session.instrument.model_dump(mode="json"),
        "visible_bars": [bar.model_dump(mode="json") for bar in delta.bars],
        "account_state": (
            execution.portfolio.model_dump(mode="json") if execution is not None else None
        ),
        "plan": (
            execution.plan.model_dump(mode="json")
            if execution is not None and execution.plan is not None
            else None
        ),
        "orders": (
            [order.model_dump(mode="json") for order in execution.orders]
            if execution is not None
            else []
        ),
        "executions": (
            [fill.model_dump(mode="json") for fill in execution.fills]
            if execution is not None
            else []
        ),
        "deterministic_review": (review.model_dump(mode="json") if review is not None else None),
        "deterministic_rule_checks": (
            playbook_evaluation.model_dump(mode="json") if playbook_evaluation is not None else None
        ),
        "allowed_evidence_ids": sorted(evidence_ids),
        "forbidden_fields": (
            []
            if after_action
            else [
                "future_bars",
                "final_pnl",
                "mfe",
                "mae",
                "later_orders",
                "later_fills",
            ]
        ),
    }
    return context, evidence_ids
