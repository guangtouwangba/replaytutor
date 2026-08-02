from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Query, Request
from fastapi.responses import FileResponse

from replaytutor.contracts import (
    BinanceConnectionStatus,
    ReviewArtifact,
    ReviewListResponse,
    ReviewRequest,
    TradeEpisode,
    TradeSyncResult,
)
from replaytutor.modules.trade_review.service import TradeReviewService

router = APIRouter(prefix="/api/v1", tags=["trade-review"])


def service(request: Request) -> TradeReviewService:
    return TradeReviewService(request.app.state.settings)


@router.get("/binance/check", response_model=BinanceConnectionStatus)
async def check_binance(request: Request) -> BinanceConnectionStatus:
    return await service(request).check_connection()


@router.post("/binance/sync", response_model=TradeSyncResult)
async def sync_binance(
    request: Request,
    days: int = Query(default=180, ge=1, le=183),
) -> TradeSyncResult:
    return await service(request).sync_recent(days)


@router.post("/reviews", response_model=ReviewArtifact)
async def create_review(request: Request, payload: ReviewRequest) -> ReviewArtifact:
    return await service(request).generate_review(payload)


@router.get("/reviews", response_model=ReviewListResponse)
def list_reviews(
    request: Request,
    limit: int = Query(default=20, ge=1, le=100),
) -> ReviewListResponse:
    return ReviewListResponse(reviews=service(request).list_reviews(limit))


@router.get("/reviews/{review_id}", response_model=ReviewArtifact)
def get_review(request: Request, review_id: str) -> ReviewArtifact:
    return service(request).get_review(review_id)


@router.get("/reviews/{review_id}/report", response_class=FileResponse)
def get_review_report(request: Request, review_id: str) -> FileResponse:
    return FileResponse(
        service(request).report_path(review_id),
        media_type="text/html",
        filename=f"{review_id}.html",
        content_disposition_type="inline",
    )


@router.get("/episodes", response_model=list[TradeEpisode])
def list_episodes(
    request: Request,
    count: int = Query(default=10, ge=1, le=100),
    symbol: str | None = Query(default=None, pattern=r"^[A-Z0-9]{5,20}$"),
    direction: Literal["long", "short"] | None = Query(default=None),
) -> list[TradeEpisode]:
    return service(request).select_episodes(
        ReviewRequest(
            scope_kind="recent",
            count=count,
            symbol=symbol,
            direction=direction,
            sync_first=False,
        )
    )


@router.put("/episodes/{episode_id}/journal", status_code=204)
def update_journal(
    request: Request,
    episode_id: str,
    payload: dict[str, object],
) -> None:
    plan = payload.get("plan")
    service(request).update_journal(
        episode_id,
        plan if isinstance(plan, dict) else {},
        str(payload.get("notes", "")),
    )
