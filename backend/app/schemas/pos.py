"""Point-of-sale schemas.

Deliberately excludes cost fields (``purchase_price``): a cashier must never see
what the shop paid. Only sell-side data leaves this API.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel

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


# --- Offline bundle --------------------------------------------------------
class OfflineBranch(BaseModel):
    id: uuid.UUID
    name: str
    code: str
    address: str | None
    phone: str | None


class OfflineBusiness(BaseModel):
    name: str | None
    currency: str
    tax_enabled: bool
    tax_inclusive: bool
    tax_label: str
    default_tax_rate: Decimal


class OfflineRegister(BaseModel):
    id: uuid.UUID
    name: str
    is_active: bool


class OfflinePaymentMethod(BaseModel):
    id: uuid.UUID
    name: str
    code: str
    kind: str
    opens_cash_drawer: bool
    requires_reference: bool


class OfflineCategory(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    product_count: int


class OfflineProduct(BaseModel):
    id: uuid.UUID
    name: str
    sku: str
    barcode: str | None
    unit: str
    selling_price: Decimal
    discount_price: Decimal | None
    image_url: str | None
    category_id: uuid.UUID | None
    minimum_stock: Decimal
    #: Last-known on-hand at the branch — a display hint, not authoritative.
    stock_quantity: Decimal
    stock_status: str


class OfflineSession(BaseModel):
    id: uuid.UUID
    register_id: uuid.UUID
    opening_cash: Decimal


class OfflineBundle(BaseModel):
    """A snapshot the till caches to keep selling with no network.

    Read-only and refreshed while online. Every price and quantity here is a
    snapshot; the authoritative pricing and stock check happens server-side when
    a queued sale is synced.
    """

    schema_version: int
    generated_at: datetime
    branch: OfflineBranch
    business: OfflineBusiness
    registers: list[OfflineRegister]
    payment_methods: list[OfflinePaymentMethod]
    categories: list[OfflineCategory]
    products: list[OfflineProduct]
    open_session: OfflineSession | None
