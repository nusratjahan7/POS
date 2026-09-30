from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Date, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.branch import Branch
    from app.models.expense_category import ExpenseCategory
    from app.models.payment_method import PaymentMethod
    from app.models.register_session import RegisterSession
    from app.models.user import User

MONEY = Numeric(12, 2)


class Expense(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Money the business spends, filed by category.

    An expense paid from the till (its method ``opens_cash_drawer``) names the
    register session it came out of and posts a negative cash movement, so the
    drawer's reconciliation accounts for it.
    """

    __tablename__ = "expenses"
    __table_args__ = (CheckConstraint("amount > 0", name="amount_positive"),)

    branch_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("branches.id", ondelete="RESTRICT"),
        index=True,
        nullable=False,
    )
    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("expense_categories.id", ondelete="RESTRICT"),
        index=True,
        nullable=False,
    )
    payment_method_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("payment_methods.id", ondelete="RESTRICT"),
        index=True,
        nullable=False,
    )
    #: The drawer a cash expense was paid from; null when the method is not cash.
    register_session_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("register_sessions.id", ondelete="RESTRICT"),
        index=True,
        nullable=True,
    )

    amount: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    description: Mapped[str | None] = mapped_column(String(255))
    reference: Mapped[str | None] = mapped_column(String(64))
    spent_at: Mapped[date] = mapped_column(Date, nullable=False)

    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), index=True
    )

    branch: Mapped[Branch] = relationship(lazy="joined")
    category: Mapped[ExpenseCategory] = relationship(lazy="joined")
    payment_method: Mapped[PaymentMethod] = relationship(lazy="joined")
    register_session: Mapped[RegisterSession | None] = relationship(lazy="joined")
    created_by: Mapped[User | None] = relationship(lazy="joined")

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<Expense {self.amount} {self.spent_at}>"
