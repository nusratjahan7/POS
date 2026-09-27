"""categories hierarchy and images, brand logos

Revision ID: 0005_catalog_taxonomy
Revises: 0004_store_foundation
Create Date: 2026-09-27

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005_catalog_taxonomy"
down_revision: str | None = "0004_store_foundation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.add_column("categories", sa.Column("image_url", sa.String(length=500), nullable=True))
    op.add_column("categories", sa.Column("parent_id", UUID, nullable=True))
    op.create_foreign_key(
        "fk_categories_parent_id_categories",
        "categories",
        "categories",
        ["parent_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_categories_parent_id", "categories", ["parent_id"], unique=False)
    op.create_check_constraint(
        "ck_categories_parent_not_self",
        "categories",
        "parent_id IS NULL OR parent_id != id",
    )

    op.add_column("brands", sa.Column("logo_url", sa.String(length=500), nullable=True))


def downgrade() -> None:
    op.drop_column("brands", "logo_url")

    op.drop_constraint("ck_categories_parent_not_self", "categories", type_="check")
    op.drop_index("ix_categories_parent_id", table_name="categories")
    op.drop_constraint("fk_categories_parent_id_categories", "categories", type_="foreignkey")
    op.drop_column("categories", "parent_id")
    op.drop_column("categories", "image_url")
