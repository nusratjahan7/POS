from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.branch import BranchSummary
from app.schemas.common import ORMModel

Money = Annotated[Decimal, Field(ge=0, max_digits=12, decimal_places=2)]
PositiveMoney = Annotated[Decimal, Field(gt=0, max_digits=12, decimal_places=2)]


class RegisterRef(ORMModel):
    id: uuid.UUID
    name: str


class CashUser(ORMModel):
    id: uuid.UUID
    full_name: str


class RegisterSessionRead(ORMModel):
    # `register` as a field name shadows ABCMeta.register, so the attribute is
    # named differently and aliased back to `register` on the wire.
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    register_ref: RegisterRef = Field(alias="register")
    branch: BranchSummary
    opening_cash: Decimal
    status: str
    opened_by: CashUser | None
    opened_at: datetime
    closed_by: CashUser | None
    closed_at: datetime | None
    #: Live (computed) while the session is open; stored once closed.
    expected_cash: Decimal | None
    actual_cash: Decimal | None
    #: actual cash minus expected; negative is short.
    difference: Decimal | None
    closing_note: str | None


class CashMovementRead(ORMModel):
    id: uuid.UUID
    movement_type: str
    #: Signed: positive into the drawer, negative out.
    amount: Decimal
    reference_type: str
    reference_id: uuid.UUID | None
    note: str | None
    user: CashUser | None
    created_at: datetime


class SessionSummary(BaseModel):
    opening_cash: Decimal
    cash_sales: Decimal
    cash_refunds: Decimal
    cash_expenses: Decimal
    cash_in: Decimal
    cash_out: Decimal
    expected_cash: Decimal
    movements: list[CashMovementRead]


class RegisterSessionDetail(BaseModel):
    """A session and how its drawer adds up."""

    session: RegisterSessionRead
    summary: SessionSummary


class RegisterSessionOpen(BaseModel):
    register_id: uuid.UUID
    opening_cash: Money = Decimal("0")


class RegisterSessionClose(BaseModel):
    actual_cash: Money
    note: str | None = Field(default=None, max_length=255)


class CashAdjustment(BaseModel):
    """Cash put into or taken out of the drawer mid-shift."""

    amount: PositiveMoney
    note: str | None = Field(default=None, max_length=255)
