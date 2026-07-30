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
