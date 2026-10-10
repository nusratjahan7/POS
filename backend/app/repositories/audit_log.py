from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import date, timedelta
from typing import Any, ClassVar

from sqlalchemy import Select, or_, select

from app.models.audit_log import AuditLog
from app.repositories.base import BaseRepository
from app.utils.pagination import PageParams
from app.utils.text import like_pattern


class AuditLogRepository(BaseRepository[AuditLog]):
    model = AuditLog

    SORTABLE: ClassVar[dict[str, Any]] = {
        "created_at": AuditLog.created_at,
        "action": AuditLog.action,
        "module": AuditLog.module,
    }

    def _apply_filters(
        self,
        stmt: Select[Any],
        *,
        module: str | None = None,
        action: str | None = None,
        entity: str | None = None,
        entity_id: str | None = None,
        user_id: uuid.UUID | None = None,
        search: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> Select[Any]:
        if module:
            stmt = stmt.where(AuditLog.module == module)
        if action:
            stmt = stmt.where(AuditLog.action == action)
        if entity:
            stmt = stmt.where(AuditLog.entity == entity)
        if entity_id:
            stmt = stmt.where(AuditLog.entity_id == entity_id)
        if user_id is not None:
            stmt = stmt.where(AuditLog.user_id == user_id)
        if search:
            pattern = like_pattern(search)
            stmt = stmt.where(
                or_(
                    AuditLog.action.ilike(pattern, escape="\\"),
                    AuditLog.module.ilike(pattern, escape="\\"),
                    AuditLog.entity.ilike(pattern, escape="\\"),
                    AuditLog.user_email.ilike(pattern, escape="\\"),
                    AuditLog.user_name.ilike(pattern, escape="\\"),
                )
            )
        if date_from is not None:
            stmt = stmt.where(AuditLog.created_at >= date_from)
        if date_to is not None:
            # Inclusive of the whole end day.
            stmt = stmt.where(AuditLog.created_at < date_to + timedelta(days=1))
        return stmt

    async def list_logs(
        self,
        params: PageParams,
        *,
        sort: tuple[Any, bool] | None = None,
        **filters: Any,
    ) -> tuple[Sequence[AuditLog], int]:
        stmt = self._apply_filters(select(AuditLog), **filters)
        if sort is not None:
            column, descending = sort
            stmt = stmt.order_by(column.desc() if descending else column.asc())
        else:
            stmt = stmt.order_by(AuditLog.created_at.desc())
        return await self.paginate(stmt, params)
