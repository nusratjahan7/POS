"""suppliers and purchase management

Revision ID: 0008_suppliers_purchases
Revises: 0007_inventory
Create Date: 2026-09-27

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0008_suppliers_purchases"
down_revision: str | None = "0007_inventory"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UUID = postgresql.UUID(as_uuid=True)
NOW = sa.text("now()")
MONEY = sa.Numeric(12, 2)
QUANTITY = sa.Numeric(12, 3)

PURCHASE_STATUSES = ("draft", "pending", "received", "cancelled")


def upgrade() -> None:
    op.create_table(
        "suppliers",
        sa.Column("id", UUID, server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("company", sa.String(length=160), nullable=True),
        sa.Column("phone", sa.String(length=32), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("address", sa.String(length=255), nullable=True),
        sa.Column("opening_balance", MONEY, server_default=sa.text("0"), nullable=False),
        sa.Column("balance", MONEY, server_default=sa.text("0"), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_suppliers"),
    )
    op.create_index("ix_suppliers_name", "suppliers", ["name"], unique=True)

    statuses = ", ".join(f"'{value}'" for value in PURCHASE_STATUSES)

    op.create_table(
        "purchases",
        sa.Column("id", UUID, server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("purchase_number", sa.String(length=32), nullable=False),
        sa.Column("supplier_id", UUID, nullable=False),
        sa.Column("branch_id", UUID, nullable=False),
        sa.Column("purchase_date", sa.Date(), nullable=False),
        sa.Column("subtotal", MONEY, server_default=sa.text("0"), nullable=False),
        sa.Column("discount", MONEY, server_default=sa.text("0"), nullable=False),
        sa.Column("tax", MONEY, server_default=sa.text("0"), nullable=False),
        sa.Column("total", MONEY, server_default=sa.text("0"), nullable=False),
        sa.Column("paid", MONEY, server_default=sa.text("0"), nullable=False),
        sa.Column("due", MONEY, server_default=sa.text("0"), nullable=False),
        sa.Column(
            "status", sa.String(length=16), server_default=sa.text("'draft'"), nullable=False
        ),
        sa.Column("note", sa.String(length=255), nullable=True),
        sa.Column("created_by_id", UUID, nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.CheckConstraint(f"status IN ({statuses})", name="ck_purchases_valid_status"),
        sa.CheckConstraint("subtotal >= 0", name="ck_purchases_subtotal_non_negative"),
        sa.CheckConstraint("discount >= 0", name="ck_purchases_discount_non_negative"),
        sa.CheckConstraint("tax >= 0", name="ck_purchases_tax_non_negative"),
        sa.CheckConstraint("total >= 0", name="ck_purchases_total_non_negative"),
        sa.CheckConstraint("paid >= 0", name="ck_purchases_paid_non_negative"),
        sa.CheckConstraint("due >= 0", name="ck_purchases_due_non_negative"),
        sa.CheckConstraint("total = subtotal - discount + tax", name="ck_purchases_total_math"),
        sa.CheckConstraint("due = total - paid", name="ck_purchases_due_math"),
        sa.ForeignKeyConstraint(
            ["branch_id"],
            ["branches.id"],
            name="fk_purchases_branch_id_branches",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_id"],
            ["users.id"],
            name="fk_purchases_created_by_id_users",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["supplier_id"],
            ["suppliers.id"],
            name="fk_purchases_supplier_id_suppliers",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_purchases"),
    )
    op.create_index("ix_purchases_purchase_number", "purchases", ["purchase_number"], unique=True)
    op.create_index("ix_purchases_supplier_id", "purchases", ["supplier_id"], unique=False)
    op.create_index("ix_purchases_branch_id", "purchases", ["branch_id"], unique=False)
    op.create_index("ix_purchases_created_by_id", "purchases", ["created_by_id"], unique=False)

    op.create_table(
        "purchase_items",
        sa.Column("id", UUID, server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("purchase_id", UUID, nullable=False),
        sa.Column("product_id", UUID, nullable=False),
        sa.Column("quantity", QUANTITY, nullable=False),
        sa.Column("unit_price", MONEY, nullable=False),
        sa.Column("subtotal", MONEY, nullable=False),
        sa.CheckConstraint("quantity > 0", name="ck_purchase_items_quantity_positive"),
        sa.CheckConstraint("unit_price >= 0", name="ck_purchase_items_unit_price_non_negative"),
        sa.CheckConstraint("subtotal >= 0", name="ck_purchase_items_subtotal_non_negative"),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["products.id"],
            name="fk_purchase_items_product_id_products",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["purchase_id"],
            ["purchases.id"],
            name="fk_purchase_items_purchase_id_purchases",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_purchase_items"),
        sa.UniqueConstraint(
            "purchase_id", "product_id", name="uq_purchase_items_purchase_id_product_id"
        ),
    )
    op.create_index(
        "ix_purchase_items_purchase_id", "purchase_items", ["purchase_id"], unique=False
    )
    op.create_index("ix_purchase_items_product_id", "purchase_items", ["product_id"], unique=False)

    op.create_table(
        "supplier_payments",
        sa.Column("id", UUID, server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("supplier_id", UUID, nullable=False),
        sa.Column("purchase_id", UUID, nullable=True),
        sa.Column("amount", MONEY, nullable=False),
        sa.Column("method", sa.String(length=20), nullable=True),
        sa.Column("reference", sa.String(length=64), nullable=True),
        sa.Column("note", sa.String(length=255), nullable=True),
        sa.Column("user_id", UUID, nullable=True),
        sa.Column("paid_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.CheckConstraint("amount > 0", name="ck_supplier_payments_amount_positive"),
        sa.ForeignKeyConstraint(
            ["purchase_id"],
            ["purchases.id"],
            name="fk_supplier_payments_purchase_id_purchases",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["supplier_id"],
            ["suppliers.id"],
            name="fk_supplier_payments_supplier_id_suppliers",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_supplier_payments_user_id_users",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_supplier_payments"),
    )
    op.create_index("ix_supplier_payments_supplier_id", "supplier_payments", ["supplier_id"])
    op.create_index("ix_supplier_payments_purchase_id", "supplier_payments", ["purchase_id"])


def downgrade() -> None:
    op.drop_index("ix_supplier_payments_purchase_id", table_name="supplier_payments")
    op.drop_index("ix_supplier_payments_supplier_id", table_name="supplier_payments")
    op.drop_table("supplier_payments")

    op.drop_index("ix_purchase_items_product_id", table_name="purchase_items")
    op.drop_index("ix_purchase_items_purchase_id", table_name="purchase_items")
    op.drop_table("purchase_items")

    op.drop_index("ix_purchases_created_by_id", table_name="purchases")
    op.drop_index("ix_purchases_branch_id", table_name="purchases")
    op.drop_index("ix_purchases_supplier_id", table_name="purchases")
    op.drop_index("ix_purchases_purchase_number", table_name="purchases")
    op.drop_table("purchases")

    op.drop_index("ix_suppliers_name", table_name="suppliers")
    op.drop_table("suppliers")
