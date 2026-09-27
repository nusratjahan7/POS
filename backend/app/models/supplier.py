from __future__ import annotations

from decimal import Decimal

from sqlalchemy import Boolean, Numeric, String, text
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
    """

    __tablename__ = "suppliers"

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
