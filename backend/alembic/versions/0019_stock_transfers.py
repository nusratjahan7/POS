"""stock transfers between branches

Adds the transfer document (header + lines) and widens the stock-movement and
notification value sets it needs: ``transfer_out`` / ``transfer_in`` movement
types, a ``transfer`` reference type, and the two transfer notification types.

Revision ID: 0019_stock_transfers
Revises: 0018_multi_branch
Create Date: 2026-10-10

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0019_stock_transfers"
down_revision: str | None = "0018_multi_branch"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UUID = postgresql.UUID(as_uuid=True)
NOW = sa.text("now()")
QUANTITY = sa.Numeric(12, 3)

# Keep in lock-step with app.models.stock_movement.MOVEMENT_TYPES / REFERENCE_TYPES.
MOVEMENT_TYPES = (
    "'opening', 'stock_in', 'stock_out', 'adjustment', 'damage', 'return', "
    "'transfer_out', 'transfer_in'"
)
PREVIOUS_MOVEMENT_TYPES = "'opening', 'stock_in', 'stock_out', 'adjustment', 'damage', 'return'"
REFERENCE_TYPES = "'manual', 'opening', 'purchase', 'sale', 'sale_return', 'transfer'"
PREVIOUS_REFERENCE_TYPES = "'manual', 'opening', 'purchase', 'sale', 'sale_return'"

# Keep in lock-step with the subject line of transfer notifications.
NOTIFICATION_TYPES = (
    "'low_stock', 'out_of_stock', 'customer_due', 'supplier_due', 'new_sale', "
    "'refund', 'system', 'transfer_shipped', 'transfer_received'"
)
PREVIOUS_NOTIFICATION_TYPES = (
    "'low_stock', 'out_of_stock', 'customer_due', 'supplier_due', 'new_sale', 'refund', 'system'"
)

TRANSFER_STATUSES = "'draft', 'requested', 'approved', 'shipped', 'received', 'cancelled'"


def upgrade() -> None:
    op.drop_constraint("ck_stock_movements_valid_movement_type", "stock_movements", type_="check")
    op.create_check_constraint(
        "ck_stock_movements_valid_movement_type",
        "stock_movements",
        f"movement_type IN ({MOVEMENT_TYPES})",
    )

    op.drop_constraint("ck_stock_movements_valid_reference_type", "stock_movements", type_="check")
    op.create_check_constraint(
        "ck_stock_movements_valid_reference_type",
        "stock_movements",
        f"reference_type IN ({REFERENCE_TYPES})",
    )

    op.drop_constraint("ck_notifications_valid_type", "notifications", type_="check")
    op.create_check_constraint(
        "ck_notifications_valid_type",
        "notifications",
        f"type IN ({NOTIFICATION_TYPES})",
    )

    op.create_table(
        "stock_transfers",
        sa.Column("id", UUID, server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("transfer_number", sa.String(length=32), nullable=False),
        sa.Column(
            "status", sa.String(length=16), server_default=sa.text("'draft'"), nullable=False
        ),
        sa.Column("from_branch_id", UUID, nullable=False),
        sa.Column("to_branch_id", UUID, nullable=False),
        sa.Column("reference", sa.String(length=64), nullable=True),
        sa.Column("note", sa.String(length=255), nullable=True),
        sa.Column("cancel_reason", sa.String(length=255), nullable=True),
        sa.Column("created_by_id", UUID, nullable=True),
        sa.Column("requested_by_id", UUID, nullable=True),
        sa.Column("approved_by_id", UUID, nullable=True),
        sa.Column("shipped_by_id", UUID, nullable=True),
        sa.Column("received_by_id", UUID, nullable=True),
        sa.Column("cancelled_by_id", UUID, nullable=True),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("shipped_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.CheckConstraint(
            f"status IN ({TRANSFER_STATUSES})", name="ck_stock_transfers_valid_status"
        ),
        sa.CheckConstraint(
            "from_branch_id <> to_branch_id", name="ck_stock_transfers_distinct_branches"
        ),
        sa.ForeignKeyConstraint(
            ["from_branch_id"],
            ["branches.id"],
            name="fk_stock_transfers_from_branch_id_branches",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["to_branch_id"],
            ["branches.id"],
            name="fk_stock_transfers_to_branch_id_branches",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_id"],
            ["users.id"],
            name="fk_stock_transfers_created_by_id_users",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["requested_by_id"],
            ["users.id"],
            name="fk_stock_transfers_requested_by_id_users",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["approved_by_id"],
            ["users.id"],
            name="fk_stock_transfers_approved_by_id_users",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["shipped_by_id"],
            ["users.id"],
            name="fk_stock_transfers_shipped_by_id_users",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["received_by_id"],
            ["users.id"],
            name="fk_stock_transfers_received_by_id_users",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["cancelled_by_id"],
            ["users.id"],
            name="fk_stock_transfers_cancelled_by_id_users",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_stock_transfers"),
    )
    op.create_index(
        "ix_stock_transfers_transfer_number", "stock_transfers", ["transfer_number"], unique=True
    )
    op.create_index("ix_stock_transfers_status", "stock_transfers", ["status"], unique=False)
    op.create_index(
        "ix_stock_transfers_from_branch_id", "stock_transfers", ["from_branch_id"], unique=False
    )
    op.create_index(
        "ix_stock_transfers_to_branch_id", "stock_transfers", ["to_branch_id"], unique=False
    )
    op.create_index(
        "ix_stock_transfers_created_by_id", "stock_transfers", ["created_by_id"], unique=False
    )
    op.create_index(
        "ix_stock_transfers_approved_by_id", "stock_transfers", ["approved_by_id"], unique=False
    )
    op.create_index(
        "ix_stock_transfers_shipped_by_id", "stock_transfers", ["shipped_by_id"], unique=False
    )
    op.create_index(
        "ix_stock_transfers_received_by_id", "stock_transfers", ["received_by_id"], unique=False
    )

    op.create_table(
        "stock_transfer_lines",
        sa.Column("id", UUID, server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("transfer_id", UUID, nullable=False),
        sa.Column("product_id", UUID, nullable=False),
        sa.Column("product_name", sa.String(length=200), nullable=False),
        sa.Column("sku", sa.String(length=64), nullable=False),
        sa.Column("quantity", QUANTITY, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.CheckConstraint("quantity > 0", name="ck_stock_transfer_lines_quantity_positive"),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["products.id"],
            name="fk_stock_transfer_lines_product_id_products",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["transfer_id"],
            ["stock_transfers.id"],
            name="fk_stock_transfer_lines_transfer_id_stock_transfers",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_stock_transfer_lines"),
        sa.UniqueConstraint(
            "transfer_id",
            "product_id",
            name="uq_stock_transfer_lines_transfer_id_product_id",
        ),
    )
    op.create_index(
        "ix_stock_transfer_lines_transfer_id", "stock_transfer_lines", ["transfer_id"], unique=False
    )
    op.create_index(
        "ix_stock_transfer_lines_product_id", "stock_transfer_lines", ["product_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_stock_transfer_lines_product_id", table_name="stock_transfer_lines")
    op.drop_index("ix_stock_transfer_lines_transfer_id", table_name="stock_transfer_lines")
    op.drop_table("stock_transfer_lines")

    for name in (
        "ix_stock_transfers_received_by_id",
        "ix_stock_transfers_shipped_by_id",
        "ix_stock_transfers_approved_by_id",
        "ix_stock_transfers_created_by_id",
        "ix_stock_transfers_to_branch_id",
        "ix_stock_transfers_from_branch_id",
        "ix_stock_transfers_status",
        "ix_stock_transfers_transfer_number",
    ):
        op.drop_index(name, table_name="stock_transfers")
    op.drop_table("stock_transfers")

    op.drop_constraint("ck_notifications_valid_type", "notifications", type_="check")
    op.create_check_constraint(
        "ck_notifications_valid_type",
        "notifications",
        f"type IN ({PREVIOUS_NOTIFICATION_TYPES})",
    )

    op.drop_constraint("ck_stock_movements_valid_reference_type", "stock_movements", type_="check")
    op.create_check_constraint(
        "ck_stock_movements_valid_reference_type",
        "stock_movements",
        f"reference_type IN ({PREVIOUS_REFERENCE_TYPES})",
    )

    op.drop_constraint("ck_stock_movements_valid_movement_type", "stock_movements", type_="check")
    op.create_check_constraint(
        "ck_stock_movements_valid_movement_type",
        "stock_movements",
        f"movement_type IN ({PREVIOUS_MOVEMENT_TYPES})",
    )
