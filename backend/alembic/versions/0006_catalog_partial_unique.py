"""catalog uniqueness applies to live rows only

Soft-deleted rows must not reserve a name, slug, SKU or barcode forever. These
indexes become partial (``WHERE deleted_at IS NULL``) to match the service-level
existence checks, which already ignore deleted rows.

Revision ID: 0006_catalog_partial_unique
Revises: 0005_catalog_taxonomy
Create Date: 2026-09-27

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006_catalog_partial_unique"
down_revision: str | None = "0005_catalog_taxonomy"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

LIVE = sa.text("deleted_at IS NULL")

# (index name, table, column) — all currently plain unique indexes.
UNIQUE_INDEXES: tuple[tuple[str, str, str], ...] = (
    ("ix_products_slug", "products", "slug"),
    ("ix_products_sku", "products", "sku"),
    ("ix_products_barcode", "products", "barcode"),
    ("ix_categories_name", "categories", "name"),
    ("ix_categories_slug", "categories", "slug"),
    ("ix_brands_name", "brands", "name"),
    ("ix_brands_slug", "brands", "slug"),
)


def upgrade() -> None:
    for name, table, column in UNIQUE_INDEXES:
        op.drop_index(name, table_name=table)
        op.create_index(name, table, [column], unique=True, postgresql_where=LIVE)


def downgrade() -> None:
    for name, table, column in UNIQUE_INDEXES:
        op.drop_index(name, table_name=table)
        op.create_index(name, table, [column], unique=True)
