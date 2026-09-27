from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, CheckConstraint, Numeric, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.branch import Branch

RATE = Numeric(6, 3)


class Business(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """The trading entity the whole installation belongs to.

    Single-tenant today: the API treats the first active row as *the* business
    and creates a sensible default on first access. Keeping it a real table (and
    putting ``business_id`` on every branch) means a future multi-business
    deployment is a data migration, not a schema rewrite.
    """

    __tablename__ = "businesses"
    __table_args__ = (
        CheckConstraint("default_tax_rate >= 0", name="default_tax_rate_non_negative"),
        CheckConstraint("default_tax_rate <= 100", name="default_tax_rate_at_most_100"),
    )

    name: Mapped[str] = mapped_column(String(160), nullable=False)
    logo_url: Mapped[str | None] = mapped_column(String(500))
    phone: Mapped[str | None] = mapped_column(String(32))
    email: Mapped[str | None] = mapped_column(String(255))
    address: Mapped[str | None] = mapped_column(String(255))

    # ISO 4217 code and IANA time zone name. Both are validated at the schema
    # boundary so a typo can never reach the database.
    currency: Mapped[str] = mapped_column(String(3), server_default=text("'USD'"), nullable=False)
    timezone: Mapped[str] = mapped_column(String(64), server_default=text("'UTC'"), nullable=False)

    # Tax settings. `default_tax_rate` is a percentage (e.g. 15.000 = 15%).
    tax_enabled: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("false"), nullable=False
    )
    tax_inclusive: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=text("true"), nullable=False
    )
    tax_label: Mapped[str] = mapped_column(String(32), server_default=text("'Tax'"), nullable=False)
    default_tax_rate: Mapped[Decimal] = mapped_column(
        RATE, server_default=text("0"), nullable=False
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=text("true"), nullable=False
    )

    branches: Mapped[list[Branch]] = relationship(
        back_populates="business",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<Business {self.name}>"
