from __future__ import annotations

from decimal import Decimal

from replaytutor.modules.market_rules.crypto_spot import CryptoSpotRules, RuleViolation


class USDTPerpetualRules(CryptoSpotRules):
    def validate_leverage(self, value: int) -> int:
        if not 1 <= value <= 125:
            raise RuleViolation("USDT perpetual leverage must be between 1 and 125")
        return value

    def validate_callback_rate(self, value: str | None) -> Decimal:
        if value is None:
            raise RuleViolation("callback_rate is required")
        rate = Decimal(value)
        if not Decimal("0.001") <= rate <= Decimal("0.10"):
            raise RuleViolation("callback_rate must be between 0.001 and 0.10")
        return rate
