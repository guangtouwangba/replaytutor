from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from replaytutor.config import Settings
from replaytutor.main import create_app
from replaytutor.storage.database import upgrade_database


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(data_dir=tmp_path / "data")


@pytest.fixture
def client(settings: Settings) -> Iterator[TestClient]:
    upgrade_database(settings)
    with TestClient(create_app(settings)) as test_client:
        yield test_client
