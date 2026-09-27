"""Point-of-sale schemas.

Deliberately excludes cost fields (``purchase_price``): a cashier must never see
what the shop paid. Only sell-side data leaves this API.
"""

from __future__ import annotations

import uuid
from decimal import Decimal

from app.schemas.common import ORMModel


class PosProduct(ORMModel):
    id: uuid.UUID
    name: str
    sku: str
    barcode: str | None
    unit: str
    selling_price: Decimal
    discount_price: Decimal | None
    image_url: str | None
    category_id: uuid.UUID | None
    # Stock at the branch the till is ringing up, and its status.
    stock_quantity: Decimal
    stock_status: str


class PosCategory(ORMModel):
    id: uuid.UUID
    name: str
    slug: str
    product_count: int


class PosStock(ORMModel):
    """On-hand stock for one product, at one branch — the till's cart cap."""

    product_id: uuid.UUID
    stock_quantity: Decimal
    stock_status: str
