from __future__ import annotations

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.brand import Brand
    from app.models.category import Category

MONEY = Numeric(12, 2)
QUANTITY = Numeric(12, 3)


class Product(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """A sellable item.

    Money is ``Numeric`` end to end and never a float: prices arrive as
    ``Decimal`` from the API, are stored exactly, and are serialised as strings
    so no precision is lost in transit.

    ``stock_quantity`` is a denormalised cache for fast list rendering. Inventory
    transactions do not exist yet, so nothing maintains it except the optional
    opening balance captured on create — Module 07 will own it.

    Extension path (deliberately NOT implemented yet). SKUs and barcodes live on
    the product today because nothing can vary yet; when it can, they move to the
    variant and the product keeps them as the default:

    * ``ProductVariant(product_id)`` — size/colour splits, each with its own
      SKU, barcode and price override.
    * ``StockBatch(variant_id, lot_number, expires_on)`` — batch and expiry.
    * ``SerialNumber(variant_id, serial)`` — individually tracked units.

    Keeping category, brand, unit and the price columns here means those tables
    can attach by foreign key without reworking this one.
    """

    __tablename__ = "products"
    __table_args__ = (
        CheckConstraint("purchase_price >= 0", name="purchase_price_non_negative"),
        CheckConstraint("selling_price >= 0", name="selling_price_non_negative"),
        CheckConstraint(
            "discount_price IS NULL OR discount_price >= 0", name="discount_non_negative"
        ),
        CheckConstraint("minimum_stock >= 0", name="minimum_stock_non_negative"),
        CheckConstraint("stock_quantity >= 0", name="stock_quantity_non_negative"),
        # Uniqueness applies only to live rows: a soft-deleted product must not
        # reserve its slug/SKU/barcode forever.
        Index(
            "ix_products_slug",
            "slug",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index(
            "ix_products_sku",
            "sku",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index(
            "ix_products_barcode",
            "barcode",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(220), nullable=False)
    sku: Mapped[str] = mapped_column(String(64), nullable=False)
    barcode: Mapped[str | None] = mapped_column(String(64))

    category_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="SET NULL"),
        index=True,
    )
    brand_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("brands.id", ondelete="SET NULL"),
        index=True,
    )

    purchase_price: Mapped[Decimal] = mapped_column(MONEY, server_default=text("0"), nullable=False)
    selling_price: Mapped[Decimal] = mapped_column(MONEY, server_default=text("0"), nullable=False)
    discount_price: Mapped[Decimal | None] = mapped_column(MONEY)

    unit: Mapped[str] = mapped_column(String(20), server_default=text("'unit'"), nullable=False)
    minimum_stock: Mapped[Decimal] = mapped_column(
        QUANTITY, server_default=text("0"), nullable=False
    )
    stock_quantity: Mapped[Decimal] = mapped_column(
        QUANTITY, server_default=text("0"), nullable=False
    )

    description: Mapped[str | None] = mapped_column(Text)
    image_url: Mapped[str | None] = mapped_column(String(500))

    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=text("true"), nullable=False
    )

    category: Mapped[Category | None] = relationship(back_populates="products", lazy="joined")
    brand: Mapped[Brand | None] = relationship(back_populates="products", lazy="joined")

    @property
    def is_low_stock(self) -> bool:
        return self.stock_quantity <= self.minimum_stock

    @property
    def stock_status(self) -> str:
        """Derived for display only; the authoritative ledger arrives with inventory."""
        if self.stock_quantity <= 0:
            return "out_of_stock"
        if self.is_low_stock:
            return "low_stock"
        return "in_stock"

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<Product {self.sku}>"
