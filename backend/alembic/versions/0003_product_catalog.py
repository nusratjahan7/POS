"""product catalog: categories, brands, products

Revision ID: 0003_product_catalog
Revises: 0002_password_reset_tokens
Create Date: 2026-09-27

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003_product_catalog"
down_revision: str | None = "0002_password_reset_tokens"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UUID = postgresql.UUID(as_uuid=True)
NOW = sa.text("now()")
MONEY = sa.Numeric(12, 2)
QUANTITY = sa.Numeric(12, 3)


def _taxonomy(table: str) -> None:
    """`categories` and `brands` are structurally identical."""
    op.create_table(
        table,
        sa.Column("id", UUID, server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("slug", sa.String(length=140), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name=f"pk_{table}"),
    )
    op.create_index(f"ix_{table}_name", table, ["name"], unique=True)
    op.create_index(f"ix_{table}_slug", table, ["slug"], unique=True)


def upgrade() -> None:
    _taxonomy("categories")
    _taxonomy("brands")

    op.create_table(
        "products",
        sa.Column("id", UUID, server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("slug", sa.String(length=220), nullable=False),
        sa.Column("sku", sa.String(length=64), nullable=False),
        sa.Column("barcode", sa.String(length=64), nullable=True),
        sa.Column("category_id", UUID, nullable=True),
        sa.Column("brand_id", UUID, nullable=True),
        # Money is exact: Numeric, never float.
        sa.Column("purchase_price", MONEY, server_default=sa.text("0"), nullable=False),
        sa.Column("selling_price", MONEY, server_default=sa.text("0"), nullable=False),
        sa.Column("discount_price", MONEY, nullable=True),
        sa.Column("unit", sa.String(length=20), server_default=sa.text("'unit'"), nullable=False),
        sa.Column("minimum_stock", QUANTITY, server_default=sa.text("0"), nullable=False),
        # Denormalised cache; the inventory ledger will own this column.
        sa.Column("stock_quantity", QUANTITY, server_default=sa.text("0"), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("image_url", sa.String(length=500), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("purchase_price >= 0", name="ck_products_purchase_price_non_negative"),
        sa.CheckConstraint("selling_price >= 0", name="ck_products_selling_price_non_negative"),
        sa.CheckConstraint(
            "discount_price IS NULL OR discount_price >= 0",
            name="ck_products_discount_non_negative",
        ),
        sa.CheckConstraint("minimum_stock >= 0", name="ck_products_minimum_stock_non_negative"),
        sa.CheckConstraint("stock_quantity >= 0", name="ck_products_stock_quantity_non_negative"),
        sa.ForeignKeyConstraint(
            ["brand_id"],
            ["brands.id"],
            name="fk_products_brand_id_brands",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["category_id"],
            ["categories.id"],
            name="fk_products_category_id_categories",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_products"),
    )
    op.create_index("ix_products_slug", "products", ["slug"], unique=True)
    op.create_index("ix_products_sku", "products", ["sku"], unique=True)
    op.create_index("ix_products_barcode", "products", ["barcode"], unique=True)
    op.create_index("ix_products_category_id", "products", ["category_id"], unique=False)
    op.create_index("ix_products_brand_id", "products", ["brand_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_products_brand_id", table_name="products")
    op.drop_index("ix_products_category_id", table_name="products")
    op.drop_index("ix_products_barcode", table_name="products")
    op.drop_index("ix_products_sku", table_name="products")
    op.drop_index("ix_products_slug", table_name="products")
    op.drop_table("products")

    for table in ("brands", "categories"):
        op.drop_index(f"ix_{table}_slug", table_name=table)
        op.drop_index(f"ix_{table}_name", table_name=table)
        op.drop_table(table)
