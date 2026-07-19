from __future__ import annotations

import sqlite3

from replaytutor.config import Settings
from replaytutor.storage.database import inspect_database, upgrade_database


def test_migration_is_idempotent_and_database_pragmas_are_enabled(
    settings: Settings,
) -> None:
    upgrade_database(settings)
    upgrade_database(settings)

    status = inspect_database(settings)
    assert status.journal_mode == "wal"
    assert status.foreign_keys is True
    assert status.busy_timeout_ms == 5000
    assert status.migration_current == status.migration_head == "0001_m0"

    with sqlite3.connect(settings.database_path) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
    assert tables == {"alembic_version", "system_meta"}


def test_initial_migration_recovers_from_sqlite_ddl_without_revision(
    settings: Settings,
) -> None:
    settings.database_path.parent.mkdir(parents=True)
    with sqlite3.connect(settings.database_path) as connection:
        connection.execute(
            """
            CREATE TABLE system_meta (
                key VARCHAR(128) NOT NULL PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL
            )
            """
        )

    upgrade_database(settings)

    status = inspect_database(settings)
    assert status.migration_current == status.migration_head == "0001_m0"
