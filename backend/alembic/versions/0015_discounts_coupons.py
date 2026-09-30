"""discounts and coupons

A single ``discounts`` table covers automatic promotions and coded coupons; the
link tables target products/categories/brands, and ``discount_redemptions``
records what actually applied to each sale.

Revision ID: 0015_discounts_coupons
Revises: 0014_expenses_cash_register
Create Date: 2026-09-30

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0015_discounts_coupons"
down_revision: str | None = "0014_expenses_cash_register"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UUID = postgresql.UUID(as_uuid=True)
NOW = sa.text("now()")
MONEY = sa.Numeric(12, 2)

SCOPES = "'product', 'cart'"
TYPES = "'percentage', 'fixed'"


def upgrade() -> None:
    op.create_table(
        "discounts",
        sa.Column("id", UUID, server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("code", sa.String(length=40), nullable=True),
        sa.Column("scope", sa.String(length=16), server_default=sa.text("'cart'"), nullable=False),
        sa.Column(
            "type", sa.String(length=16), server_default=sa.text("'percentage'"), nullable=False
        ),
        sa.Column("value", MONEY, server_default=sa.text("0"), nullable=False),
        sa.Column("min_order_amount", MONEY, server_default=sa.text("0"), nullable=False),
        sa.Column("max_discount_amount", MONEY, nullable=True),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("usage_limit", sa.Integer(), nullable=True),
        sa.Column("per_customer_limit", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column(
            "first_order_only", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
        sa.Column(
            "exclude_discounted", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
        sa.Column("free_shipping", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(f"scope IN ({SCOPES})", name="ck_discounts_valid_scope"),
        sa.CheckConstraint(f"type IN ({TYPES})", name="ck_discounts_valid_type"),
        sa.CheckConstraint("value >= 0", name="ck_discounts_value_non_negative"),
        sa.CheckConstraint(
            "type <> 'percentage' OR value <= 100", name="ck_discounts_percentage_at_most_100"
        ),
        sa.CheckConstraint("min_order_amount >= 0", name="ck_discounts_min_order_non_negative"),
        sa.CheckConstraint(
            "max_discount_amount IS NULL OR max_discount_amount >= 0",
            name="ck_discounts_max_discount_non_negative",
        ),
        sa.CheckConstraint(
            "usage_limit IS NULL OR usage_limit >= 0", name="ck_discounts_usage_limit_non_negative"
        ),
        sa.CheckConstraint(
            "per_customer_limit IS NULL OR per_customer_limit >= 0",
            name="ck_discounts_per_customer_limit_non_negative",
        ),
        sa.CheckConstraint(
            "starts_at IS NULL OR expires_at IS NULL OR expires_at >= starts_at",
            name="ck_discounts_window_ordered",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_discounts"),
    )
    op.create_index(
        "ix_discounts_code",
        "discounts",
        ["code"],
        unique=True,
        postgresql_where=sa.text("code IS NOT NULL AND deleted_at IS NULL"),
    )

    for table, target, target_fk in (
        ("discount_products", "product_id", "products"),
        ("discount_categories", "category_id", "categories"),
        ("discount_brands", "brand_id", "brands"),
    ):
        op.create_table(
            table,
            sa.Column("id", UUID, server_default=sa.text("gen_random_uuid()"), nullable=False),
            sa.Column("discount_id", UUID, nullable=False),
            sa.Column(target, UUID, nullable=False),
            sa.ForeignKeyConstraint(
                ["discount_id"],
                ["discounts.id"],
                name=f"fk_{table}_discount_id_discounts",
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                [target],
                [f"{target_fk}.id"],
                name=f"fk_{table}_{target}_{target_fk}",
                ondelete="CASCADE",
            ),
            sa.PrimaryKeyConstraint("id", name=f"pk_{table}"),
            sa.UniqueConstraint("discount_id", target, name=f"uq_{table}_discount_id_{target}"),
        )
        op.create_index(f"ix_{table}_discount_id", table, ["discount_id"])
        op.create_index(f"ix_{table}_{target}", table, [target])

    op.create_table(
        "discount_redemptions",
        sa.Column("id", UUID, server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("discount_id", UUID, nullable=True),
        sa.Column("sale_id", UUID, nullable=False),
        sa.Column("customer_id", UUID, nullable=True),
        sa.Column("code", sa.String(length=40), nullable=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("amount", MONEY, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.CheckConstraint("amount >= 0", name="ck_discount_redemptions_amount_non_negative"),
        sa.ForeignKeyConstraint(
            ["discount_id"],
            ["discounts.id"],
            name="fk_discount_redemptions_discount_id_discounts",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["sale_id"],
            ["sales.id"],
            name="fk_discount_redemptions_sale_id_sales",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["customer_id"],
            ["customers.id"],
            name="fk_discount_redemptions_customer_id_customers",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_discount_redemptions"),
    )
    op.create_index(
        "ix_discount_redemptions_discount_id", "discount_redemptions", ["discount_id"]
    )
    op.create_index("ix_discount_redemptions_sale_id", "discount_redemptions", ["sale_id"])
    op.create_index(
        "ix_discount_redemptions_customer_id", "discount_redemptions", ["customer_id"]
    )
    op.create_index("ix_discount_redemptions_created_at", "discount_redemptions", ["created_at"])


def downgrade() -> None:
    for name in (
        "ix_discount_redemptions_created_at",
        "ix_discount_redemptions_customer_id",
        "ix_discount_redemptions_sale_id",
        "ix_discount_redemptions_discount_id",
    ):
        op.drop_index(name, table_name="discount_redemptions")
    op.drop_table("discount_redemptions")

    for table, target in (
        ("discount_brands", "brand_id"),
        ("discount_categories", "category_id"),
        ("discount_products", "product_id"),
    ):
        op.drop_index(f"ix_{table}_{target}", table_name=table)
        op.drop_index(f"ix_{table}_discount_id", table_name=table)
        op.drop_table(table)

    op.drop_index("ix_discounts_code", table_name="discounts")
    op.drop_table("discounts")
