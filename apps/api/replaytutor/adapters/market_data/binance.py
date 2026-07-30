from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from decimal import Decimal

import httpx

from replaytutor.modules.market_data.models import NormalizedBar


class BinanceAdapterError(RuntimeError):
    pass


class BinancePublicAdapter:
    base_url = "https://data-api.binance.vision"

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._client = client

    async def fetch_klines(
        self,
        symbol: str,
        start_time: datetime,
        end_time: datetime,
    ) -> list[NormalizedBar]:
        if start_time.tzinfo is None or end_time.tzinfo is None:
            raise ValueError("Binance time range must be timezone-aware")
        start_ms = int(start_time.astimezone(UTC).timestamp() * 1000)
        end_ms = int(end_time.astimezone(UTC).timestamp() * 1000)
        if start_ms >= end_ms:
            raise ValueError("start_time must be before end_time")

        owns_client = self._client is None
        client = self._client or httpx.AsyncClient(base_url=self.base_url, timeout=30)
        bars: list[NormalizedBar] = []
        cursor = start_ms
        try:
            while cursor < end_ms:
                payload = await self._request_page(client, symbol, cursor, end_ms - 1)
                if not payload:
                    break
                for row in payload:
                    open_ms = int(str(row[0]))
                    if open_ms >= end_ms:
                        continue
                    bars.append(
                        NormalizedBar(
                            open_time=datetime.fromtimestamp(open_ms / 1000, tz=UTC),
                            open=Decimal(str(row[1])),
                            high=Decimal(str(row[2])),
                            low=Decimal(str(row[3])),
                            close=Decimal(str(row[4])),
                            volume=Decimal(str(row[5])),
                            close_time=datetime.fromtimestamp(int(str(row[6])) / 1000, tz=UTC),
                            source_row_id=str(open_ms),
                        )
                    )
                next_cursor = int(str(payload[-1][0])) + 60_000
                if next_cursor <= cursor:
                    raise BinanceAdapterError("Binance pagination did not advance")
                cursor = next_cursor
                if len(payload) < 1000:
                    break
        finally:
            if owns_client:
                await client.aclose()
        return bars

    async def _request_page(
        self,
        client: httpx.AsyncClient,
        symbol: str,
        start_ms: int,
        end_ms: int,
    ) -> list[list[object]]:
        for attempt in range(4):
            response = await client.get(
                "/api/v3/klines",
                params={
                    "symbol": symbol,
                    "interval": "1m",
                    "startTime": start_ms,
                    "endTime": end_ms,
                    "limit": 1000,
                },
            )
            if response.status_code == 429:
                retry_after = response.headers.get("Retry-After")
                delay = float(retry_after) if retry_after else min(2**attempt, 8)
                if attempt == 3:
                    raise BinanceAdapterError("Binance rate limit retry budget exhausted")
                await asyncio.sleep(delay)
                continue
            if response.status_code == 418:
                raise BinanceAdapterError("Binance temporarily banned this IP after rate limits")
            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as error:
                raise BinanceAdapterError(
                    f"Binance returned HTTP {response.status_code}"
                ) from error
            result = response.json()
            if not isinstance(result, list):
                raise BinanceAdapterError("Binance returned an invalid kline payload")
            return result
        raise BinanceAdapterError("Binance request failed")
