from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal
from typing import Literal, cast

from replaytutor.config import Settings
from replaytutor.contracts import (
    MarketDepthImportRequest,
    MarketDepthInputLevel,
    MarketDepthLevel,
    MarketDepthResponse,
    MarketDepthSnapshot,
    ReplaySession,
)
from replaytutor.ids import new_id
from replaytutor.modules.market_data.service import MarketDataService, utc_text
from replaytutor.storage.database import connect_database

STALE_AFTER_SECONDS = 60.0


class MarketDepthError(RuntimeError):
    pass


class MarketDepthService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.market_data = MarketDataService(settings)

    def import_snapshot(
        self,
        snapshot_id: str,
        payload: MarketDepthImportRequest,
        *,
        source_kind: Literal["binance_rest", "file_import"] = "file_import",
    ) -> MarketDepthSnapshot:
        snapshot = self.market_data.get_snapshot(snapshot_id)
        captured_at = payload.captured_at
        if captured_at.tzinfo is None:
            raise MarketDepthError("Market depth captured_at must include a timezone")
        captured_at = captured_at.astimezone(UTC)
        if captured_at < snapshot.coverage_start or captured_at > snapshot.coverage_end:
            raise MarketDepthError("Market depth timestamp must be inside dataset coverage")

        bids = self._normalize(payload.bids, descending=True)
        asks = self._normalize(payload.asks, descending=False)
        if Decimal(bids[0].price) >= Decimal(asks[0].price):
            raise MarketDepthError("Market depth is crossed or locked")

        depth_id = new_id("dpt")
        with connect_database(self.settings.database_path) as connection:
            connection.execute(
                """
                INSERT INTO market_depth_snapshot (
                    depth_id, snapshot_id, instrument_id, captured_at,
                    source_kind, last_update_id, bids_json, asks_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    depth_id,
                    snapshot_id,
                    snapshot.instrument.instrument_id,
                    utc_text(captured_at),
                    source_kind,
                    payload.last_update_id,
                    json.dumps([level.model_dump() for level in bids], separators=(",", ":")),
                    json.dumps([level.model_dump() for level in asks], separators=(",", ":")),
                    utc_text(datetime.now(UTC)),
                ),
            )
        return self._build_snapshot(
            depth_id=depth_id,
            snapshot_id=snapshot_id,
            instrument_id=snapshot.instrument.instrument_id,
            captured_at=captured_at,
            source_kind=source_kind,
            last_update_id=payload.last_update_id,
            bids=bids,
            asks=asks,
        )

    def for_session(self, session: ReplaySession, levels: int) -> MarketDepthResponse:
        with connect_database(self.settings.database_path) as connection:
            row = connection.execute(
                """
                SELECT * FROM market_depth_snapshot
                WHERE snapshot_id = ? AND captured_at <= ?
                ORDER BY captured_at DESC, depth_id DESC
                LIMIT 1
                """,
                (session.snapshot_id, utc_text(session.frame.visible_at.astimezone(UTC))),
            ).fetchone()
        if row is None:
            return MarketDepthResponse(
                session_id=session.session_id,
                frame_id=session.frame.frame_id,
                visible_at=session.frame.visible_at,
                status="unavailable",
                reason="historical_depth_not_captured",
            )

        captured_at = datetime.fromisoformat(str(row["captured_at"]).replace("Z", "+00:00"))
        age_seconds = max(0.0, (session.frame.visible_at - captured_at).total_seconds())
        bids = [MarketDepthLevel.model_validate(item) for item in json.loads(row["bids_json"])][
            :levels
        ]
        asks = [MarketDepthLevel.model_validate(item) for item in json.loads(row["asks_json"])][
            :levels
        ]
        depth = self._build_snapshot(
            depth_id=str(row["depth_id"]),
            snapshot_id=str(row["snapshot_id"]),
            instrument_id=str(row["instrument_id"]),
            captured_at=captured_at,
            source_kind=cast(Literal["binance_rest", "file_import"], str(row["source_kind"])),
            last_update_id=row["last_update_id"],
            bids=bids,
            asks=asks,
        )
        stale = age_seconds > STALE_AFTER_SECONDS
        return MarketDepthResponse(
            session_id=session.session_id,
            frame_id=session.frame.frame_id,
            visible_at=session.frame.visible_at,
            status="stale" if stale else "available",
            reason="depth_snapshot_is_stale" if stale else None,
            age_seconds=age_seconds,
            depth=depth,
        )

    @staticmethod
    def _normalize(
        raw_levels: list[MarketDepthInputLevel], *, descending: bool
    ) -> list[MarketDepthLevel]:
        quantities: dict[Decimal, Decimal] = {}
        for level in raw_levels:
            price = Decimal(level.price)
            quantity = Decimal(level.quantity)
            if price <= 0 or quantity < 0:
                raise MarketDepthError(
                    "Market depth prices must be positive and quantities non-negative"
                )
            if quantity == 0:
                continue
            quantities[price] = quantity
        if not quantities:
            raise MarketDepthError("Market depth side has no positive quantity")

        cumulative_quantity = Decimal(0)
        cumulative_notional = Decimal(0)
        result: list[MarketDepthLevel] = []
        for price in sorted(quantities, reverse=descending):
            quantity = quantities[price]
            notional = price * quantity
            cumulative_quantity += quantity
            cumulative_notional += notional
            result.append(
                MarketDepthLevel(
                    price=str(price),
                    quantity=str(quantity),
                    cumulative_quantity=str(cumulative_quantity),
                    notional=str(notional),
                    cumulative_notional=str(cumulative_notional),
                )
            )
        return result

    @staticmethod
    def _build_snapshot(
        *,
        depth_id: str,
        snapshot_id: str,
        instrument_id: str,
        captured_at: datetime,
        source_kind: Literal["binance_rest", "file_import"],
        last_update_id: int | None,
        bids: list[MarketDepthLevel],
        asks: list[MarketDepthLevel],
    ) -> MarketDepthSnapshot:
        best_bid = Decimal(bids[0].price)
        best_ask = Decimal(asks[0].price)
        spread = best_ask - best_bid
        return MarketDepthSnapshot(
            depth_id=depth_id,
            snapshot_id=snapshot_id,
            instrument_id=instrument_id,
            captured_at=captured_at,
            source_kind=source_kind,
            last_update_id=last_update_id,
            bids=bids,
            asks=asks,
            best_bid=str(best_bid),
            best_ask=str(best_ask),
            spread=str(spread),
            midpoint=str((best_bid + best_ask) / Decimal(2)),
        )
