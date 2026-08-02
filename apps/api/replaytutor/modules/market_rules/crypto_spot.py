from __future__ import annotations

from decimal import Decimal


class RuleViolation(ValueError):
    pass


class CryptoSpotRules:
    def __init__(self, *, tick_size: str, lot_size: str) -> None:
        self.tick_size = Decimal(tick_size)
        self.lot_size = Decimal(lot_size)

    def validate_quantity(self, value: str) -> Decimal:
        quantity = Decimal(value)
        if quantity <= 0:
            raise RuleViolation("Quantity must be positive")
        if quantity % self.lot_size != 0:
            raise RuleViolation(f"Quantity must align to lot size {self.lot_size}")
        return quantity

    def validate_price(self, value: str | None, *, field: str) -> Decimal:
        if value is None:
            raise RuleViolation(f"{field} is required")
        price = Decimal(value)
        if price <= 0:
            raise RuleViolation(f"{field} must be positive")
        if price % self.tick_size != 0:
            raise RuleViolation(f"{field} must align to tick size {self.tick_size}")
        return price
