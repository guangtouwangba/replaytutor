from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, File, Query, Request, UploadFile

from replaytutor.config import Settings
from replaytutor.contracts import (
    BarListResponse,
    BinanceDownloadRequest,
    CommitImportRequest,
    DatasetListResponse,
    DataSnapshot,
    GoldenDatasetRequest,
    ImportPreview,
)
from replaytutor.errors import ApiError
from replaytutor.modules.market_data.service import MarketDataError, MarketDataService

router = APIRouter(prefix="/api/v1", tags=["market-data"])


def service(request: Request) -> MarketDataService:
    settings: Settings = request.app.state.settings
    return MarketDataService(settings)


def translate(error: MarketDataError) -> ApiError:
    message = str(error)
    status = 404 if "not found" in message.lower() else 422
    return ApiError("market_data_error", message, status_code=status)


@router.get("/datasets", response_model=DatasetListResponse)
def list_datasets(request: Request) -> DatasetListResponse:
    return DatasetListResponse(datasets=service(request).list_snapshots())


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
            payload.symbol, payload.start_time, payload.end_time
        )
    except (MarketDataError, ValueError) as error:
        raise ApiError("market_data_error", str(error), status_code=422) from error


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
