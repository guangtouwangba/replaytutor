from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal


@dataclass(frozen=True)
class LedgerState:
    cash: Decimal
    quantity: Decimal = Decimal("0")
    average_entry: Decimal = Decimal("0")
    realized_pnl: Decimal = Decimal("0")
    fees: Decimal = Decimal("0")


def apply_fill(
    state: LedgerState,
    *,
    side: Literal["BUY", "SELL"],
    price: Decimal,
    quantity: Decimal,
    fee: Decimal,
) -> LedgerState:
    notional = price * quantity
    if side == "BUY":
        if state.cash < notional + fee:
            raise ValueError("Insufficient cash")
        total_cost = state.average_entry * state.quantity + notional
        new_quantity = state.quantity + quantity
        return LedgerState(
            cash=state.cash - notional - fee,
            quantity=new_quantity,
            average_entry=total_cost / new_quantity,
            realized_pnl=state.realized_pnl,
            fees=state.fees + fee,
        )
    if state.quantity < quantity:
        raise ValueError("Insufficient position")
    remaining = state.quantity - quantity
    return LedgerState(
        cash=state.cash + notional - fee,
        quantity=remaining,
        average_entry=state.average_entry if remaining else Decimal("0"),
        realized_pnl=state.realized_pnl + (price - state.average_entry) * quantity,
        fees=state.fees + fee,
    )
