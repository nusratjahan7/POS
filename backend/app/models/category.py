from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.product import Product


class Category(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """A product grouping, optionally nested one level (or more) deep.

    ``parent_id`` is self-referencing and nullable, so a flat category is simply
    a row with no parent. The hierarchy is intentionally unconstrained in depth;
    the service layer enforces the two rules that matter — a parent must exist,
    and a category may never become a descendant of itself.
    """

    __tablename__ = "categories"
    __table_args__ = (
        CheckConstraint("parent_id IS NULL OR parent_id != id", name="parent_not_self"),
    )

    name: Mapped[str] = mapped_column(String(120), unique=True, index=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(140), unique=True, index=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(255))
    image_url: Mapped[str | None] = mapped_column(String(500))

    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="SET NULL"),
        index=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=text("true"), nullable=False
    )

    parent: Mapped[Category | None] = relationship(
        "Category",
        back_populates="children",
        remote_side="Category.id",
        # Self-referential eager loading needs an explicit depth; one level is
        # all a response serialises.
        lazy="joined",
        join_depth=1,
    )
    children: Mapped[list[Category]] = relationship(
        "Category",
        back_populates="parent",
    )
    products: Mapped[list[Product]] = relationship(back_populates="category")

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<Category {self.slug}>"
