from __future__ import annotations

import asyncio
from datetime import UTC, datetime

from replaytutor.config import Settings
from replaytutor.contracts import (
    BinanceDownloadRequest,
    DatasetDownloadJob,
    DatasetDownloadJobListResponse,
)
from replaytutor.ids import new_id
from replaytutor.modules.market_data.service import MarketDataService, utc_text
from replaytutor.storage.database import connect_database


class DatasetDownloadJobError(RuntimeError):
    pass


class DatasetDownloadJobService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def create(self, payload: BinanceDownloadRequest) -> DatasetDownloadJob:
        if payload.start_time >= payload.end_time:
            raise DatasetDownloadJobError("start_time must be before end_time")
        total_bars = max(
            1,
            int((payload.end_time - payload.start_time).total_seconds() // 60),
        )
        with connect_database(self.settings.database_path) as connection:
            existing = connection.execute(
                """
                SELECT * FROM dataset_download_job
                WHERE status IN ('queued', 'running')
                  AND symbol = ? AND market_type = ? AND timeframe = ?
                  AND start_time = ? AND end_time = ?
                ORDER BY created_at DESC LIMIT 1
                """,
                (
                    payload.symbol,
                    payload.market_type,
                    payload.timeframe,
                    utc_text(payload.start_time),
                    utc_text(payload.end_time),
                ),
            ).fetchone()
            if existing is not None:
                return self._from_row(dict(existing))
            job_id = new_id("job")
            created_at = datetime.now(UTC)
            connection.execute(
                """
                INSERT INTO dataset_download_job (
                    job_id, kind, status, symbol, market_type, timeframe,
                    start_time, end_time, completed_bars, total_bars, created_at
                ) VALUES (?, 'binance_market_data', 'queued', ?, ?, ?, ?, ?, 0, ?, ?)
                """,
                (
                    job_id,
                    payload.symbol,
                    payload.market_type,
                    payload.timeframe,
                    utc_text(payload.start_time),
                    utc_text(payload.end_time),
                    total_bars,
                    utc_text(created_at),
                ),
            )
        return self.get(job_id)

    def get(self, job_id: str) -> DatasetDownloadJob:
        with connect_database(self.settings.database_path) as connection:
            row = connection.execute(
                "SELECT * FROM dataset_download_job WHERE job_id = ?",
                (job_id,),
            ).fetchone()
        if row is None:
            raise DatasetDownloadJobError("Dataset download job not found")
        return self._from_row(dict(row))

    def list(self, limit: int = 20) -> DatasetDownloadJobListResponse:
        with connect_database(self.settings.database_path) as connection:
            rows = connection.execute(
                "SELECT * FROM dataset_download_job ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return DatasetDownloadJobListResponse(
            jobs=[self._from_row(dict(row)) for row in rows]
        )

    def recover_pending(self) -> list[str]:
        with connect_database(self.settings.database_path) as connection:
            connection.execute(
                """
                UPDATE dataset_download_job
                SET status = 'queued', started_at = NULL,
                    error = 'Application restarted; download resumed'
                WHERE status = 'running'
                """
            )
            rows = connection.execute(
                "SELECT job_id FROM dataset_download_job WHERE status = 'queued'"
            ).fetchall()
        return [str(row["job_id"]) for row in rows]

    async def run(self, job_id: str) -> None:
        job = self.get(job_id)
        if job.status not in {"queued", "running"}:
            return
        now = datetime.now(UTC)
        with connect_database(self.settings.database_path) as connection:
            connection.execute(
                """
                UPDATE dataset_download_job
                SET status = 'running', started_at = ?, finished_at = NULL, error = NULL
                WHERE job_id = ?
                """,
                (utc_text(now), job_id),
            )

        def report(completed_bars: int) -> None:
            with connect_database(self.settings.database_path) as connection:
                connection.execute(
                    """
                    UPDATE dataset_download_job
                    SET completed_bars = MIN(?, total_bars)
                    WHERE job_id = ? AND status = 'running'
                    """,
                    (completed_bars, job_id),
                )

        try:
            snapshot = await MarketDataService(self.settings).download_binance(
                job.symbol,
                job.start_time,
                job.end_time,
                job.market_type,
                progress=report,
            )
        except asyncio.CancelledError:
            with connect_database(self.settings.database_path) as connection:
                connection.execute(
                    """
                    UPDATE dataset_download_job
                    SET status = 'queued', started_at = NULL,
                        error = 'Application stopped; download will resume on next start'
                    WHERE job_id = ?
                    """,
                    (job_id,),
                )
            raise
        except Exception as error:
            with connect_database(self.settings.database_path) as connection:
                connection.execute(
                    """
                    UPDATE dataset_download_job
                    SET status = 'failed', error = ?, finished_at = ?
                    WHERE job_id = ?
                    """,
                    (str(error), utc_text(datetime.now(UTC)), job_id),
                )
            return
        with connect_database(self.settings.database_path) as connection:
            connection.execute(
                """
                UPDATE dataset_download_job
                SET status = 'succeeded', completed_bars = total_bars,
                    snapshot_id = ?, error = NULL, finished_at = ?
                WHERE job_id = ?
                """,
                (snapshot.snapshot_id, utc_text(datetime.now(UTC)), job_id),
            )

    @staticmethod
    def _from_row(row: dict[str, object]) -> DatasetDownloadJob:
        completed = int(str(row["completed_bars"]))
        total = int(str(row["total_bars"]))
        payload = dict(row)
        payload["progress"] = min(completed / total, 1)
        return DatasetDownloadJob.model_validate(payload)
