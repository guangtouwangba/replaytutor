from __future__ import annotations

import sqlite3

from alembic import command

from replaytutor.config import Settings
from replaytutor.storage.database import (
    alembic_config,
    inspect_database,
    upgrade_database,
)


def test_migration_is_idempotent_and_database_pragmas_are_enabled(
    settings: Settings,
) -> None:
    upgrade_database(settings)
    upgrade_database(settings)

    status = inspect_database(settings)
    assert status.journal_mode == "wal"
    assert status.foreign_keys is True
    assert status.busy_timeout_ms == 5000
    assert status.migration_current == status.migration_head == "0017_chart_objects_v2"

    with sqlite3.connect(settings.database_path) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
    assert tables == {
        "alembic_version",
        "account_event",
            "app_preference",
            "chart_context_bundle",
            "chart_tool_preference",
            "chart_tool_template",
            "data_import",
            "dataset_download_job",
        "data_snapshot",
        "execution_fill",
        "ledger_journal",
        "paper_fill",
        "paper_order",
        "playbook_version",
        "instrument",
        "replay_frame",
        "replay_session",
        "session_command",
        "session_event",
        "session_annotation",
        "session_annotation_event",
        "system_meta",
        "trade_plan",
        "training_review",
        "tutor_run",
        "trade_episode",
        "trade_income",
        "trade_journal",
        "trade_order",
        "trade_review",
        "trade_sync",
    }


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
    assert status.migration_current == status.migration_head == "0017_chart_objects_v2"


def test_playbook_migration_recovers_from_partial_non_transactional_ddl(
    settings: Settings,
) -> None:
    upgrade_database(settings)
    with sqlite3.connect(settings.database_path) as connection:
        connection.execute("ALTER TABLE replay_session DROP COLUMN playbook_id")
        connection.execute("UPDATE alembic_version SET version_num = '0007_tutor'")

    upgrade_database(settings)

    status = inspect_database(settings)
    assert status.migration_current == "0017_chart_objects_v2"
    with sqlite3.connect(settings.database_path) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        columns = {
            row[1] for row in connection.execute("PRAGMA table_info(replay_session)")
        }
    assert "playbook_version" in tables
    assert "playbook_id" in columns


def test_local_hardening_migration_downgrade_and_upgrade_drill(
    settings: Settings,
) -> None:
    upgrade_database(settings)
    command.downgrade(alembic_config(settings), "0011_playbook_rules")
    with sqlite3.connect(settings.database_path) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        columns = {
            row[1] for row in connection.execute("PRAGMA table_info(replay_session)")
        }
    assert "app_preference" not in tables
    assert "deleted_at" not in columns

    upgrade_database(settings)
    status = inspect_database(settings)
    assert status.migration_current == "0017_chart_objects_v2"
