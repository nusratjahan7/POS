from __future__ import annotations

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Numeric,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.branch import Branch

MONEY = Numeric(12, 2)


class Register(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """A till belonging to a branch.

    This is the anchor the future sales module resolves a transaction through:
    ``business -> branch -> register -> cashier(user)``. No cash movement is
    recorded here yet — the opening-balance columns only describe how a shift is
    expected to start once the register module owns the ledger.
    """

    __tablename__ = "registers"
    __table_args__ = (
        UniqueConstraint("branch_id", "name", name="uq_registers_branch_id_name"),
        CheckConstraint("default_opening_balance >= 0", name="opening_balance_non_negative"),
    )

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    branch_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("branches.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=text("true"), nullable=False
    )

    # Opening-balance settings: the float a shift is expected to hold, whether a
    # cashier must record it, and whether they may override the default.
    default_opening_balance: Mapped[Decimal] = mapped_column(
        MONEY, server_default=text("0"), nullable=False
    )
    require_opening_balance: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("false"), nullable=False
    )
    allow_opening_balance_override: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=text("true"), nullable=False
    )

    branch: Mapped[Branch] = relationship(back_populates="registers", lazy="joined")

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<Register {self.name}>"
