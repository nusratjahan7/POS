"""Exact money arithmetic shared by the services that price documents."""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

CENT = Decimal("0.01")
ZERO = Decimal("0.00")


def money(value: Decimal) -> Decimal:
    """Round a computed amount to the currency's two decimal places."""
    return value.quantize(CENT, rounding=ROUND_HALF_UP)
