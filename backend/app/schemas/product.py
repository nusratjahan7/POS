from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, Field, ValidationInfo, field_validator

from app.schemas.brand import BrandSummary
from app.schemas.category import CategorySummary
from app.schemas.common import ORMModel

# Money is `Decimal` everywhere — never a float. Pydantic serialises it as a
# string in JSON, so what leaves the API is exactly what was stored.
Money = Annotated[Decimal, Field(ge=0, max_digits=12, decimal_places=2)]
Quantity = Annotated[Decimal, Field(ge=0, max_digits=12, decimal_places=3)]
OptionalMoney = Annotated[Decimal | None, Field(ge=0, max_digits=12, decimal_places=2)]

CODE_PATTERN = r"^[A-Za-z0-9._-]+$"


class ProductBase(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    sku: str = Field(min_length=1, max_length=64, pattern=CODE_PATTERN)
    barcode: str | None = Field(default=None, max_length=64, pattern=CODE_PATTERN)
    category_id: uuid.UUID | None = None
    brand_id: uuid.UUID | None = None
    purchase_price: Money = Decimal("0")
    selling_price: Money = Decimal("0")
    discount_price: OptionalMoney = None
    unit: str = Field(default="unit", min_length=1, max_length=20)
    minimum_stock: Quantity = Decimal("0")
    description: str | None = Field(default=None, max_length=4000)
    image_url: str | None = Field(default=None, max_length=500)
    is_active: bool = True

    @field_validator("discount_price")
    @classmethod
    def _discount_within_selling_price(
        cls, value: Decimal | None, info: ValidationInfo
    ) -> Decimal | None:
        # `selling_price` is declared above, so it is already populated here.
        selling = info.data.get("selling_price")
        if value is not None and selling is not None and value > selling:
            raise ValueError("The discount price cannot exceed the selling price.")
        return value


class ProductCreate(ProductBase):
    """Opening stock is recorded once, here.

    It is an opening balance, not an inventory transaction: nothing adjusts it
    afterwards until the inventory module owns the ledger.
    """

    opening_stock: Quantity = Decimal("0")


class ProductUpdate(BaseModel):
    """Every field optional; omitted keys are left untouched.

    Deliberately absent: `stock_quantity` and `opening_stock`. Stock only moves
    through inventory transactions, which this module does not implement.
    """

    name: str | None = Field(default=None, min_length=1, max_length=200)
    sku: str | None = Field(default=None, min_length=1, max_length=64, pattern=CODE_PATTERN)
    barcode: str | None = Field(default=None, max_length=64, pattern=CODE_PATTERN)
    category_id: uuid.UUID | None = None
    brand_id: uuid.UUID | None = None
    purchase_price: Money | None = None
    selling_price: Money | None = None
    discount_price: OptionalMoney = None
    unit: str | None = Field(default=None, min_length=1, max_length=20)
    minimum_stock: Quantity | None = None
    description: str | None = Field(default=None, max_length=4000)
    image_url: str | None = Field(default=None, max_length=500)
    is_active: bool | None = None


class ProductRead(ORMModel):
    id: uuid.UUID
    name: str
    slug: str
    sku: str
    barcode: str | None
    category_id: uuid.UUID | None
    brand_id: uuid.UUID | None
    category: CategorySummary | None
    brand: BrandSummary | None
    purchase_price: Decimal
    selling_price: Decimal
    discount_price: Decimal | None
    unit: str
    minimum_stock: Decimal
    stock_quantity: Decimal
    description: str | None
    image_url: str | None
    is_active: bool
    # Derived on the model from stock_quantity versus minimum_stock.
    stock_status: str
    is_low_stock: bool
    created_at: datetime
    updated_at: datetime
