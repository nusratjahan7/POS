from __future__ import annotations

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Numeric, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.branch import Branch
    from app.models.product import Product

QUANTITY = Numeric(12, 3)


class StockLevel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Current on-hand quantity for one product at one branch.

    This row is the *only* authority on stock. It is written exclusively by
    :class:`~app.services.inventory.InventoryService`, which holds a row lock
    (``SELECT ... FOR UPDATE``) while moving stock, so two concurrent movements
    for the same product/branch can never interleave.

    ``Product.stock_quantity`` is a denormalised sum of these rows, maintained in
    the same transaction for fast list rendering.
    """

    __tablename__ = "stock_levels"
    __table_args__ = (
        UniqueConstraint("product_id", "branch_id", name="uq_stock_levels_product_id_branch_id"),
        CheckConstraint("quantity >= 0", name="quantity_non_negative"),
    )

    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    branch_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("branches.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    quantity: Mapped[Decimal] = mapped_column(QUANTITY, server_default=text("0"), nullable=False)

    # Loaded explicitly by the read queries. Left lazy so the ``SELECT ... FOR
    # UPDATE`` in the write path is a plain single-table lock (Postgres rejects
    # FOR UPDATE on the nullable side of an outer join).
    product: Mapped[Product] = relationship()
    branch: Mapped[Branch] = relationship()

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<StockLevel {self.product_id}@{self.branch_id}={self.quantity}>"
