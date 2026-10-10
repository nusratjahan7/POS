from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import UUIDPrimaryKeyMixin

# Keep these tuples in lock-step with the CHECK constraints and the API literals.
NOTIFICATION_TYPES = (
    "low_stock",
    "out_of_stock",
    "customer_due",
    "supplier_due",
    "new_sale",
    "refund",
    "system",
)
NOTIFICATION_SEVERITIES = ("info", "warning", "critical")

_TYPES_SQL = ", ".join(f"'{value}'" for value in NOTIFICATION_TYPES)
_SEVERITIES_SQL = ", ".join(f"'{value}'" for value in NOTIFICATION_SEVERITIES)


class Notification(Base, UUIDPrimaryKeyMixin):
    """An in-app notification addressed to one recipient.

    Rows are fanned out per recipient at creation time (``user_id`` is the
    recipient, not the actor), so an unread count and read state are exact and
    cheap to query. ``entity_type``/``entity_id`` point at the record that caused
    the notification, and ``data`` carries a small typed payload (amounts, names)
    the centre renders without re-fetching the source.
    """

    __tablename__ = "notifications"
    __table_args__ = (
        CheckConstraint(f"type IN ({_TYPES_SQL})", name="valid_type"),
        CheckConstraint(f"severity IN ({_SEVERITIES_SQL})", name="valid_severity"),
        Index("ix_notifications_user_id_read_at", "user_id", "read_at"),
        Index("ix_notifications_user_id_created_at", "user_id", "created_at"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    type: Mapped[str] = mapped_column(String(32), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), server_default=text("'info'"), nullable=False)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    body: Mapped[str | None] = mapped_column(String(500))

    entity_type: Mapped[str | None] = mapped_column(String(40))
    entity_id: Mapped[str | None] = mapped_column(String(64))
    data: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<Notification {self.type} for {self.user_id}>"
