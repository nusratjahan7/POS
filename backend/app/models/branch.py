from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.business import Business
    from app.models.register import Register
    from app.models.user import User


class Branch(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """A physical store location. Every branch-scoped record points here."""

    __tablename__ = "branches"

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    code: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)
    address: Mapped[str | None] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(32))
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=text("true"), nullable=False
    )

    # The owning business. Nullable only so pre-existing rows survive the
    # migration; the service backfills the default business on creation.
    business_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("businesses.id", ondelete="SET NULL"),
        index=True,
    )

    business: Mapped[Business | None] = relationship(back_populates="branches")
    registers: Mapped[list[Register]] = relationship(
        back_populates="branch",
        cascade="all, delete-orphan",
    )
    users: Mapped[list[User]] = relationship(back_populates="branch")

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<Branch {self.code}>"
