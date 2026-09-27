"""Brand management."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.models.brand import Brand
from app.repositories.brand import BrandRepository
from app.schemas.brand import BrandCreate, BrandUpdate
from app.utils.pagination import PageParams
from app.utils.text import slugify

SLUG_MAX_LENGTH = 120


class BrandService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.brands = BrandRepository(session)

    async def get_or_404(self, brand_id: uuid.UUID) -> Brand:
        brand = await self.brands.get(brand_id)
        if brand is None or brand.is_deleted:
            raise NotFoundError("Brand not found.", code="brand_not_found")
        return brand

    async def list_brands(
        self,
        params: PageParams,
        *,
        search: str | None = None,
        is_active: bool | None = None,
        sort: tuple[Any, bool] | None = None,
    ) -> tuple[Sequence[Brand], int]:
        return await self.brands.list_brands(params, sort=sort, search=search, is_active=is_active)

    async def list_all(self) -> Sequence[Brand]:
        return await self.brands.list_all()

    async def _unique_slug(self, name: str, *, exclude_id: uuid.UUID | None = None) -> str:
        base = slugify(name, max_length=SLUG_MAX_LENGTH)
        candidate, suffix = base, 2
        while await self.brands.slug_exists(candidate, exclude_id=exclude_id):
            candidate = f"{base}-{suffix}"
            suffix += 1
        return candidate

    async def _assert_name_free(self, name: str, *, exclude_id: uuid.UUID | None = None) -> None:
        if await self.brands.name_exists(name, exclude_id=exclude_id):
            raise ConflictError(
                "A brand with that name already exists.",
                code="brand_name_taken",
                details=[{"field": "name", "message": "Already in use."}],
            )

    async def create(self, payload: BrandCreate) -> Brand:
        name = payload.name.strip()
        await self._assert_name_free(name)

        brand = Brand(
            name=name,
            slug=await self._unique_slug(name),
            description=payload.description,
            logo_url=payload.logo_url,
            is_active=payload.is_active,
        )
        await self.brands.add(brand)
        await self.session.commit()
        return brand

    async def update(self, brand_id: uuid.UUID, payload: BrandUpdate) -> Brand:
        brand = await self.get_or_404(brand_id)

        if payload.name is not None:
            name = payload.name.strip()
            if name.lower() != brand.name.lower():
                await self._assert_name_free(name, exclude_id=brand.id)
                brand.name = name
                brand.slug = await self._unique_slug(name, exclude_id=brand.id)

        if "description" in payload.model_fields_set:
            brand.description = payload.description
        if "logo_url" in payload.model_fields_set:
            brand.logo_url = payload.logo_url
        if payload.is_active is not None:
            brand.is_active = payload.is_active

        await self.session.commit()
        return brand

    async def delete(self, brand_id: uuid.UUID) -> None:
        brand = await self.get_or_404(brand_id)

        assigned = await self.brands.count_products(brand.id)
        if assigned:
            raise ConflictError(
                f"{assigned} product(s) still use this brand.",
                code="brand_in_use",
            )

        brand.is_active = False
        brand.deleted_at = datetime.now(UTC)
        await self.session.commit()
