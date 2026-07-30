from __future__ import annotations

from datetime import datetime
from pathlib import Path

import duckdb


def count_bars(parquet_path: Path) -> int:
    with duckdb.connect(":memory:") as connection:
        row = connection.execute(
            "SELECT count(*) FROM read_parquet(?)",
            [str(parquet_path)],
        ).fetchone()
    if row is None:
        return 0
    return int(row[0])


def query_bar_slice(
    parquet_path: Path,
    *,
    offset: int,
    limit: int,
) -> list[tuple[object, ...]]:
    if offset < 0 or limit < 1:
        raise ValueError("Bar slice requires a non-negative offset and positive limit")
    sql = """
        SELECT open_time_utc, close_time_utc, open_raw, high_raw, low_raw,
               close_raw, volume_raw, quality_flags
        FROM read_parquet(?)
        ORDER BY open_time_utc
        LIMIT ? OFFSET ?
    """
    with duckdb.connect(":memory:") as connection:
        return connection.execute(sql, [str(parquet_path), limit, offset]).fetchall()


def query_bars(
    parquet_path: Path,
    *,
    start: datetime | None,
    end: datetime | None,
    limit: int,
) -> list[tuple[object, ...]]:
    clauses: list[str] = []
    parameters: list[object] = [str(parquet_path)]
    if start is not None:
        clauses.append("open_time_utc >= ?")
        parameters.append(start)
    if end is not None:
        clauses.append("close_time_utc <= ?")
        parameters.append(end)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    parameters.append(limit + 1)
    sql = f"""
        SELECT open_time_utc, close_time_utc, open_raw, high_raw, low_raw,
               close_raw, volume_raw, quality_flags
        FROM read_parquet(?)
        {where}
        ORDER BY open_time_utc
        LIMIT ?
    """
    with duckdb.connect(":memory:") as connection:
        return connection.execute(sql, parameters).fetchall()
