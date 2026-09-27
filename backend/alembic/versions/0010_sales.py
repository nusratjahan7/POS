"""sales, sale items and sale payments

Revision ID: 0010_sales
Revises: 0009_customers
Create Date: 2026-09-27

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0010_sales"
down_revision: str | None = "0009_customers"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UUID = postgresql.UUID(as_uuid=True)
NOW = sa.text("now()")
MONEY = sa.Numeric(12, 2)
QUANTITY = sa.Numeric(12, 3)
STATUSES = "'completed', 'voided'"


def upgrade() -> None:
    op.create_table(
        "sales",
        sa.Column("id", UUID, server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("sale_number", sa.String(length=32), nullable=False),
        sa.Column("branch_id", UUID, nullable=False),
        sa.Column("register_id", UUID, nullable=True),
        sa.Column("customer_id", UUID, nullable=True),
        sa.Column("cashier_id", UUID, nullable=True),
        sa.Column("subtotal", MONEY, server_default=sa.text("0"), nullable=False),
        sa.Column("discount", MONEY, server_default=sa.text("0"), nullable=False),
        sa.Column("tax", MONEY, server_default=sa.text("0"), nullable=False),
        sa.Column("total", MONEY, server_default=sa.text("0"), nullable=False),
        sa.Column("paid", MONEY, server_default=sa.text("0"), nullable=False),
        sa.Column("due", MONEY, server_default=sa.text("0"), nullable=False),
        sa.Column("change_amount", MONEY, server_default=sa.text("0"), nullable=False),
        sa.Column(
            "status", sa.String(length=16), server_default=sa.text("'completed'"), nullable=False
        ),
        sa.Column("note", sa.String(length=255), nullable=True),
        sa.Column("sold_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.Column("voided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.CheckConstraint("change_amount >= 0", name="ck_sales_change_amount_non_negative"),
        sa.CheckConstraint("discount >= 0", name="ck_sales_discount_non_negative"),
        sa.CheckConstraint("due = total - paid", name="ck_sales_due_math"),
        sa.CheckConstraint("due >= 0", name="ck_sales_due_non_negative"),
        sa.CheckConstraint("paid >= 0", name="ck_sales_paid_non_negative"),
        sa.CheckConstraint("subtotal >= 0", name="ck_sales_subtotal_non_negative"),
        sa.CheckConstraint("tax >= 0", name="ck_sales_tax_non_negative"),
        sa.CheckConstraint("total = subtotal - discount + tax", name="ck_sales_total_math"),
        sa.CheckConstraint("total >= 0", name="ck_sales_total_non_negative"),
        sa.CheckConstraint(f"status IN ({STATUSES})", name="ck_sales_valid_status"),
        sa.ForeignKeyConstraint(
            ["branch_id"],
            ["branches.id"],
            name="fk_sales_branch_id_branches",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["cashier_id"],
            ["users.id"],
            name="fk_sales_cashier_id_users",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["customer_id"],
            ["customers.id"],
            name="fk_sales_customer_id_customers",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["register_id"],
            ["registers.id"],
            name="fk_sales_register_id_registers",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_sales"),
    )
    op.create_index("ix_sales_sale_number", "sales", ["sale_number"], unique=True)
    op.create_index("ix_sales_branch_id", "sales", ["branch_id"], unique=False)
    op.create_index("ix_sales_register_id", "sales", ["register_id"], unique=False)
    op.create_index("ix_sales_customer_id", "sales", ["customer_id"], unique=False)
    op.create_index("ix_sales_cashier_id", "sales", ["cashier_id"], unique=False)
    op.create_index("ix_sales_sold_at", "sales", ["sold_at"], unique=False)

    op.create_table(
        "sale_items",
        sa.Column("id", UUID, server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("sale_id", UUID, nullable=False),
        sa.Column("product_id", UUID, nullable=False),
        sa.Column("product_name", sa.String(length=200), nullable=False),
        sa.Column("sku", sa.String(length=64), nullable=False),
        sa.Column("unit", sa.String(length=20), nullable=False),
        sa.Column("quantity", QUANTITY, nullable=False),
        sa.Column("unit_price", MONEY, nullable=False),
        sa.Column("discount", MONEY, nullable=False),
        sa.Column("subtotal", MONEY, nullable=False),
        sa.Column("line_total", MONEY, nullable=False),
        sa.CheckConstraint("discount >= 0", name="ck_sale_items_discount_non_negative"),
        sa.CheckConstraint("discount <= subtotal", name="ck_sale_items_discount_within_subtotal"),
        sa.CheckConstraint(
            "line_total = subtotal - discount", name="ck_sale_items_line_total_math"
        ),
        sa.CheckConstraint("line_total >= 0", name="ck_sale_items_line_total_non_negative"),
        sa.CheckConstraint("quantity > 0", name="ck_sale_items_quantity_positive"),
        sa.CheckConstraint("subtotal >= 0", name="ck_sale_items_subtotal_non_negative"),
        sa.CheckConstraint("unit_price >= 0", name="ck_sale_items_unit_price_non_negative"),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["products.id"],
            name="fk_sale_items_product_id_products",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["sale_id"],
            ["sales.id"],
            name="fk_sale_items_sale_id_sales",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_sale_items"),
        sa.UniqueConstraint("sale_id", "product_id", name="uq_sale_items_sale_id_product_id"),
    )
    op.create_index("ix_sale_items_sale_id", "sale_items", ["sale_id"], unique=False)
    op.create_index("ix_sale_items_product_id", "sale_items", ["product_id"], unique=False)

    op.create_table(
        "sale_payments",
        sa.Column("id", UUID, server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("sale_id", UUID, nullable=False),
        sa.Column("payment_method_id", UUID, nullable=False),
        sa.Column("amount", MONEY, nullable=False),
        sa.Column("tendered", MONEY, nullable=True),
        sa.Column("change_given", MONEY, server_default=sa.text("0"), nullable=False),
        sa.Column("reference", sa.String(length=64), nullable=True),
        sa.Column("note", sa.String(length=255), nullable=True),
        sa.Column("user_id", UUID, nullable=True),
        sa.Column("paid_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.CheckConstraint("amount > 0", name="ck_sale_payments_amount_positive"),
        sa.CheckConstraint("change_given >= 0", name="ck_sale_payments_change_non_negative"),
        sa.CheckConstraint(
            "tendered IS NULL OR tendered >= amount", name="ck_sale_payments_tendered_covers_amount"
        ),
        sa.ForeignKeyConstraint(
            ["payment_method_id"],
            ["payment_methods.id"],
            name="fk_sale_payments_payment_method_id_payment_methods",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["sale_id"],
            ["sales.id"],
            name="fk_sale_payments_sale_id_sales",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_sale_payments_user_id_users",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_sale_payments"),
    )
    op.create_index("ix_sale_payments_sale_id", "sale_payments", ["sale_id"], unique=False)
    op.create_index(
        "ix_sale_payments_payment_method_id", "sale_payments", ["payment_method_id"], unique=False
    )
    op.create_index("ix_sale_payments_user_id", "sale_payments", ["user_id"], unique=False)
    op.create_index("ix_sale_payments_paid_at", "sale_payments", ["paid_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_sale_payments_paid_at", table_name="sale_payments")
    op.drop_index("ix_sale_payments_user_id", table_name="sale_payments")
    op.drop_index("ix_sale_payments_payment_method_id", table_name="sale_payments")
    op.drop_index("ix_sale_payments_sale_id", table_name="sale_payments")
    op.drop_table("sale_payments")

    op.drop_index("ix_sale_items_product_id", table_name="sale_items")
    op.drop_index("ix_sale_items_sale_id", table_name="sale_items")
    op.drop_table("sale_items")

    op.drop_index("ix_sales_sold_at", table_name="sales")
    op.drop_index("ix_sales_cashier_id", table_name="sales")
    op.drop_index("ix_sales_customer_id", table_name="sales")
    op.drop_index("ix_sales_register_id", table_name="sales")
    op.drop_index("ix_sales_branch_id", table_name="sales")
    op.drop_index("ix_sales_sale_number", table_name="sales")
    op.drop_table("sales")
