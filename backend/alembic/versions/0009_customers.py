"""customers and customer payments

Revision ID: 0009_customers
Revises: 0008_suppliers_purchases
Create Date: 2026-09-27

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0009_customers"
down_revision: str | None = "0008_suppliers_purchases"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UUID = postgresql.UUID(as_uuid=True)
NOW = sa.text("now()")
MONEY = sa.Numeric(12, 2)


def upgrade() -> None:
    op.create_table(
        "customers",
        sa.Column("id", UUID, server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("phone", sa.String(length=32), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("address", sa.String(length=255), nullable=True),
        sa.Column("opening_balance", MONEY, server_default=sa.text("0"), nullable=False),
        sa.Column("balance", MONEY, server_default=sa.text("0"), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_customers"),
    )
    # Names are not unique — real customers share names.
    op.create_index("ix_customers_name", "customers", ["name"], unique=False)
    op.create_index("ix_customers_phone", "customers", ["phone"], unique=False)

    op.create_table(
        "customer_payments",
        sa.Column("id", UUID, server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("customer_id", UUID, nullable=False),
        sa.Column("amount", MONEY, nullable=False),
        sa.Column("method", sa.String(length=20), nullable=True),
        sa.Column("reference", sa.String(length=64), nullable=True),
        sa.Column("note", sa.String(length=255), nullable=True),
        sa.Column("user_id", UUID, nullable=True),
        sa.Column("paid_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.CheckConstraint("amount > 0", name="ck_customer_payments_amount_positive"),
        sa.ForeignKeyConstraint(
            ["customer_id"],
            ["customers.id"],
            name="fk_customer_payments_customer_id_customers",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_customer_payments_user_id_users",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_customer_payments"),
    )
    op.create_index("ix_customer_payments_customer_id", "customer_payments", ["customer_id"])
    op.create_index("ix_customer_payments_paid_at", "customer_payments", ["paid_at"])


def downgrade() -> None:
    op.drop_index("ix_customer_payments_paid_at", table_name="customer_payments")
    op.drop_index("ix_customer_payments_customer_id", table_name="customer_payments")
    op.drop_table("customer_payments")

    op.drop_index("ix_customers_phone", table_name="customers")
    op.drop_index("ix_customers_name", table_name="customers")
    op.drop_table("customers")
