from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, Field

from app.schemas.branch import BranchSummary
from app.schemas.common import ORMModel
from app.schemas.supplier import SupplierSummary

Money = Annotated[Decimal, Field(ge=0, max_digits=12, decimal_places=2)]
Quantity = Annotated[Decimal, Field(gt=0, max_digits=12, decimal_places=3)]

PurchaseStatus = Literal["draft", "pending", "received", "cancelled"]
# Only draft/pending may be set by the client; `received`/`cancelled` are service transitions.
EditablePurchaseStatus = Literal["draft", "pending"]


class PurchaseItemCreate(BaseModel):
    product_id: uuid.UUID
    quantity: Quantity
    unit_price: Money


class PurchaseProduct(ORMModel):
    id: uuid.UUID
    name: str
    sku: str
    unit: str


class PurchaseItemRead(ORMModel):
    id: uuid.UUID
    product: PurchaseProduct
    quantity: Decimal
    unit_price: Decimal
    subtotal: Decimal


class PurchaseCreate(BaseModel):
    supplier_id: uuid.UUID
    branch_id: uuid.UUID
    purchase_date: date
    discount: Money = Decimal("0")
    tax: Money = Decimal("0")
    paid: Money = Decimal("0")
    status: EditablePurchaseStatus = "draft"
    note: str | None = Field(default=None, max_length=255)
    items: list[PurchaseItemCreate] = Field(min_length=1)


class PurchaseUpdate(BaseModel):
    """Editable only while the purchase is draft/pending. Sending `items` replaces them."""

    supplier_id: uuid.UUID | None = None
    branch_id: uuid.UUID | None = None
    purchase_date: date | None = None
    discount: Money | None = None
    tax: Money | None = None
    paid: Money | None = None
    status: EditablePurchaseStatus | None = None
    note: str | None = Field(default=None, max_length=255)
    items: list[PurchaseItemCreate] | None = Field(default=None, min_length=1)


class PurchaseSummary(ORMModel):
    id: uuid.UUID
    purchase_number: str
    supplier: SupplierSummary
    branch: BranchSummary
    purchase_date: date
    subtotal: Decimal
    discount: Decimal
    tax: Decimal
    total: Decimal
    paid: Decimal
    due: Decimal
    status: str
    created_at: datetime


class PurchaseUser(ORMModel):
    id: uuid.UUID
    full_name: str


class PurchaseRead(ORMModel):
    id: uuid.UUID
    purchase_number: str
    supplier: SupplierSummary
    branch: BranchSummary
    purchase_date: date
    subtotal: Decimal
    discount: Decimal
    tax: Decimal
    total: Decimal
    paid: Decimal
    due: Decimal
    status: str
    note: str | None
    created_by: PurchaseUser | None
    items: list[PurchaseItemRead]
    received_at: datetime | None
    cancelled_at: datetime | None
    created_at: datetime
    updated_at: datetime
