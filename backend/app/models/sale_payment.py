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
from app.db.mixins import UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.payment_method import PaymentMethod
    from app.models.sale import Sale
    from app.models.user import User

MONEY = Numeric(12, 2)


class SalePayment(Base, UUIDPrimaryKeyMixin):
    """One tender against a sale.

    A sale may carry several of these — that is what makes split (mixed) payment
    work: part cash, part card, the rest on account.

    ``amount`` is the portion **applied** to the sale. For cash, ``tendered`` is
    what the customer handed over and ``change_given`` the difference returned;
    recording them separately is what keeps ``Sale.paid`` truthful.
    """

    __tablename__ = "sale_payments"
    __table_args__ = (
        CheckConstraint("amount > 0", name="amount_positive"),
        CheckConstraint("change_given >= 0", name="change_non_negative"),
        CheckConstraint("tendered IS NULL OR tendered >= amount", name="tendered_covers_amount"),
    )

    sale_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sales.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    payment_method_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("payment_methods.id", ondelete="RESTRICT"),
        index=True,
        nullable=False,
    )

    amount: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    tendered: Mapped[Decimal | None] = mapped_column(MONEY)
    change_given: Mapped[Decimal] = mapped_column(MONEY, server_default=text("0"), nullable=False)

    reference: Mapped[str | None] = mapped_column(String(64))
    note: Mapped[str | None] = mapped_column(String(255))
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    paid_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    sale: Mapped[Sale] = relationship(back_populates="payments")
    payment_method: Mapped[PaymentMethod] = relationship(lazy="joined")
    user: Mapped[User | None] = relationship(lazy="joined")

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<SalePayment {self.amount}>"
