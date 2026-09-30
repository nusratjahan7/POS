from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import ORMModel

Money = Annotated[Decimal, Field(ge=0, max_digits=12, decimal_places=2)]

DiscountScope = Literal["product", "cart"]
DiscountType = Literal["percentage", "fixed"]


class DiscountBase(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    #: Present = a coupon the till must quote; absent = an automatic offer.
    code: str | None = Field(default=None, max_length=40)
    scope: DiscountScope = "cart"
    type: DiscountType = "percentage"
    value: Money = Decimal("0")
    min_order_amount: Money = Decimal("0")
    max_discount_amount: Money | None = None
    starts_at: datetime | None = None
    expires_at: datetime | None = None
    usage_limit: int | None = Field(default=None, ge=0)
    per_customer_limit: int | None = Field(default=None, ge=0)
    is_active: bool = True
    first_order_only: bool = False
    exclude_discounted: bool = False
    #: Reserved — there is no shipping in the app yet, so this changes nothing.
    free_shipping: bool = False
    product_ids: list[uuid.UUID] = Field(default_factory=list)
    category_ids: list[uuid.UUID] = Field(default_factory=list)
    brand_ids: list[uuid.UUID] = Field(default_factory=list)


class DiscountCreate(DiscountBase):
    pass


class DiscountUpdate(BaseModel):
    """Every field optional; omitted keys are left untouched."""

    name: str | None = Field(default=None, min_length=1, max_length=120)
    code: str | None = Field(default=None, max_length=40)
    scope: DiscountScope | None = None
    type: DiscountType | None = None
    value: Money | None = None
    min_order_amount: Money | None = None
    max_discount_amount: Money | None = None
    starts_at: datetime | None = None
    expires_at: datetime | None = None
    usage_limit: int | None = Field(default=None, ge=0)
    per_customer_limit: int | None = Field(default=None, ge=0)
    is_active: bool | None = None
    first_order_only: bool | None = None
    exclude_discounted: bool | None = None
    free_shipping: bool | None = None
    product_ids: list[uuid.UUID] | None = None
    category_ids: list[uuid.UUID] | None = None
    brand_ids: list[uuid.UUID] | None = None


class DiscountRead(ORMModel):
    id: uuid.UUID
    name: str
    code: str | None
    scope: str
    type: str
    value: Decimal
    min_order_amount: Decimal
    max_discount_amount: Decimal | None
    starts_at: datetime | None
    expires_at: datetime | None
    usage_limit: int | None
    per_customer_limit: int | None
    is_active: bool
    first_order_only: bool
    exclude_discounted: bool
    free_shipping: bool
    #: Targeting, as ids — the client resolves names from its own lists.
    product_ids: list[uuid.UUID]
    category_ids: list[uuid.UUID]
    brand_ids: list[uuid.UUID]
    redeemed_count: int = 0
    created_at: datetime
    updated_at: datetime


# --- Pricing preview -------------------------------------------------------
class DiscountLineInput(BaseModel):
    product_id: uuid.UUID
    quantity: Annotated[Decimal, Field(gt=0, max_digits=12, decimal_places=3)]
    #: The cashier's manual line discount.
    discount: Money = Decimal("0")


class DiscountPreviewRequest(BaseModel):
    """What the till sends to preview a basket's discounts (never persisted)."""

    model_config = ConfigDict(from_attributes=True)

    branch_id: uuid.UUID | None = None
    customer_id: uuid.UUID | None = None
    items: list[DiscountLineInput] = Field(min_length=1)
    order_discount: Money = Decimal("0")
    coupon_code: str | None = Field(default=None, max_length=40)


class DiscountLineResult(BaseModel):
    product_id: uuid.UUID
    automatic_discount: Decimal
    manual_discount: Decimal
    #: automatic + manual, capped at the line subtotal.
    discount: Decimal
    line_total: Decimal


class DiscountApplied(BaseModel):
    """One discount that contributed to a sale, for the receipt/breakdown."""

    code: str | None
    name: str
    amount: Decimal


class PriceBreakdown(BaseModel):
    lines: list[DiscountLineResult]
    subtotal: Decimal
    line_discounts: Decimal
    automatic_discount: Decimal
    coupon_discount: Decimal
    order_discount: Decimal
    total_discount: Decimal
    net: Decimal
    #: Tax on the net, and the amount actually payable (inclusive or net + tax).
    tax: Decimal
    total: Decimal
    coupon: DiscountApplied | None
    applied: list[DiscountApplied]
