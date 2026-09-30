from __future__ import annotations

from sqlalchemy import Boolean, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin


class ExpenseCategory(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """A bucket an expense is filed under (Rent, Utilities, Salaries, …).

    Names are unique among live rows only, so a deleted category never reserves
    its name forever — the same rule the product taxonomy uses.
    """

    __tablename__ = "expense_categories"

    name: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=text("true"), nullable=False
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<ExpenseCategory {self.name}>"
