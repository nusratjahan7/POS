"""reporting: sale-line cost snapshot and a purchase-date index

Adds ``sale_items.cost_price`` — the unit cost captured when a sale is rung up —
so gross-profit reporting survives later purchase-price changes. Existing rows
are backfilled from the product's current purchase price, so historic figures are
approximate. Also indexes ``purchases.purchase_date`` for the report ranges
(``expenses.spent_at`` is already indexed by 0014).

Revision ID: 0016_reporting
Revises: 0015_discounts_coupons
Create Date: 2026-09-30

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0016_reporting"
down_revision: str | None = "0015_discounts_coupons"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

MONEY = sa.Numeric(12, 2)


def upgrade() -> None:
    op.add_column(
        "sale_items",
        sa.Column("cost_price", MONEY, server_default=sa.text("0"), nullable=False),
    )
    op.execute(
        """
        UPDATE sale_items AS si
        SET cost_price = p.purchase_price
        FROM products AS p
        WHERE p.id = si.product_id
        """
    )

    op.create_index("ix_purchases_purchase_date", "purchases", ["purchase_date"])


def downgrade() -> None:
    op.drop_index("ix_purchases_purchase_date", table_name="purchases")
    op.drop_column("sale_items", "cost_price")
