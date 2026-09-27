"""Category management, including the parent/child hierarchy."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError, UnprocessableError
from app.models.category import Category
from app.repositories.category import CategoryRepository
from app.schemas.category import CategoryCreate, CategoryNode, CategoryUpdate
from app.utils.pagination import PageParams
from app.utils.text import slugify

# Chosen so a natural-looking name always fits `Category.slug` (140 chars).
SLUG_MAX_LENGTH = 120

# A safety valve for the ancestor walk; a real catalogue is never this deep, but
# a corrupted parent chain must not be able to hang the request.
MAX_HIERARCHY_DEPTH = 50


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
        parent_id: uuid.UUID | None = None,
        top_level: bool | None = None,
        sort: tuple[Any, bool] | None = None,
    ) -> tuple[Sequence[Category], int]:
        return await self.categories.list_categories(
            params,
            sort=sort,
            search=search,
            is_active=is_active,
            parent_id=parent_id,
            top_level=top_level,
        )

    async def list_all(self) -> Sequence[Category]:
        return await self.categories.list_all()

    async def tree(self) -> list[CategoryNode]:
        """Every category, nested by parent. Orphans (a missing/deleted parent)
        surface as roots so nothing is ever hidden from the management screen."""
        categories = await self.categories.list_all(active_only=False)

        nodes: dict[uuid.UUID, CategoryNode] = {
            category.id: CategoryNode(
                id=category.id,
                name=category.name,
                slug=category.slug,
                image_url=category.image_url,
                parent_id=category.parent_id,
                is_active=category.is_active,
            )
            for category in categories
        }

        roots: list[CategoryNode] = []
        for category in categories:
            node = nodes[category.id]
            parent = nodes.get(category.parent_id) if category.parent_id else None
            if parent is None:
                roots.append(node)
            else:
                parent.children.append(node)
        return roots

    # --- Internals ---------------------------------------------------------
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

    async def _resolve_parent(
        self,
        parent_id: uuid.UUID | None,
        *,
        child_id: uuid.UUID | None = None,
    ) -> Category | None:
        """Validate a proposed parent and guard against cycles.

        Returns the parent instance (or ``None`` for top level). Assigned to the
        relationship — not just the FK — so the response serialises without a
        lazy load after a write.
        """
        if parent_id is None:
            return None

        if child_id is not None and parent_id == child_id:
            raise UnprocessableError(
                "A category cannot be its own parent.",
                code="category_cycle",
                details=[{"field": "parent_id", "message": "Cannot be its own parent."}],
            )

        parent = await self.categories.get(parent_id)
        if parent is None or parent.is_deleted:
            raise UnprocessableError(
                "The selected parent category does not exist.",
                code="unknown_parent_category",
                details=[{"field": "parent_id", "message": "Unknown category."}],
            )

        # Walk up from the proposed parent; if we reach the category itself, the
        # move would create a loop.
        if child_id is not None:
            ancestor = parent
            for _ in range(MAX_HIERARCHY_DEPTH):
                if ancestor.parent_id is None:
                    break
                if ancestor.parent_id == child_id:
                    raise UnprocessableError(
                        "A category cannot be moved under one of its own descendants.",
                        code="category_cycle",
                        details=[
                            {"field": "parent_id", "message": "Creates a circular hierarchy."}
                        ],
                    )
                next_ancestor = await self.categories.get(ancestor.parent_id)
                if next_ancestor is None:
                    break
                ancestor = next_ancestor
        return parent

    # --- Commands ----------------------------------------------------------
    async def create(self, payload: CategoryCreate) -> Category:
        name = payload.name.strip()
        await self._assert_name_free(name)
        parent = await self._resolve_parent(payload.parent_id)

        category = Category(
            name=name,
            slug=await self._unique_slug(name),
            description=payload.description,
            image_url=payload.image_url,
            parent=parent,
            is_active=payload.is_active,
        )
        await self.categories.add(category)
        await self.session.commit()
        return category

    async def update(self, category_id: uuid.UUID, payload: CategoryUpdate) -> Category:
        category = await self.get_or_404(category_id)
        provided = payload.model_fields_set

        if payload.name is not None:
            name = payload.name.strip()
            if name.lower() != category.name.lower():
                await self._assert_name_free(name, exclude_id=category.id)
                category.name = name
                # Renaming moves the slug so links keep matching the name.
                category.slug = await self._unique_slug(name, exclude_id=category.id)

        if "description" in provided:
            category.description = payload.description
        if "image_url" in provided:
            category.image_url = payload.image_url
        if "parent_id" in provided:
            category.parent = await self._resolve_parent(payload.parent_id, child_id=category.id)
        if payload.is_active is not None:
            category.is_active = payload.is_active

        await self.session.commit()
        return category

    async def delete(self, category_id: uuid.UUID) -> None:
        category = await self.get_or_404(category_id)

        children = await self.categories.count_children(category.id)
        if children:
            noun = "sub-category" if children == 1 else "sub-categories"
            raise ConflictError(
                f"This category still has {children} {noun}.",
                code="category_has_children",
            )

        assigned = await self.categories.count_products(category.id)
        if assigned:
            raise ConflictError(
                f"{assigned} product(s) still use this category.",
                code="category_in_use",
            )

        category.is_active = False
        category.deleted_at = datetime.now(UTC)
        await self.session.commit()
