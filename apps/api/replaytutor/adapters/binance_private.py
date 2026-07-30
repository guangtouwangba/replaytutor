from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import httpx


class BinanceReadOnlyError(RuntimeError):
    pass


def load_binance_credentials(config_path: Path) -> tuple[str, str, bool]:
    if not config_path.is_file():
        raise BinanceReadOnlyError(f"Binance credential file is missing: {config_path}")
    try:
        document = json.loads(config_path.read_text(encoding="utf-8"))
        config = document["binance"]
        api_key = str(config["api_key"]).strip()
        api_secret = str(config["api_secret"]).strip()
        testnet = bool(config.get("testnet", False))
    except (KeyError, TypeError, json.JSONDecodeError) as exc:
        raise BinanceReadOnlyError("Binance credential file is invalid") from exc
    if not api_key or not api_secret:
        raise BinanceReadOnlyError("Binance credentials are empty")
    return api_key, api_secret, testnet


class BinanceReadOnlyClient:
    """Binance client that intentionally exposes signed GET requests only."""

    def __init__(
        self,
        config_path: Path,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self.api_key, self._api_secret, self.testnet = load_binance_credentials(config_path)
        if self.testnet:
            raise BinanceReadOnlyError("Trade-review imports require a Binance mainnet read key")
        self._client = http_client
        self._owns_client = http_client is None

    async def __aenter__(self) -> BinanceReadOnlyClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=30)
        return self

    async def __aexit__(self, *_args: object) -> None:
        if self._owns_client and self._client is not None:
            await self._client.aclose()
            self._client = None

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            raise RuntimeError("BinanceReadOnlyClient must be used as an async context manager")
        return self._client

    async def signed_get(
        self,
        base_url: str,
        path: str,
        params: Mapping[str, object] | None = None,
        *,
        time_path: str,
        max_attempts: int = 5,
    ) -> Any:
        base_payload: dict[str, str | int | float | bool] = {
            key: value
            for key, raw_value in (params or {}).items()
            if isinstance((value := raw_value), (str, int, float, bool))
        }
        safe_endpoint = f"{base_url}{path}"
        response: httpx.Response | None = None
        for attempt in range(max_attempts):
            payload = {
                **base_payload,
                "timestamp": await self.server_time(base_url, time_path),
                "recvWindow": 10_000,
            }
            query = urlencode(payload)
            signature = hmac.new(
                self._api_secret.encode(),
                query.encode(),
                hashlib.sha256,
            ).hexdigest()
            response = await self.client.get(
                safe_endpoint,
                params={**payload, "signature": signature},
                headers={"X-MBX-APIKEY": self.api_key},
            )
            if response.status_code in {418, 429}:
                retry_after = float(response.headers.get("Retry-After", "1"))
                await asyncio.sleep(min(max(retry_after, 0), 30))
                continue
            try:
                body = response.json()
            except ValueError:
                body = {}
            if (
                response.status_code >= 400
                and isinstance(body, dict)
                and body.get("code") == -1021
                and attempt + 1 < max_attempts
            ):
                await asyncio.sleep(0.1)
                continue
            break
        if response is None:
            raise BinanceReadOnlyError(f"{path} did not return a response")
        if response.status_code >= 400:
            code: object = response.status_code
            message = "Binance read request failed"
            try:
                body = response.json()
                code = body.get("code", code)
                message = str(body.get("msg", message))
            except (ValueError, AttributeError):
                pass
            raise BinanceReadOnlyError(f"{path} failed ({code}): {message}")
        return response.json()

    async def server_time(self, base_url: str, time_path: str) -> int:
        response = await self.client.get(f"{base_url}{time_path}")
        response.raise_for_status()
        return int(response.json()["serverTime"])

    async def check_permissions(self) -> dict[str, object]:
        body = await self.signed_get(
            "https://api.binance.com",
            "/sapi/v1/account/apiRestrictions",
            time_path="/api/v3/time",
        )
        return {
            "readable": True,
            "mainnet": True,
            "read_enabled": bool(body.get("enableReading")),
            "futures_trade_enabled": bool(body.get("enableFutures")),
            "withdrawals_enabled": bool(body.get("enableWithdrawals")),
            "ip_restricted": bool(body.get("ipRestrict")),
            "diagnostics": (
                []
                if body.get("ipRestrict")
                else ["API key is not restricted to trusted IP addresses"]
            ),
        }

    async def user_trades(
        self,
        start_ms: int,
        end_ms: int,
        *,
        symbol: str | None = None,
        limit: int = 1000,
    ) -> list[dict[str, object]]:
        params: dict[str, object] = {
            "startTime": start_ms,
            "endTime": end_ms,
            "limit": limit,
        }
        if symbol:
            params["symbol"] = symbol
        body = await self.signed_get(
            "https://fapi.binance.com",
            "/fapi/v1/userTrades",
            params,
            time_path="/fapi/v1/time",
        )
        return list(body)

    async def all_orders(
        self,
        symbol: str,
        start_ms: int,
        end_ms: int,
        *,
        limit: int = 1000,
    ) -> list[dict[str, object]]:
        body = await self.signed_get(
            "https://fapi.binance.com",
            "/fapi/v1/allOrders",
            {
                "symbol": symbol,
                "startTime": start_ms,
                "endTime": end_ms,
                "limit": limit,
            },
            time_path="/fapi/v1/time",
        )
        return list(body)

    async def income(
        self,
        start_ms: int,
        end_ms: int,
        *,
        limit: int = 1000,
    ) -> list[dict[str, object]]:
        body = await self.signed_get(
            "https://fapi.binance.com",
            "/fapi/v1/income",
            {"startTime": start_ms, "endTime": end_ms, "limit": limit},
            time_path="/fapi/v1/time",
        )
        return list(body)

    async def klines(
        self,
        symbol: str,
        start_ms: int,
        end_ms: int,
        *,
        interval: str = "1m",
        limit: int = 1500,
    ) -> list[list[object]]:
        response = await self.client.get(
            "https://fapi.binance.com/fapi/v1/klines",
            params={
                "symbol": symbol,
                "interval": interval,
                "startTime": start_ms,
                "endTime": end_ms,
                "limit": limit,
            },
        )
        if response.status_code >= 400:
            raise BinanceReadOnlyError(f"/fapi/v1/klines failed ({response.status_code})")
        return list(response.json())

    async def request_trade_export(self, start: datetime, end: datetime) -> str:
        body = await self.signed_get(
            "https://fapi.binance.com",
            "/fapi/v1/trade/asyn",
            {
                "startTime": int(start.astimezone(UTC).timestamp() * 1000),
                "endTime": int(end.astimezone(UTC).timestamp() * 1000),
            },
            time_path="/fapi/v1/time",
        )
        return str(body["downloadId"])

    async def trade_export_status(self, download_id: str) -> dict[str, object]:
        body = await self.signed_get(
            "https://fapi.binance.com",
            "/fapi/v1/trade/asyn/id",
            {"downloadId": download_id},
            time_path="/fapi/v1/time",
        )
        return dict(body)
