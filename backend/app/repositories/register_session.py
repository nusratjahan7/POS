from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import date
from typing import Any, ClassVar

from sqlalchemy import Select, func, select

from app.models.register_session import RegisterSession
from app.repositories.base import BaseRepository
from app.utils.pagination import PageParams


class RegisterSessionRepository(BaseRepository[RegisterSession]):
    model = RegisterSession

    SORTABLE: ClassVar[dict[str, Any]] = {
        "opened_at": RegisterSession.opened_at,
        "closed_at": RegisterSession.closed_at,
        "created_at": RegisterSession.created_at,
    }

    def build_list_query(
        self,
        *,
        register_id: uuid.UUID | None = None,
        branch_id: uuid.UUID | None = None,
        status: str | None = None,
        cashier_id: uuid.UUID | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> Select[Any]:
        stmt = select(RegisterSession)
        if register_id is not None:
            stmt = stmt.where(RegisterSession.register_id == register_id)
        if branch_id is not None:
            stmt = stmt.where(RegisterSession.branch_id == branch_id)
        if status is not None:
            stmt = stmt.where(RegisterSession.status == status)
        if cashier_id is not None:
            stmt = stmt.where(RegisterSession.opened_by_id == cashier_id)
        if date_from is not None:
            stmt = stmt.where(func.date(RegisterSession.opened_at) >= date_from)
        if date_to is not None:
            stmt = stmt.where(func.date(RegisterSession.opened_at) <= date_to)
        return stmt

    async def list_sessions(
        self,
        params: PageParams,
        *,
        sort: tuple[Any, bool] | None = None,
        **filters: Any,
    ) -> tuple[Sequence[RegisterSession], int]:
        stmt = self.build_list_query(**filters)
        if sort is not None:
            column, descending = sort
            stmt = stmt.order_by(column.desc() if descending else column.asc())
        else:
            stmt = stmt.order_by(RegisterSession.opened_at.desc())
        return await self.paginate(stmt, params)

    async def get_open_for_register(self, register_id: uuid.UUID) -> RegisterSession | None:
        stmt = select(RegisterSession).where(
            RegisterSession.register_id == register_id,
            RegisterSession.status == "open",
        )
        return (await self.session.execute(stmt)).scalars().one_or_none()

    async def get_detailed(self, session_id: uuid.UUID) -> RegisterSession | None:
        """A session with its movements loaded, refreshed from the database.

        ``populate_existing`` matters: after a write (e.g. closing) the identity
        map still holds the pre-write relationships, so a plain select would
        return a stale ``closed_by``/``movements``.
        """
        stmt = (
            select(RegisterSession)
            .where(RegisterSession.id == session_id)
            .execution_options(populate_existing=True)
        )
        return (await self.session.execute(stmt)).scalars().one_or_none()

    async def list_open(self, *, branch_id: uuid.UUID | None = None) -> Sequence[RegisterSession]:
        stmt = select(RegisterSession).where(RegisterSession.status == "open")
        if branch_id is not None:
            stmt = stmt.where(RegisterSession.branch_id == branch_id)
        result = await self.session.execute(stmt.order_by(RegisterSession.opened_at.asc()))
        return result.scalars().all()
