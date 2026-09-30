from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Numeric, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.payment_method import PaymentMethod
    from app.models.sale import Sale
    from app.models.sale_return_item import SaleReturnItem
    from app.models.user import User

MONEY = Numeric(12, 2)

# Keep in lock-step with the CHECK constraint and the API literals.
RETURN_STATUSES = ("requested", "approved", "completed", "cancelled")
_STATUSES_SQL = ", ".join(f"'{value}'" for value in RETURN_STATUSES)


class SaleReturn(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Goods coming back from a completed sale, with the refund they carry.

    This is the **only** way money goes back to a customer. It is created and
    applied in one transaction: every line goes back into stock, the refund
    clears whatever the customer still owed before any cash is handed over, and
    the sale's ``returned_amount`` moves with it — so the sale's totals stay the
    arithmetic the database enforces while still reflecting what came back.

    A line refunds its own net (after its line discount), capped so that the sum
    of a sale's returns can never exceed what the sale was worth.
    """

    __tablename__ = "sale_returns"
    __table_args__ = (
        CheckConstraint(f"status IN ({_STATUSES_SQL})", name="valid_status"),
        CheckConstraint("refund_amount >= 0", name="refund_amount_non_negative"),
        CheckConstraint("credit_reversed >= 0", name="credit_reversed_non_negative"),
        CheckConstraint("cash_refund >= 0", name="cash_refund_non_negative"),
        CheckConstraint("credit_reversed + cash_refund = refund_amount", name="refund_split_math"),
    )

    sale_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sales.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    return_number: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)

    status: Mapped[str] = mapped_column(
        String(16), server_default=text("'completed'"), nullable=False
    )
    reason: Mapped[str | None] = mapped_column(String(255))
    note: Mapped[str | None] = mapped_column(String(255))

    #: How the cash part went back. Null when the refund only cleared a balance.
    payment_method_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("payment_methods.id", ondelete="RESTRICT"),
        index=True,
        nullable=True,
    )
    refund_reference: Mapped[str | None] = mapped_column(String(64))

    #: Value of the goods returned, split into what cleared debt and what was paid out.
    refund_amount: Mapped[Decimal] = mapped_column(MONEY, server_default=text("0"), nullable=False)
    credit_reversed: Mapped[Decimal] = mapped_column(
        MONEY, server_default=text("0"), nullable=False
    )
    cash_refund: Mapped[Decimal] = mapped_column(MONEY, server_default=text("0"), nullable=False)

    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    completed_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    cancelled_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    sale: Mapped[Sale] = relationship(lazy="joined")
    payment_method: Mapped[PaymentMethod | None] = relationship(lazy="joined")
    created_by: Mapped[User | None] = relationship(lazy="joined", foreign_keys=[created_by_id])
    completed_by: Mapped[User | None] = relationship(lazy="joined", foreign_keys=[completed_by_id])
    items: Mapped[list[SaleReturnItem]] = relationship(
        back_populates="sale_return",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<SaleReturn {self.return_number} {self.refund_amount}>"
