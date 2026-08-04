from __future__ import annotations

from replaytutor.adapters.agents import CodexAdapter
from replaytutor.config import Settings
from replaytutor.contracts import AgentCapability
from replaytutor.storage.database import connect_database


def discover_codex_capability(settings: Settings) -> AgentCapability:
    capability = CodexAdapter().discover()
    if not capability.available:
        return capability
    with connect_database(settings.database_path) as connection:
        completed = connection.execute(
            "SELECT 1 FROM tutor_run WHERE status = 'completed' LIMIT 1"
        ).fetchone()
        auth_failure = connection.execute(
            """SELECT 1 FROM tutor_run
            WHERE status = 'failed'
              AND (error LIKE '%authentication%' OR error LIKE '%codex login%')
            LIMIT 1"""
        ).fetchone()
    if completed is not None:
        return capability.model_copy(update={"authentication": "verified"})
    if auth_failure is not None:
        return capability.model_copy(update={"authentication": "failed"})
    return capability
