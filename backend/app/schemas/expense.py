from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.branch import BranchSummary
from app.schemas.common import ORMModel
from app.schemas.register_session import RegisterRef

Money = Annotated[Decimal, Field(ge=0, max_digits=12, decimal_places=2)]
Amount = Annotated[Decimal, Field(gt=0, max_digits=12, decimal_places=2)]


class ExpenseCategoryBase(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    description: str | None = Field(default=None, max_length=255)
    is_active: bool = True


class ExpenseCategoryCreate(ExpenseCategoryBase):
    pass


class ExpenseCategoryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    description: str | None = Field(default=None, max_length=255)
    is_active: bool | None = None


class ExpenseCategoryRead(ORMModel):
    id: uuid.UUID
    name: str
    description: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ExpenseCategorySummary(ORMModel):
    id: uuid.UUID
    name: str


class ExpensePaymentMethod(ORMModel):
    id: uuid.UUID
    name: str
    code: str
    kind: str
    #: True for cash — the method that draws on a register's cash.
    opens_cash_drawer: bool


class ExpenseUser(ORMModel):
    id: uuid.UUID
    full_name: str


class ExpenseRegister(ORMModel):
    """The drawer a cash expense came from: its session and the till it belongs to."""

    # `register` as a field name shadows ABCMeta.register — aliased back on the wire.
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    status: str
    register_ref: RegisterRef = Field(alias="register")


class ExpenseCreate(BaseModel):
    """Money the business spent, filed by category."""

    branch_id: uuid.UUID
    category_id: uuid.UUID
    payment_method_id: uuid.UUID
    amount: Amount
    description: str | None = Field(default=None, max_length=255)
    reference: str | None = Field(default=None, max_length=64)
    spent_at: date
    #: Required when the method is cash — the register session it was paid from.
    register_session_id: uuid.UUID | None = None


class ExpenseRead(ORMModel):
    id: uuid.UUID
    branch: BranchSummary
    category: ExpenseCategorySummary
    payment_method: ExpensePaymentMethod
    register_session: ExpenseRegister | None
    amount: Decimal
    description: str | None
    reference: str | None
    spent_at: date
    created_by: ExpenseUser | None
    created_at: datetime


class ExpenseTotal(BaseModel):
    """Total spend for the current filter set — the list's summary figure."""

    amount: Decimal
