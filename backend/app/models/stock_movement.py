from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Numeric, String, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.branch import Branch
    from app.models.product import Product
    from app.models.user import User

QUANTITY = Numeric(12, 3)

# Keep these tuples in lock-step with the CHECK constraints and the API Literals.
MOVEMENT_TYPES = ("opening", "stock_in", "stock_out", "adjustment", "damage", "return")
REFERENCE_TYPES = ("manual", "opening", "purchase", "sale", "sale_return")

_MOVEMENT_TYPES_SQL = ", ".join(f"'{value}'" for value in MOVEMENT_TYPES)
_REFERENCE_TYPES_SQL = ", ".join(f"'{value}'" for value in REFERENCE_TYPES)


class StockMovement(Base, UUIDPrimaryKeyMixin):
    """An immutable record of one change to on-hand stock.

    Append-only: there is no update or delete path. Every write to a
    :class:`~app.models.stock_level.StockLevel` is accompanied by exactly one of
    these rows, in the same transaction — the ledger is the audit trail and the
    proof that "stock never moves without a movement".

    ``quantity`` is the *signed* change (positive increases, negative decreases),
    so ``new_stock = previous_stock + quantity`` always holds. Future modules
    (purchases, sales) post here through ``InventoryService`` with a
    ``reference_type``/``reference_id`` pointing back at their record.
    """

    __tablename__ = "stock_movements"
    __table_args__ = (
        CheckConstraint(f"movement_type IN ({_MOVEMENT_TYPES_SQL})", name="valid_movement_type"),
        CheckConstraint(f"reference_type IN ({_REFERENCE_TYPES_SQL})", name="valid_reference_type"),
        CheckConstraint("quantity <> 0", name="quantity_non_zero"),
        CheckConstraint("new_stock = previous_stock + quantity", name="stock_math"),
        CheckConstraint("previous_stock >= 0", name="previous_stock_non_negative"),
        CheckConstraint("new_stock >= 0", name="new_stock_non_negative"),
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

    quantity: Mapped[Decimal] = mapped_column(QUANTITY, nullable=False)
    movement_type: Mapped[str] = mapped_column(String(20), nullable=False)
    reference_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="manual", server_default=text("'manual'")
    )
    reference_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), index=True, nullable=True
    )

    previous_stock: Mapped[Decimal] = mapped_column(QUANTITY, nullable=False)
    new_stock: Mapped[Decimal] = mapped_column(QUANTITY, nullable=False)

    note: Mapped[str | None] = mapped_column(String(255))
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    product: Mapped[Product] = relationship(lazy="joined")
    branch: Mapped[Branch] = relationship(lazy="joined")
    user: Mapped[User | None] = relationship(lazy="joined")

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<StockMovement {self.movement_type} {self.quantity} {self.new_stock}>"
