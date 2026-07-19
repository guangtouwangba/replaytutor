from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ErrorDetail(ContractModel):
    code: str
    message: str
    retryable: bool = False
    request_id: str
    details: dict[str, object] = Field(default_factory=dict)


class ErrorEnvelope(ContractModel):
    error: ErrorDetail


class HealthService(ContractModel):
    status: Literal["healthy", "degraded", "unavailable"]
    version: str | None = None
    detail: str | None = None


class DatabaseHealth(HealthService):
    path: str
    journal_mode: str
    foreign_keys: bool
    migration_current: str | None
    migration_head: str | None


class DataHealth(HealthService):
    path: str
    writable: bool


class AgentExecutableHealth(ContractModel):
    agent_id: Literal["codex-local", "claude-local"]
    installed: bool
    executable: str | None
    authentication: Literal["not_checked"] = "not_checked"


class HealthResponse(ContractModel):
    schema_version: Literal["1.0"] = "1.0"
    status: Literal["healthy", "degraded"]
    request_id: str
    api: HealthService
    database: DatabaseHealth
    data: DataHealth
    agents: list[AgentExecutableHealth]
