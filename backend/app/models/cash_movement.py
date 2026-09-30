from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Numeric, String, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.register_session import RegisterSession
    from app.models.user import User

MONEY = Numeric(12, 2)

# Keep in lock-step with the CHECK constraints and the API literals.
MOVEMENT_TYPES = ("sale", "refund", "expense", "cash_in", "cash_out")
REFERENCE_TYPES = ("sale", "sale_return", "expense", "manual")
_TYPES_SQL = ", ".join(f"'{value}'" for value in MOVEMENT_TYPES)
_REFERENCES_SQL = ", ".join(f"'{value}'" for value in REFERENCE_TYPES)


class CashMovement(Base, UUIDPrimaryKeyMixin):
    """One signed movement of cash in a register's drawer.

    Append-only, like the stock ledger: ``amount`` is positive when cash enters
    the drawer (a cash sale, a cash-in) and negative when it leaves (a refund, a
    cash expense, a cash-out). The session's expected cash is the opening float
    plus the sum of these.
    """

    __tablename__ = "cash_movements"
    __table_args__ = (
        CheckConstraint(f"movement_type IN ({_TYPES_SQL})", name="valid_movement_type"),
        CheckConstraint(f"reference_type IN ({_REFERENCES_SQL})", name="valid_reference_type"),
        CheckConstraint("amount <> 0", name="amount_non_zero"),
    )

    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("register_sessions.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    movement_type: Mapped[str] = mapped_column(String(20), nullable=False)
    amount: Mapped[Decimal] = mapped_column(MONEY, nullable=False)

    reference_type: Mapped[str] = mapped_column(
        String(20), server_default=text("'manual'"), nullable=False
    )
    reference_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)
    note: Mapped[str | None] = mapped_column(String(255))

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    session: Mapped[RegisterSession] = relationship(back_populates="movements")
    user: Mapped[User | None] = relationship("User", lazy="joined")

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<CashMovement {self.movement_type} {self.amount}>"
