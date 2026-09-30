from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel
from app.schemas.sale import SalePaymentMethod, SaleUser

Quantity = Annotated[Decimal, Field(gt=0, max_digits=12, decimal_places=3)]

ReturnStatus = Literal["requested", "approved", "completed", "cancelled"]


class SaleReturnItemCreate(BaseModel):
    """How many units of one sale line are coming back."""

    sale_item_id: uuid.UUID
    quantity: Quantity


class SaleReturnCreate(BaseModel):
    """What the operator posts to hand goods back.

    Carries **no amounts** — the server prices the refund from the sale line's own
    net, so a client can never talk it into refunding more than was charged.
    """

    items: list[SaleReturnItemCreate] = Field(min_length=1)
    reason: str | None = Field(default=None, max_length=255)
    note: str | None = Field(default=None, max_length=255)
    #: How any cash part goes back. Required when the refund pays out money.
    payment_method_id: uuid.UUID | None = None
    reference: str | None = Field(default=None, max_length=64)


class SaleReturnItemRead(ORMModel):
    id: uuid.UUID
    sale_item_id: uuid.UUID
    product_id: uuid.UUID
    product_name: str
    sku: str
    quantity: Decimal
    unit_price: Decimal
    #: The refund this line carries.
    line_total: Decimal


class SaleReturnRead(ORMModel):
    id: uuid.UUID
    return_number: str
    status: str
    reason: str | None
    note: str | None
    #: Value of the goods returned, split into what cleared debt and what was paid out.
    refund_amount: Decimal
    credit_reversed: Decimal
    cash_refund: Decimal
    payment_method: SalePaymentMethod | None
    refund_reference: str | None
    created_by: SaleUser | None
    completed_by: SaleUser | None
    created_at: datetime
    completed_at: datetime | None
    cancelled_at: datetime | None
    items: list[SaleReturnItemRead]
