from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import uvicorn

from replaytutor.adapters.market_data.binance import BinancePublicAdapter
from replaytutor.config import get_settings
from replaytutor.contract_generation import check_contracts, export_contracts
from replaytutor.contracts import ReviewRequest
from replaytutor.modules.market_data.quality import inspect_bars
from replaytutor.modules.trade_review.service import TradeReviewService
from replaytutor.storage.database import upgrade_database
from replaytutor.storage.parquet import canonical_json, sha256_file, write_bars


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="replaytutor")
    commands = root.add_subparsers(dest="command", required=True)
    commands.add_parser("api", help="start the local API")
    contracts = commands.add_parser("contracts", help="manage generated contracts")
    contracts.add_argument("action", choices=("check", "export"))
    data = commands.add_parser("data", help="manage bundled market data")
    data.add_argument("action", choices=("build-golden",))
    binance = commands.add_parser("binance", help="read-only Binance account imports")
    binance.add_argument("action", choices=("check", "sync"))
    binance.add_argument("--days", type=int, default=180)
    review = commands.add_parser("review", help="generate a price-action trade review")
    review_commands = review.add_subparsers(dest="review_action", required=True)
    today = review_commands.add_parser("today")
    today.add_argument("--symbol")
    today.add_argument("--direction", choices=("long", "short"))
    today.add_argument("--no-sync", action="store_true")
    recent = review_commands.add_parser("recent")
    recent.add_argument("--count", type=int, default=10)
    recent.add_argument("--symbol")
    recent.add_argument("--direction", choices=("long", "short"))
    recent.add_argument("--no-sync", action="store_true")
    trade = review_commands.add_parser("trade")
    trade.add_argument("episode_id")
    trade.add_argument("--no-sync", action="store_true")
    return root


def main() -> None:
    args = parser().parse_args()
    if args.command == "api":
        settings = get_settings()
        uvicorn.run(
            "replaytutor.main:app",
            host=settings.host,
            port=settings.port,
            log_level=settings.log_level.lower(),
            reload=True,
            reload_dirs=[str(Path(__file__).resolve().parent)],
        )
        return

    if args.command == "data":
        asyncio.run(build_golden_fixture())
        return

    if args.command == "binance":
        asyncio.run(run_binance_command(args))
        return

    if args.command == "review":
        asyncio.run(run_review_command(args))
        return

    if args.action == "export":
        print(export_contracts())
        return
    if not check_contracts():
        raise SystemExit(
            "Generated contracts are stale. Run: "
            "uv run --project apps/api replaytutor contracts export"
        )
    print("contracts are clean")


async def run_binance_command(args: argparse.Namespace) -> None:
    settings = get_settings()
    upgrade_database(settings)
    service = TradeReviewService(settings)
    if args.action == "check":
        result = await service.check_connection()
    else:
        result = await service.sync_recent(args.days)
    print(result.model_dump_json(indent=2))


async def run_review_command(args: argparse.Namespace) -> None:
    settings = get_settings()
    upgrade_database(settings)
    service = TradeReviewService(settings)
    action = args.review_action
    request = ReviewRequest(
        scope_kind="trade" if action == "trade" else action,
        count=getattr(args, "count", 10),
        episode_id=getattr(args, "episode_id", None),
        symbol=getattr(args, "symbol", None),
        direction=getattr(args, "direction", None),
        sync_first=not args.no_sync,
    )
    result = await service.generate_review(request)
    report_path = service.report_path(result.review_id)
    print(
        json.dumps(
            {
                "review_id": result.review_id,
                "episode_count": result.episode_count,
                "top_positives": result.top_positives,
                "top_improvements": result.top_improvements,
                "recurring_patterns": result.recurring_patterns,
                "report_html": str(report_path),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


async def build_golden_fixture() -> None:
    start = datetime(2025, 1, 1, tzinfo=UTC)
    end = datetime(2025, 2, 1, tzinfo=UTC)
    bars = await BinancePublicAdapter().fetch_klines("BTCUSDT", start, end)
    quality = inspect_bars(bars, continuous=True)
    if len(bars) != 44_640 or quality.status != "passed":
        raise SystemExit(f"Golden dataset failed quality gate: {quality.model_dump()}")
    fixture_dir = Path(__file__).resolve().parents[3] / "tests" / "fixtures" / "market"
    fixture_dir.mkdir(parents=True, exist_ok=True)
    parquet_path = fixture_dir / "btcusdt-1m-2025-01.parquet"
    write_bars(
        parquet_path,
        bars,
        {
            "schema_version": "1.0",
            "source_id": "btcusdt-1m-2025-01",
            "instrument_id": "BTCUSDT",
            "timeframe": "1m",
            "created_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        },
    )
    normalized_rows = [
        [
            int(bar.open_time.timestamp() * 1000),
            str(bar.open),
            str(bar.high),
            str(bar.low),
            str(bar.close),
            str(bar.volume),
            int(bar.close_time.timestamp() * 1000),
        ]
        for bar in bars
    ]
    source_hash = hashlib.sha256(canonical_json(normalized_rows).encode()).hexdigest()
    manifest = {
        "schema_version": "1.0",
        "dataset_id": "btcusdt-1m-2025-01",
        "source": "Binance Spot public market data REST API",
        "endpoint": "https://data-api.binance.vision/api/v3/klines",
        "request": {
            "symbol": "BTCUSDT",
            "interval": "1m",
            "start_time": "2025-01-01T00:00:00.000Z",
            "end_time_exclusive": "2025-02-01T00:00:00.000Z",
            "page_limit": 1000,
        },
        "captured_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "row_count": len(bars),
        "source_fields_sha256": source_hash,
        "normalized_parquet_sha256": sha256_file(parquet_path),
        "quality": quality.model_dump(mode="json"),
    }
    manifest_path = fixture_dir / "btcusdt-1m-2025-01.manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(f"wrote {parquet_path} ({len(bars)} bars)")
