from __future__ import annotations

from sqlalchemy import Boolean, CheckConstraint, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin

# The set a sale can be tendered with. `kind` groups them for reporting and for
# behaviour the till will apply (cash opens the drawer, non-cash takes a ref).
PAYMENT_KINDS = ("cash", "card", "mobile", "bank", "other")


class PaymentMethod(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """A way a customer can pay.

    The application seeds the common set (Cash, Card, bKash, Nagad, Bank,
    Other). Seeded rows are ``is_system`` and cannot be deleted or re-coded, but
    their display name and availability can still be managed.
    """

    __tablename__ = "payment_methods"
    __table_args__ = (
        CheckConstraint("kind IN ('cash', 'card', 'mobile', 'bank', 'other')", name="valid_kind"),
    )

    name: Mapped[str] = mapped_column(String(80), unique=True, index=True, nullable=False)
    code: Mapped[str] = mapped_column(String(40), unique=True, index=True, nullable=False)
    kind: Mapped[str] = mapped_column(String(20), server_default=text("'other'"), nullable=False)
    description: Mapped[str | None] = mapped_column(String(255))

    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=text("true"), nullable=False
    )
    # Cash is counted into the drawer; the rest are recorded against a reference.
    opens_cash_drawer: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("false"), nullable=False
    )
    requires_reference: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("false"), nullable=False
    )
    is_system: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("false"), nullable=False
    )
    sort_order: Mapped[int] = mapped_column(
        Integer, default=0, server_default=text("0"), nullable=False
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<PaymentMethod {self.code}>"
