from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import Any, ClassVar

from sqlalchemy import Select, func, select

from app.models.expense_category import ExpenseCategory
from app.repositories.base import BaseRepository
from app.utils.pagination import PageParams
from app.utils.text import like_pattern


class ExpenseCategoryRepository(BaseRepository[ExpenseCategory]):
    model = ExpenseCategory

    SORTABLE: ClassVar[dict[str, Any]] = {
        "name": ExpenseCategory.name,
        "created_at": ExpenseCategory.created_at,
        "updated_at": ExpenseCategory.updated_at,
    }

    async def name_exists(self, name: str, *, exclude_id: uuid.UUID | None = None) -> bool:
        stmt = select(ExpenseCategory.id).where(
            func.lower(ExpenseCategory.name) == name.strip().lower(),
            ExpenseCategory.deleted_at.is_(None),
        )
        if exclude_id is not None:
            stmt = stmt.where(ExpenseCategory.id != exclude_id)
        return (await self.session.execute(stmt.limit(1))).scalar_one_or_none() is not None

    def build_list_query(
        self, *, search: str | None = None, is_active: bool | None = None
    ) -> Select[Any]:
        stmt = select(ExpenseCategory).where(ExpenseCategory.deleted_at.is_(None))
        if search:
            pattern = like_pattern(search)
            stmt = stmt.where(ExpenseCategory.name.ilike(pattern, escape="\\"))
        if is_active is not None:
            stmt = stmt.where(ExpenseCategory.is_active.is_(is_active))
        return stmt

    async def list_categories(
        self,
        params: PageParams,
        *,
        sort: tuple[Any, bool] | None = None,
        **filters: Any,
    ) -> tuple[Sequence[ExpenseCategory], int]:
        stmt = self.build_list_query(**filters)
        if sort is not None:
            column, descending = sort
            stmt = stmt.order_by(column.desc() if descending else column.asc())
        else:
            stmt = stmt.order_by(ExpenseCategory.name.asc())
        return await self.paginate(stmt, params)

    async def list_all(self, *, active_only: bool = True) -> Sequence[ExpenseCategory]:
        stmt = select(ExpenseCategory).where(ExpenseCategory.deleted_at.is_(None))
        if active_only:
            stmt = stmt.where(ExpenseCategory.is_active.is_(True))
        result = await self.session.execute(stmt.order_by(ExpenseCategory.name.asc()))
        return result.scalars().all()
