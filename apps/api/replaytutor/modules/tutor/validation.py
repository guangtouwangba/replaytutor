from __future__ import annotations

import re

from replaytutor.contracts import TutorResponse


class TutorValidationError(ValueError):
    pass


_DRAWING_RULES = {
    "trend_line": ("line", {"trend"}, 2),
    "horizontal_line": ("line", {"support", "resistance"}, 1),
    "parallel_channel": ("zone", {"channel"}, 3),
    "zone": ("zone", {"support", "resistance"}, 2),
}

_DRAWING_ACTION_RE = re.compile(
    r"(?:画|绘制|标出|标记|添加|加上|显示|draw|plot|mark|add|show)",
    re.IGNORECASE,
)
_DRAWING_TARGET_RE = re.compile(
    r"(?:趋势线|支撑|压力|阻力|通道|区域|水平线|trend\s*line|support|resistance|channel|zone)",
    re.IGNORECASE,
)


def is_explicit_drawing_request(question: str) -> bool:
    """Require both a drawing action and a supported technical-analysis target."""

    return bool(_DRAWING_ACTION_RE.search(question) and _DRAWING_TARGET_RE.search(question))


def sanitize_chart_instructions(
    response: TutorResponse,
    context: dict[str, object],
) -> TutorResponse:
    """Keep only drawings anchored to exact visible OHLC evidence."""

    timeframe = str(context.get("analysis_timeframe", "1m"))
    question = str(context.get("question", ""))
    locale = str(context.get("locale", "en-US"))
    if response.annotations and not is_explicit_drawing_request(question):
        risks = list(response.risks_and_unknowns)
        risks.append(
            f"宿主已删除 {len(response.annotations)} 个未经用户明确请求的 AI 绘图对象。"
            if locale == "zh-CN"
            else (
                f"The host removed {len(response.annotations)} AI drawing object(s) "
                "because the user did not explicitly request drawing."
            )
        )
        return response.model_copy(
            update={"annotations": [], "risks_and_unknowns": risks}
        )
    raw_bars = context.get("visible_bars", [])
    bars = raw_bars if isinstance(raw_bars, list) else []
    by_time = {
        str(bar["close_time"]): bar
        for bar in bars
        if isinstance(bar, dict) and "close_time" in bar
    }
    visible_bar_ids = {
        str(bar["bar_id"])
        for bar in bars
        if isinstance(bar, dict) and "bar_id" in bar
    }
    accepted = []
    removed = 0
    for instruction in response.annotations:
        rule = _DRAWING_RULES.get(instruction.tool)
        valid = rule is not None and instruction.timeframe == timeframe
        valid = (
            valid
            and bool(instruction.evidence_ids)
            and set(instruction.evidence_ids) <= visible_bar_ids
        )
        if rule is not None:
            shape, purposes, point_count = rule
            valid = valid and instruction.shape == shape
            valid = valid and instruction.purpose in purposes
            valid = valid and len(instruction.points) == point_count
        for point in instruction.points:
            point_json = point.model_dump(mode="json")
            bar = by_time.get(str(point_json["time"]))
            if bar is None:
                valid = False
                continue
            raw = bar.get("raw", {}) if isinstance(bar, dict) else {}
            ohlc = {str(raw.get(key)) for key in ("open", "high", "low", "close")}
            if point.price not in ohlc or str(bar.get("bar_id")) not in instruction.evidence_ids:
                valid = False
        if valid:
            accepted.append(instruction)
        else:
            removed += 1
    risks = list(response.risks_and_unknowns)
    if removed:
        risks.append(
            f"宿主已删除 {removed} 个未通过当前周期可见 OHLC 与证据校验的 AI 绘图对象。"
            if locale == "zh-CN"
            else (
                f"The host removed {removed} AI drawing object(s) that failed visible "
                "OHLC and evidence validation for the active timeframe."
            )
        )
    return response.model_copy(
        update={"annotations": accepted, "risks_and_unknowns": risks}
    )


def strict_output_schema(value: object) -> object:
    if isinstance(value, list):
        return [strict_output_schema(item) for item in value]
    if not isinstance(value, dict):
        return value
    transformed = {key: strict_output_schema(item) for key, item in value.items()}
    properties = transformed.get("properties")
    if isinstance(properties, dict):
        transformed["required"] = list(properties)
        transformed["additionalProperties"] = False
    return transformed


def validate_evidence(response: TutorResponse, allowed: set[str]) -> TutorResponse:
    referenced: set[str] = set()
    for item in response.observations:
        referenced.update(item.evidence_ids)
    for item in response.inferences:
        referenced.update(item.evidence_ids)
    for item in response.rule_checks:
        referenced.update(item.evidence_ids)
    for item in response.annotations:
        referenced.update(item.evidence_ids)
    invalid = referenced - allowed
    if invalid:
        raise TutorValidationError(
            f"Tutor referenced evidence outside the current frame: {sorted(invalid)}"
        )
    return response


def sanitize_evidence(response: TutorResponse, allowed: set[str]) -> TutorResponse:
    """Remove model-mistyped references while preserving valid, auditable analysis."""

    invalid: set[str] = set()

    def valid_ids(evidence_ids: list[str]) -> list[str]:
        invalid.update(set(evidence_ids) - allowed)
        return [evidence_id for evidence_id in evidence_ids if evidence_id in allowed]

    observations = [
        item.model_copy(update={"evidence_ids": valid_ids(item.evidence_ids)})
        for item in response.observations
    ]
    inferences = [
        item.model_copy(update={"evidence_ids": valid_ids(item.evidence_ids)})
        for item in response.inferences
    ]
    rule_checks = [
        item.model_copy(update={"evidence_ids": valid_ids(item.evidence_ids)})
        for item in response.rule_checks
    ]
    annotations = []
    for item in response.annotations:
        evidence_ids = valid_ids(item.evidence_ids)
        if item.evidence_ids and not evidence_ids:
            continue
        annotations.append(item.model_copy(update={"evidence_ids": evidence_ids}))
    risks = list(response.risks_and_unknowns)
    if invalid:
        risks.append(
            f"宿主已删除 {len(invalid)} 个不在当前 frame 白名单中的 AI 证据引用。"
        )
    return response.model_copy(
        update={
            "observations": observations,
            "inferences": inferences,
            "rule_checks": rule_checks,
            "annotations": annotations,
            "risks_and_unknowns": risks,
        }
    )
