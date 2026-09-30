"""sale returns and refunds

Adds the return document (header + lines), the sale's running ``returned_amount``
and a ``sale_return`` stock-movement reference type.

Revision ID: 0012_sale_returns
Revises: 0011_sale_refunds
Create Date: 2026-09-29

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0012_sale_returns"
down_revision: str | None = "0011_sale_refunds"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UUID = postgresql.UUID(as_uuid=True)
NOW = sa.text("now()")
MONEY = sa.Numeric(12, 2)
QUANTITY = sa.Numeric(12, 3)

RETURN_STATUSES = "'requested', 'approved', 'completed', 'cancelled'"
REFERENCE_TYPES = "'manual', 'opening', 'purchase', 'sale', 'sale_return'"
PREVIOUS_REFERENCE_TYPES = "'manual', 'opening', 'purchase', 'sale'"


def upgrade() -> None:
    op.add_column(
        "sales",
        sa.Column("returned_amount", MONEY, server_default=sa.text("0"), nullable=False),
    )
    op.create_check_constraint(
        "ck_sales_returned_amount_non_negative", "sales", "returned_amount >= 0"
    )
    op.create_check_constraint(
        "ck_sales_returned_amount_within_total", "sales", "returned_amount <= total"
    )

    op.drop_constraint("ck_stock_movements_valid_reference_type", "stock_movements", type_="check")
    op.create_check_constraint(
        "ck_stock_movements_valid_reference_type",
        "stock_movements",
        f"reference_type IN ({REFERENCE_TYPES})",
    )

    op.create_table(
        "sale_returns",
        sa.Column("id", UUID, server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("sale_id", UUID, nullable=False),
        sa.Column("return_number", sa.String(length=32), nullable=False),
        sa.Column(
            "status", sa.String(length=16), server_default=sa.text("'completed'"), nullable=False
        ),
        sa.Column("reason", sa.String(length=255), nullable=True),
        sa.Column("note", sa.String(length=255), nullable=True),
        sa.Column("payment_method_id", UUID, nullable=True),
        sa.Column("refund_reference", sa.String(length=64), nullable=True),
        sa.Column("refund_amount", MONEY, server_default=sa.text("0"), nullable=False),
        sa.Column("credit_reversed", MONEY, server_default=sa.text("0"), nullable=False),
        sa.Column("cash_refund", MONEY, server_default=sa.text("0"), nullable=False),
        sa.Column("created_by_id", UUID, nullable=True),
        sa.Column("completed_by_id", UUID, nullable=True),
        sa.Column("cancelled_by_id", UUID, nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.CheckConstraint(f"status IN ({RETURN_STATUSES})", name="ck_sale_returns_valid_status"),
        sa.CheckConstraint("cash_refund >= 0", name="ck_sale_returns_cash_refund_non_negative"),
        sa.CheckConstraint(
            "credit_reversed >= 0", name="ck_sale_returns_credit_reversed_non_negative"
        ),
        sa.CheckConstraint("refund_amount >= 0", name="ck_sale_returns_refund_amount_non_negative"),
        sa.CheckConstraint(
            "credit_reversed + cash_refund = refund_amount",
            name="ck_sale_returns_refund_split_math",
        ),
        sa.ForeignKeyConstraint(
            ["cancelled_by_id"],
            ["users.id"],
            name="fk_sale_returns_cancelled_by_id_users",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["completed_by_id"],
            ["users.id"],
            name="fk_sale_returns_completed_by_id_users",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_id"],
            ["users.id"],
            name="fk_sale_returns_created_by_id_users",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["payment_method_id"],
            ["payment_methods.id"],
            name="fk_sale_returns_payment_method_id_payment_methods",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["sale_id"], ["sales.id"], name="fk_sale_returns_sale_id_sales", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_sale_returns"),
    )
    op.create_index("ix_sale_returns_sale_id", "sale_returns", ["sale_id"], unique=False)
    op.create_index("ix_sale_returns_return_number", "sale_returns", ["return_number"], unique=True)
    op.create_index(
        "ix_sale_returns_payment_method_id", "sale_returns", ["payment_method_id"], unique=False
    )
    op.create_index(
        "ix_sale_returns_created_by_id", "sale_returns", ["created_by_id"], unique=False
    )
    op.create_index(
        "ix_sale_returns_completed_by_id", "sale_returns", ["completed_by_id"], unique=False
    )

    op.create_table(
        "sale_return_items",
        sa.Column("id", UUID, server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("return_id", UUID, nullable=False),
        sa.Column("sale_item_id", UUID, nullable=False),
        sa.Column("product_id", UUID, nullable=False),
        sa.Column("product_name", sa.String(length=200), nullable=False),
        sa.Column("sku", sa.String(length=64), nullable=False),
        sa.Column("quantity", QUANTITY, nullable=False),
        sa.Column("unit_price", MONEY, nullable=False),
        sa.Column("line_total", MONEY, nullable=False),
        sa.CheckConstraint("line_total >= 0", name="ck_sale_return_items_line_total_non_negative"),
        sa.CheckConstraint("quantity > 0", name="ck_sale_return_items_quantity_positive"),
        sa.CheckConstraint("unit_price >= 0", name="ck_sale_return_items_unit_price_non_negative"),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["products.id"],
            name="fk_sale_return_items_product_id_products",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["return_id"],
            ["sale_returns.id"],
            name="fk_sale_return_items_return_id_sale_returns",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["sale_item_id"],
            ["sale_items.id"],
            name="fk_sale_return_items_sale_item_id_sale_items",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_sale_return_items"),
    )
    op.create_index(
        "ix_sale_return_items_return_id", "sale_return_items", ["return_id"], unique=False
    )
    op.create_index(
        "ix_sale_return_items_sale_item_id", "sale_return_items", ["sale_item_id"], unique=False
    )
    op.create_index(
        "ix_sale_return_items_product_id", "sale_return_items", ["product_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_sale_return_items_product_id", table_name="sale_return_items")
    op.drop_index("ix_sale_return_items_sale_item_id", table_name="sale_return_items")
    op.drop_index("ix_sale_return_items_return_id", table_name="sale_return_items")
    op.drop_table("sale_return_items")

    op.drop_index("ix_sale_returns_completed_by_id", table_name="sale_returns")
    op.drop_index("ix_sale_returns_created_by_id", table_name="sale_returns")
    op.drop_index("ix_sale_returns_payment_method_id", table_name="sale_returns")
    op.drop_index("ix_sale_returns_return_number", table_name="sale_returns")
    op.drop_index("ix_sale_returns_sale_id", table_name="sale_returns")
    op.drop_table("sale_returns")

    op.drop_constraint("ck_stock_movements_valid_reference_type", "stock_movements", type_="check")
    op.create_check_constraint(
        "ck_stock_movements_valid_reference_type",
        "stock_movements",
        f"reference_type IN ({PREVIOUS_REFERENCE_TYPES})",
    )

    op.drop_constraint("ck_sales_returned_amount_within_total", "sales", type_="check")
    op.drop_constraint("ck_sales_returned_amount_non_negative", "sales", type_="check")
    op.drop_column("sales", "returned_amount")
