from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import Any, ClassVar

from sqlalchemy import Select, func, select

from app.models.associations import user_roles
from app.models.role import Role
from app.repositories.base import BaseRepository
from app.utils.pagination import PageParams
from app.utils.text import like_pattern


class RoleRepository(BaseRepository[Role]):
    model = Role

    SORTABLE: ClassVar[dict[str, Any]] = {
        "created_at": Role.created_at,
        "updated_at": Role.updated_at,
        "name": Role.name,
    }

    async def get_by_name(self, name: str, *, include_deleted: bool = False) -> Role | None:
        stmt = select(Role).where(Role.name == name.strip())
        if not include_deleted:
            stmt = stmt.where(Role.deleted_at.is_(None))
        return (await self.session.execute(stmt)).scalars().unique().one_or_none()

    async def name_exists(self, name: str, *, exclude_id: uuid.UUID | None = None) -> bool:
        stmt = select(Role.id).where(Role.name == name.strip())
        if exclude_id is not None:
            stmt = stmt.where(Role.id != exclude_id)
        return (await self.session.execute(stmt.limit(1))).scalar_one_or_none() is not None

    async def get_many(self, role_ids: Sequence[uuid.UUID]) -> Sequence[Role]:
        if not role_ids:
            return []
        stmt = select(Role).where(Role.id.in_(list(role_ids)), Role.deleted_at.is_(None))
        return (await self.session.execute(stmt)).scalars().unique().all()

    def build_list_query(self, *, search: str | None = None) -> Select[Any]:
        stmt = select(Role).where(Role.deleted_at.is_(None))
        if search:
            pattern = like_pattern(search)
            stmt = stmt.where(
                Role.name.ilike(pattern, escape="\\") | Role.description.ilike(pattern, escape="\\")
            )
        return stmt

    async def list_roles(
        self,
        params: PageParams,
        *,
        sort: tuple[Any, bool] | None = None,
        search: str | None = None,
    ) -> tuple[Sequence[Role], int]:
        stmt = self.build_list_query(search=search)
        if sort is not None:
            column, descending = sort
            stmt = stmt.order_by(column.desc() if descending else column.asc())
        else:
            stmt = stmt.order_by(Role.name.asc())
        return await self.paginate(stmt, params)

    async def list_all(self) -> Sequence[Role]:
        stmt = select(Role).where(Role.deleted_at.is_(None)).order_by(Role.name.asc())
        return (await self.session.execute(stmt)).scalars().unique().all()

    async def count_users(self, role_id: uuid.UUID) -> int:
        stmt = select(func.count()).select_from(user_roles).where(user_roles.c.role_id == role_id)
        return int((await self.session.execute(stmt)).scalar_one())
