from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import select

from app.models.permission import Permission
from app.repositories.base import BaseRepository


class PermissionRepository(BaseRepository[Permission]):
    model = Permission

    async def get_by_code(self, code: str) -> Permission | None:
        stmt = select(Permission).where(Permission.code == code)
        return (await self.session.execute(stmt)).scalars().one_or_none()

    async def get_by_codes(self, codes: Sequence[str]) -> Sequence[Permission]:
        if not codes:
            return []
        stmt = select(Permission).where(Permission.code.in_(list(codes)))
        return (await self.session.execute(stmt)).scalars().all()

    async def list_all(self) -> Sequence[Permission]:
        stmt = select(Permission).order_by(Permission.resource.asc(), Permission.action.asc())
        return (await self.session.execute(stmt)).scalars().all()
