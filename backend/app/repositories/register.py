from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import Any, ClassVar

from sqlalchemy import Select, func, select

from app.models.register import Register
from app.repositories.base import BaseRepository
from app.utils.pagination import PageParams
from app.utils.text import like_pattern


class RegisterRepository(BaseRepository[Register]):
    model = Register

    SORTABLE: ClassVar[dict[str, Any]] = {
        "created_at": Register.created_at,
        "updated_at": Register.updated_at,
        "name": Register.name,
    }

    async def name_exists(
        self,
        name: str,
        *,
        branch_id: uuid.UUID,
        exclude_id: uuid.UUID | None = None,
    ) -> bool:
        stmt = select(Register.id).where(
            Register.branch_id == branch_id,
            func.lower(Register.name) == name.strip().lower(),
            Register.deleted_at.is_(None),
        )
        if exclude_id is not None:
            stmt = stmt.where(Register.id != exclude_id)
        return (await self.session.execute(stmt.limit(1))).scalar_one_or_none() is not None

    def build_list_query(
        self,
        *,
        search: str | None = None,
        branch_id: uuid.UUID | None = None,
        is_active: bool | None = None,
    ) -> Select[Any]:
        stmt = select(Register).where(Register.deleted_at.is_(None))
        if search:
            pattern = like_pattern(search)
            stmt = stmt.where(Register.name.ilike(pattern, escape="\\"))
        if branch_id is not None:
            stmt = stmt.where(Register.branch_id == branch_id)
        if is_active is not None:
            stmt = stmt.where(Register.is_active.is_(is_active))
        return stmt

    async def list_registers(
        self,
        params: PageParams,
        *,
        sort: tuple[Any, bool] | None = None,
        **filters: Any,
    ) -> tuple[Sequence[Register], int]:
        stmt = self.build_list_query(**filters)
        if sort is not None:
            column, descending = sort
            stmt = stmt.order_by(column.desc() if descending else column.asc())
        else:
            stmt = stmt.order_by(Register.name.asc())
        return await self.paginate(stmt, params)

    async def list_all(self, *, branch_id: uuid.UUID | None = None) -> Sequence[Register]:
        stmt = select(Register).where(Register.deleted_at.is_(None))
        if branch_id is not None:
            stmt = stmt.where(Register.branch_id == branch_id)
        return (await self.session.execute(stmt.order_by(Register.name.asc()))).scalars().all()

    async def count_in_branch(self, branch_id: uuid.UUID) -> int:
        stmt = select(func.count(Register.id)).where(
            Register.branch_id == branch_id, Register.deleted_at.is_(None)
        )
        return int((await self.session.execute(stmt)).scalar_one())
