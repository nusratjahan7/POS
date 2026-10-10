from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import UUIDPrimaryKeyMixin


class AuditLog(Base, UUIDPrimaryKeyMixin):
    """An immutable record of one sensitive action.

    Append-only: there is no update or delete path. The actor is stored both as a
    foreign key and as a denormalised ``user_email``/``user_name`` snapshot, so the
    entry still reads correctly after the account is renamed or removed.

    ``old_data``/``new_data`` are JSON snapshots built explicitly by the caller and
    passed through a deep redactor (see :class:`~app.services.audit_log.AuditLogService`),
    so a password, hash or token can never reach this table.
    """

    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_logs_module_action", "module", "action"),
        Index("ix_audit_logs_entity", "entity", "entity_id"),
    )

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    user_email: Mapped[str | None] = mapped_column(String(255))
    user_name: Mapped[str | None] = mapped_column(String(160))

    action: Mapped[str] = mapped_column(String(60), nullable=False)
    module: Mapped[str] = mapped_column(String(40), nullable=False)

    entity: Mapped[str | None] = mapped_column(String(40))
    entity_id: Mapped[str | None] = mapped_column(String(64))

    old_data: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    new_data: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    ip_address: Mapped[str | None] = mapped_column(String(45))
    user_agent: Mapped[str | None] = mapped_column(String(255))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<AuditLog {self.module}.{self.action} by {self.user_email}>"
