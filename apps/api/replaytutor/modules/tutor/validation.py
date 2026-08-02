from __future__ import annotations

from replaytutor.contracts import TutorResponse


class TutorValidationError(ValueError):
    pass


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
