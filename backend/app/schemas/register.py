from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, Field

from app.schemas.branch import BranchSummary
from app.schemas.common import ORMModel

Money = Annotated[Decimal, Field(ge=0, max_digits=12, decimal_places=2)]


class RegisterBase(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    branch_id: uuid.UUID
    is_active: bool = True
    default_opening_balance: Money = Decimal("0")
    require_opening_balance: bool = False
    allow_opening_balance_override: bool = True


class RegisterCreate(RegisterBase):
    pass


class RegisterUpdate(BaseModel):
    """Every field optional; omitted keys are left untouched."""

    name: str | None = Field(default=None, min_length=1, max_length=120)
    branch_id: uuid.UUID | None = None
    is_active: bool | None = None
    default_opening_balance: Money | None = None
    require_opening_balance: bool | None = None
    allow_opening_balance_override: bool | None = None


class RegisterRead(ORMModel):
    id: uuid.UUID
    name: str
    branch_id: uuid.UUID
    branch: BranchSummary
    is_active: bool
    default_opening_balance: Decimal
    require_opening_balance: bool
    allow_opening_balance_override: bool
    created_at: datetime
    updated_at: datetime


class RegisterSummary(ORMModel):
    """Lightweight list for pickers (e.g. choosing a till before a sale)."""

    id: uuid.UUID
    name: str
    branch_id: uuid.UUID
