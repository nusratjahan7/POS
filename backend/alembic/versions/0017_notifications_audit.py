"""notifications and the persisted audit log

Two new append-mostly tables. ``notifications`` holds one row per recipient
(fanned out when the causing action commits), so an unread count and per-user read
state are exact. ``audit_logs`` records sensitive actions with old/new snapshots;
the actor is denormalised so entries survive user deletion, and snapshots are
redacted in the service layer so no secret is ever stored.

Revision ID: 0017_notifications_audit
Revises: 0016_reporting
Create Date: 2026-10-10

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0017_notifications_audit"
down_revision: str | None = "0016_reporting"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UUID = postgresql.UUID(as_uuid=True)
JSONB = postgresql.JSONB(astext_type=sa.Text())
NOW = sa.text("now()")

NOTIFICATION_TYPES = (
    "'low_stock', 'out_of_stock', 'customer_due', 'supplier_due', "
    "'new_sale', 'refund', 'system'"
)
NOTIFICATION_SEVERITIES = "'info', 'warning', 'critical'"


def upgrade() -> None:
    op.create_table(
        "notifications",
        sa.Column("id", UUID, server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", UUID, nullable=False),
        sa.Column("type", sa.String(length=32), nullable=False),
        sa.Column(
            "severity", sa.String(length=16), server_default=sa.text("'info'"), nullable=False
        ),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("body", sa.String(length=500), nullable=True),
        sa.Column("entity_type", sa.String(length=40), nullable=True),
        sa.Column("entity_id", sa.String(length=64), nullable=True),
        sa.Column("data", JSONB, nullable=True),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.CheckConstraint(
            f"severity IN ({NOTIFICATION_SEVERITIES})", name="ck_notifications_valid_severity"
        ),
        sa.CheckConstraint(f"type IN ({NOTIFICATION_TYPES})", name="ck_notifications_valid_type"),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_notifications_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_notifications"),
    )
    op.create_index(
        "ix_notifications_user_id_created_at",
        "notifications",
        ["user_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_notifications_user_id_read_at",
        "notifications",
        ["user_id", "read_at"],
        unique=False,
    )

    op.create_table(
        "audit_logs",
        sa.Column("id", UUID, server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", UUID, nullable=True),
        sa.Column("user_email", sa.String(length=255), nullable=True),
        sa.Column("user_name", sa.String(length=160), nullable=True),
        sa.Column("action", sa.String(length=60), nullable=False),
        sa.Column("module", sa.String(length=40), nullable=False),
        sa.Column("entity", sa.String(length=40), nullable=True),
        sa.Column("entity_id", sa.String(length=64), nullable=True),
        sa.Column("old_data", JSONB, nullable=True),
        sa.Column("new_data", JSONB, nullable=True),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.Column("user_agent", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_audit_logs_user_id_users",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_audit_logs"),
    )
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"], unique=False)
    op.create_index("ix_audit_logs_entity", "audit_logs", ["entity", "entity_id"], unique=False)
    op.create_index(
        "ix_audit_logs_module_action", "audit_logs", ["module", "action"], unique=False
    )
    op.create_index("ix_audit_logs_user_id", "audit_logs", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_audit_logs_user_id", table_name="audit_logs")
    op.drop_index("ix_audit_logs_module_action", table_name="audit_logs")
    op.drop_index("ix_audit_logs_entity", table_name="audit_logs")
    op.drop_index("ix_audit_logs_created_at", table_name="audit_logs")
    op.drop_table("audit_logs")

    op.drop_index("ix_notifications_user_id_read_at", table_name="notifications")
    op.drop_index("ix_notifications_user_id_created_at", table_name="notifications")
    op.drop_table("notifications")
