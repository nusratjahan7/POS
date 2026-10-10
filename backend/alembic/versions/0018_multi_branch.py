"""user to branch assignments (multi-branch support)

Adds ``user_branches`` — the many-to-many grant that decides which branches an
account may read and act on. ``users.branch_id`` remains the primary/default
branch; this table is the explicit assignment list. Existing accounts are
backfilled with their current primary branch so single-branch installs behave
exactly as before the upgrade.

Revision ID: 0018_multi_branch
Revises: 0017_notifications_audit
Create Date: 2026-10-10

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0018_multi_branch"
down_revision: str | None = "0017_notifications_audit"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UUID = postgresql.UUID(as_uuid=True)
NOW = sa.text("now()")


def upgrade() -> None:
    op.create_table(
        "user_branches",
        sa.Column("user_id", UUID, nullable=False),
        sa.Column("branch_id", UUID, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_user_branches_user_id_users",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["branch_id"],
            ["branches.id"],
            name="fk_user_branches_branch_id_branches",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("user_id", "branch_id", name="pk_user_branches"),
    )
    op.create_index(
        "ix_user_branches_branch_id", "user_branches", ["branch_id"], unique=False
    )

    # Backfill: every live account keeps its current primary branch in the
    # assignment list, so existing users see no change.
    op.execute(
        """
        INSERT INTO user_branches (user_id, branch_id)
        SELECT id, branch_id
        FROM users
        WHERE branch_id IS NOT NULL AND deleted_at IS NULL
        ON CONFLICT DO NOTHING
        """
    )


def downgrade() -> None:
    op.drop_index("ix_user_branches_branch_id", table_name="user_branches")
    op.drop_table("user_branches")
