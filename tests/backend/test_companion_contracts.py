from __future__ import annotations

import pytest
from pydantic import ValidationError

from replaytutor.contracts import (
    CompanionError,
    CompanionRequest,
    CompanionResponse,
    CompanionSessionListParams,
)


def test_companion_request_forbids_unknown_methods_and_extra_fields() -> None:
    with pytest.raises(ValidationError):
        CompanionRequest.model_validate(
            {
                "protocol_version": "1.0",
                "request_id": "req_contract-0001",
                "method": "orders.submit",
                "params": {},
            }
        )

    with pytest.raises(ValidationError):
        CompanionRequest.model_validate(
            {
                "protocol_version": "1.0",
                "request_id": "req_contract-0002",
                "method": "system.health",
                "params": {},
                "url": "http://127.0.0.1:8788/api/v1/orders",
            }
        )


def test_companion_list_limit_is_bounded() -> None:
    assert CompanionSessionListParams().limit == 50
    with pytest.raises(ValidationError):
        CompanionSessionListParams(limit=51)


def test_companion_response_requires_exactly_one_outcome() -> None:
    success = CompanionResponse(
        request_id="req_contract-0003",
        ok=True,
        result={"status": "ready"},
    )
    assert success.error is None

    failure = CompanionResponse(
        request_id="req_contract-0004",
        ok=False,
        error=CompanionError(code="method_not_allowed", message="Method is not allowed"),
    )
    assert failure.result is None

    with pytest.raises(ValidationError):
        CompanionResponse(request_id="req_contract-0005", ok=True)
