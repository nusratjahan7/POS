"""sale refunds: refund fields, the refunded status and a return movement type

Revision ID: 0011_sale_refunds
Revises: 0010_sales
Create Date: 2026-09-29

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0011_sale_refunds"
down_revision: str | None = "0010_sales"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UUID = postgresql.UUID(as_uuid=True)

# Widened value sets — keep in lock-step with app.models.sale.SALE_STATUSES and
# app.models.stock_movement.MOVEMENT_TYPES.
SALE_STATUSES = "'completed', 'voided', 'refunded'"
MOVEMENT_TYPES = "'opening', 'stock_in', 'stock_out', 'adjustment', 'damage', 'return'"
PREVIOUS_SALE_STATUSES = "'completed', 'voided'"
PREVIOUS_MOVEMENT_TYPES = "'opening', 'stock_in', 'stock_out', 'adjustment', 'damage'"


def upgrade() -> None:
    op.add_column("sales", sa.Column("refunded_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("sales", sa.Column("refunded_by_id", UUID, nullable=True))
    op.add_column("sales", sa.Column("refund_reason", sa.String(length=255), nullable=True))
    op.create_foreign_key(
        "fk_sales_refunded_by_id_users",
        "sales",
        "users",
        ["refunded_by_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_sales_refunded_by_id", "sales", ["refunded_by_id"], unique=False)

    op.drop_constraint("ck_sales_valid_status", "sales", type_="check")
    op.create_check_constraint("ck_sales_valid_status", "sales", f"status IN ({SALE_STATUSES})")

    op.drop_constraint("ck_stock_movements_valid_movement_type", "stock_movements", type_="check")
    op.create_check_constraint(
        "ck_stock_movements_valid_movement_type",
        "stock_movements",
        f"movement_type IN ({MOVEMENT_TYPES})",
    )


def downgrade() -> None:
    op.drop_constraint("ck_stock_movements_valid_movement_type", "stock_movements", type_="check")
    op.create_check_constraint(
        "ck_stock_movements_valid_movement_type",
        "stock_movements",
        f"movement_type IN ({PREVIOUS_MOVEMENT_TYPES})",
    )

    op.drop_constraint("ck_sales_valid_status", "sales", type_="check")
    op.create_check_constraint(
        "ck_sales_valid_status", "sales", f"status IN ({PREVIOUS_SALE_STATUSES})"
    )

    op.drop_index("ix_sales_refunded_by_id", table_name="sales")
    op.drop_constraint("fk_sales_refunded_by_id_users", "sales", type_="foreignkey")
    op.drop_column("sales", "refund_reason")
    op.drop_column("sales", "refunded_by_id")
    op.drop_column("sales", "refunded_at")
