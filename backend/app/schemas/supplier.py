from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, EmailStr, Field

from app.schemas.common import ORMModel

Money = Annotated[Decimal, Field(ge=0, max_digits=12, decimal_places=2)]


class SupplierBase(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    company: str | None = Field(default=None, max_length=160)
    phone: str | None = Field(default=None, max_length=32)
    email: EmailStr | None = None
    address: str | None = Field(default=None, max_length=255)
    opening_balance: Money = Decimal("0")
    is_active: bool = True


class SupplierCreate(SupplierBase):
    pass


class SupplierUpdate(BaseModel):
    """Every field optional; omitted keys are left untouched."""

    name: str | None = Field(default=None, min_length=1, max_length=160)
    company: str | None = Field(default=None, max_length=160)
    phone: str | None = Field(default=None, max_length=32)
    email: EmailStr | None = None
    address: str | None = Field(default=None, max_length=255)
    is_active: bool | None = None


class SupplierRead(ORMModel):
    id: uuid.UUID
    name: str
    company: str | None
    phone: str | None
    email: str | None
    address: str | None
    opening_balance: Decimal
    # Current amount owed: opening balance plus received purchase dues, less payments.
    balance: Decimal
    is_active: bool
    created_at: datetime
    updated_at: datetime


class SupplierSummary(ORMModel):
    id: uuid.UUID
    name: str
    balance: Decimal
