from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, Field

from app.schemas.branch import BranchSummary
from app.schemas.common import ORMModel
from app.schemas.customer import CustomerSummary

Money = Annotated[Decimal, Field(ge=0, max_digits=12, decimal_places=2)]
PositiveMoney = Annotated[Decimal, Field(gt=0, max_digits=12, decimal_places=2)]
Quantity = Annotated[Decimal, Field(gt=0, max_digits=12, decimal_places=3)]

SaleStatus = Literal["completed", "voided", "refunded"]

#: Settlement state, derived from ``paid``/``due`` — never stored.
PaymentStatus = Literal["paid", "partial", "unpaid"]


class SaleItemCreate(BaseModel):
    product_id: uuid.UUID
    quantity: Quantity
    discount: Money = Decimal("0")


class SalePaymentCreate(BaseModel):
    payment_method_id: uuid.UUID
    amount: PositiveMoney
    #: Cash handed over; anything above `amount` is returned as change.
    tendered: Money | None = None
    reference: str | None = Field(default=None, max_length=64)
    note: str | None = Field(default=None, max_length=255)


class SaleCreate(BaseModel):
    """What the till posts when it completes a sale.

    Deliberately carries **no prices and no totals** — the server resolves the
    current price of every product and computes the discount, tax and grand total
    itself. Anything the client calculates is a preview and is never persisted.
    """

    branch_id: uuid.UUID
    #: The till this sale is rung on. Its register session must be open.
    register_id: uuid.UUID
    customer_id: uuid.UUID | None = None
    note: str | None = Field(default=None, max_length=255)
    order_discount: Money = Decimal("0")
    items: list[SaleItemCreate] = Field(min_length=1)
    payments: list[SalePaymentCreate] = Field(min_length=1)


class SaleItemRead(ORMModel):
    id: uuid.UUID
    product_id: uuid.UUID
    product_name: str
    sku: str
    unit: str
    quantity: Decimal
    unit_price: Decimal
    discount: Decimal
    subtotal: Decimal
    line_total: Decimal


class SalePaymentMethod(ORMModel):
    id: uuid.UUID
    name: str
    code: str
    kind: str


class SalePaymentRead(ORMModel):
    id: uuid.UUID
    payment_method: SalePaymentMethod
    amount: Decimal
    tendered: Decimal | None
    change_given: Decimal
    reference: str | None
    note: str | None
    paid_at: datetime


class SaleUser(ORMModel):
    id: uuid.UUID
    full_name: str


class SaleCashierOption(ORMModel):
    """A cashier who has rung up at least one sale — the management filter's list.

    Deliberately its own shape rather than the staff directory, so the sales
    screen does not depend on the ``users:read`` permission.
    """

    id: uuid.UUID
    full_name: str


class SaleSummary(ORMModel):
    id: uuid.UUID
    sale_number: str
    branch: BranchSummary
    customer: CustomerSummary | None
    cashier: SaleUser | None
    sold_at: datetime
    subtotal: Decimal
    discount: Decimal
    tax: Decimal
    total: Decimal
    paid: Decimal
    due: Decimal
    change_amount: Decimal
    status: str
    #: Distinct product lines; eager-loaded, so the list costs no extra query.
    item_count: int
    #: What the customer handed over (paid plus change given back).
    received_amount: Decimal


class SaleRead(ORMModel):
    id: uuid.UUID
    sale_number: str
    branch: BranchSummary
    register_id: uuid.UUID | None
    customer: CustomerSummary | None
    cashier: SaleUser | None
    subtotal: Decimal
    discount: Decimal
    tax: Decimal
    total: Decimal
    paid: Decimal
    due: Decimal
    change_amount: Decimal
    #: Value of goods returned so far, across every completed return.
    returned_amount: Decimal
    #: What the customer handed over (paid plus change given back).
    received_amount: Decimal
    status: str
    note: str | None
    items: list[SaleItemRead]
    payments: list[SalePaymentRead]
    sold_at: datetime
    created_at: datetime
    refunded_at: datetime | None
    refunded_by: SaleUser | None
    refund_reason: str | None


class SaleBusiness(ORMModel):
    name: str
    logo_url: str | None
    phone: str | None
    email: str | None
    address: str | None
    currency: str
    tax_label: str


class SaleBranch(ORMModel):
    """The branch a sale happened at, with the contact details a receipt shows."""

    id: uuid.UUID
    name: str
    code: str
    address: str | None
    phone: str | None


class SaleReceipt(BaseModel):
    """Everything a printable receipt needs, in one call."""

    business: SaleBusiness
    #: The receipt's branch, enriched beyond `SaleRead.branch` with address/phone.
    branch: SaleBranch
    sale: SaleRead
