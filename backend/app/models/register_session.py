from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Numeric, String, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.branch import Branch
    from app.models.cash_movement import CashMovement
    from app.models.register import Register
    from app.models.user import User

MONEY = Numeric(12, 2)

# Keep in lock-step with the CHECK constraint and the API literals.
SESSION_STATUSES = ("open", "closed")
_STATUSES_SQL = ", ".join(f"'{value}'" for value in SESSION_STATUSES)


class RegisterSession(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """One shift on one till: the float it opened with and how it closed.

    Every cash event during the shift is a :class:`CashMovement` against this
    session, so the expected drawer is always ``opening_cash + Σ movements``.
    A partial unique index allows at most one open session per register.
    """

    __tablename__ = "register_sessions"
    __table_args__ = (
        CheckConstraint(f"status IN ({_STATUSES_SQL})", name="valid_status"),
        CheckConstraint("opening_cash >= 0", name="opening_cash_non_negative"),
        CheckConstraint("actual_cash IS NULL OR actual_cash >= 0", name="actual_cash_non_negative"),
        Index(
            "uq_register_sessions_open_register",
            "register_id",
            unique=True,
            postgresql_where=text("status = 'open'"),
        ),
    )

    register_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("registers.id", ondelete="RESTRICT"),
        index=True,
        nullable=False,
    )
    branch_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("branches.id", ondelete="RESTRICT"),
        index=True,
        nullable=False,
    )

    opening_cash: Mapped[Decimal] = mapped_column(
        MONEY, server_default=text("0"), nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(16), server_default=text("'open'"), nullable=False
    )

    opened_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    opened_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    closed_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    #: Filled at close: what the ledger says should be there, what was counted,
    #: and the over/short between them (negative = short).
    expected_cash: Mapped[Decimal | None] = mapped_column(MONEY)
    actual_cash: Mapped[Decimal | None] = mapped_column(MONEY)
    difference: Mapped[Decimal | None] = mapped_column(MONEY)
    closing_note: Mapped[str | None] = mapped_column(String(255))

    register: Mapped[Register] = relationship(lazy="joined")
    branch: Mapped[Branch] = relationship(lazy="joined")
    opened_by: Mapped[User | None] = relationship(lazy="joined", foreign_keys=[opened_by_id])
    closed_by: Mapped[User | None] = relationship(lazy="joined", foreign_keys=[closed_by_id])
    movements: Mapped[list[CashMovement]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<RegisterSession {self.id} {self.status}>"
