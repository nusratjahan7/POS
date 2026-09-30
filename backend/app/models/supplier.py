from __future__ import annotations

from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, Numeric, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin

MONEY = Numeric(12, 2)


class Supplier(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """A vendor you buy stock from.

    ``balance`` is the current amount **owed to the supplier**. It starts at
    ``opening_balance`` and is adjusted (atomically, inside the purchase
    transaction) as purchases are received and payments recorded — it is never
    computed on the fly, so the supplier ledger stays a true running total.

    It may never go negative: a payment larger than what is owed is rejected, so
    the payable bottoms out at zero (unlike a customer's, which may run into
    store credit).
    """

    __tablename__ = "suppliers"
    __table_args__ = (CheckConstraint("balance >= 0", name="balance_non_negative"),)

    name: Mapped[str] = mapped_column(String(160), unique=True, index=True, nullable=False)
    company: Mapped[str | None] = mapped_column(String(160))
    phone: Mapped[str | None] = mapped_column(String(32))
    email: Mapped[str | None] = mapped_column(String(255))
    address: Mapped[str | None] = mapped_column(String(255))

    opening_balance: Mapped[Decimal] = mapped_column(
        MONEY, server_default=text("0"), nullable=False
    )
    balance: Mapped[Decimal] = mapped_column(MONEY, server_default=text("0"), nullable=False)

    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=text("true"), nullable=False
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<Supplier {self.name}>"
