from __future__ import annotations

import json
import shutil
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import uuid4

import pyarrow as pa
import pyarrow.csv as pa_csv
import pyarrow.parquet as pq

from replaytutor.adapters.market_data.binance import (
    BinancePublicAdapter,
    BinanceUSDMPublicAdapter,
)
from replaytutor.config import Settings
from replaytutor.contracts import (
    Bar,
    BarListResponse,
    CommitImportRequest,
    DataQuality,
    DataSnapshot,
    ImportPreview,
    Instrument,
    PriceValues,
    SnapshotDeleteResponse,
)
from replaytutor.ids import new_id, stable_id
from replaytutor.modules.market_data.models import NormalizedBar, NormalizedInstrument
from replaytutor.modules.market_data.quality import inspect_bars
from replaytutor.storage.database import connect_database
from replaytutor.storage.duckdb_query import (
    count_bars,
    find_bar_index_at_or_after,
    query_bar_slice,
    query_bars,
)
from replaytutor.storage.parquet import atomic_snapshot_commit

MAX_IMPORT_BYTES = 50 * 1024 * 1024
GOLDEN_DATASET_ID = "btcusdt-1m-2025-01"


class MarketDataError(RuntimeError):
    pass


class MarketDataService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.snapshots_dir = settings.resolved_data_dir / "market" / "snapshots"
        self.imports_dir = settings.resolved_data_dir / "imports"

    def list_snapshots(self) -> list[DataSnapshot]:
        with connect_database(self.settings.database_path) as connection:
            rows = connection.execute(
                """
                SELECT ds.*, i.* FROM data_snapshot ds
                JOIN instrument i ON i.instrument_id = ds.instrument_id
                WHERE ds.status = 'ready'
                ORDER BY ds.created_at DESC
                """
            ).fetchall()
        return [self._snapshot_from_row(dict(row)) for row in rows]

    def get_snapshot(self, snapshot_id: str) -> DataSnapshot:
        with connect_database(self.settings.database_path) as connection:
            row = connection.execute(
                """
                SELECT ds.*, i.* FROM data_snapshot ds
                JOIN instrument i ON i.instrument_id = ds.instrument_id
                WHERE ds.snapshot_id = ? AND ds.status = 'ready'
                """,
                (snapshot_id,),
            ).fetchone()
        if row is None:
            raise MarketDataError("Snapshot not found")
        return self._snapshot_from_row(dict(row))

    def delete_snapshot(self, snapshot_id: str) -> SnapshotDeleteResponse:
        snapshot_dir = (self.snapshots_dir / snapshot_id).resolve()
        if snapshot_dir.parent != self.snapshots_dir.resolve():
            raise MarketDataError("Invalid Snapshot path")

        with connect_database(self.settings.database_path) as connection:
            row = connection.execute(
                "SELECT snapshot_id FROM data_snapshot WHERE snapshot_id = ?",
                (snapshot_id,),
            ).fetchone()
            if row is None:
                raise MarketDataError("Snapshot not found")
            session_count = int(
                connection.execute(
                    "SELECT COUNT(*) FROM replay_session WHERE snapshot_id = ?",
                    (snapshot_id,),
                ).fetchone()[0]
            )
        if session_count > 0:
            raise MarketDataError(
                f"Snapshot is used by {session_count} training session(s) and cannot be deleted"
            )

        deleted_at = datetime.now(UTC)
        trash_path: Path | None = None
        if snapshot_dir.is_dir():
            trash_dir = self.settings.resolved_data_dir / "trash" / "market-snapshots"
            trash_dir.mkdir(parents=True, exist_ok=True)
            trash_path = trash_dir / (
                f"{snapshot_id}-{deleted_at.strftime('%Y%m%dT%H%M%SZ')}-{uuid4().hex[:8]}"
            )
            shutil.move(str(snapshot_dir), str(trash_path))

        try:
            with connect_database(self.settings.database_path) as connection:
                connection.execute(
                    "UPDATE data_import SET snapshot_id = NULL WHERE snapshot_id = ?",
                    (snapshot_id,),
                )
                connection.execute(
                    """
                    UPDATE dataset_download_job
                    SET snapshot_id = NULL, error = 'Snapshot deleted by user'
                    WHERE snapshot_id = ?
                    """,
                    (snapshot_id,),
                )
                cursor = connection.execute(
                    "DELETE FROM data_snapshot WHERE snapshot_id = ?",
                    (snapshot_id,),
                )
                if cursor.rowcount != 1:
                    raise MarketDataError("Snapshot not found")
        except BaseException:
            if trash_path is not None and trash_path.exists() and not snapshot_dir.exists():
                shutil.move(str(trash_path), str(snapshot_dir))
            raise

        return SnapshotDeleteResponse(
            snapshot_id=snapshot_id,
            deleted_at=deleted_at,
            trash_path=str(trash_path) if trash_path is not None else None,
        )

    def load_golden_dataset(self) -> DataSnapshot:
        existing = [item for item in self.list_snapshots() if item.source_id == GOLDEN_DATASET_ID]
        if existing:
            return existing[0]
        fixture_dir = Path(__file__).resolve().parents[5] / "tests" / "fixtures" / "market"
        fixture_path = fixture_dir / f"{GOLDEN_DATASET_ID}.parquet"
        fixture_manifest = fixture_dir / f"{GOLDEN_DATASET_ID}.manifest.json"
        if not fixture_path.is_file() or not fixture_manifest.is_file():
            raise MarketDataError(
                "Bundled BTCUSDT dataset is missing; run replaytutor data build-golden"
            )
        expected = json.loads(fixture_manifest.read_text(encoding="utf-8"))
        bars = read_normalized_file(fixture_path)
        if len(bars) != 44_640:
            raise MarketDataError("Bundled BTCUSDT dataset does not contain 44,640 rows")
        return self.commit_snapshot(
            instrument=crypto_btcusdt(),
            bars=bars,
            source_id=GOLDEN_DATASET_ID,
            source_kind="golden",
            provenance=expected,
        )

    async def download_binance(
        self,
        symbol: str,
        start_time: datetime,
        end_time: datetime,
        market_type: str = "SPOT",
        progress: Callable[[int], None] | None = None,
    ) -> DataSnapshot:
        perpetual = market_type == "USDT_PERPETUAL"
        adapter = BinanceUSDMPublicAdapter() if perpetual else BinancePublicAdapter()
        bars = await adapter.fetch_klines(symbol, start_time, end_time, progress=progress)
        instrument = crypto_instrument(symbol, perpetual=perpetual)
        endpoint = (
            "https://fapi.binance.com/fapi/v1/klines"
            if perpetual
            else "https://data-api.binance.vision/api/v3/klines"
        )
        return self.commit_snapshot(
            instrument=instrument,
            bars=bars,
            source_id=f"binance-{'usdm' if perpetual else 'public'}:{symbol}:1m",
            source_kind="binance_usdm" if perpetual else "binance_public",
            provenance={
                "endpoint": endpoint,
                "symbol": symbol,
                "interval": "1m",
                "requested_start": utc_text(start_time),
                "requested_end": utc_text(end_time),
            },
        )

    def commit_snapshot(
        self,
        *,
        instrument: NormalizedInstrument,
        bars: list[NormalizedBar],
        source_id: str,
        source_kind: str,
        provenance: dict[str, object],
    ) -> DataSnapshot:
        bars = sorted(bars, key=lambda item: item.open_time)
        quality = inspect_bars(bars, continuous=instrument.market == "CRYPTO")
        if quality.status == "failed":
            raise MarketDataError(f"Dataset failed quality checks: {', '.join(quality.flags)}")
        snapshot_id = new_id("snp")
        instrument_id = stable_id(
            "ins",
            "replaytutor:instrument",
            f"{instrument.market}:{instrument.venue}:{instrument.symbol}",
        )
        created_at = datetime.now(UTC)
        manifest_path, manifest = atomic_snapshot_commit(
            self.snapshots_dir,
            snapshot_id,
            bars,
            {
                "schema_version": "1.0",
                "snapshot_id": snapshot_id,
                "instrument_id": instrument_id,
                "symbol": instrument.symbol,
                "timeframe": "1m",
                "source_id": source_id,
                "source_kind": source_kind,
                "coverage_start": utc_text(bars[0].open_time),
                "coverage_end": utc_text(bars[-1].close_time),
                "created_at": utc_text(created_at),
                "quality": quality.model_dump(mode="json"),
                "provenance": provenance,
                "immutable": True,
            },
        )
        try:
            with connect_database(self.settings.database_path) as connection:
                connection.execute(
                    """
                    INSERT OR IGNORE INTO instrument (
                        instrument_id, canonical_symbol, display_name, asset_class, market,
                        venue, base_currency, quote_currency, timezone, tick_size, lot_size,
                        price_scale, market_rule_set_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        instrument_id,
                        instrument.symbol,
                        instrument.display_name,
                        instrument.asset_class,
                        instrument.market,
                        instrument.venue,
                        instrument.base_currency,
                        instrument.quote_currency,
                        instrument.timezone,
                        str(instrument.tick_size),
                        str(instrument.lot_size),
                        instrument.price_scale,
                        instrument.market_rule_set_id,
                    ),
                )
                connection.execute(
                    """
                    INSERT INTO data_snapshot (
                        snapshot_id, instrument_id, timeframe, source_id, source_kind,
                        coverage_start, coverage_end, created_at, content_hash, manifest_hash,
                        manifest_path, quality_json, derived_timeframes_json, status
                    ) VALUES (?, ?, '1m', ?, ?, ?, ?, ?, ?, ?, ?, ?, '[]', 'ready')
                    """,
                    (
                        snapshot_id,
                        instrument_id,
                        source_id,
                        source_kind,
                        manifest["coverage_start"],
                        manifest["coverage_end"],
                        manifest["created_at"],
                        manifest["content_hash"],
                        manifest["manifest_hash"],
                        str(manifest_path),
                        quality.model_dump_json(),
                    ),
                )
        except BaseException:
            shutil.rmtree(manifest_path.parent, ignore_errors=True)
            raise
        return self.get_snapshot(snapshot_id)

    def query_snapshot_bars(
        self,
        snapshot_id: str,
        *,
        start: datetime | None,
        end: datetime | None,
        limit: int,
    ) -> BarListResponse:
        snapshot = self.get_snapshot(snapshot_id)
        parquet_path = self.snapshots_dir / snapshot_id / "timeframe=1m" / "bars.parquet"
        rows = query_bars(parquet_path, start=start, end=end, limit=limit)
        has_more = len(rows) > limit
        bars = [self._bar_from_row(snapshot.instrument.instrument_id, row) for row in rows[:limit]]
        return BarListResponse(
            snapshot_id=snapshot_id,
            timeframe="1m",
            bars=bars,
            has_more=has_more,
        )

    def snapshot_bar_count(self, snapshot_id: str) -> int:
        self.get_snapshot(snapshot_id)
        return count_bars(self._snapshot_parquet_path(snapshot_id))

    def snapshot_bar_index_at_or_after(
        self,
        snapshot_id: str,
        start_time: datetime,
    ) -> int:
        self.get_snapshot(snapshot_id)
        return find_bar_index_at_or_after(
            self._snapshot_parquet_path(snapshot_id),
            start_time,
        )

    def query_snapshot_bar_slice(
        self,
        snapshot_id: str,
        *,
        offset: int,
        limit: int,
    ) -> list[Bar]:
        snapshot = self.get_snapshot(snapshot_id)
        rows = query_bar_slice(
            self._snapshot_parquet_path(snapshot_id),
            offset=offset,
            limit=limit,
        )
        return [
            self._bar_from_row(snapshot.instrument.instrument_id, row)
            for row in rows
        ]

    def _snapshot_parquet_path(self, snapshot_id: str) -> Path:
        return self.snapshots_dir / snapshot_id / "timeframe=1m" / "bars.parquet"

    def stage_import(self, filename: str, content: bytes) -> ImportPreview:
        if not filename.lower().endswith((".csv", ".parquet")):
            raise MarketDataError("Only CSV and Parquet files are supported")
        if len(content) > MAX_IMPORT_BYTES:
            raise MarketDataError("Import exceeds the 50 MiB MVP limit")
        import_id = new_id("imp")
        staging_dir = self.imports_dir / import_id
        staging_dir.mkdir(parents=True, exist_ok=False)
        staged_path = staging_dir / Path(filename).name
        staged_path.write_bytes(content)
        try:
            table = read_table(staged_path)
            mapping = detect_columns(table.column_names)
            bars = table_to_bars(table, mapping)
            quality = inspect_bars(bars, continuous=False)
            status = "preview_ready" if quality.status != "failed" else "failed"
            error = None if status == "preview_ready" else "File failed quality checks"
            sample = stringify_rows(table.slice(0, 5).to_pylist())
        except Exception as error_value:
            mapping = {}
            quality = DataQuality(
                status="failed",
                row_count=0,
                duplicate_count=0,
                gap_count=0,
                invalid_ohlc_count=0,
                flags=["parse_error"],
            )
            status = "failed"
            error = str(error_value)
            sample = []
        preview = ImportPreview(
            import_id=import_id,
            filename=Path(filename).name,
            status=status,
            detected_columns=mapping,
            sample_rows=sample,
            quality=quality,
            error=error,
        )
        with connect_database(self.settings.database_path) as connection:
            connection.execute(
                """
                INSERT INTO data_import (
                    import_id, filename, staged_path, status, detected_columns_json,
                    sample_rows_json, quality_json, error, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    import_id,
                    preview.filename,
                    str(staged_path),
                    status,
                    json.dumps(mapping),
                    json.dumps(sample),
                    quality.model_dump_json(),
                    error,
                    utc_text(datetime.now(UTC)),
                ),
            )
        return preview

    def get_import(self, import_id: str) -> ImportPreview:
        with connect_database(self.settings.database_path) as connection:
            row = connection.execute(
                "SELECT * FROM data_import WHERE import_id = ?", (import_id,)
            ).fetchone()
        if row is None:
            raise MarketDataError("Import not found")
        item = dict(row)
        return ImportPreview(
            import_id=item["import_id"],
            filename=item["filename"],
            status=item["status"],
            detected_columns=json.loads(item["detected_columns_json"]),
            sample_rows=json.loads(item["sample_rows_json"]),
            quality=DataQuality.model_validate_json(item["quality_json"]),
            error=item["error"],
        )

    def commit_import(self, import_id: str, request: CommitImportRequest) -> DataSnapshot:
        with connect_database(self.settings.database_path) as connection:
            row = connection.execute(
                "SELECT * FROM data_import WHERE import_id = ?", (import_id,)
            ).fetchone()
        if row is None:
            raise MarketDataError("Import not found")
        item = dict(row)
        if item["status"] != "preview_ready":
            raise MarketDataError("Import is not ready to commit")
        mapping = json.loads(item["detected_columns_json"])
        bars = table_to_bars(read_table(Path(item["staged_path"])), mapping)
        instrument = file_instrument(request)
        snapshot = self.commit_snapshot(
            instrument=instrument,
            bars=bars,
            source_id=f"file:{item['filename']}",
            source_kind="file_import",
            provenance={
                "filename": item["filename"],
                "adjustment": request.adjustment,
                "timezone": request.timezone,
            },
        )
        with connect_database(self.settings.database_path) as connection:
            connection.execute(
                "UPDATE data_import SET status = 'committed', snapshot_id = ? WHERE import_id = ?",
                (snapshot.snapshot_id, import_id),
            )
        return snapshot

    def _snapshot_from_row(self, row: dict[str, Any]) -> DataSnapshot:
        instrument = Instrument(
            instrument_id=row["instrument_id"],
            asset_class=row["asset_class"],
            market=row["market"],
            venue=row["venue"],
            canonical_symbol=row["canonical_symbol"],
            display_name=row["display_name"],
            base_currency=row["base_currency"],
            quote_currency=row["quote_currency"],
            timezone=row["timezone"],
            tick_size=row["tick_size"],
            lot_size=row["lot_size"],
            price_scale=row["price_scale"],
            market_rule_set_id=row["market_rule_set_id"],
        )
        return DataSnapshot(
            snapshot_id=row["snapshot_id"],
            instrument=instrument,
            timeframe=row["timeframe"],
            source_id=row["source_id"],
            source_kind=row["source_kind"],
            coverage_start=row["coverage_start"],
            coverage_end=row["coverage_end"],
            created_at=row["created_at"],
            content_hash=row["content_hash"],
            manifest_hash=row["manifest_hash"],
            quality=DataQuality.model_validate_json(row["quality_json"]),
            derived_timeframes=json.loads(row["derived_timeframes_json"]),
        )

    def _bar_from_row(self, instrument_id: str, row: tuple[object, ...]) -> Bar:
        open_time = as_datetime(row[0])
        return Bar(
            bar_id=stable_id("bar", instrument_id, utc_text(open_time)),
            instrument_id=instrument_id,
            timeframe="1m",
            open_time=open_time,
            close_time=as_datetime(row[1]),
            raw=PriceValues(
                open=decimal_text(row[2]),
                high=decimal_text(row[3]),
                low=decimal_text(row[4]),
                close=decimal_text(row[5]),
                volume=decimal_text(row[6]),
            ),
            quality_flags=[str(flag) for flag in row[7]] if isinstance(row[7], list) else [],
        )


def utc_text(value: datetime) -> str:
    return value.astimezone(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def as_datetime(value: object) -> datetime:
    if not isinstance(value, datetime):
        raise MarketDataError("Expected a timestamp value")
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def decimal_text(value: object) -> str:
    result = format(Decimal(str(value)), "f")
    return result.rstrip("0").rstrip(".") if "." in result else result


def crypto_btcusdt() -> NormalizedInstrument:
    return crypto_instrument("BTCUSDT")


def crypto_instrument(
    symbol: str,
    *,
    perpetual: bool = False,
) -> NormalizedInstrument:
    quote = "USDT" if symbol.endswith("USDT") else symbol[-3:]
    base = symbol[: -len(quote)]
    return NormalizedInstrument(
        symbol=symbol,
        display_name=f"{base} / {quote}",
        market="CRYPTO",
        asset_class="crypto_perpetual" if perpetual else "crypto_spot",
        venue="BINANCE_USDM" if perpetual else "BINANCE",
        base_currency=base,
        quote_currency=quote,
        timezone="UTC",
        tick_size=Decimal("0.01"),
        lot_size=Decimal("0.00001"),
        price_scale=2,
        market_rule_set_id="binance_usdm_perpetual_v1" if perpetual else "crypto_spot_v1",
    )


def file_instrument(request: CommitImportRequest) -> NormalizedInstrument:
    tick_exponent = Decimal(request.tick_size).as_tuple().exponent
    price_scale = max(0, -tick_exponent) if isinstance(tick_exponent, int) else 0
    return NormalizedInstrument(
        symbol=request.symbol.upper(),
        display_name=request.symbol.upper(),
        market=request.market,
        asset_class="equity" if request.market == "CN" else "crypto_spot",
        venue=request.venue.upper(),
        base_currency=request.symbol.upper(),
        quote_currency=request.quote_currency.upper(),
        timezone=request.timezone,
        tick_size=Decimal(request.tick_size),
        lot_size=Decimal(request.lot_size),
        price_scale=price_scale,
        market_rule_set_id="cn_equity_v1" if request.market == "CN" else "crypto_spot_v1",
    )


def read_table(path: Path) -> pa.Table:
    if path.suffix.lower() == ".parquet":
        return pq.read_table(path)
    return pa_csv.read_csv(path)


def detect_columns(columns: list[str]) -> dict[str, str]:
    aliases = {
        "open_time": ("open_time", "open_time_utc", "timestamp", "datetime", "date"),
        "close_time": ("close_time", "close_time_utc"),
        "open": ("open", "open_raw"),
        "high": ("high", "high_raw"),
        "low": ("low", "low_raw"),
        "close": ("close", "close_raw"),
        "volume": ("volume", "volume_raw", "vol"),
    }
    lookup = {column.lower(): column for column in columns}
    mapping: dict[str, str] = {}
    for target, candidates in aliases.items():
        match = next((lookup[name] for name in candidates if name in lookup), None)
        if match is not None:
            mapping[target] = match
    required = {"open_time", "open", "high", "low", "close", "volume"}
    missing = required - mapping.keys()
    if missing:
        raise MarketDataError(f"Missing required columns: {', '.join(sorted(missing))}")
    return mapping


def table_to_bars(table: pa.Table, mapping: dict[str, str]) -> list[NormalizedBar]:
    bars: list[NormalizedBar] = []
    for index, row in enumerate(table.to_pylist()):
        open_time = parse_time(row[mapping["open_time"]])
        close_column = mapping.get("close_time")
        close_time = (
            parse_time(row[close_column])
            if close_column is not None
            else open_time.replace(microsecond=0) + timedelta(minutes=1, milliseconds=-1)
        )
        bars.append(
            NormalizedBar(
                open_time=open_time,
                close_time=close_time,
                open=Decimal(str(row[mapping["open"]])),
                high=Decimal(str(row[mapping["high"]])),
                low=Decimal(str(row[mapping["low"]])),
                close=Decimal(str(row[mapping["close"]])),
                volume=Decimal(str(row[mapping["volume"]])),
                source_row_id=str(index),
            )
        )
    return bars


def parse_time(value: object) -> datetime:
    if isinstance(value, datetime):
        return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
    if isinstance(value, (int, float, Decimal)):
        numeric = float(value)
        if numeric > 10_000_000_000:
            numeric /= 1000
        return datetime.fromtimestamp(numeric, tz=UTC)
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    return parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed.astimezone(UTC)


def stringify_rows(rows: list[dict[str, object]]) -> list[dict[str, str]]:
    return [{key: str(value) for key, value in row.items()} for row in rows]


def read_normalized_file(path: Path) -> list[NormalizedBar]:
    table = read_table(path)
    return table_to_bars(table, detect_columns(table.column_names))
