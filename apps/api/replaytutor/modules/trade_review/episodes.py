from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from replaytutor.ids import stable_id


@dataclass(frozen=True)
class FillRecord:
    fill_id: str
    symbol: str
    trade_id: str
    order_id: str
    side: str
    position_side: str
    price: Decimal
    qty: Decimal
    commission: Decimal
    realized_pnl: Decimal
    executed_at: datetime
    is_maker: bool


@dataclass(frozen=True)
class EpisodeRecord:
    episode_id: str
    symbol: str
    direction: str
    position_side: str
    status: str
    opened_at: datetime
    closed_at: datetime | None
    entry_price: Decimal
    exit_price: Decimal | None
    peak_qty: Decimal
    realized_pnl: Decimal
    commission: Decimal
    allocations: tuple[dict[str, str | bool], ...]


@dataclass
class _EpisodeBuilder:
    symbol: str
    direction: str
    position_side: str
    opened_at: datetime
    entry_qty: Decimal
    entry_value: Decimal
    exit_qty: Decimal
    exit_value: Decimal
    peak_qty: Decimal
    realized_pnl: Decimal
    commission: Decimal
    allocations: list[dict[str, str | bool]]


def position_delta(fill: FillRecord) -> Decimal:
    if fill.position_side == "LONG":
        return fill.qty if fill.side == "BUY" else -fill.qty
    if fill.position_side == "SHORT":
        return -fill.qty if fill.side == "SELL" else fill.qty
    return fill.qty if fill.side == "BUY" else -fill.qty


def reconstruct_episodes(fills: list[FillRecord]) -> list[EpisodeRecord]:
    grouped: dict[tuple[str, str], list[FillRecord]] = {}
    for fill in fills:
        grouped.setdefault((fill.symbol, fill.position_side), []).append(fill)

    episodes: list[EpisodeRecord] = []
    for _, group in sorted(grouped.items()):
        ordered = sorted(group, key=lambda item: (item.executed_at, int(item.trade_id)))
        episodes.extend(_reconstruct_group(ordered))
    return sorted(episodes, key=lambda item: item.opened_at)


def _reconstruct_group(fills: list[FillRecord]) -> list[EpisodeRecord]:
    result: list[EpisodeRecord] = []
    position = Decimal(0)
    current: _EpisodeBuilder | None = None

    def begin(fill: FillRecord, qty: Decimal, delta: Decimal, commission: Decimal) -> None:
        nonlocal current, position
        direction = "long" if delta > 0 else "short"
        current = _EpisodeBuilder(
            symbol=fill.symbol,
            direction=direction,
            position_side=fill.position_side,
            opened_at=fill.executed_at,
            entry_qty=qty,
            entry_value=qty * fill.price,
            exit_qty=Decimal(0),
            exit_value=Decimal(0),
            peak_qty=qty,
            realized_pnl=Decimal(0),
            commission=commission,
            allocations=[allocation(fill, "open", qty, commission, Decimal(0))],
        )
        position = qty if direction == "long" else -qty

    def finish(closed_at: datetime | None) -> None:
        nonlocal current
        if current is None:
            return
        entry_qty = current.entry_qty
        exit_qty = current.exit_qty
        opened_at = current.opened_at
        direction = current.direction
        symbol = current.symbol
        position_side = current.position_side
        first = current.allocations[0]
        episode_id = stable_id(
            "eps",
            "replaytutor:binance-episode",
            f"{symbol}:{position_side}:{direction}:{first['fill_id']}",
        )
        result.append(
            EpisodeRecord(
                episode_id=episode_id,
                symbol=symbol,
                direction=direction,
                position_side=position_side,
                status="closed" if closed_at else "open",
                opened_at=opened_at,
                closed_at=closed_at,
                entry_price=current.entry_value / entry_qty,
                exit_price=(current.exit_value / exit_qty if exit_qty else None),
                peak_qty=current.peak_qty,
                realized_pnl=current.realized_pnl,
                commission=current.commission,
                allocations=tuple(current.allocations),
            )
        )
        current = None

    for fill in fills:
        delta = position_delta(fill)
        if delta == 0:
            continue
        if position == 0:
            begin(fill, abs(delta), delta, fill.commission)
            continue
        if (position > 0) == (delta > 0):
            assert current is not None
            qty = abs(delta)
            current.entry_qty += qty
            current.entry_value += qty * fill.price
            current.commission += fill.commission
            current.allocations.append(allocation(fill, "add", qty, fill.commission, Decimal(0)))
            position += delta
            current.peak_qty = max(current.peak_qty, abs(position))
            continue

        assert current is not None
        closing_qty = min(abs(position), abs(delta))
        ratio = closing_qty / fill.qty
        close_commission = fill.commission * ratio
        current.exit_qty += closing_qty
        current.exit_value += closing_qty * fill.price
        current.realized_pnl += fill.realized_pnl
        current.commission += close_commission
        role = "close" if closing_qty == abs(position) else "reduce"
        current.allocations.append(
            allocation(
                fill,
                role,
                closing_qty,
                close_commission,
                fill.realized_pnl,
            )
        )
        old_position = position
        position += delta
        if position == 0:
            finish(fill.executed_at)
            continue
        if (old_position > 0) != (position > 0):
            residual = abs(position)
            finish(fill.executed_at)
            residual_commission = fill.commission - close_commission
            residual_delta = residual if position > 0 else -residual
            begin(fill, residual, residual_delta, residual_commission)

    if current is not None:
        finish(None)
    return result


def allocation(
    fill: FillRecord,
    role: str,
    qty: Decimal,
    commission: Decimal,
    realized_pnl: Decimal,
) -> dict[str, str | bool]:
    return {
        "fill_id": fill.fill_id,
        "trade_id": fill.trade_id,
        "order_id": fill.order_id,
        "role": role,
        "side": fill.side,
        "qty": decimal_text(qty),
        "price": decimal_text(fill.price),
        "commission": decimal_text(commission),
        "realized_pnl": decimal_text(realized_pnl),
        "executed_at": fill.executed_at.isoformat().replace("+00:00", "Z"),
        "is_maker": fill.is_maker,
    }


def decimal_text(value: Decimal) -> str:
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"
