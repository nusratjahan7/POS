from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
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
    from app.models.brand import Brand
    from app.models.category import Category
    from app.models.product import Product

MONEY = Numeric(12, 2)

# Keep in lock-step with the CHECK constraints and the API literals.
DISCOUNT_SCOPES = ("product", "cart")
DISCOUNT_TYPES = ("percentage", "fixed")
_SCOPES_SQL = ", ".join(f"'{value}'" for value in DISCOUNT_SCOPES)
_TYPES_SQL = ", ".join(f"'{value}'" for value in DISCOUNT_TYPES)


class Discount(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """A promotion — a coupon when it carries a code, an automatic offer otherwise.

    ``scope='product'`` discounts apply to the lines they target (product /
    category / brand, or every product when untargeted); ``scope='cart'``
    discounts apply to the whole basket. Every rule is enforced server-side when a
    sale is priced — the till only ever previews the result.
    """

    __tablename__ = "discounts"
    __table_args__ = (
        CheckConstraint(f"scope IN ({_SCOPES_SQL})", name="valid_scope"),
        CheckConstraint(f"type IN ({_TYPES_SQL})", name="valid_type"),
        CheckConstraint("value >= 0", name="value_non_negative"),
        CheckConstraint("type <> 'percentage' OR value <= 100", name="percentage_at_most_100"),
        CheckConstraint("min_order_amount >= 0", name="min_order_non_negative"),
        CheckConstraint(
            "max_discount_amount IS NULL OR max_discount_amount >= 0",
            name="max_discount_non_negative",
        ),
        CheckConstraint("usage_limit IS NULL OR usage_limit >= 0", name="usage_limit_non_negative"),
        CheckConstraint(
            "per_customer_limit IS NULL OR per_customer_limit >= 0",
            name="per_customer_limit_non_negative",
        ),
        CheckConstraint(
            "starts_at IS NULL OR expires_at IS NULL OR expires_at >= starts_at",
            name="window_ordered",
        ),
        # Codes are unique among live rows only; a deleted coupon frees its code.
        Index(
            "ix_discounts_code",
            "code",
            unique=True,
            postgresql_where=text("code IS NOT NULL AND deleted_at IS NULL"),
        ),
    )

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    #: Present = a coupon (must be quoted at the till); absent = an automatic offer.
    code: Mapped[str | None] = mapped_column(String(40), index=True)

    scope: Mapped[str] = mapped_column(String(16), server_default=text("'cart'"), nullable=False)
    type: Mapped[str] = mapped_column(
        String(16), server_default=text("'percentage'"), nullable=False
    )
    value: Mapped[Decimal] = mapped_column(MONEY, server_default=text("0"), nullable=False)

    min_order_amount: Mapped[Decimal] = mapped_column(
        MONEY, server_default=text("0"), nullable=False
    )
    max_discount_amount: Mapped[Decimal | None] = mapped_column(MONEY)

    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    usage_limit: Mapped[int | None] = mapped_column(Integer)
    per_customer_limit: Mapped[int | None] = mapped_column(Integer)

    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=text("true"), nullable=False
    )
    first_order_only: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("false"), nullable=False
    )
    exclude_discounted: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("false"), nullable=False
    )
    #: Reserved: there is no shipping in the app yet, so this changes nothing.
    free_shipping: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("false"), nullable=False
    )

    products: Mapped[list[DiscountProduct]] = relationship(
        cascade="all, delete-orphan", lazy="selectin"
    )
    categories: Mapped[list[DiscountCategory]] = relationship(
        cascade="all, delete-orphan", lazy="selectin"
    )
    brands: Mapped[list[DiscountBrand]] = relationship(
        cascade="all, delete-orphan", lazy="selectin"
    )

    @property
    def product_ids(self) -> set[uuid.UUID]:
        return {link.product_id for link in self.products}

    @property
    def category_ids(self) -> set[uuid.UUID]:
        return {link.category_id for link in self.categories}

    @property
    def brand_ids(self) -> set[uuid.UUID]:
        return {link.brand_id for link in self.brands}

    @property
    def is_coupon(self) -> bool:
        return self.code is not None

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<Discount {self.code or self.name}>"


class DiscountProduct(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "discount_products"
    __table_args__ = (
        UniqueConstraint(
            "discount_id", "product_id", name="uq_discount_products_discount_id_product_id"
        ),
    )

    discount_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("discounts.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    product: Mapped[Product] = relationship(lazy="joined")


class DiscountCategory(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "discount_categories"
    __table_args__ = (
        UniqueConstraint(
            "discount_id", "category_id", name="uq_discount_categories_discount_id_category_id"
        ),
    )

    discount_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("discounts.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    category: Mapped[Category] = relationship(lazy="joined")


class DiscountBrand(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "discount_brands"
    __table_args__ = (
        UniqueConstraint(
            "discount_id", "brand_id", name="uq_discount_brands_discount_id_brand_id"
        ),
    )

    discount_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("discounts.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    brand_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("brands.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    brand: Mapped[Brand] = relationship(lazy="joined")
