from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.customer import Customer
    from app.models.sale import Sale

MONEY = Numeric(12, 2)


class DiscountRedemption(Base, UUIDPrimaryKeyMixin):
    """A promotion or coupon actually applied to a sale.

    Append-only. Doubles as the receipt's discount breakdown and the source for
    ``usage_limit`` / ``per_customer_limit`` counting. The code and name are
    snapshotted so the record survives the discount being edited or deleted.
    """

    __tablename__ = "discount_redemptions"
    __table_args__ = (CheckConstraint("amount >= 0", name="amount_non_negative"),)

    discount_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("discounts.id", ondelete="SET NULL"), index=True
    )
    sale_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sales.id", ondelete="CASCADE"), index=True, nullable=False
    )
    customer_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id", ondelete="SET NULL"), index=True
    )

    code: Mapped[str | None] = mapped_column(String(40))
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    amount: Mapped[Decimal] = mapped_column(MONEY, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    customer: Mapped[Customer | None] = relationship(lazy="joined")
    sale: Mapped[Sale] = relationship(back_populates="discounts")

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<DiscountRedemption {self.code or self.name} {self.amount}>"
