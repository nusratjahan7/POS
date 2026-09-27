"""Category management."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.models.category import Category
from app.repositories.category import CategoryRepository
from app.schemas.category import CategoryCreate, CategoryUpdate
from app.utils.pagination import PageParams
from app.utils.text import slugify

# Chosen so a natural-looking name always fits `Category.slug` (140 chars).
SLUG_MAX_LENGTH = 120


class CategoryService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.categories = CategoryRepository(session)

    async def get_or_404(self, category_id: uuid.UUID) -> Category:
        category = await self.categories.get(category_id)
        if category is None or category.is_deleted:
            raise NotFoundError("Category not found.", code="category_not_found")
        return category

    async def list_categories(
        self,
        params: PageParams,
        *,
        search: str | None = None,
        is_active: bool | None = None,
        sort: tuple[Any, bool] | None = None,
    ) -> tuple[Sequence[Category], int]:
        return await self.categories.list_categories(
            params, sort=sort, search=search, is_active=is_active
        )

    async def list_all(self) -> Sequence[Category]:
        return await self.categories.list_all()

    async def _unique_slug(self, name: str, *, exclude_id: uuid.UUID | None = None) -> str:
        base = slugify(name, max_length=SLUG_MAX_LENGTH)
        candidate, suffix = base, 2
        while await self.categories.slug_exists(candidate, exclude_id=exclude_id):
            candidate = f"{base}-{suffix}"
            suffix += 1
        return candidate

    async def _assert_name_free(self, name: str, *, exclude_id: uuid.UUID | None = None) -> None:
        if await self.categories.name_exists(name, exclude_id=exclude_id):
            raise ConflictError(
                "A category with that name already exists.",
                code="category_name_taken",
                details=[{"field": "name", "message": "Already in use."}],
            )

    async def create(self, payload: CategoryCreate) -> Category:
        name = payload.name.strip()
        await self._assert_name_free(name)

        category = Category(
            name=name,
            slug=await self._unique_slug(name),
            description=payload.description,
            is_active=payload.is_active,
        )
        await self.categories.add(category)
        await self.session.commit()
        return category

    async def update(self, category_id: uuid.UUID, payload: CategoryUpdate) -> Category:
        category = await self.get_or_404(category_id)

        if payload.name is not None:
            name = payload.name.strip()
            if name.lower() != category.name.lower():
                await self._assert_name_free(name, exclude_id=category.id)
                category.name = name
                # Renaming moves the slug so links keep matching the name.
                category.slug = await self._unique_slug(name, exclude_id=category.id)

        if "description" in payload.model_fields_set:
            category.description = payload.description
        if payload.is_active is not None:
            category.is_active = payload.is_active

        await self.session.commit()
        return category

    async def delete(self, category_id: uuid.UUID) -> None:
        category = await self.get_or_404(category_id)

        assigned = await self.categories.count_products(category.id)
        if assigned:
            raise ConflictError(
                f"{assigned} product(s) still use this category.",
                code="category_in_use",
            )

        category.is_active = False
        category.deleted_at = datetime.now(UTC)
        await self.session.commit()
