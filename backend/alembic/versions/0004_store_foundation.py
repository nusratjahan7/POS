"""store foundation: businesses, branch link, registers, payment methods

Revision ID: 0004_store_foundation
Revises: 0003_product_catalog
Create Date: 2026-09-27

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004_store_foundation"
down_revision: str | None = "0003_product_catalog"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UUID = postgresql.UUID(as_uuid=True)
NOW = sa.text("now()")
MONEY = sa.Numeric(12, 2)
RATE = sa.Numeric(6, 3)


def upgrade() -> None:
    op.create_table(
        "businesses",
        sa.Column("id", UUID, server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("logo_url", sa.String(length=500), nullable=True),
        sa.Column("phone", sa.String(length=32), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("address", sa.String(length=255), nullable=True),
        sa.Column("currency", sa.String(length=3), server_default=sa.text("'USD'"), nullable=False),
        sa.Column(
            "timezone", sa.String(length=64), server_default=sa.text("'UTC'"), nullable=False
        ),
        sa.Column("tax_enabled", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("tax_inclusive", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column(
            "tax_label", sa.String(length=32), server_default=sa.text("'Tax'"), nullable=False
        ),
        sa.Column("default_tax_rate", RATE, server_default=sa.text("0"), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "default_tax_rate >= 0", name="ck_businesses_default_tax_rate_non_negative"
        ),
        sa.CheckConstraint(
            "default_tax_rate <= 100", name="ck_businesses_default_tax_rate_at_most_100"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_businesses"),
    )

    # Existing branches adopt the first business later; the column is nullable so
    # the migration is safe on a populated database.
    op.add_column("branches", sa.Column("business_id", UUID, nullable=True))
    op.create_foreign_key(
        "fk_branches_business_id_businesses",
        "branches",
        "businesses",
        ["business_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_branches_business_id", "branches", ["business_id"], unique=False)

    op.create_table(
        "registers",
        sa.Column("id", UUID, server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("branch_id", UUID, nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("default_opening_balance", MONEY, server_default=sa.text("0"), nullable=False),
        sa.Column(
            "require_opening_balance", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
        sa.Column(
            "allow_opening_balance_override",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "default_opening_balance >= 0", name="ck_registers_opening_balance_non_negative"
        ),
        sa.ForeignKeyConstraint(
            ["branch_id"],
            ["branches.id"],
            name="fk_registers_branch_id_branches",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_registers"),
        sa.UniqueConstraint("branch_id", "name", name="uq_registers_branch_id_name"),
    )
    op.create_index("ix_registers_branch_id", "registers", ["branch_id"], unique=False)

    op.create_table(
        "payment_methods",
        sa.Column("id", UUID, server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("code", sa.String(length=40), nullable=False),
        sa.Column("kind", sa.String(length=20), server_default=sa.text("'other'"), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column(
            "opens_cash_drawer", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
        sa.Column(
            "requires_reference", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
        sa.Column("is_system", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "kind IN ('cash', 'card', 'mobile', 'bank', 'other')",
            name="ck_payment_methods_valid_kind",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_payment_methods"),
    )
    op.create_index("ix_payment_methods_name", "payment_methods", ["name"], unique=True)
    op.create_index("ix_payment_methods_code", "payment_methods", ["code"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_payment_methods_code", table_name="payment_methods")
    op.drop_index("ix_payment_methods_name", table_name="payment_methods")
    op.drop_table("payment_methods")

    op.drop_index("ix_registers_branch_id", table_name="registers")
    op.drop_table("registers")

    op.drop_index("ix_branches_business_id", table_name="branches")
    op.drop_constraint("fk_branches_business_id_businesses", "branches", type_="foreignkey")
    op.drop_column("branches", "business_id")

    op.drop_table("businesses")
