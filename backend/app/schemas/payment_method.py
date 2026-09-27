from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel

# Keep in lock-step with the model's CHECK constraint.
PaymentKind = Literal["cash", "card", "mobile", "bank", "other"]

CODE_PATTERN = r"^[A-Za-z0-9._-]+$"


class PaymentMethodBase(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    code: str = Field(min_length=1, max_length=40, pattern=CODE_PATTERN)
    kind: PaymentKind = "other"
    description: str | None = Field(default=None, max_length=255)
    is_active: bool = True
    opens_cash_drawer: bool = False
    requires_reference: bool = False
    sort_order: int = Field(default=0, ge=0, le=1000)


class PaymentMethodCreate(PaymentMethodBase):
    pass


class PaymentMethodUpdate(BaseModel):
    """Every field optional; omitted keys are left untouched."""

    name: str | None = Field(default=None, min_length=1, max_length=80)
    code: str | None = Field(default=None, min_length=1, max_length=40, pattern=CODE_PATTERN)
    kind: PaymentKind | None = None
    description: str | None = Field(default=None, max_length=255)
    is_active: bool | None = None
    opens_cash_drawer: bool | None = None
    requires_reference: bool | None = None
    sort_order: int | None = Field(default=None, ge=0, le=1000)


class PaymentMethodRead(ORMModel):
    id: uuid.UUID
    name: str
    code: str
    kind: str
    description: str | None
    is_active: bool
    opens_cash_drawer: bool
    requires_reference: bool
    is_system: bool
    sort_order: int
    created_at: datetime
    updated_at: datetime


class PaymentMethodSummary(ORMModel):
    id: uuid.UUID
    name: str
    code: str
    kind: str
    #: The till needs these to prompt correctly before tendering: whether to ask
    #: for a transaction reference, and whether the drawer should open.
    opens_cash_drawer: bool
    requires_reference: bool
