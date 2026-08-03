from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine
from sqlalchemy.engine import URL

from replaytutor.config import Settings


@dataclass(frozen=True)
class DatabaseStatus:
    path: Path
    journal_mode: str
    foreign_keys: bool
    busy_timeout_ms: int
    migration_current: str | None
    migration_head: str | None


def connect_database(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=5, check_same_thread=False)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute("PRAGMA foreign_keys=ON")
    connection.execute("PRAGMA busy_timeout=5000")
    return connection


def alembic_config(settings: Settings) -> Config:
    api_root = Path(__file__).resolve().parents[2]
    config = Config(str(api_root / "alembic.ini"))
    config.set_main_option("script_location", str(api_root / "alembic"))
    url = URL.create("sqlite+pysqlite", database=str(settings.database_path))
    config.set_main_option("sqlalchemy.url", url.render_as_string(hide_password=False))
    return config


def upgrade_database(settings: Settings) -> None:
    settings.database_path.parent.mkdir(parents=True, exist_ok=True)
    command.upgrade(alembic_config(settings), "head")


def inspect_database(settings: Settings) -> DatabaseStatus:
    with connect_database(settings.database_path) as connection:
        journal_mode = str(connection.execute("PRAGMA journal_mode").fetchone()[0]).lower()
        foreign_keys = bool(connection.execute("PRAGMA foreign_keys").fetchone()[0])
        busy_timeout_ms = int(connection.execute("PRAGMA busy_timeout").fetchone()[0])

    config = alembic_config(settings)
    script = ScriptDirectory.from_config(config)
    migration_head = script.get_current_head()
    database_url = config.get_main_option("sqlalchemy.url")
    if database_url is None:
        raise RuntimeError("Alembic database URL is not configured")
    engine = create_engine(database_url)
    try:
        with engine.connect() as connection:
            migration_current = MigrationContext.configure(connection).get_current_revision()
    finally:
        engine.dispose()

    return DatabaseStatus(
        path=settings.database_path,
        journal_mode=journal_mode,
        foreign_keys=foreign_keys,
        busy_timeout_ms=busy_timeout_ms,
        migration_current=migration_current,
        migration_head=migration_head,
    )
