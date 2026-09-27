from __future__ import annotations

from sqlalchemy import select

from app.models.business import Business
from app.repositories.base import BaseRepository


class BusinessRepository(BaseRepository[Business]):
    model = Business

    async def get_default(self) -> Business | None:
        """The single active business, oldest first.

        Multi-business is not supported yet, so "the" business is the earliest
        active row that has not been soft-deleted.
        """
        stmt = (
            select(Business)
            .where(Business.deleted_at.is_(None))
            .order_by(Business.created_at.asc())
            .limit(1)
        )
        return (await self.session.execute(stmt)).scalars().first()
