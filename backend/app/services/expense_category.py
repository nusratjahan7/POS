"""Expense categories — the buckets expenses are filed under."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.models.expense_category import ExpenseCategory
from app.repositories.expense_category import ExpenseCategoryRepository
from app.schemas.expense import ExpenseCategoryCreate, ExpenseCategoryUpdate
from app.utils.pagination import PageParams


class ExpenseCategoryService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.categories = ExpenseCategoryRepository(session)

    async def get_or_404(self, category_id: uuid.UUID) -> ExpenseCategory:
        category = await self.categories.get(category_id)
        if category is None or category.is_deleted:
            raise NotFoundError("Expense category not found.", code="expense_category_not_found")
        return category

    async def list_categories(
        self,
        params: PageParams,
        *,
        search: str | None = None,
        is_active: bool | None = None,
        sort: tuple[Any, bool] | None = None,
    ) -> tuple[Sequence[ExpenseCategory], int]:
        return await self.categories.list_categories(
            params, sort=sort, search=search, is_active=is_active
        )

    async def list_all(self) -> Sequence[ExpenseCategory]:
        return await self.categories.list_all()

    async def _assert_name_free(self, name: str, *, exclude_id: uuid.UUID | None = None) -> None:
        if await self.categories.name_exists(name, exclude_id=exclude_id):
            raise ConflictError(
                "An expense category with that name already exists.",
                code="expense_category_name_taken",
                details=[{"field": "name", "message": "Already in use."}],
            )

    async def create(self, payload: ExpenseCategoryCreate) -> ExpenseCategory:
        name = payload.name.strip()
        await self._assert_name_free(name)
        category = ExpenseCategory(
            name=name,
            description=payload.description,
            is_active=payload.is_active,
        )
        await self.categories.add(category)
        await self.session.commit()
        return category

    async def update(
        self, category_id: uuid.UUID, payload: ExpenseCategoryUpdate
    ) -> ExpenseCategory:
        category = await self.get_or_404(category_id)
        if payload.name is not None:
            name = payload.name.strip()
            if name.lower() != category.name.lower():
                await self._assert_name_free(name, exclude_id=category.id)
                category.name = name
        if payload.description is not None:
            category.description = payload.description
        if payload.is_active is not None:
            category.is_active = payload.is_active
        await self.session.commit()
        return category

    async def delete(self, category_id: uuid.UUID) -> None:
        category = await self.get_or_404(category_id)
        category.is_active = False
        category.deleted_at = datetime.now(UTC)
        await self.session.commit()
