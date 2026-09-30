"""dues management: protect the supplier payable and index payment dates

The supplier balance is a payable that is only ever increased by a received
purchase and decreased by a payment — never below what is owed. The check makes
that invariant the database's business too. The payment index mirrors
``ix_customer_payments_paid_at`` so both ledgers order by date efficiently.

No new tables: the ledgers are derived from rows that already exist.

Revision ID: 0013_dues_ledger
Revises: 0012_sale_returns
Create Date: 2026-09-30

"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0013_dues_ledger"
down_revision: str | None = "0012_sale_returns"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_check_constraint(
        "ck_suppliers_balance_non_negative", "suppliers", "balance >= 0"
    )
    op.create_index(
        "ix_supplier_payments_paid_at", "supplier_payments", ["paid_at"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_supplier_payments_paid_at", table_name="supplier_payments")
    op.drop_constraint("ck_suppliers_balance_non_negative", "suppliers", type_="check")
