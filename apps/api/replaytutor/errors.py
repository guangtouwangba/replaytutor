from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from replaytutor.contracts import ErrorDetail, ErrorEnvelope


class ApiError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        status_code: int = 400,
        retryable: bool = False,
        details: dict[str, object] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.retryable = retryable
        self.details = details or {}


def request_id(request: Request) -> str:
    return str(getattr(request.state, "request_id", "unknown"))


def error_response(
    request: Request,
    *,
    status_code: int,
    code: str,
    message: str,
    retryable: bool = False,
    details: dict[str, object] | None = None,
) -> JSONResponse:
    payload = ErrorEnvelope(
        error=ErrorDetail(
            code=code,
            message=message,
            retryable=retryable,
            request_id=request_id(request),
            details=details or {},
        )
    )
    return JSONResponse(status_code=status_code, content=payload.model_dump(mode="json"))


def install_exception_handlers(app: FastAPI) -> None:
    async def handle_api_error(request: Request, exc: Exception) -> JSONResponse:
        assert isinstance(exc, ApiError)
        return error_response(
            request,
            status_code=exc.status_code,
            code=exc.code,
            message=exc.message,
            retryable=exc.retryable,
            details=exc.details,
        )

    async def handle_http_error(request: Request, exc: Exception) -> JSONResponse:
        assert isinstance(exc, StarletteHTTPException)
        code = "not_found" if exc.status_code == 404 else "http_error"
        return error_response(
            request,
            status_code=exc.status_code,
            code=code,
            message=str(exc.detail),
        )

    async def handle_validation_error(request: Request, exc: Exception) -> JSONResponse:
        assert isinstance(exc, RequestValidationError)
        return error_response(
            request,
            status_code=422,
            code="validation_error",
            message="Request validation failed",
            details={"errors": exc.errors()},
        )

    async def handle_unexpected_error(request: Request, _exc: Exception) -> JSONResponse:
        return error_response(
            request,
            status_code=500,
            code="internal_error",
            message="An unexpected error occurred",
            retryable=True,
        )

    handlers: list[tuple[type[Exception], Callable[[Request, Any], Awaitable[JSONResponse]]]] = [
        (ApiError, handle_api_error),
        (StarletteHTTPException, handle_http_error),
        (RequestValidationError, handle_validation_error),
        (Exception, handle_unexpected_error),
    ]
    for exception_type, handler in handlers:
        app.add_exception_handler(exception_type, handler)
