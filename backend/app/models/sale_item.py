from __future__ import annotations

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.product import Product
    from app.models.sale import Sale

MONEY = Numeric(12, 2)
QUANTITY = Numeric(12, 3)


class SaleItem(Base, UUIDPrimaryKeyMixin):
    """One product line on a sale.

    The product's name, SKU and unit are **snapshotted** so a receipt reprinted
    later still shows what was actually sold, even if the catalogue changes.

    ``unit_price`` is the price the server resolved at the time of sale (the
    discount price when one is set), never a figure the till supplied.
    """

    __tablename__ = "sale_items"
    __table_args__ = (
        UniqueConstraint("sale_id", "product_id", name="uq_sale_items_sale_id_product_id"),
        CheckConstraint("quantity > 0", name="quantity_positive"),
        CheckConstraint("unit_price >= 0", name="unit_price_non_negative"),
        CheckConstraint("discount >= 0", name="discount_non_negative"),
        CheckConstraint("subtotal >= 0", name="subtotal_non_negative"),
        CheckConstraint("line_total >= 0", name="line_total_non_negative"),
        CheckConstraint("discount <= subtotal", name="discount_within_subtotal"),
        CheckConstraint("line_total = subtotal - discount", name="line_total_math"),
    )

    sale_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sales.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="RESTRICT"),
        index=True,
        nullable=False,
    )

    # Snapshot of what was sold, for reprintable receipts.
    product_name: Mapped[str] = mapped_column(String(200), nullable=False)
    sku: Mapped[str] = mapped_column(String(64), nullable=False)
    unit: Mapped[str] = mapped_column(String(20), nullable=False)

    quantity: Mapped[Decimal] = mapped_column(QUANTITY, nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    discount: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    subtotal: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    line_total: Mapped[Decimal] = mapped_column(MONEY, nullable=False)

    sale: Mapped[Sale] = relationship(back_populates="items")
    product: Mapped[Product] = relationship(lazy="joined")

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<SaleItem {self.sku} {self.quantity}>"
