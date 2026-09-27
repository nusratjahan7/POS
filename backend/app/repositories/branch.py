from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import Any, ClassVar

from sqlalchemy import Select, func, select

from app.models.branch import Branch
from app.models.user import User
from app.repositories.base import BaseRepository
from app.utils.pagination import PageParams
from app.utils.text import like_pattern, normalize_code


class BranchRepository(BaseRepository[Branch]):
    model = Branch

    SORTABLE: ClassVar[dict[str, Any]] = {
        "created_at": Branch.created_at,
        "name": Branch.name,
        "code": Branch.code,
    }

    async def get_by_code(self, code: str) -> Branch | None:
        stmt = select(Branch).where(Branch.code == normalize_code(code))
        return (await self.session.execute(stmt)).scalars().one_or_none()

    async def code_exists(self, code: str, *, exclude_id: uuid.UUID | None = None) -> bool:
        stmt = select(Branch.id).where(Branch.code == normalize_code(code))
        if exclude_id is not None:
            stmt = stmt.where(Branch.id != exclude_id)
        return (await self.session.execute(stmt.limit(1))).scalar_one_or_none() is not None

    def build_list_query(
        self,
        *,
        search: str | None = None,
        is_active: bool | None = None,
    ) -> Select[Any]:
        stmt = select(Branch).where(Branch.deleted_at.is_(None))
        if search:
            pattern = like_pattern(search)
            stmt = stmt.where(
                Branch.name.ilike(pattern, escape="\\") | Branch.code.ilike(pattern, escape="\\")
            )
        if is_active is not None:
            stmt = stmt.where(Branch.is_active.is_(is_active))
        return stmt

    async def list_branches(
        self,
        params: PageParams,
        *,
        sort: tuple[Any, bool] | None = None,
        **filters: Any,
    ) -> tuple[Sequence[Branch], int]:
        stmt = self.build_list_query(**filters)
        if sort is not None:
            column, descending = sort
            stmt = stmt.order_by(column.desc() if descending else column.asc())
        else:
            stmt = stmt.order_by(Branch.name.asc())
        return await self.paginate(stmt, params)

    async def list_all(self) -> Sequence[Branch]:
        stmt = select(Branch).where(Branch.deleted_at.is_(None)).order_by(Branch.name.asc())
        return (await self.session.execute(stmt)).scalars().all()

    async def count_users(self, branch_id: uuid.UUID) -> int:
        stmt = select(func.count(User.id)).where(
            User.branch_id == branch_id, User.deleted_at.is_(None)
        )
        return int((await self.session.execute(stmt)).scalar_one())
