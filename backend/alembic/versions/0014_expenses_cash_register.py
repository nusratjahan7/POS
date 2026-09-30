"""expenses and the cash register session ledger

Adds the spend ledger (categories + expenses) and the cash reconciliation
workflow: register sessions, their signed cash movements, and the open-session
uniqueness the till relies on.

Revision ID: 0014_expenses_cash_register
Revises: 0013_dues_ledger
Create Date: 2026-09-30

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0014_expenses_cash_register"
down_revision: str | None = "0013_dues_ledger"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UUID = postgresql.UUID(as_uuid=True)
NOW = sa.text("now()")
MONEY = sa.Numeric(12, 2)

SESSION_STATUSES = "'open', 'closed'"
MOVEMENT_TYPES = "'sale', 'refund', 'expense', 'cash_in', 'cash_out'"
REFERENCE_TYPES = "'sale', 'sale_return', 'expense', 'manual'"


def upgrade() -> None:
    op.create_table(
        "expense_categories",
        sa.Column("id", UUID, server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_expense_categories"),
    )
    # A deleted category must not reserve its name forever.
    op.create_index(
        "ix_expense_categories_name",
        "expense_categories",
        ["name"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    op.create_table(
        "register_sessions",
        sa.Column("id", UUID, server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("register_id", UUID, nullable=False),
        sa.Column("branch_id", UUID, nullable=False),
        sa.Column("opening_cash", MONEY, server_default=sa.text("0"), nullable=False),
        sa.Column(
            "status", sa.String(length=16), server_default=sa.text("'open'"), nullable=False
        ),
        sa.Column("opened_by_id", UUID, nullable=True),
        sa.Column("opened_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.Column("closed_by_id", UUID, nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expected_cash", MONEY, nullable=True),
        sa.Column("actual_cash", MONEY, nullable=True),
        sa.Column("difference", MONEY, nullable=True),
        sa.Column("closing_note", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.CheckConstraint(
            f"status IN ({SESSION_STATUSES})", name="ck_register_sessions_valid_status"
        ),
        sa.CheckConstraint(
            "opening_cash >= 0", name="ck_register_sessions_opening_cash_non_negative"
        ),
        sa.CheckConstraint(
            "actual_cash IS NULL OR actual_cash >= 0",
            name="ck_register_sessions_actual_cash_non_negative",
        ),
        sa.ForeignKeyConstraint(
            ["register_id"],
            ["registers.id"],
            name="fk_register_sessions_register_id_registers",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["branch_id"],
            ["branches.id"],
            name="fk_register_sessions_branch_id_branches",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["opened_by_id"],
            ["users.id"],
            name="fk_register_sessions_opened_by_id_users",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["closed_by_id"],
            ["users.id"],
            name="fk_register_sessions_closed_by_id_users",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_register_sessions"),
    )
    op.create_index("ix_register_sessions_register_id", "register_sessions", ["register_id"])
    op.create_index("ix_register_sessions_branch_id", "register_sessions", ["branch_id"])
    op.create_index("ix_register_sessions_opened_by_id", "register_sessions", ["opened_by_id"])
    op.create_index("ix_register_sessions_closed_by_id", "register_sessions", ["closed_by_id"])
    op.create_index("ix_register_sessions_opened_at", "register_sessions", ["opened_at"])
    # At most one open session per register — enforced by the database.
    op.create_index(
        "uq_register_sessions_open_register",
        "register_sessions",
        ["register_id"],
        unique=True,
        postgresql_where=sa.text("status = 'open'"),
    )

    op.create_table(
        "expenses",
        sa.Column("id", UUID, server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("branch_id", UUID, nullable=False),
        sa.Column("category_id", UUID, nullable=False),
        sa.Column("payment_method_id", UUID, nullable=False),
        sa.Column("register_session_id", UUID, nullable=True),
        sa.Column("amount", MONEY, nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("reference", sa.String(length=64), nullable=True),
        sa.Column("spent_at", sa.Date(), nullable=False),
        sa.Column("created_by_id", UUID, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.CheckConstraint("amount > 0", name="ck_expenses_amount_positive"),
        sa.ForeignKeyConstraint(
            ["branch_id"],
            ["branches.id"],
            name="fk_expenses_branch_id_branches",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["category_id"],
            ["expense_categories.id"],
            name="fk_expenses_category_id_expense_categories",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["payment_method_id"],
            ["payment_methods.id"],
            name="fk_expenses_payment_method_id_payment_methods",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["register_session_id"],
            ["register_sessions.id"],
            name="fk_expenses_register_session_id_register_sessions",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_id"],
            ["users.id"],
            name="fk_expenses_created_by_id_users",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_expenses"),
    )
    op.create_index("ix_expenses_branch_id", "expenses", ["branch_id"])
    op.create_index("ix_expenses_category_id", "expenses", ["category_id"])
    op.create_index("ix_expenses_payment_method_id", "expenses", ["payment_method_id"])
    op.create_index("ix_expenses_register_session_id", "expenses", ["register_session_id"])
    op.create_index("ix_expenses_created_by_id", "expenses", ["created_by_id"])
    op.create_index("ix_expenses_spent_at", "expenses", ["spent_at"])

    op.create_table(
        "cash_movements",
        sa.Column("id", UUID, server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("session_id", UUID, nullable=False),
        sa.Column("movement_type", sa.String(length=20), nullable=False),
        sa.Column("amount", MONEY, nullable=False),
        sa.Column(
            "reference_type",
            sa.String(length=20),
            server_default=sa.text("'manual'"),
            nullable=False,
        ),
        sa.Column("reference_id", UUID, nullable=True),
        sa.Column("note", sa.String(length=255), nullable=True),
        sa.Column("user_id", UUID, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.CheckConstraint(
            f"movement_type IN ({MOVEMENT_TYPES})", name="ck_cash_movements_valid_movement_type"
        ),
        sa.CheckConstraint(
            f"reference_type IN ({REFERENCE_TYPES})",
            name="ck_cash_movements_valid_reference_type",
        ),
        sa.CheckConstraint("amount <> 0", name="ck_cash_movements_amount_non_zero"),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["register_sessions.id"],
            name="fk_cash_movements_session_id_register_sessions",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_cash_movements_user_id_users",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_cash_movements"),
    )
    op.create_index("ix_cash_movements_session_id", "cash_movements", ["session_id"])
    op.create_index("ix_cash_movements_reference_id", "cash_movements", ["reference_id"])
    op.create_index("ix_cash_movements_user_id", "cash_movements", ["user_id"])
    op.create_index("ix_cash_movements_created_at", "cash_movements", ["created_at"])


def downgrade() -> None:
    for name in (
        "ix_cash_movements_created_at",
        "ix_cash_movements_user_id",
        "ix_cash_movements_reference_id",
        "ix_cash_movements_session_id",
    ):
        op.drop_index(name, table_name="cash_movements")
    op.drop_table("cash_movements")

    for name in (
        "ix_expenses_spent_at",
        "ix_expenses_created_by_id",
        "ix_expenses_register_session_id",
        "ix_expenses_payment_method_id",
        "ix_expenses_category_id",
        "ix_expenses_branch_id",
    ):
        op.drop_index(name, table_name="expenses")
    op.drop_table("expenses")

    op.drop_index("uq_register_sessions_open_register", table_name="register_sessions")
    for name in (
        "ix_register_sessions_opened_at",
        "ix_register_sessions_closed_by_id",
        "ix_register_sessions_opened_by_id",
        "ix_register_sessions_branch_id",
        "ix_register_sessions_register_id",
    ):
        op.drop_index(name, table_name="register_sessions")
    op.drop_table("register_sessions")

    op.drop_index("ix_expense_categories_name", table_name="expense_categories")
    op.drop_table("expense_categories")
