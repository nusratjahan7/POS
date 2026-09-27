from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, EmailStr, Field

from app.schemas.common import ORMModel

Money = Annotated[Decimal, Field(ge=0, max_digits=12, decimal_places=2)]
PaymentAmount = Annotated[Decimal, Field(gt=0, max_digits=12, decimal_places=2)]


class CustomerBase(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    phone: str | None = Field(default=None, max_length=32)
    email: EmailStr | None = None
    address: str | None = Field(default=None, max_length=255)
    opening_balance: Money = Decimal("0")
    is_active: bool = True


class CustomerCreate(CustomerBase):
    pass


class CustomerUpdate(BaseModel):
    """Every field optional; omitted keys are left untouched."""

    name: str | None = Field(default=None, min_length=1, max_length=160)
    phone: str | None = Field(default=None, max_length=32)
    email: EmailStr | None = None
    address: str | None = Field(default=None, max_length=255)
    is_active: bool | None = None


class CustomerRead(ORMModel):
    id: uuid.UUID
    name: str
    phone: str | None
    email: str | None
    address: str | None
    opening_balance: Decimal
    # Amount the customer currently owes (a receivable).
    balance: Decimal
    is_active: bool
    created_at: datetime
    updated_at: datetime


class CustomerSummary(ORMModel):
    id: uuid.UUID
    name: str
    balance: Decimal


class PaymentUser(ORMModel):
    id: uuid.UUID
    full_name: str


class CustomerPaymentCreate(BaseModel):
    amount: PaymentAmount
    method: str | None = Field(default=None, max_length=20)
    reference: str | None = Field(default=None, max_length=64)
    note: str | None = Field(default=None, max_length=255)


class CustomerPaymentRead(ORMModel):
    id: uuid.UUID
    amount: Decimal
    method: str | None
    reference: str | None
    note: str | None
    user: PaymentUser | None
    paid_at: datetime


class CustomerPurchaseRead(ORMModel):
    """A sale summary.

    Placeholder shape, returned empty until the sales module ships; kept here so
    the details screen and its client types do not change when it does.
    """

    id: uuid.UUID
    reference: str
    purchased_at: datetime
    total: Decimal
    paid: Decimal
    due: Decimal


class CustomerDetails(BaseModel):
    """Everything the customer detail screen shows in one response."""

    customer: CustomerRead
    total_orders: int
    total_purchase_amount: Decimal
    total_paid: Decimal
    outstanding_due: Decimal
    recent_payments: list[CustomerPaymentRead]
    recent_purchases: list[CustomerPurchaseRead]
