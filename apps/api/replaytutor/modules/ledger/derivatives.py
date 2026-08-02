from __future__ import annotations

from dataclasses import dataclass, replace
from decimal import Decimal
from typing import Literal


@dataclass(frozen=True)
class FuturesPosition:
    quantity: Decimal = Decimal("0")
    average_entry: Decimal = Decimal("0")


@dataclass(frozen=True)
class FuturesLedgerState:
    wallet_balance: Decimal
    long: FuturesPosition = FuturesPosition()
    short: FuturesPosition = FuturesPosition()
    realized_pnl: Decimal = Decimal("0")
    fees: Decimal = Decimal("0")
    funding_paid: Decimal = Decimal("0")
    liquidated: bool = False


def _open(position: FuturesPosition, quantity: Decimal, price: Decimal) -> FuturesPosition:
    total = position.average_entry * position.quantity + price * quantity
    new_quantity = position.quantity + quantity
    return FuturesPosition(new_quantity, total / new_quantity)


def _close(
    position: FuturesPosition,
    quantity: Decimal,
    price: Decimal,
    *,
    direction: Literal["LONG", "SHORT"],
) -> tuple[FuturesPosition, Decimal, Decimal]:
    closed = min(position.quantity, quantity)
    pnl = (
        (price - position.average_entry) * closed
        if direction == "LONG"
        else (position.average_entry - price) * closed
    )
    remaining = position.quantity - closed
    return (
        FuturesPosition(remaining, position.average_entry if remaining else Decimal("0")),
        pnl,
        quantity - closed,
    )


def apply_futures_fill(
    state: FuturesLedgerState,
    *,
    side: Literal["BUY", "SELL"],
    position_side: Literal["BOTH", "LONG", "SHORT"],
    position_mode: Literal["ONEWAY", "HEDGE"],
    price: Decimal,
    quantity: Decimal,
    fee: Decimal,
    reduce_only: bool,
) -> FuturesLedgerState:
    if quantity <= 0:
        raise ValueError("Quantity must be positive")
    if state.liquidated:
        raise ValueError("Account is liquidated")
    if position_mode == "HEDGE" and position_side == "BOTH":
        raise ValueError("Hedge mode requires LONG or SHORT position side")
    if position_mode == "ONEWAY" and position_side != "BOTH":
        raise ValueError("One-way mode requires BOTH position side")

    long = state.long
    short = state.short
    pnl = Decimal("0")
    remaining = quantity
    if position_mode == "HEDGE":
        if position_side == "LONG":
            if side == "BUY":
                if reduce_only:
                    raise ValueError("Reduce-only order would increase a long")
                long = _open(long, quantity, price)
                remaining = Decimal("0")
            else:
                long, pnl, remaining = _close(long, quantity, price, direction="LONG")
        else:
            if side == "SELL":
                if reduce_only:
                    raise ValueError("Reduce-only order would increase a short")
                short = _open(short, quantity, price)
                remaining = Decimal("0")
            else:
                short, pnl, remaining = _close(short, quantity, price, direction="SHORT")
        if remaining:
            raise ValueError("Order exceeds reducible position")
    elif side == "BUY":
        short, pnl, remaining = _close(short, quantity, price, direction="SHORT")
        if remaining:
            if reduce_only:
                raise ValueError("Reduce-only order exceeds short position")
            long = _open(long, remaining, price)
    else:
        long, pnl, remaining = _close(long, quantity, price, direction="LONG")
        if remaining:
            if reduce_only:
                raise ValueError("Reduce-only order exceeds long position")
            short = _open(short, remaining, price)

    wallet = state.wallet_balance + pnl - fee
    if wallet < 0:
        raise ValueError("Insufficient margin")
    return FuturesLedgerState(
        wallet_balance=wallet,
        long=long,
        short=short,
        realized_pnl=state.realized_pnl + pnl,
        fees=state.fees + fee,
        funding_paid=state.funding_paid,
        liquidated=False,
    )


def apply_funding(
    state: FuturesLedgerState,
    *,
    mark_price: Decimal,
    funding_rate: Decimal,
) -> tuple[FuturesLedgerState, Decimal]:
    # Positive funding: longs pay shorts. The returned amount is account outflow.
    amount = (
        state.long.quantity * mark_price * funding_rate
        - state.short.quantity * mark_price * funding_rate
    )
    return (
        replace(
            state,
            wallet_balance=state.wallet_balance - amount,
            funding_paid=state.funding_paid + amount,
        ),
        amount,
    )


def unrealized_pnl(state: FuturesLedgerState, mark_price: Decimal) -> Decimal:
    return (mark_price - state.long.average_entry) * state.long.quantity + (
        state.short.average_entry - mark_price
    ) * state.short.quantity


def initial_margin(state: FuturesLedgerState, mark_price: Decimal, leverage: int) -> Decimal:
    return (state.long.quantity + state.short.quantity) * mark_price / Decimal(leverage)


def maintenance_margin(
    state: FuturesLedgerState,
    mark_price: Decimal,
    maintenance_margin_rate: Decimal,
) -> Decimal:
    return (state.long.quantity + state.short.quantity) * mark_price * maintenance_margin_rate


def is_liquidatable(
    state: FuturesLedgerState,
    *,
    mark_price: Decimal,
    maintenance_margin_rate: Decimal,
) -> bool:
    margin_balance = state.wallet_balance + unrealized_pnl(state, mark_price)
    return margin_balance <= maintenance_margin(state, mark_price, maintenance_margin_rate)


def liquidate(state: FuturesLedgerState, *, mark_price: Decimal) -> FuturesLedgerState:
    pnl = unrealized_pnl(state, mark_price)
    return FuturesLedgerState(
        wallet_balance=max(Decimal("0"), state.wallet_balance + pnl),
        realized_pnl=state.realized_pnl + pnl,
        fees=state.fees,
        funding_paid=state.funding_paid,
        liquidated=True,
    )


def liquidation_price(
    state: FuturesLedgerState,
    *,
    direction: Literal["LONG", "SHORT"],
    margin_mode: Literal["ISOLATED", "CROSS"],
    leverage: int,
    maintenance_margin_rate: Decimal,
) -> Decimal | None:
    position = state.long if direction == "LONG" else state.short
    if not position.quantity:
        return None
    allocated = (
        position.average_entry * position.quantity / Decimal(leverage)
        if margin_mode == "ISOLATED"
        else state.wallet_balance
    )
    if direction == "LONG":
        return max(
            Decimal("0"),
            (position.average_entry * position.quantity - allocated)
            / (position.quantity * (Decimal("1") - maintenance_margin_rate)),
        )
    return (position.average_entry * position.quantity + allocated) / (
        position.quantity * (Decimal("1") + maintenance_margin_rate)
    )
