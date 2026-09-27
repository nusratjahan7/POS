from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.branch import Branch
    from app.models.customer import Customer
    from app.models.register import Register
    from app.models.sale_item import SaleItem
    from app.models.sale_payment import SalePayment
    from app.models.user import User

MONEY = Numeric(12, 2)

# Keep in lock-step with the CHECK constraint and the API literals.
SALE_STATUSES = ("completed", "voided")
_STATUSES_SQL = ", ".join(f"'{value}'" for value in SALE_STATUSES)


class Sale(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A completed sale and its tender.

    Every figure here is computed by the server (``SaleService.create``) from the
    products' current prices and the business's tax settings — the till's numbers
    are only ever a preview.

    ``paid`` is what was **applied** to this sale and ``due`` what was carried on
    the customer's account, so ``due = total - paid`` always holds. Cash handed
    over above the amount applied is kept separately in ``change_amount`` and
    never inflates ``paid``.

    Stock leaves the branch exactly once, through ``InventoryService``, posting a
    ``stock_out`` movement with ``reference_type='sale'``.
    """

    __tablename__ = "sales"
    __table_args__ = (
        CheckConstraint(f"status IN ({_STATUSES_SQL})", name="valid_status"),
        CheckConstraint("subtotal >= 0", name="subtotal_non_negative"),
        CheckConstraint("discount >= 0", name="discount_non_negative"),
        CheckConstraint("tax >= 0", name="tax_non_negative"),
        CheckConstraint("total >= 0", name="total_non_negative"),
        CheckConstraint("paid >= 0", name="paid_non_negative"),
        CheckConstraint("due >= 0", name="due_non_negative"),
        CheckConstraint("change_amount >= 0", name="change_amount_non_negative"),
        CheckConstraint("total = subtotal - discount + tax", name="total_math"),
        CheckConstraint("due = total - paid", name="due_math"),
    )

    sale_number: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)

    branch_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("branches.id", ondelete="RESTRICT"),
        index=True,
        nullable=False,
    )
    register_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("registers.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    customer_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    cashier_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )

    subtotal: Mapped[Decimal] = mapped_column(MONEY, server_default=text("0"), nullable=False)
    discount: Mapped[Decimal] = mapped_column(MONEY, server_default=text("0"), nullable=False)
    tax: Mapped[Decimal] = mapped_column(MONEY, server_default=text("0"), nullable=False)
    total: Mapped[Decimal] = mapped_column(MONEY, server_default=text("0"), nullable=False)
    paid: Mapped[Decimal] = mapped_column(MONEY, server_default=text("0"), nullable=False)
    due: Mapped[Decimal] = mapped_column(MONEY, server_default=text("0"), nullable=False)
    change_amount: Mapped[Decimal] = mapped_column(MONEY, server_default=text("0"), nullable=False)

    status: Mapped[str] = mapped_column(
        String(16), server_default=text("'completed'"), nullable=False
    )
    note: Mapped[str | None] = mapped_column(String(255))

    sold_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    voided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    branch: Mapped[Branch] = relationship(lazy="joined")
    register: Mapped[Register | None] = relationship(lazy="joined")
    customer: Mapped[Customer | None] = relationship(lazy="joined")
    cashier: Mapped[User | None] = relationship(lazy="joined")
    items: Mapped[list[SaleItem]] = relationship(
        back_populates="sale",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    payments: Mapped[list[SalePayment]] = relationship(
        back_populates="sale",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<Sale {self.sale_number} {self.total}>"
