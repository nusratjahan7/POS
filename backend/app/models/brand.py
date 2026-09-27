from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.product import Product


class Brand(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """The manufacturer or label a product belongs to."""

    __tablename__ = "brands"

    name: Mapped[str] = mapped_column(String(120), unique=True, index=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(140), unique=True, index=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=text("true"), nullable=False
    )

    products: Mapped[list[Product]] = relationship(back_populates="brand")

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<Brand {self.slug}>"
