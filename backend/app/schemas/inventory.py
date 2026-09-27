from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, Field, computed_field, model_validator

from app.schemas.branch import BranchSummary
from app.schemas.common import ORMModel

MovementType = Literal["opening", "stock_in", "stock_out", "adjustment", "damage"]
ReferenceType = Literal["manual", "opening", "purchase", "sale"]

Quantity = Annotated[Decimal, Field(max_digits=12, decimal_places=3)]

# Sign each movement type must carry: positive increases stock, negative decreases.
_REQUIRED_SIGN: dict[str, int] = {
    "opening": 1,
    "stock_in": 1,
    "stock_out": -1,
    "damage": -1,
}


class StockProduct(ORMModel):
    """The product fields the inventory screens need, and nothing more."""

    id: uuid.UUID
    name: str
    sku: str
    unit: str
    minimum_stock: Decimal
    image_url: str | None


class StockLevelRead(ORMModel):
    id: uuid.UUID
    product: StockProduct
    branch: BranchSummary
    quantity: Decimal
    updated_at: datetime

    @computed_field  # type: ignore[prop-decorator]
    @property
    def stock_status(self) -> str:
        """Mirrors ``Product.stock_status`` but for this branch's level."""
        if self.quantity <= 0:
            return "out_of_stock"
        if self.quantity <= self.product.minimum_stock:
            return "low_stock"
        return "in_stock"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_low_stock(self) -> bool:
        return self.quantity <= self.product.minimum_stock


class MovementUser(ORMModel):
    id: uuid.UUID
    full_name: str
    email: str


class MovementRead(ORMModel):
    id: uuid.UUID
    product: StockProduct
    branch: BranchSummary
    quantity: Decimal
    movement_type: str
    reference_type: str
    reference_id: uuid.UUID | None
    previous_stock: Decimal
    new_stock: Decimal
    note: str | None
    user: MovementUser | None
    created_at: datetime


class MovementCreate(BaseModel):
    """Record a stock movement.

    ``quantity`` is the signed change: positive increases stock, negative
    decreases it. The sign must agree with ``movement_type`` (an adjustment may
    go either way). Stock may never be taken below zero.
    """

    product_id: uuid.UUID
    branch_id: uuid.UUID
    movement_type: MovementType
    quantity: Quantity
    reference_type: ReferenceType = "manual"
    reference_id: uuid.UUID | None = None
    note: str | None = Field(default=None, max_length=255)

    @model_validator(mode="after")
    def _validate_sign(self) -> MovementCreate:
        if self.quantity == 0:
            raise ValueError("A movement must change the quantity by a non-zero amount.")

        required = _REQUIRED_SIGN.get(self.movement_type)
        if required is not None and self.quantity * required <= 0:
            direction = "positive" if required > 0 else "negative"
            raise ValueError(f"A {self.movement_type} movement must have a {direction} quantity.")
        return self


class InventorySummary(BaseModel):
    """Counts for the low-stock / out-of-stock views."""

    total_levels: int
    in_stock: int
    low_stock: int
    out_of_stock: int
    total_quantity: Decimal
