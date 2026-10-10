from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, Field, computed_field, model_validator

from app.schemas.branch import BranchSummary
from app.schemas.common import ORMModel

TransferStatus = Literal["draft", "requested", "approved", "shipped", "received", "cancelled"]

#: A positive quantity with three decimal places, matching Numeric(12, 3).
Quantity = Annotated[Decimal, Field(gt=0, max_digits=12, decimal_places=3)]


class TransferLineCreate(BaseModel):
    product_id: uuid.UUID
    quantity: Quantity


class TransferCreate(BaseModel):
    """Raise a transfer. ``submit`` sends it straight to the approval queue."""

    from_branch_id: uuid.UUID
    to_branch_id: uuid.UUID
    reference: str | None = Field(default=None, max_length=64)
    note: str | None = Field(default=None, max_length=255)
    items: list[TransferLineCreate] = Field(min_length=1, max_length=200)
    submit: bool = False

    @model_validator(mode="after")
    def _distinct_branches(self) -> TransferCreate:
        if self.from_branch_id == self.to_branch_id:
            raise ValueError("A transfer's source and destination branches must differ.")
        return self


class TransferUpdate(BaseModel):
    """Edit a transfer while it is still a draft."""

    from_branch_id: uuid.UUID | None = None
    to_branch_id: uuid.UUID | None = None
    reference: str | None = Field(default=None, max_length=64)
    note: str | None = Field(default=None, max_length=255)
    items: list[TransferLineCreate] | None = Field(default=None, max_length=200)


class TransferCancel(BaseModel):
    reason: str | None = Field(default=None, max_length=255)


class TransferNote(BaseModel):
    note: str | None = Field(default=None, max_length=255)


class TransferUser(ORMModel):
    id: uuid.UUID
    full_name: str


class TransferLineRead(ORMModel):
    id: uuid.UUID
    product_id: uuid.UUID
    product_name: str
    sku: str
    quantity: Decimal


class TransferRead(ORMModel):
    id: uuid.UUID
    transfer_number: str
    status: str
    from_branch: BranchSummary
    to_branch: BranchSummary
    reference: str | None
    note: str | None
    cancel_reason: str | None

    items: list[TransferLineRead]

    created_by: TransferUser | None
    requested_by: TransferUser | None
    approved_by: TransferUser | None
    shipped_by: TransferUser | None
    received_by: TransferUser | None
    cancelled_by: TransferUser | None

    requested_at: datetime | None
    approved_at: datetime | None
    shipped_at: datetime | None
    received_at: datetime | None
    cancelled_at: datetime | None
    created_at: datetime
    updated_at: datetime

    @computed_field  # type: ignore[prop-decorator]
    @property
    def item_count(self) -> int:
        return len(self.items)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total_quantity(self) -> Decimal:
        return sum((line.quantity for line in self.items), Decimal("0"))


class TransferSummary(ORMModel):
    id: uuid.UUID
    transfer_number: str
    status: str
    from_branch: BranchSummary
    to_branch: BranchSummary
    reference: str | None
    items: list[TransferLineRead]
    created_at: datetime
    updated_at: datetime
    shipped_at: datetime | None
    received_at: datetime | None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def item_count(self) -> int:
        return len(self.items)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total_quantity(self) -> Decimal:
        return sum((line.quantity for line in self.items), Decimal("0"))
