from __future__ import annotations

import hashlib
import json
import re
import shutil
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from replaytutor.config import Settings
from replaytutor.contracts import (
    BackupArtifact,
    CleanupResult,
    LocalPreferences,
    MaintenanceStatus,
)
from replaytutor.modules.market_data.service import utc_text
from replaytutor.storage.database import connect_database

BACKUP_PATTERN = re.compile(r"^backup_[0-9]{8}T[0-9]{6}Z_[0-9a-f]{8}$")


class LocalSystemService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.backup_dir = settings.resolved_data_dir / "backups"
        self.agent_runs_dir = settings.resolved_data_dir / "runtime" / "agent-runs"
        self.agent_trash_dir = settings.resolved_data_dir / "trash" / "agent-runs"

    def get_preferences(self) -> LocalPreferences:
        with connect_database(self.settings.database_path) as connection:
            row = connection.execute(
                """SELECT payload_json, updated_at FROM app_preference
                WHERE preference_key = 'local'"""
            ).fetchone()
        if row is None:
            return LocalPreferences()
        payload = json.loads(str(row["payload_json"]))
        payload["updated_at"] = str(row["updated_at"])
        return LocalPreferences.model_validate(payload)

    def save_preferences(self, preferences: LocalPreferences) -> LocalPreferences:
        now = datetime.now(UTC)
        saved = preferences.model_copy(update={"updated_at": now})
        payload = saved.model_dump(mode="json", exclude={"updated_at"})
        with connect_database(self.settings.database_path) as connection:
            connection.execute(
                """INSERT INTO app_preference (
                    preference_key, payload_json, updated_at
                ) VALUES ('local', ?, ?)
                ON CONFLICT(preference_key) DO UPDATE SET
                    payload_json = excluded.payload_json,
                    updated_at = excluded.updated_at""",
                (
                    json.dumps(payload, ensure_ascii=False, sort_keys=True),
                    utc_text(now),
                ),
            )
        return saved

    def create_backup(self) -> BackupArtifact:
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        now = datetime.now(UTC)
        backup_id = f"backup_{now.strftime('%Y%m%dT%H%M%SZ')}_{uuid4().hex[:8]}"
        path = self.backup_dir / f"{backup_id}.db"
        with (
            sqlite3.connect(self.settings.database_path) as source,
            sqlite3.connect(path) as destination,
        ):
            source.backup(destination)
        return self._artifact(path)

    def restore_backup(self, backup_id: str) -> BackupArtifact:
        path = self._backup_path(backup_id)
        if not path.is_file():
            raise ValueError("Backup not found")
        self.create_backup()
        with sqlite3.connect(path) as source:
            integrity = source.execute("PRAGMA integrity_check").fetchone()
            if integrity is None or str(integrity[0]).lower() != "ok":
                raise ValueError("Backup integrity check failed")
            with sqlite3.connect(self.settings.database_path) as destination:
                source.backup(destination)
        return self._artifact(path)

    def status(self) -> MaintenanceStatus:
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.agent_trash_dir.mkdir(parents=True, exist_ok=True)
        backups = [
            self._artifact(path)
            for path in sorted(self.backup_dir.glob("backup_*.db"), reverse=True)
            if BACKUP_PATTERN.fullmatch(path.stem)
        ]
        trashed = sum(path.is_dir() for path in self.agent_trash_dir.iterdir())
        return MaintenanceStatus(
            backups=backups,
            trashed_agent_runs=trashed,
        )

    def cleanup_agent_runs(self, retain_days: int) -> CleanupResult:
        self.agent_runs_dir.mkdir(parents=True, exist_ok=True)
        self.agent_trash_dir.mkdir(parents=True, exist_ok=True)
        cutoff = datetime.now(UTC) - timedelta(days=retain_days)
        moved = 0
        for path in self.agent_runs_dir.iterdir():
            if not path.is_dir():
                continue
            modified = datetime.fromtimestamp(path.stat().st_mtime, tz=UTC)
            if modified >= cutoff:
                continue
            target = self.agent_trash_dir / path.name
            if target.exists():
                target = self.agent_trash_dir / f"{path.name}-{uuid4().hex[:8]}"
            shutil.move(str(path), str(target))
            moved += 1
        return CleanupResult(
            moved_agent_runs=moved,
            trash_path=str(self.agent_trash_dir),
        )

    def recover_orphaned_tutor_runs(self) -> int:
        now = datetime.now(UTC)
        with connect_database(self.settings.database_path) as connection:
            cursor = connection.execute(
                """UPDATE tutor_run
                SET status = 'failed',
                    error = 'Recovered orphaned run after application restart',
                    completed_at = ?
                WHERE status = 'running'""",
                (utc_text(now),),
            )
            return max(cursor.rowcount, 0)

    def _backup_path(self, backup_id: str) -> Path:
        if not BACKUP_PATTERN.fullmatch(backup_id):
            raise ValueError("Invalid backup id")
        return self.backup_dir / f"{backup_id}.db"

    @staticmethod
    def _artifact(path: Path) -> BackupArtifact:
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        stat = path.stat()
        return BackupArtifact(
            backup_id=path.stem,
            created_at=datetime.fromtimestamp(stat.st_mtime, tz=UTC),
            size_bytes=stat.st_size,
            sha256=digest,
        )
