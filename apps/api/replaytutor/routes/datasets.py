from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, File, Query, Request, Response, UploadFile, status

from replaytutor.adapters.market_data.binance import (
    BinanceAdapterError,
    BinancePublicAdapter,
    BinanceUSDMPublicAdapter,
)
from replaytutor.config import Settings
from replaytutor.contracts import (
    BarListResponse,
    BinanceDownloadRequest,
    CommitImportRequest,
    DatasetDownloadJob,
    DatasetDownloadJobListResponse,
    DatasetListResponse,
    DataSnapshot,
    GoldenDatasetRequest,
    ImportPreview,
    MarketDepthImportRequest,
    MarketDepthInputLevel,
    MarketDepthSnapshot,
    SnapshotDeleteResponse,
)
from replaytutor.errors import ApiError
from replaytutor.modules.market_data.download_jobs import (
    DatasetDownloadJobError,
    DatasetDownloadJobService,
)
from replaytutor.modules.market_data.service import MarketDataError, MarketDataService
from replaytutor.modules.market_depth import MarketDepthError, MarketDepthService

router = APIRouter(prefix="/api/v1", tags=["market-data"])


def service(request: Request) -> MarketDataService:
    settings: Settings = request.app.state.settings
    return MarketDataService(settings)


def job_service(request: Request) -> DatasetDownloadJobService:
    settings: Settings = request.app.state.settings
    return DatasetDownloadJobService(settings)


def depth_service(request: Request) -> MarketDepthService:
    settings: Settings = request.app.state.settings
    return MarketDepthService(settings)


def schedule_download(request: Request, job_id: str) -> None:
    tasks: set[asyncio.Task[None]] = request.app.state.background_tasks
    if any(task.get_name() == job_id for task in tasks):
        return
    task = asyncio.create_task(job_service(request).run(job_id), name=job_id)
    tasks.add(task)
    task.add_done_callback(tasks.discard)


def translate(error: MarketDataError) -> ApiError:
    message = str(error)
    status = 404 if "not found" in message.lower() else 422
    return ApiError("market_data_error", message, status_code=status)


@router.get("/datasets", response_model=DatasetListResponse)
def list_datasets(request: Request) -> DatasetListResponse:
    return DatasetListResponse(datasets=service(request).list_snapshots())


@router.delete("/datasets/{snapshot_id}", response_model=SnapshotDeleteResponse)
def delete_dataset(request: Request, snapshot_id: str) -> SnapshotDeleteResponse:
    try:
        return service(request).delete_snapshot(snapshot_id)
    except MarketDataError as error:
        message = str(error)
        status_code = 409 if "training session" in message else 404
        raise ApiError("snapshot_delete_error", message, status_code=status_code) from error


@router.post("/datasets/golden", response_model=DataSnapshot)
def load_golden(request: Request, _payload: GoldenDatasetRequest) -> DataSnapshot:
    try:
        return service(request).load_golden_dataset()
    except MarketDataError as error:
        raise translate(error) from error


@router.post("/datasets/binance", response_model=DataSnapshot)
async def download_binance(request: Request, payload: BinanceDownloadRequest) -> DataSnapshot:
    try:
        return await service(request).download_binance(
            payload.symbol,
            payload.start_time,
            payload.end_time,
            payload.market_type,
        )
    except (MarketDataError, ValueError) as error:
        raise ApiError("market_data_error", str(error), status_code=422) from error


@router.post(
    "/dataset-downloads",
    response_model=DatasetDownloadJob,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_dataset_download(
    request: Request,
    response: Response,
    payload: BinanceDownloadRequest,
) -> DatasetDownloadJob:
    try:
        job = job_service(request).create(payload)
        schedule_download(request, job.job_id)
        response.headers["Location"] = f"/api/v1/dataset-downloads/{job.job_id}"
        return job
    except (DatasetDownloadJobError, ValueError) as error:
        raise ApiError("dataset_download_error", str(error), status_code=422) from error


@router.get("/dataset-downloads", response_model=DatasetDownloadJobListResponse)
def list_dataset_downloads(
    request: Request,
    limit: int = Query(default=20, ge=1, le=100),
) -> DatasetDownloadJobListResponse:
    return job_service(request).list(limit)


@router.get("/dataset-downloads/{job_id}", response_model=DatasetDownloadJob)
def get_dataset_download(request: Request, job_id: str) -> DatasetDownloadJob:
    try:
        return job_service(request).get(job_id)
    except DatasetDownloadJobError as error:
        raise ApiError("dataset_download_error", str(error), status_code=404) from error


@router.get("/datasets/{snapshot_id}/bars", response_model=BarListResponse)
def get_bars(
    request: Request,
    snapshot_id: str,
    start: datetime | None = None,
    end: datetime | None = None,
    limit: int = Query(default=500, ge=1, le=5000),
) -> BarListResponse:
    try:
        return service(request).query_snapshot_bars(snapshot_id, start=start, end=end, limit=limit)
    except MarketDataError as error:
        raise translate(error) from error


@router.post(
    "/datasets/{snapshot_id}/market-depth/import",
    response_model=MarketDepthSnapshot,
)
def import_market_depth(
    request: Request,
    snapshot_id: str,
    payload: MarketDepthImportRequest,
) -> MarketDepthSnapshot:
    try:
        return depth_service(request).import_snapshot(snapshot_id, payload)
    except (MarketDataError, MarketDepthError) as error:
        raise ApiError("market_depth_error", str(error), status_code=422) from error


@router.post(
    "/datasets/{snapshot_id}/market-depth/capture-binance",
    response_model=MarketDepthSnapshot,
)
async def capture_binance_market_depth(
    request: Request,
    snapshot_id: str,
    limit: int = Query(default=100, ge=5, le=5000),
) -> MarketDepthSnapshot:
    try:
        snapshot = service(request).get_snapshot(snapshot_id)
        adapter = (
            BinanceUSDMPublicAdapter()
            if snapshot.instrument.asset_class == "crypto_perpetual"
            else BinancePublicAdapter()
        )
        captured = await adapter.fetch_depth(snapshot.instrument.canonical_symbol, limit)
        payload = MarketDepthImportRequest(
            captured_at=captured.captured_at,
            last_update_id=captured.last_update_id,
            bids=[
                MarketDepthInputLevel(price=price, quantity=quantity)
                for price, quantity in captured.bids
            ],
            asks=[
                MarketDepthInputLevel(price=price, quantity=quantity)
                for price, quantity in captured.asks
            ],
        )
        return depth_service(request).import_snapshot(
            snapshot_id,
            payload,
            source_kind="binance_rest",
        )
    except (MarketDataError, MarketDepthError, BinanceAdapterError, ValueError) as error:
        raise ApiError("market_depth_error", str(error), status_code=422) from error


@router.post("/datasets/imports", response_model=ImportPreview)
async def stage_import(request: Request, file: Annotated[UploadFile, File()]) -> ImportPreview:
    try:
        return service(request).stage_import(file.filename or "import.csv", await file.read())
    except MarketDataError as error:
        raise translate(error) from error


@router.get("/datasets/imports/{import_id}", response_model=ImportPreview)
def get_import(request: Request, import_id: str) -> ImportPreview:
    try:
        return service(request).get_import(import_id)
    except MarketDataError as error:
        raise translate(error) from error


@router.post("/datasets/imports/{import_id}/commit", response_model=DataSnapshot)
def commit_import(request: Request, import_id: str, payload: CommitImportRequest) -> DataSnapshot:
    try:
        return service(request).commit_import(import_id, payload)
    except MarketDataError as error:
        raise translate(error) from error
