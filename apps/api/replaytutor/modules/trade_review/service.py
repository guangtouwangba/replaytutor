from __future__ import annotations

import json
from collections import Counter
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from replaytutor.adapters.binance_private import (
    BinanceReadOnlyClient,
    BinanceReadOnlyError,
)
from replaytutor.config import Settings
from replaytutor.contracts import (
    BinanceConnectionStatus,
    EpisodeReview,
    ReviewArtifact,
    ReviewRequest,
    TradeEpisode,
    TradeSyncResult,
)
from replaytutor.ids import new_id, stable_id
from replaytutor.modules.trade_review.episodes import (
    EpisodeRecord,
    FillRecord,
    decimal_text,
    reconstruct_episodes,
)
from replaytutor.modules.trade_review.price_action import (
    TIMEFRAME_MINUTES,
    TimeframeRead,
    analyze_timeframe,
    annotation,
    bars_from_binance,
    review_dimensions,
)
from replaytutor.modules.trade_review.render import render_review_html
from replaytutor.storage.database import connect_database

SHANGHAI = ZoneInfo("Asia/Shanghai")
SEVEN_DAYS_MS = 7 * 24 * 60 * 60 * 1000


class TradeReviewError(RuntimeError):
    pass


class TradeReviewService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.reviews_dir = settings.resolved_data_dir / "reviews"

    async def check_connection(self) -> BinanceConnectionStatus:
        try:
            async with BinanceReadOnlyClient(self.settings.resolved_binance_config_path) as client:
                return BinanceConnectionStatus.model_validate(await client.check_permissions())
        except BinanceReadOnlyError as exc:
            return BinanceConnectionStatus(
                readable=False,
                mainnet=True,
                read_enabled=False,
                futures_trade_enabled=False,
                withdrawals_enabled=False,
                ip_restricted=False,
                diagnostics=[str(exc)],
            )

    async def ensure_synced(self, days: int) -> TradeSyncResult | None:
        desired_start = datetime.now(UTC) - timedelta(days=days)
        with connect_database(self.settings.database_path) as connection:
            row = connection.execute(
                """
                SELECT * FROM trade_sync
                WHERE market_type = 'usdm_perp'
                  AND coverage_status IN ('complete', 'partial')
                ORDER BY created_at DESC LIMIT 1
                """
            ).fetchone()
        if row is not None:
            item = dict(row)
            coverage_start = parse_time(item["coverage_start"])
            coverage_end = parse_time(item["coverage_end"])
            if coverage_start <= desired_start + timedelta(
                minutes=5
            ) and coverage_end >= datetime.now(UTC) - timedelta(minutes=5):
                return None
        return await self.sync_recent(days)

    async def sync_recent(self, days: int = 180) -> TradeSyncResult:
        if days < 1 or days > 183:
            raise TradeReviewError("Recent API sync supports 1 to 183 days")
        end = datetime.now(UTC)
        start = end - timedelta(days=days)
        diagnostics: list[str] = []
        sync_id = new_id("syn")
        all_trades: list[dict[str, object]] = []
        all_income: list[dict[str, object]] = []
        all_orders: list[dict[str, object]] = []
        coverage_status = "complete"
        try:
            async with BinanceReadOnlyClient(self.settings.resolved_binance_config_path) as client:
                all_trades = await self._fetch_trades(client, start, end)
                all_income = await self._fetch_income(client, start, end)
                symbols = sorted(
                    {str(item.get("symbol", "")) for item in all_trades if item.get("symbol")}
                )
                orders_start = max(start, end - timedelta(days=89))
                if orders_start > start:
                    coverage_status = "partial"
                    diagnostics.append(
                        "Binance allOrders is limited to the recent 90 days; "
                        "older fills are complete but historical order metadata is partial"
                    )
                for symbol in symbols:
                    all_orders.extend(await self._fetch_orders(client, symbol, orders_start, end))
        except BinanceReadOnlyError as exc:
            diagnostics.append(str(exc))
            self._write_sync(
                sync_id,
                start,
                end,
                "failed",
                0,
                0,
                0,
                diagnostics,
            )
            raise TradeReviewError(str(exc)) from exc

        fill_count = self._store_trades(all_trades)
        income_count = self._store_income(all_income)
        order_count = self._store_orders(all_orders)
        episode_count = self.rebuild_episodes()
        if not all_trades:
            diagnostics.append("No USDⓈ-M fills were returned for the requested window")
        self._write_sync(
            sync_id,
            start,
            end,
            coverage_status,
            fill_count,
            order_count,
            income_count,
            diagnostics,
        )
        return TradeSyncResult(
            sync_id=sync_id,
            coverage_start=start,
            coverage_end=end,
            coverage_status=coverage_status,
            fill_count=fill_count,
            order_count=order_count,
            income_count=income_count,
            episode_count=episode_count,
            diagnostics=diagnostics,
        )

    async def generate_review(self, request: ReviewRequest) -> ReviewArtifact:
        if request.sync_first:
            await self.ensure_synced(2 if request.scope_kind == "today" else 180)
        episodes = self.select_episodes(request)
        review_id = new_id("rev")
        created_at = datetime.now(UTC)
        source_by_episode = await self._fetch_episode_market_data(episodes)
        reviews: list[EpisodeReview] = []
        render_episodes: list[dict[str, object]] = []
        for episode in episodes:
            source = source_by_episode.get(episode.episode_id, [])
            episode_review, render_data = self._review_episode(episode, source)
            reviews.append(episode_review)
            render_episodes.append(render_data)

        total_pnl = sum((Decimal(item.realized_pnl) for item in episodes), Decimal(0))
        total_commission = sum((Decimal(item.commission) for item in episodes), Decimal(0))
        top_positives = frequent_items(item for review in reviews for item in review.positives)
        top_improvements = frequent_items(
            item for review in reviews for item in review.improvements
        )
        recurring = recurring_patterns(reviews)
        report_url = f"/api/v1/reviews/{review_id}/report"
        artifact = ReviewArtifact(
            review_id=review_id,
            scope_kind=request.scope_kind,
            scope_value=self.scope_value(request),
            created_at=created_at,
            episode_count=len(reviews),
            total_realized_pnl=decimal_text(total_pnl),
            total_commission=decimal_text(total_commission),
            reviews=reviews,
            top_positives=top_positives,
            top_improvements=top_improvements,
            recurring_patterns=recurring,
            report_url=report_url,
        )
        output_dir = (
            self.reviews_dir / created_at.strftime("%Y") / created_at.strftime("%m") / review_id
        )
        output_dir.mkdir(parents=True, exist_ok=False)
        json_path = output_dir / "report.json"
        html_path = output_dir / "report.html"
        json_path.write_text(
            artifact.model_dump_json(indent=2),
            encoding="utf-8",
        )
        html_payload: dict[str, object] = {
            "title": "Binance 价格行为交易复盘",
            "scope_label": self.scope_label(request),
            "created_at": iso_time(created_at),
            "episode_count": artifact.episode_count,
            "total_realized_pnl": artifact.total_realized_pnl,
            "total_commission": artifact.total_commission,
            "top_positives": top_positives,
            "top_improvements": top_improvements,
            "recurring_patterns": recurring,
            "episodes": render_episodes,
        }
        html_path.write_text(render_review_html(html_payload), encoding="utf-8")
        with connect_database(self.settings.database_path) as connection:
            connection.execute(
                """
                INSERT INTO trade_review (
                    review_id, scope_kind, scope_value, episode_ids_json, summary_json,
                    report_json_path, report_html_path, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    review_id,
                    request.scope_kind,
                    artifact.scope_value,
                    json.dumps([item.episode_id for item in episodes]),
                    artifact.model_dump_json(),
                    str(json_path),
                    str(html_path),
                    iso_time(created_at),
                ),
            )
        return artifact

    def select_episodes(self, request: ReviewRequest) -> list[TradeEpisode]:
        conditions = ["1 = 1"]
        params: list[object] = []
        if request.symbol:
            conditions.append("symbol = ?")
            params.append(request.symbol)
        if request.direction:
            conditions.append("direction = ?")
            params.append(request.direction)
        if request.scope_kind == "today":
            now_local = datetime.now(SHANGHAI)
            day_start = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = day_start + timedelta(days=1)
            conditions.append(
                """
                EXISTS (
                    SELECT 1 FROM execution_fill f
                    WHERE instr(allocations_json, f.fill_id) > 0
                    AND f.executed_at >= ? AND f.executed_at < ?
                )
                """
            )
            params.extend([iso_time(day_start.astimezone(UTC)), iso_time(day_end.astimezone(UTC))])
            order = "opened_at ASC"
            limit = 500
        elif request.scope_kind == "trade":
            if not request.episode_id:
                raise TradeReviewError("episode_id is required for a trade review")
            conditions.append("episode_id = ?")
            params.append(request.episode_id)
            order = "opened_at DESC"
            limit = 1
        else:
            conditions.append("status = 'closed'")
            order = "closed_at DESC"
            limit = request.count
        query = (
            "SELECT * FROM trade_episode WHERE "
            + " AND ".join(conditions)
            + f" ORDER BY {order} LIMIT ?"
        )
        params.append(limit)
        with connect_database(self.settings.database_path) as connection:
            rows = connection.execute(query, params).fetchall()
        return [episode_contract(dict(row)) for row in rows]

    def list_reviews(self, limit: int = 20) -> list[ReviewArtifact]:
        with connect_database(self.settings.database_path) as connection:
            rows = connection.execute(
                "SELECT summary_json FROM trade_review ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [ReviewArtifact.model_validate_json(str(row["summary_json"])) for row in rows]

    def get_review(self, review_id: str) -> ReviewArtifact:
        with connect_database(self.settings.database_path) as connection:
            row = connection.execute(
                "SELECT summary_json FROM trade_review WHERE review_id = ?",
                (review_id,),
            ).fetchone()
        if row is None:
            raise TradeReviewError("Review not found")
        return ReviewArtifact.model_validate_json(str(row["summary_json"]))

    def report_path(self, review_id: str) -> Path:
        with connect_database(self.settings.database_path) as connection:
            row = connection.execute(
                "SELECT report_html_path FROM trade_review WHERE review_id = ?",
                (review_id,),
            ).fetchone()
        if row is None:
            raise TradeReviewError("Review not found")
        path = Path(str(row["report_html_path"])).resolve()
        if not path.is_file() or self.reviews_dir.resolve() not in path.parents:
            raise TradeReviewError("Review report is unavailable")
        return path

    def update_journal(
        self,
        episode_id: str,
        plan: dict[str, object],
        notes: str,
    ) -> None:
        with connect_database(self.settings.database_path) as connection:
            exists = connection.execute(
                "SELECT 1 FROM trade_episode WHERE episode_id = ?",
                (episode_id,),
            ).fetchone()
            if exists is None:
                raise TradeReviewError("Episode not found")
            connection.execute(
                """
                INSERT INTO trade_journal (episode_id, plan_json, notes, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(episode_id) DO UPDATE SET
                    plan_json = excluded.plan_json,
                    notes = excluded.notes,
                    updated_at = excluded.updated_at
                """,
                (episode_id, json.dumps(plan), notes, iso_time(datetime.now(UTC))),
            )

    async def _fetch_trades(
        self,
        client: BinanceReadOnlyClient,
        start: datetime,
        end: datetime,
    ) -> list[dict[str, object]]:
        result: list[dict[str, object]] = []
        for window_start, window_end in time_windows(start, end):
            cursor = window_start
            while cursor < window_end:
                page = await client.user_trades(cursor, window_end, limit=1000)
                result.extend(page)
                if len(page) < 1000:
                    break
                next_cursor = max(int(str(item["time"])) for item in page) + 1
                if next_cursor <= cursor:
                    raise TradeReviewError("Binance trade pagination did not advance")
                cursor = next_cursor
        return dedupe(result, lambda item: (str(item["symbol"]), str(item["id"])))

    async def _fetch_orders(
        self,
        client: BinanceReadOnlyClient,
        symbol: str,
        start: datetime,
        end: datetime,
    ) -> list[dict[str, object]]:
        result: list[dict[str, object]] = []
        for window_start, window_end in time_windows(start, end):
            page = await client.all_orders(symbol, window_start, window_end)
            result.extend(page)
        return dedupe(result, lambda item: str(item["orderId"]))

    async def _fetch_income(
        self,
        client: BinanceReadOnlyClient,
        start: datetime,
        end: datetime,
    ) -> list[dict[str, object]]:
        result: list[dict[str, object]] = []
        for window_start, window_end in time_windows(start, end):
            cursor = window_start
            while cursor < window_end:
                page = await client.income(cursor, window_end, limit=1000)
                result.extend(page)
                if len(page) < 1000:
                    break
                next_cursor = max(int(str(item["time"])) for item in page) + 1
                if next_cursor <= cursor:
                    raise TradeReviewError("Binance income pagination did not advance")
                cursor = next_cursor
        return dedupe(result, lambda item: str(item["tranId"]))

    def _store_trades(self, trades: list[dict[str, object]]) -> int:
        with connect_database(self.settings.database_path) as connection:
            for item in trades:
                symbol, trade_id = str(item["symbol"]), str(item["id"])
                fill_id = stable_id(
                    "fil",
                    "replaytutor:binance-usdm-fill",
                    f"{symbol}:{trade_id}",
                )
                connection.execute(
                    """
                    INSERT INTO execution_fill (
                        fill_id, market_type, symbol, trade_id, order_id, side,
                        position_side, price, qty, quote_qty, commission,
                        commission_asset, realized_pnl, executed_at, is_buyer,
                        is_maker, raw_json
                    ) VALUES (?, 'usdm_perp', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(market_type, symbol, trade_id) DO UPDATE SET
                        raw_json = excluded.raw_json
                    """,
                    (
                        fill_id,
                        symbol,
                        trade_id,
                        str(item["orderId"]),
                        str(item["side"]),
                        str(item.get("positionSide", "BOTH")),
                        str(item["price"]),
                        str(item["qty"]),
                        str(item.get("quoteQty", "0")),
                        str(item.get("commission", "0")),
                        str(item.get("commissionAsset", "")),
                        str(item.get("realizedPnl", "0")),
                        ms_time(item["time"]),
                        bool(item.get("buyer")),
                        bool(item.get("maker")),
                        json.dumps(item, separators=(",", ":")),
                    ),
                )
        return len(trades)

    def _store_orders(self, orders: list[dict[str, object]]) -> int:
        with connect_database(self.settings.database_path) as connection:
            for item in orders:
                connection.execute(
                    """
                    INSERT INTO trade_order (
                        market_type, symbol, order_id, order_type, side, position_side,
                        status, price, stop_price, avg_price, orig_qty, executed_qty,
                        reduce_only, created_at, updated_at, raw_json
                    ) VALUES ('usdm_perp', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(market_type, symbol, order_id) DO UPDATE SET
                        status = excluded.status,
                        avg_price = excluded.avg_price,
                        executed_qty = excluded.executed_qty,
                        updated_at = excluded.updated_at,
                        raw_json = excluded.raw_json
                    """,
                    (
                        str(item["symbol"]),
                        str(item["orderId"]),
                        str(item.get("type", "")),
                        str(item.get("side", "")),
                        str(item.get("positionSide", "BOTH")),
                        str(item.get("status", "")),
                        str(item.get("price", "0")),
                        str(item.get("stopPrice", "0")),
                        str(item.get("avgPrice", "0")),
                        str(item.get("origQty", "0")),
                        str(item.get("executedQty", "0")),
                        bool(item.get("reduceOnly")),
                        ms_time(item.get("time", item.get("updateTime", 0))),
                        ms_time(item.get("updateTime", item.get("time", 0))),
                        json.dumps(item, separators=(",", ":")),
                    ),
                )
        return len(orders)

    def _store_income(self, incomes: list[dict[str, object]]) -> int:
        with connect_database(self.settings.database_path) as connection:
            for item in incomes:
                connection.execute(
                    """
                    INSERT INTO trade_income (
                        market_type, transaction_id, symbol, income_type, income,
                        asset, occurred_at, raw_json
                    ) VALUES ('usdm_perp', ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(market_type, transaction_id) DO UPDATE SET
                        raw_json = excluded.raw_json
                    """,
                    (
                        str(item["tranId"]),
                        str(item.get("symbol", "")),
                        str(item.get("incomeType", "")),
                        str(item.get("income", "0")),
                        str(item.get("asset", "")),
                        ms_time(item["time"]),
                        json.dumps(item, separators=(",", ":")),
                    ),
                )
        return len(incomes)

    def rebuild_episodes(self) -> int:
        with connect_database(self.settings.database_path) as connection:
            rows = connection.execute(
                "SELECT * FROM execution_fill ORDER BY executed_at, CAST(trade_id AS INTEGER)"
            ).fetchall()
        fills = [
            FillRecord(
                fill_id=str(row["fill_id"]),
                symbol=str(row["symbol"]),
                trade_id=str(row["trade_id"]),
                order_id=str(row["order_id"]),
                side=str(row["side"]),
                position_side=str(row["position_side"]),
                price=Decimal(str(row["price"])),
                qty=Decimal(str(row["qty"])),
                commission=Decimal(str(row["commission"])),
                realized_pnl=Decimal(str(row["realized_pnl"])),
                executed_at=parse_time(str(row["executed_at"])),
                is_maker=bool(row["is_maker"]),
            )
            for row in rows
        ]
        episodes = reconstruct_episodes(fills)
        with connect_database(self.settings.database_path) as connection:
            connection.execute("DELETE FROM trade_episode")
            for item in episodes:
                connection.execute(
                    """
                    INSERT INTO trade_episode (
                        episode_id, market_type, symbol, direction, position_side, status,
                        opened_at, closed_at, entry_price, exit_price, peak_qty,
                        realized_pnl, commission, allocations_json, updated_at
                    ) VALUES (?, 'usdm_perp', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    episode_row(item),
                )
        return len(episodes)

    async def _fetch_episode_market_data(
        self,
        episodes: list[TradeEpisode],
    ) -> dict[str, list[list[object]]]:
        result: dict[str, list[list[object]]] = {}
        if not episodes:
            return result
        async with BinanceReadOnlyClient(self.settings.resolved_binance_config_path) as client:
            by_symbol: dict[str, list[TradeEpisode]] = {}
            for episode in episodes:
                by_symbol.setdefault(episode.symbol, []).append(episode)
            now = datetime.now(UTC)
            for symbol, symbol_episodes in by_symbol.items():
                start = min(item.opened_at for item in symbol_episodes) - timedelta(days=20)
                end_anchor = max((item.closed_at or now) for item in symbol_episodes)
                end = min(now, end_anchor + timedelta(days=10))
                if end - start <= timedelta(days=45):
                    rows = await self._fetch_klines(client, symbol, start, end)
                    for episode in symbol_episodes:
                        result[episode.episode_id] = rows
                    continue
                for episode in symbol_episodes:
                    episode_start = episode.opened_at - timedelta(days=20)
                    episode_end_anchor = episode.closed_at or now
                    episode_end = min(now, episode_end_anchor + timedelta(days=10))
                    result[episode.episode_id] = await self._fetch_klines(
                        client,
                        symbol,
                        episode_start,
                        episode_end,
                    )
        return result

    async def _fetch_klines(
        self,
        client: BinanceReadOnlyClient,
        symbol: str,
        start: datetime,
        end: datetime,
    ) -> list[list[object]]:
        cursor = int(start.timestamp() * 1000)
        end_ms = int(end.timestamp() * 1000)
        rows: list[list[object]] = []
        while cursor < end_ms:
            page = await client.klines(
                symbol,
                cursor,
                end_ms,
                interval="1m",
                limit=1500,
            )
            if not page:
                break
            rows.extend(page)
            next_cursor = int(str(page[-1][0])) + 60_000
            if next_cursor <= cursor:
                raise TradeReviewError("Binance kline pagination did not advance")
            cursor = next_cursor
            if len(page) < 1500:
                break
        return rows

    def _review_episode(
        self,
        episode: TradeEpisode,
        rows: list[list[object]],
    ) -> tuple[EpisodeReview, dict[str, object]]:
        source = bars_from_binance(rows)
        entry_ms = int(episode.opened_at.timestamp() * 1000)
        exit_time = episode.closed_at or datetime.now(UTC)
        exit_ms = int(exit_time.timestamp() * 1000)
        reads: dict[str, TimeframeRead] = {}
        for timeframe in TIMEFRAME_MINUTES:
            reads[timeframe] = analyze_timeframe(
                source,
                timeframe,
                entry_ms,
                exit_ms,
                float(episode.entry_price),
                episode.direction,
            )
        mfe, mae, mfe_price, mae_price = excursion_metrics(
            source,
            entry_ms,
            exit_ms,
            float(episode.entry_price),
            episode.direction,
        )
        exit_efficiency = None
        if episode.exit_price is not None and mfe > 0:
            realized_move = (
                float(episode.exit_price) - float(episode.entry_price)
                if episode.direction == "long"
                else float(episode.entry_price) - float(episode.exit_price)
            )
            exit_efficiency = max(-1.0, min(1.0, realized_move / mfe))
        dimensions, positives, improvements, missing, outcome = review_dimensions(
            reads,
            episode.direction,
            float(episode.entry_price),
            float(episode.realized_pnl),
            episode.status,
            mfe,
            mae,
            exit_efficiency,
        )
        allocations = self._episode_allocations(episode.episode_id)
        annotations = [item for read in reads.values() for item in read.annotations]
        if source:
            annotations.extend(
                [
                    annotation(
                        "5m",
                        "management",
                        "line",
                        "MFE 最大顺向位置",
                        f"相对入场最大顺向波动 {mfe:.6g}",
                        "replaytutor:deterministic-mfe",
                        1,
                        "after_action",
                        "neutral",
                        [(entry_ms, mfe_price), (exit_ms, mfe_price)],
                    ),
                    annotation(
                        "5m",
                        "management",
                        "line",
                        "MAE 最大逆向位置",
                        f"相对入场最大逆向波动 {mae:.6g}",
                        "replaytutor:deterministic-mae",
                        1,
                        "after_action",
                        "neutral",
                        [(entry_ms, mae_price), (exit_ms, mae_price)],
                    ),
                ]
            )
        review = EpisodeReview.model_validate(
            {
                "episode": episode,
                "process_outcome": outcome,
                "dimensions": dimensions,
                "annotations": annotations,
                "positives": positives,
                "improvements": improvements,
                "missing_context": missing,
            }
        )
        render = {
            "episode": episode.model_dump(mode="json"),
            "process_outcome": outcome,
            "dimensions": [item.model_dump(mode="json") for item in dimensions],
            "annotations": [item.model_dump(mode="json") for item in annotations],
            "allocations": allocations,
            "charts": {
                timeframe: {
                    "bars": list(read.bars),
                    "environment": read.environment,
                    "always_in": read.always_in,
                }
                for timeframe, read in reads.items()
            },
        }
        return review, render

    def _episode_allocations(self, episode_id: str) -> list[dict[str, object]]:
        with connect_database(self.settings.database_path) as connection:
            row = connection.execute(
                "SELECT allocations_json FROM trade_episode WHERE episode_id = ?",
                (episode_id,),
            ).fetchone()
        return list(json.loads(str(row["allocations_json"]))) if row else []

    def _write_sync(
        self,
        sync_id: str,
        start: datetime,
        end: datetime,
        status: str,
        fill_count: int,
        order_count: int,
        income_count: int,
        diagnostics: list[str],
    ) -> None:
        with connect_database(self.settings.database_path) as connection:
            connection.execute(
                """
                INSERT INTO trade_sync (
                    sync_id, market_type, coverage_start, coverage_end, coverage_status,
                    fill_count, order_count, income_count, diagnostics_json, created_at
                ) VALUES (?, 'usdm_perp', ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    sync_id,
                    iso_time(start),
                    iso_time(end),
                    status,
                    fill_count,
                    order_count,
                    income_count,
                    json.dumps(diagnostics),
                    iso_time(datetime.now(UTC)),
                ),
            )

    def scope_value(self, request: ReviewRequest) -> str:
        if request.scope_kind == "today":
            return datetime.now(SHANGHAI).date().isoformat()
        if request.scope_kind == "recent":
            return str(request.count)
        return str(request.episode_id)

    def scope_label(self, request: ReviewRequest) -> str:
        suffix = ""
        if request.symbol:
            suffix += f" · {request.symbol}"
        if request.direction:
            suffix += f" · {request.direction}"
        if request.scope_kind == "today":
            return f"今日交易 {datetime.now(SHANGHAI).date().isoformat()}{suffix}"
        if request.scope_kind == "recent":
            return f"最近 {request.count} 笔已完成交易{suffix}"
        return f"单笔交易 {request.episode_id}{suffix}"


def episode_row(item: EpisodeRecord) -> tuple[object, ...]:
    return (
        item.episode_id,
        item.symbol,
        item.direction,
        item.position_side,
        item.status,
        iso_time(item.opened_at),
        iso_time(item.closed_at) if item.closed_at else None,
        decimal_text(item.entry_price),
        decimal_text(item.exit_price) if item.exit_price is not None else None,
        decimal_text(item.peak_qty),
        decimal_text(item.realized_pnl),
        decimal_text(item.commission),
        json.dumps(item.allocations, separators=(",", ":")),
        iso_time(datetime.now(UTC)),
    )


def episode_contract(row: dict[str, object]) -> TradeEpisode:
    allocations = json.loads(str(row["allocations_json"]))
    return TradeEpisode.model_validate(
        {
            "episode_id": str(row["episode_id"]),
            "symbol": str(row["symbol"]),
            "direction": str(row["direction"]),
            "position_side": str(row["position_side"]),
            "status": str(row["status"]),
            "opened_at": parse_time(str(row["opened_at"])),
            "closed_at": (parse_time(str(row["closed_at"])) if row["closed_at"] else None),
            "entry_price": str(row["entry_price"]),
            "exit_price": str(row["exit_price"]) if row["exit_price"] else None,
            "peak_qty": str(row["peak_qty"]),
            "realized_pnl": str(row["realized_pnl"]),
            "commission": str(row["commission"]),
            "fill_count": len(allocations),
        }
    )


def time_windows(start: datetime, end: datetime) -> list[tuple[int, int]]:
    start_ms = int(start.timestamp() * 1000)
    end_ms = int(end.timestamp() * 1000)
    result: list[tuple[int, int]] = []
    cursor = start_ms
    while cursor < end_ms:
        window_end = min(end_ms, cursor + SEVEN_DAYS_MS - 1)
        result.append((cursor, window_end))
        cursor = window_end + 1
    return result


def dedupe(
    values: list[dict[str, object]],
    key: Any,
) -> list[dict[str, object]]:
    result: dict[object, dict[str, object]] = {}
    for item in values:
        result[key(item)] = item
    return list(result.values())


def excursion_metrics(
    bars: list[Any],
    entry_ms: int,
    exit_ms: int,
    entry: float,
    direction: str,
) -> tuple[float, float, float, float]:
    held = [bar for bar in bars if bar.open_ms <= exit_ms and bar.close_ms >= entry_ms]
    if not held:
        return 0, 0, entry, entry
    max_price = max(bar.high for bar in held)
    min_price = min(bar.low for bar in held)
    if direction == "long":
        return max(0, max_price - entry), max(0, entry - min_price), max_price, min_price
    return max(0, entry - min_price), max(0, max_price - entry), min_price, max_price


def frequent_items(values: Any, limit: int = 3) -> list[str]:
    counts = Counter(values)
    return [item for item, _ in counts.most_common(limit)]


def recurring_patterns(reviews: list[EpisodeReview]) -> list[str]:
    improvements = Counter(item for review in reviews for item in review.improvements)
    repeated = [f"{item} ({count} 笔)" for item, count in improvements.most_common(3) if count >= 2]
    return repeated or ["当前样本尚未形成重复错误模式"]


def ms_time(value: object) -> str:
    return iso_time(datetime.fromtimestamp(int(str(value)) / 1000, tz=UTC))


def iso_time(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)
