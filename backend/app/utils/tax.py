"""Tax on a discounted net, following the business's tax settings.

One implementation, used both when a sale is created and when the till previews
a basket, so the figure the cashier is shown can never disagree with the figure
the sale is recorded at.
"""

from __future__ import annotations

from decimal import Decimal

from app.models.business import Business
from app.utils.money import ZERO, money

HUNDRED = Decimal("100")


def tax_for(net: Decimal, business: Business | None) -> Decimal:
    """Tax on the discounted net (zero when tax is off or unset)."""
    if business is None or not business.tax_enabled or business.default_tax_rate <= 0:
        return ZERO
    rate = business.default_tax_rate / HUNDRED
    if business.tax_inclusive:
        # The shelf price already contains the tax; extract the embedded part.
        return money(net - net / (1 + rate))
    return money(net * rate)


def total_for(net: Decimal, tax: Decimal, business: Business | None) -> Decimal:
    """The amount payable: an inclusive price already holds its tax."""
    if business is not None and business.tax_enabled and business.tax_inclusive:
        return money(net)
    return money(net + tax)
