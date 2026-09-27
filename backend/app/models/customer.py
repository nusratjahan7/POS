from __future__ import annotations

from decimal import Decimal

from sqlalchemy import Boolean, Numeric, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin

MONEY = Numeric(12, 2)


class Customer(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """A person who buys from you.

    ``balance`` is the amount the customer **owes you** (a receivable). It starts
    at ``opening_balance``, grows with credit sales, and shrinks with payments —
    the credit-sales module will call :meth:`CustomerService.charge_credit`.

    Unlike suppliers, names are intentionally **not** unique: real customers share
    names, so dedupe is by phone/email at the edges, not by the database.
    """

    __tablename__ = "customers"

    name: Mapped[str] = mapped_column(String(160), index=True, nullable=False)
    phone: Mapped[str | None] = mapped_column(String(32), index=True)
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
        return f"<Customer {self.name}>"
