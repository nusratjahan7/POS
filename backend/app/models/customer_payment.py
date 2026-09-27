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
from app.models.customer import Customer

if TYPE_CHECKING:
    from app.models.user import User

MONEY = Numeric(12, 2)


class CustomerPayment(Base, UUIDPrimaryKeyMixin):
    """Money received from a customer against what they owed.

    Append-only, and always accompanied (in the same transaction) by a decrease
    of ``Customer.balance`` — payments and the running balance can never drift.
    """

    __tablename__ = "customer_payments"
    __table_args__ = (CheckConstraint("amount > 0", name="amount_positive"),)

    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="RESTRICT"),
        index=True,
        nullable=False,
    )

    amount: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    method: Mapped[str | None] = mapped_column(String(20))
    reference: Mapped[str | None] = mapped_column(String(64))
    note: Mapped[str | None] = mapped_column(String(255))

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    paid_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    customer: Mapped[Customer] = relationship(lazy="joined")
    user: Mapped[User | None] = relationship("User", lazy="joined")
