from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.branch import Branch
    from app.models.purchase_item import PurchaseItem
    from app.models.supplier import Supplier
    from app.models.user import User

MONEY = Numeric(12, 2)

# Keep in lock-step with the CHECK constraint and the API Literal.
PURCHASE_STATUSES = ("draft", "pending", "received", "cancelled")
_STATUSES_SQL = ", ".join(f"'{value}'" for value in PURCHASE_STATUSES)


class Purchase(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A purchase order and its receipt.

    Stock is **only** affected when the order transitions to ``received``
    (``PurchaseService.receive``), which — in a single database transaction —
    writes the stock movements, bumps the supplier balance and records any
    payment. Drafts and pending orders never touch inventory.
    """

    __tablename__ = "purchases"
    __table_args__ = (
        CheckConstraint(f"status IN ({_STATUSES_SQL})", name="valid_status"),
        CheckConstraint("subtotal >= 0", name="subtotal_non_negative"),
        CheckConstraint("discount >= 0", name="discount_non_negative"),
        CheckConstraint("tax >= 0", name="tax_non_negative"),
        CheckConstraint("total >= 0", name="total_non_negative"),
        CheckConstraint("paid >= 0", name="paid_non_negative"),
        CheckConstraint("due >= 0", name="due_non_negative"),
        CheckConstraint("total = subtotal - discount + tax", name="total_math"),
        CheckConstraint("due = total - paid", name="due_math"),
    )

    purchase_number: Mapped[str] = mapped_column(
        String(32), unique=True, index=True, nullable=False
    )

    supplier_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("suppliers.id", ondelete="RESTRICT"),
        index=True,
        nullable=False,
    )
    branch_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("branches.id", ondelete="RESTRICT"),
        index=True,
        nullable=False,
    )

    purchase_date: Mapped[date] = mapped_column(Date, nullable=False)

    subtotal: Mapped[Decimal] = mapped_column(MONEY, server_default=text("0"), nullable=False)
    discount: Mapped[Decimal] = mapped_column(MONEY, server_default=text("0"), nullable=False)
    tax: Mapped[Decimal] = mapped_column(MONEY, server_default=text("0"), nullable=False)
    total: Mapped[Decimal] = mapped_column(MONEY, server_default=text("0"), nullable=False)
    paid: Mapped[Decimal] = mapped_column(MONEY, server_default=text("0"), nullable=False)
    due: Mapped[Decimal] = mapped_column(MONEY, server_default=text("0"), nullable=False)

    status: Mapped[str] = mapped_column(String(16), server_default=text("'draft'"), nullable=False)
    note: Mapped[str | None] = mapped_column(String(255))

    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    supplier: Mapped[Supplier] = relationship(lazy="joined")
    branch: Mapped[Branch] = relationship(lazy="joined")
    created_by: Mapped[User | None] = relationship(lazy="joined")
    items: Mapped[list[PurchaseItem]] = relationship(
        back_populates="purchase",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<Purchase {self.purchase_number} {self.status}>"
