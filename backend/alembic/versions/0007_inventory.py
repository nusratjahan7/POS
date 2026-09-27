"""inventory: stock levels and the stock movement ledger

Revision ID: 0007_inventory
Revises: 0006_catalog_partial_unique
Create Date: 2026-09-27

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0007_inventory"
down_revision: str | None = "0006_catalog_partial_unique"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UUID = postgresql.UUID(as_uuid=True)
NOW = sa.text("now()")
QUANTITY = sa.Numeric(12, 3)

MOVEMENT_TYPES = ("opening", "stock_in", "stock_out", "adjustment", "damage")
REFERENCE_TYPES = ("manual", "opening", "purchase", "sale")


def upgrade() -> None:
    op.create_table(
        "stock_levels",
        sa.Column("id", UUID, server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("product_id", UUID, nullable=False),
        sa.Column("branch_id", UUID, nullable=False),
        sa.Column("quantity", QUANTITY, server_default=sa.text("0"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.CheckConstraint("quantity >= 0", name="ck_stock_levels_quantity_non_negative"),
        sa.ForeignKeyConstraint(
            ["branch_id"],
            ["branches.id"],
            name="fk_stock_levels_branch_id_branches",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["products.id"],
            name="fk_stock_levels_product_id_products",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_stock_levels"),
        sa.UniqueConstraint("product_id", "branch_id", name="uq_stock_levels_product_id_branch_id"),
    )
    op.create_index("ix_stock_levels_product_id", "stock_levels", ["product_id"], unique=False)
    op.create_index("ix_stock_levels_branch_id", "stock_levels", ["branch_id"], unique=False)

    movement_types = ", ".join(f"'{value}'" for value in MOVEMENT_TYPES)
    reference_types = ", ".join(f"'{value}'" for value in REFERENCE_TYPES)

    op.create_table(
        "stock_movements",
        sa.Column("id", UUID, server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("product_id", UUID, nullable=False),
        sa.Column("branch_id", UUID, nullable=False),
        sa.Column("quantity", QUANTITY, nullable=False),
        sa.Column("movement_type", sa.String(length=20), nullable=False),
        sa.Column(
            "reference_type",
            sa.String(length=20),
            server_default=sa.text("'manual'"),
            nullable=False,
        ),
        sa.Column("reference_id", UUID, nullable=True),
        sa.Column("previous_stock", QUANTITY, nullable=False),
        sa.Column("new_stock", QUANTITY, nullable=False),
        sa.Column("note", sa.String(length=255), nullable=True),
        sa.Column("user_id", UUID, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.CheckConstraint(
            f"movement_type IN ({movement_types})", name="ck_stock_movements_valid_movement_type"
        ),
        sa.CheckConstraint(
            f"reference_type IN ({reference_types})",
            name="ck_stock_movements_valid_reference_type",
        ),
        sa.CheckConstraint("quantity <> 0", name="ck_stock_movements_quantity_non_zero"),
        sa.CheckConstraint(
            "new_stock = previous_stock + quantity", name="ck_stock_movements_stock_math"
        ),
        sa.CheckConstraint(
            "previous_stock >= 0", name="ck_stock_movements_previous_stock_non_negative"
        ),
        sa.CheckConstraint("new_stock >= 0", name="ck_stock_movements_new_stock_non_negative"),
        sa.ForeignKeyConstraint(
            ["branch_id"],
            ["branches.id"],
            name="fk_stock_movements_branch_id_branches",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["products.id"],
            name="fk_stock_movements_product_id_products",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_stock_movements_user_id_users", ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_stock_movements"),
    )
    op.create_index(
        "ix_stock_movements_product_id", "stock_movements", ["product_id"], unique=False
    )
    op.create_index("ix_stock_movements_branch_id", "stock_movements", ["branch_id"], unique=False)
    op.create_index(
        "ix_stock_movements_reference_id", "stock_movements", ["reference_id"], unique=False
    )
    op.create_index("ix_stock_movements_user_id", "stock_movements", ["user_id"], unique=False)
    op.create_index(
        "ix_stock_movements_created_at", "stock_movements", ["created_at"], unique=False
    )


def downgrade() -> None:
    for name in (
        "ix_stock_movements_created_at",
        "ix_stock_movements_user_id",
        "ix_stock_movements_reference_id",
        "ix_stock_movements_branch_id",
        "ix_stock_movements_product_id",
    ):
        op.drop_index(name, table_name="stock_movements")
    op.drop_table("stock_movements")

    op.drop_index("ix_stock_levels_branch_id", table_name="stock_levels")
    op.drop_index("ix_stock_levels_product_id", table_name="stock_levels")
    op.drop_table("stock_levels")
