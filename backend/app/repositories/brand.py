from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import Any, ClassVar

from sqlalchemy import Select, func, select

from app.models.brand import Brand
from app.models.product import Product
from app.repositories.base import BaseRepository
from app.utils.pagination import PageParams
from app.utils.text import like_pattern


class BrandRepository(BaseRepository[Brand]):
    model = Brand

    SORTABLE: ClassVar[dict[str, Any]] = {
        "name": Brand.name,
        "created_at": Brand.created_at,
        "updated_at": Brand.updated_at,
    }

    async def slug_exists(self, slug: str, *, exclude_id: uuid.UUID | None = None) -> bool:
        return await self._exists(Brand.slug == slug, exclude_id=exclude_id)

    async def name_exists(self, name: str, *, exclude_id: uuid.UUID | None = None) -> bool:
        return await self._exists(
            func.lower(Brand.name) == name.strip().lower(), exclude_id=exclude_id
        )

    async def _exists(self, *conditions: Any, exclude_id: uuid.UUID | None = None) -> bool:
        stmt = select(Brand.id).where(*conditions, Brand.deleted_at.is_(None))
        if exclude_id is not None:
            stmt = stmt.where(Brand.id != exclude_id)
        return (await self.session.execute(stmt.limit(1))).scalar_one_or_none() is not None

    async def count_products(self, brand_id: uuid.UUID) -> int:
        stmt = select(func.count(Product.id)).where(
            Product.brand_id == brand_id, Product.deleted_at.is_(None)
        )
        return int((await self.session.execute(stmt)).scalar_one())

    def build_list_query(self, *, search: str | None = None, is_active: bool | None = None):
        stmt = select(Brand).where(Brand.deleted_at.is_(None))
        if search:
            pattern = like_pattern(search)
            stmt = stmt.where(Brand.name.ilike(pattern, escape="\\"))
        if is_active is not None:
            stmt = stmt.where(Brand.is_active.is_(is_active))
        return stmt

    async def list_brands(
        self,
        params: PageParams,
        *,
        sort: tuple[Any, bool] | None = None,
        search: str | None = None,
        is_active: bool | None = None,
    ) -> tuple[Sequence[Brand], int]:
        stmt: Select[Any] = self.build_list_query(search=search, is_active=is_active)
        if sort is not None:
            column, descending = sort
            stmt = stmt.order_by(column.desc() if descending else column.asc())
        else:
            stmt = stmt.order_by(Brand.name.asc())
        return await self.paginate(stmt, params)

    async def list_all(self, *, active_only: bool = True) -> Sequence[Brand]:
        stmt = select(Brand).where(Brand.deleted_at.is_(None))
        if active_only:
            stmt = stmt.where(Brand.is_active.is_(True))
        return (await self.session.execute(stmt.order_by(Brand.name.asc()))).scalars().all()
