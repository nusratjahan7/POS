"""Generic repository primitives.

Repositories own SQL. Services own business rules. Nothing here raises HTTP
concepts — callers translate results into domain errors.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import Any, Generic, TypeVar

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import Base
from app.utils.pagination import PageParams

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    model: type[ModelT]

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, entity_id: uuid.UUID) -> ModelT | None:
        return await self.session.get(self.model, entity_id)

    async def add(self, obj: ModelT) -> ModelT:
        self.session.add(obj)
        await self.session.flush()
        return obj

    async def delete(self, obj: ModelT) -> None:
        await self.session.delete(obj)
        await self.session.flush()

    async def flush(self) -> None:
        await self.session.flush()

    async def count(self, stmt: Select[Any]) -> int:
        count_stmt = select(func.count()).select_from(stmt.order_by(None).subquery())
        return int((await self.session.execute(count_stmt)).scalar_one())

    async def paginate(
        self,
        stmt: Select[Any],
        params: PageParams,
    ) -> tuple[Sequence[ModelT], int]:
        total = await self.count(stmt)
        result = await self.session.execute(stmt.limit(params.limit).offset(params.offset))
        return result.scalars().unique().all(), total
