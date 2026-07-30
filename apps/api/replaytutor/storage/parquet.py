from __future__ import annotations

import hashlib
import json
import os
import shutil
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

from replaytutor.modules.market_data.models import NormalizedBar

PRICE_TYPE = pa.decimal128(24, 8)
VOLUME_TYPE = pa.decimal128(30, 8)


def canonical_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_bars(path: Path, bars: list[NormalizedBar], metadata: dict[str, str]) -> None:
    schema = pa.schema(
        [
            ("schema_version", pa.string()),
            ("open_time_utc", pa.timestamp("ms", tz="UTC")),
            ("close_time_utc", pa.timestamp("ms", tz="UTC")),
            ("open_raw", PRICE_TYPE),
            ("high_raw", PRICE_TYPE),
            ("low_raw", PRICE_TYPE),
            ("close_raw", PRICE_TYPE),
            ("volume_raw", VOLUME_TYPE),
            ("adjustment_factor", PRICE_TYPE),
            ("open_adjusted", PRICE_TYPE),
            ("high_adjusted", PRICE_TYPE),
            ("low_adjusted", PRICE_TYPE),
            ("close_adjusted", PRICE_TYPE),
            ("source_row_id", pa.string()),
            ("quality_flags", pa.list_(pa.string())),
        ],
        metadata={key.encode(): value.encode() for key, value in metadata.items()},
    )
    records: list[dict[str, Any]] = []
    for bar in bars:
        records.append(
            {
                "schema_version": "1.0",
                "open_time_utc": bar.open_time.astimezone(UTC),
                "close_time_utc": bar.close_time.astimezone(UTC),
                "open_raw": bar.open,
                "high_raw": bar.high,
                "low_raw": bar.low,
                "close_raw": bar.close,
                "volume_raw": bar.volume,
                "adjustment_factor": Decimal("1"),
                "open_adjusted": bar.open,
                "high_adjusted": bar.high,
                "low_adjusted": bar.low,
                "close_adjusted": bar.close,
                "source_row_id": bar.source_row_id,
                "quality_flags": list(bar.quality_flags),
            }
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    table = pa.Table.from_pylist(records, schema=schema)
    pq.write_table(table, path, compression="zstd", version="2.6")
    with path.open("rb") as file:
        os.fsync(file.fileno())


def atomic_snapshot_commit(
    snapshots_dir: Path,
    snapshot_id: str,
    bars: list[NormalizedBar],
    manifest_core: dict[str, object],
) -> tuple[Path, dict[str, object]]:
    final_dir = snapshots_dir / snapshot_id
    staging_dir = snapshots_dir / f".{snapshot_id}.staging"
    if final_dir.exists():
        raise FileExistsError(f"Snapshot already exists: {snapshot_id}")
    if staging_dir.exists():
        shutil.rmtree(staging_dir)
    staging_dir.mkdir(parents=True)
    try:
        parquet_path = staging_dir / "timeframe=1m" / "bars.parquet"
        write_bars(
            parquet_path,
            bars,
            {
                "schema_version": "1.0",
                "source_id": str(manifest_core["source_id"]),
                "instrument_id": str(manifest_core["instrument_id"]),
                "timeframe": "1m",
                "created_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            },
        )
        content_hash = sha256_file(parquet_path)
        manifest_without_hash = {
            **manifest_core,
            "content_hash": content_hash,
            "files": [
                {
                    "path": "timeframe=1m/bars.parquet",
                    "sha256": content_hash,
                    "rows": len(bars),
                }
            ],
        }
        manifest_hash = hashlib.sha256(
            canonical_json(manifest_without_hash).encode("utf-8")
        ).hexdigest()
        manifest = {**manifest_without_hash, "manifest_hash": manifest_hash}
        manifest_path = staging_dir / "manifest.json"
        manifest_path.write_text(
            json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        with manifest_path.open("rb") as file:
            os.fsync(file.fileno())
        os.rename(staging_dir, final_dir)
        directory_fd = os.open(snapshots_dir, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
        return final_dir / "manifest.json", manifest
    except BaseException:
        if staging_dir.exists():
            shutil.rmtree(staging_dir)
        raise
