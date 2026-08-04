from __future__ import annotations

import json
import re
from collections.abc import Callable
from typing import get_args
from urllib.parse import urlencode

from pydantic import BaseModel, ValidationError

from replaytutor import __version__
from replaytutor.config import Settings
from replaytutor.contracts import (
    CompanionAgentResult,
    CompanionBootstrapParams,
    CompanionBootstrapResult,
    CompanionEmptyParams,
    CompanionError,
    CompanionErrorCode,
    CompanionEvidenceParams,
    CompanionHealthResult,
    CompanionMethod,
    CompanionNavigationParams,
    CompanionNavigationTarget,
    CompanionRequest,
    CompanionResponse,
    CompanionRunParams,
    CompanionRunStartParams,
    CompanionSessionListParams,
    CompanionSessionListResult,
    CompanionSessionParams,
    CompanionSessionStateResult,
    CompanionSessionSummary,
    CompanionThreadCreateParams,
    CompanionThreadListParams,
    CompanionThreadParams,
    ReplaySession,
)
from replaytutor.modules.evidence_review import EvidenceResolver
from replaytutor.modules.market_data.service import MarketDataError
from replaytutor.modules.training_session.service import (
    SessionNotFoundError,
    TrainingSessionError,
    TrainingSessionService,
)
from replaytutor.modules.tutor import TutorRuntime
from replaytutor.modules.tutor.capabilities import discover_codex_capability
from replaytutor.modules.tutor.runtime import TutorRunNotFoundError, TutorThreadNotFoundError
from replaytutor.runtime import is_writable
from replaytutor.storage.database import inspect_database

PROTOCOL_VERSION = "1.0"
MAX_MESSAGE_BYTES = 512 * 1024
SAFE_REQUEST_ID = re.compile(r"^req_[A-Za-z0-9-]{4,124}$")
ALLOWED_METHODS = frozenset(get_args(CompanionMethod))


class CompanionFacade:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.sessions = TrainingSessionService(settings)
        self.tutor = TutorRuntime(settings)
        self.evidence = EvidenceResolver(settings)

    def dispatch(self, payload: dict[str, object]) -> CompanionResponse:
        request_id = self._request_id(payload)
        if len(json.dumps(payload, ensure_ascii=False).encode("utf-8")) > MAX_MESSAGE_BYTES:
            return self._failure(
                request_id,
                "payload_too_large",
                "Companion payload exceeds 512 KiB",
            )
        if payload.get("protocol_version") != PROTOCOL_VERSION:
            return self._failure(
                request_id,
                "protocol_incompatible",
                "Companion protocol version is not supported",
            )
        method = payload.get("method")
        if method not in ALLOWED_METHODS:
            return self._failure(
                request_id,
                "method_not_allowed",
                "Companion method is not allowed",
            )
        try:
            request = CompanionRequest.model_validate(payload)
            result = self._execute(request)
            return CompanionResponse(
                request_id=request.request_id,
                ok=True,
                result=result.model_dump(mode="json"),
            )
        except ValidationError:
            return self._failure(
                request_id,
                "payload_invalid",
                "Companion payload failed schema validation",
            )
        except SessionNotFoundError:
            code = "evidence_not_found" if method == "evidence.resolve" else "session_not_found"
            return self._failure(request_id, code, "Requested ReplayTutor resource was not found")
        except TutorThreadNotFoundError:
            return self._failure(request_id, "payload_invalid", "Tutor thread was not found")
        except TutorRunNotFoundError:
            return self._failure(request_id, "run_failed", "Tutor run was not found")
        except ValueError as error:
            message = str(error).lower()
            if "disabled" in message:
                return self._failure(request_id, "tutor_disabled", "Codex Tutor is disabled")
            if "running" in message:
                return self._failure(
                    request_id,
                    "run_conflict",
                    "Tutor conversation already has a running request",
                    retryable=True,
                )
            return self._failure(request_id, "payload_invalid", "Companion request is invalid")
        except (TrainingSessionError, MarketDataError):
            return self._failure(
                request_id,
                "session_not_found",
                "ReplayTutor session is unavailable",
            )
        except Exception:
            return self._failure(
                request_id,
                "internal_error",
                "ReplayTutor could not complete the companion request",
                retryable=True,
            )

    def _execute(self, request: CompanionRequest) -> BaseModel:
        handlers: dict[str, Callable[[dict[str, object]], BaseModel]] = {
            "system.bootstrap": self._bootstrap,
            "system.health": self._health,
            "agent.codex.discover": self._discover_codex,
            "session.list": self._list_sessions,
            "session.get": self._get_session,
            "tutor.thread.list": self._list_threads,
            "tutor.thread.create": self._create_thread,
            "tutor.thread.get": self._get_thread,
            "tutor.run.start": self._start_run,
            "tutor.run.get": self._get_run,
            "tutor.run.cancel": self._cancel_run,
            "evidence.resolve": self._resolve_evidence,
            "navigation.open_replaytutor": self._navigation_target,
        }
        return handlers[request.method](request.params)

    def _bootstrap(self, raw: dict[str, object]) -> CompanionBootstrapResult:
        CompanionBootstrapParams.model_validate(raw)
        return CompanionBootstrapResult(
            connector_version=__version__,
            replaytutor_version=__version__,
            capabilities=[
                "session.read",
                "tutor.run",
                "evidence.resolve",
                "navigation.local",
            ],
        )

    def _health(self, raw: dict[str, object]) -> CompanionHealthResult:
        CompanionEmptyParams.model_validate(raw)
        database = inspect_database(self.settings)
        database_healthy = (
            database.journal_mode == "wal"
            and database.foreign_keys
            and database.busy_timeout_ms == 5000
            and database.migration_current == database.migration_head
            and database.migration_head is not None
        )
        data_writable = is_writable(self.settings.resolved_data_dir)
        return CompanionHealthResult(
            status="healthy" if database_healthy and data_writable else "degraded",
            api_version=__version__,
            database_status="healthy" if database_healthy else "degraded",
            data_status="healthy" if data_writable else "unavailable",
        )

    def _discover_codex(self, raw: dict[str, object]) -> CompanionAgentResult:
        CompanionEmptyParams.model_validate(raw)
        capability = discover_codex_capability(self.settings)
        return CompanionAgentResult(
            installed=capability.installed,
            version=capability.version,
            available=capability.available,
            authentication=capability.authentication,
            diagnostics=capability.diagnostics,
        )

    def _list_sessions(self, raw: dict[str, object]) -> CompanionSessionListResult:
        params = CompanionSessionListParams.model_validate(raw)
        sessions = sorted(
            self.sessions.list().sessions,
            key=lambda session: (
                session.status in {"completed", "stopped"},
                -session.updated_at.timestamp(),
            ),
        )[: params.limit]
        return CompanionSessionListResult(
            sessions=[self._session_summary(session) for session in sessions]
        )

    def _get_session(self, raw: dict[str, object]) -> CompanionSessionStateResult:
        params = CompanionSessionParams.model_validate(raw)
        session = self.sessions.get(params.session_id).session
        return CompanionSessionStateResult(session=self._session_summary(session))

    def _list_threads(self, raw: dict[str, object]) -> BaseModel:
        params = CompanionThreadListParams.model_validate(raw)
        return self.tutor.list_threads(params.session_id)

    def _create_thread(self, raw: dict[str, object]) -> BaseModel:
        params = CompanionThreadCreateParams.model_validate(raw)
        return self.tutor.create_thread(params.session_id, params.request)

    def _get_thread(self, raw: dict[str, object]) -> BaseModel:
        params = CompanionThreadParams.model_validate(raw)
        return self.tutor.get_thread(params.thread_id)

    def _start_run(self, raw: dict[str, object]) -> BaseModel:
        params = CompanionRunStartParams.model_validate(raw)
        return self.tutor.start(params.session_id, params.request)

    def _get_run(self, raw: dict[str, object]) -> BaseModel:
        params = CompanionRunParams.model_validate(raw)
        return self.tutor.get(params.run_id)

    def _cancel_run(self, raw: dict[str, object]) -> BaseModel:
        params = CompanionRunParams.model_validate(raw)
        return self.tutor.cancel(params.run_id)

    def _resolve_evidence(self, raw: dict[str, object]) -> BaseModel:
        params = CompanionEvidenceParams.model_validate(raw)
        self.sessions.ensure_available(params.session_id)
        return self.evidence.resolve(params.session_id, params.evidence_id)

    def _navigation_target(self, raw: dict[str, object]) -> CompanionNavigationTarget:
        params = CompanionNavigationParams.model_validate(raw)
        session = self.sessions.get(params.session_id).session
        mode = "review" if session.status == "completed" and params.mode == "review" else "replay"
        query: dict[str, str] = {"mode": mode}
        if params.evidence_id is not None:
            self.evidence.resolve(params.session_id, params.evidence_id)
            query["evidence"] = params.evidence_id
        return CompanionNavigationTarget(
            path=f"/sessions/{params.session_id}?{urlencode(query)}"
        )

    @staticmethod
    def _session_summary(session: ReplaySession) -> CompanionSessionSummary:
        return CompanionSessionSummary(
            session_id=session.session_id,
            snapshot_id=session.snapshot_id,
            instrument=session.instrument,
            status=session.status,
            frame_id=session.frame.frame_id,
            revision=session.revision,
            visible_at=session.frame.visible_at,
            updated_at=session.updated_at,
        )

    @staticmethod
    def _request_id(payload: dict[str, object]) -> str:
        value = payload.get("request_id")
        if isinstance(value, str) and SAFE_REQUEST_ID.fullmatch(value):
            return value
        return "req_invalid"

    @staticmethod
    def _failure(
        request_id: str,
        code: CompanionErrorCode,
        message: str,
        *,
        retryable: bool = False,
    ) -> CompanionResponse:
        return CompanionResponse(
            request_id=request_id,
            ok=False,
            error=CompanionError(code=code, message=message, retryable=retryable),
        )
