from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import Any, ClassVar

from sqlalchemy import Select, or_, select

from app.models.product import Product
from app.repositories.base import BaseRepository
from app.utils.pagination import PageParams
from app.utils.text import like_pattern


class ProductRepository(BaseRepository[Product]):
    model = Product

    SORTABLE: ClassVar[dict[str, Any]] = {
        "name": Product.name,
        "sku": Product.sku,
        "purchase_price": Product.purchase_price,
        "selling_price": Product.selling_price,
        "stock_quantity": Product.stock_quantity,
        "created_at": Product.created_at,
        "updated_at": Product.updated_at,
    }

    async def slug_exists(self, slug: str, *, exclude_id: uuid.UUID | None = None) -> bool:
        return await self._exists(Product.slug == slug, exclude_id=exclude_id)

    async def sku_exists(self, sku: str, *, exclude_id: uuid.UUID | None = None) -> bool:
        return await self._exists(Product.sku == sku, exclude_id=exclude_id)

    async def barcode_exists(self, barcode: str, *, exclude_id: uuid.UUID | None = None) -> bool:
        return await self._exists(Product.barcode == barcode, exclude_id=exclude_id)

    async def _exists(self, *conditions: Any, exclude_id: uuid.UUID | None = None) -> bool:
        """Only live rows count — a soft-deleted product frees its identifiers."""
        stmt = select(Product.id).where(*conditions, Product.deleted_at.is_(None))
        if exclude_id is not None:
            stmt = stmt.where(Product.id != exclude_id)
        return (await self.session.execute(stmt.limit(1))).scalar_one_or_none() is not None

    def build_list_query(
        self,
        *,
        search: str | None = None,
        sku: str | None = None,
        barcode: str | None = None,
        category_id: uuid.UUID | None = None,
        brand_id: uuid.UUID | None = None,
        is_active: bool | None = None,
        include_deleted: bool = False,
    ) -> Select[Any]:
        stmt = select(Product)
        if not include_deleted:
            stmt = stmt.where(Product.deleted_at.is_(None))

        if search:
            # Free-text covers the three things staff actually type or scan.
            pattern = like_pattern(search)
            stmt = stmt.where(
                or_(
                    Product.name.ilike(pattern, escape="\\"),
                    Product.sku.ilike(pattern, escape="\\"),
                    Product.barcode.ilike(pattern, escape="\\"),
                )
            )
        if sku:
            stmt = stmt.where(Product.sku == sku)
        if barcode:
            stmt = stmt.where(Product.barcode == barcode)
        if category_id is not None:
            stmt = stmt.where(Product.category_id == category_id)
        if brand_id is not None:
            stmt = stmt.where(Product.brand_id == brand_id)
        if is_active is not None:
            stmt = stmt.where(Product.is_active.is_(is_active))
        return stmt

    async def list_products(
        self,
        params: PageParams,
        *,
        sort: tuple[Any, bool] | None = None,
        **filters: Any,
    ) -> tuple[Sequence[Product], int]:
        stmt = self.build_list_query(**filters)
        if sort is not None:
            column, descending = sort
            stmt = stmt.order_by(column.desc() if descending else column.asc())
        else:
            stmt = stmt.order_by(Product.name.asc())
        return await self.paginate(stmt, params)

    async def list_all(self, *, active_only: bool = True) -> Sequence[Product]:
        stmt = select(Product).where(Product.deleted_at.is_(None))
        if active_only:
            stmt = stmt.where(Product.is_active.is_(True))
        return (
            (await self.session.execute(stmt.order_by(Product.name.asc()))).scalars().unique().all()
        )

    async def list_by_ids(self, product_ids: Sequence[uuid.UUID]) -> Sequence[Product]:
        ids = list(product_ids)
        if not ids:
            return []
        stmt = select(Product).where(Product.id.in_(ids), Product.deleted_at.is_(None))
        return (await self.session.execute(stmt)).scalars().unique().all()
