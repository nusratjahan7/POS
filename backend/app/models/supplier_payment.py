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
from app.models.supplier import Supplier

if TYPE_CHECKING:
    from app.models.user import User

MONEY = Numeric(12, 2)


class SupplierPayment(Base, UUIDPrimaryKeyMixin):
    """An immutable record of money paid to a supplier.

    Payments made when a purchase is received are recorded here too, so the
    supplier's balance and history are fully auditable from one place.
    """

    __tablename__ = "supplier_payments"
    __table_args__ = (CheckConstraint("amount > 0", name="amount_positive"),)

    supplier_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("suppliers.id", ondelete="RESTRICT"),
        index=True,
        nullable=False,
    )
    purchase_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("purchases.id", ondelete="SET NULL"), index=True
    )

    amount: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    method: Mapped[str | None] = mapped_column(String(20))
    reference: Mapped[str | None] = mapped_column(String(64))
    note: Mapped[str | None] = mapped_column(String(255))

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    paid_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    supplier: Mapped[Supplier] = relationship(lazy="joined")
    user: Mapped[User | None] = relationship("User", lazy="joined")
