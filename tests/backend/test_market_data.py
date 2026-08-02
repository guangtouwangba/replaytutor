from __future__ import annotations

import hashlib
import json
import time
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from replaytutor.adapters.market_data.binance import BinancePublicAdapter
from replaytutor.config import Settings
from replaytutor.modules.market_data.service import MarketDataService
from replaytutor.storage.database import upgrade_database


def test_golden_dataset_is_real_complete_and_queryable(settings: Settings) -> None:
    fixture_dir = Path(__file__).parents[2] / "tests" / "fixtures" / "market"
    fixture = fixture_dir / "btcusdt-1m-2025-01.parquet"
    manifest = json.loads(
        (fixture_dir / "btcusdt-1m-2025-01.manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["row_count"] == 44_640
    assert manifest["quality"]["status"] == "passed"
    assert (
        hashlib.sha256(fixture.read_bytes()).hexdigest()
        == manifest["normalized_parquet_sha256"]
    )

    service = MarketDataService(settings)
    upgrade_database(settings)
    snapshot = service.load_golden_dataset()
    assert snapshot.quality.row_count == 44_640
    assert snapshot.instrument.canonical_symbol == "BTCUSDT"
    assert snapshot.source_kind == "golden"

    visible_end = datetime(2025, 1, 1, 0, 4, tzinfo=UTC)
    result = service.query_snapshot_bars(
        snapshot.snapshot_id,
        start=datetime(2025, 1, 1, tzinfo=UTC),
        end=visible_end,
        limit=100,
    )
    assert len(result.bars) == 4
    assert all(bar.close_time <= visible_end for bar in result.bars)
    assert result.bars[0].raw.open == "93576"


def test_dataset_routes_load_list_and_stage_file(client: TestClient) -> None:
    loaded = client.post("/api/v1/datasets/golden", json={})
    assert loaded.status_code == 200
    snapshot_id = loaded.json()["snapshot_id"]

    listed = client.get("/api/v1/datasets")
    assert listed.status_code == 200
    assert [item["snapshot_id"] for item in listed.json()["datasets"]] == [snapshot_id]

    csv_content = b"""open_time,open,high,low,close,volume
2025-01-02T01:30:00Z,10.00,10.20,9.90,10.10,1000
2025-01-02T01:31:00Z,10.10,10.30,10.00,10.20,1100
"""
    preview = client.post(
        "/api/v1/datasets/imports",
        files={"file": ("600000.csv", csv_content, "text/csv")},
    )
    assert preview.status_code == 200
    body = preview.json()
    assert body["status"] == "preview_ready"
    assert body["quality"]["row_count"] == 2

    committed = client.post(
        f"/api/v1/datasets/imports/{body['import_id']}/commit",
        json={
            "symbol": "600000",
            "market": "CN",
            "venue": "SSE",
            "timezone": "Asia/Shanghai",
            "quote_currency": "CNY",
            "adjustment": "raw",
            "tick_size": "0.01",
            "lot_size": "100",
        },
    )
    assert committed.status_code == 200
    assert committed.json()["instrument"]["market"] == "CN"


def test_unused_snapshot_can_be_moved_to_trash_and_deleted(
    client: TestClient,
    settings: Settings,
) -> None:
    snapshot_id = client.post("/api/v1/datasets/golden", json={}).json()["snapshot_id"]
    snapshot_dir = settings.resolved_data_dir / "market" / "snapshots" / snapshot_id
    assert snapshot_dir.is_dir()

    deleted = client.delete(f"/api/v1/datasets/{snapshot_id}")

    assert deleted.status_code == 200
    payload = deleted.json()
    assert payload["snapshot_id"] == snapshot_id
    assert payload["trash_path"] is not None
    assert Path(payload["trash_path"]).is_dir()
    assert not snapshot_dir.exists()
    assert client.get("/api/v1/datasets").json()["datasets"] == []


def test_snapshot_used_by_a_training_session_cannot_be_deleted(
    client: TestClient,
) -> None:
    snapshot_id = client.post("/api/v1/datasets/golden", json={}).json()["snapshot_id"]
    created = client.post(
        "/api/v1/sessions",
        json={"snapshot_id": snapshot_id, "warmup_bars": 20},
    )
    assert created.status_code == 200

    deleted = client.delete(f"/api/v1/datasets/{snapshot_id}")

    assert deleted.status_code == 409
    assert "training session" in deleted.json()["error"]["message"]
    assert client.get(f"/api/v1/datasets/{snapshot_id}/bars?limit=1").status_code == 200


@pytest.mark.asyncio
async def test_binance_adapter_retries_429_and_uses_utc_pagination() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(429, headers={"Retry-After": "0"})
        assert request.url.params["interval"] == "1m"
        assert request.url.params["limit"] == "1000"
        return httpx.Response(
            200,
            json=[
                [
                    1735689600000,
                    "93576.00",
                    "93600.00",
                    "93500.00",
                    "93580.00",
                    "1.2",
                    1735689659999,
                ]
            ],
        )

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        base_url="https://data-api.binance.vision",
    ) as http_client:
        bars = await BinancePublicAdapter(http_client).fetch_klines(
            "BTCUSDT",
            datetime(2025, 1, 1, tzinfo=UTC),
            datetime(2025, 1, 1, 0, 1, tzinfo=UTC),
        )
    assert calls == 2
    assert len(bars) == 1
    assert str(bars[0].open) == "93576.00"


def test_binance_download_runs_as_a_durable_background_job(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_download(
        service: MarketDataService,
        _symbol: str,
        _start_time: datetime,
        _end_time: datetime,
        _market_type: str = "SPOT",
        progress: object | None = None,
    ):
        if callable(progress):
            progress(1_000)
        return service.load_golden_dataset()

    monkeypatch.setattr(MarketDataService, "download_binance", fake_download)
    created = client.post(
        "/api/v1/dataset-downloads",
        json={
            "symbol": "BTCUSDT",
            "market_type": "SPOT",
            "timeframe": "1m",
            "start_time": "2025-01-01T00:00:00Z",
            "end_time": "2025-01-03T00:00:00Z",
        },
    )
    assert created.status_code == 202
    job_id = created.json()["job_id"]
    assert created.headers["location"].endswith(job_id)

    terminal = created.json()
    for _ in range(100):
        terminal = client.get(f"/api/v1/dataset-downloads/{job_id}").json()
        if terminal["status"] in {"succeeded", "failed"}:
            break
        time.sleep(0.01)

    assert terminal["status"] == "succeeded"
    assert terminal["progress"] == 1
    assert terminal["snapshot_id"] is not None
    listed = client.get("/api/v1/dataset-downloads").json()
    assert listed["jobs"][0]["job_id"] == job_id


def test_duplicate_active_download_requests_reuse_the_job(
    settings: Settings,
) -> None:
    upgrade_database(settings)
    from replaytutor.contracts import BinanceDownloadRequest
    from replaytutor.modules.market_data.download_jobs import DatasetDownloadJobService

    payload = BinanceDownloadRequest(
        symbol="ETHUSDT",
        market_type="USDT_PERPETUAL",
        start_time=datetime(2025, 1, 1, tzinfo=UTC),
        end_time=datetime(2025, 1, 2, tzinfo=UTC),
    )
    jobs = DatasetDownloadJobService(settings)
    first = jobs.create(payload)
    second = jobs.create(payload)
    assert second.job_id == first.job_id
