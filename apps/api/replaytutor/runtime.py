from __future__ import annotations

import os
from pathlib import Path

from replaytutor.config import Settings


def runtime_directories(settings: Settings) -> tuple[Path, ...]:
    root = settings.resolved_data_dir
    return (
        root,
        root / "market" / "snapshots",
        root / "imports",
        root / "runtime" / "agent-runs",
        root / "exports",
        Path("logs").resolve(),
    )


def ensure_runtime_directories(settings: Settings) -> None:
    for directory in runtime_directories(settings):
        directory.mkdir(parents=True, exist_ok=True)


def is_writable(directory: Path) -> bool:
    return directory.is_dir() and os.access(directory, os.W_OK)
