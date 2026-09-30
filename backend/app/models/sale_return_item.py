from __future__ import annotations

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.sale_return import SaleReturn

MONEY = Numeric(12, 2)
QUANTITY = Numeric(12, 3)


class SaleReturnItem(Base, UUIDPrimaryKeyMixin):
    """One line coming back: how many units of a sale line, and what they refund.

    The product name and SKU are **snapshotted** so a return history still reads
    correctly if the catalogue changes, mirroring how the sale line does it.
    """

    __tablename__ = "sale_return_items"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="quantity_positive"),
        CheckConstraint("unit_price >= 0", name="unit_price_non_negative"),
        CheckConstraint("line_total >= 0", name="line_total_non_negative"),
    )

    return_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sale_returns.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    #: The sale line this came from. RESTRICT so a returned line cannot vanish.
    sale_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sale_items.id", ondelete="RESTRICT"),
        index=True,
        nullable=False,
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="RESTRICT"),
        index=True,
        nullable=False,
    )

    product_name: Mapped[str] = mapped_column(String(200), nullable=False)
    sku: Mapped[str] = mapped_column(String(64), nullable=False)

    quantity: Mapped[Decimal] = mapped_column(QUANTITY, nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    #: The refund this line carries (its net, proportionally for a partial quantity).
    line_total: Mapped[Decimal] = mapped_column(MONEY, nullable=False)

    sale_return: Mapped[SaleReturn] = relationship(back_populates="items")

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<SaleReturnItem {self.sku} {self.quantity}>"
