"""offline sale idempotency key

Adds ``sales.offline_id`` — the client-assigned key a till stamps on a sale rung
while offline. A unique index makes replaying the same queued sale idempotent:
the second insert fails on the index and the service returns the original sale
instead of creating a duplicate.

Revision ID: 0020_offline_sales
Revises: 0019_stock_transfers
Create Date: 2026-10-10

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0020_offline_sales"
down_revision: str | None = "0019_stock_transfers"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.add_column("sales", sa.Column("offline_id", UUID, nullable=True))
    # Postgres permits many NULLs under a unique index, so online sales (NULL)
    # are unaffected while replaying a non-null key can never duplicate.
    op.create_index("ix_sales_offline_id", "sales", ["offline_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_sales_offline_id", table_name="sales")
    op.drop_column("sales", "offline_id")
