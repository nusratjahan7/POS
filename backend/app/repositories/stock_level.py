from __future__ import annotations

import uuid
from collections.abc import Sequence
from decimal import Decimal
from typing import Any, ClassVar

from sqlalchemy import Select, and_, func, or_, select
from sqlalchemy.orm import contains_eager, joinedload

from app.models.product import Product
from app.models.stock_level import StockLevel
from app.repositories.base import BaseRepository
from app.utils.pagination import PageParams
from app.utils.text import like_pattern


class StockLevelRepository(BaseRepository[StockLevel]):
    model = StockLevel

    SORTABLE: ClassVar[dict[str, Any]] = {
        "product_name": Product.name,
        "quantity": StockLevel.quantity,
        "created_at": StockLevel.created_at,
        "updated_at": StockLevel.updated_at,
    }

    def build_list_query(
        self,
        *,
        search: str | None = None,
        branch_id: uuid.UUID | None = None,
        category_id: uuid.UUID | None = None,
        status: str | None = None,
    ) -> Select[Any]:
        # ``contains_eager`` reuses the explicit join for the relationship, so the
        # product (and its category/brand) is available for the response without a
        # second join or a lazy load.
        stmt = (
            select(StockLevel)
            .join(StockLevel.product)
            .options(contains_eager(StockLevel.product), joinedload(StockLevel.branch))
            .where(Product.deleted_at.is_(None))
        )

        if search:
            pattern = like_pattern(search)
            stmt = stmt.where(
                or_(
                    Product.name.ilike(pattern, escape="\\"),
                    Product.sku.ilike(pattern, escape="\\"),
                    Product.barcode.ilike(pattern, escape="\\"),
                )
            )
        if branch_id is not None:
            stmt = stmt.where(StockLevel.branch_id == branch_id)
        if category_id is not None:
            stmt = stmt.where(Product.category_id == category_id)

        if status == "out_of_stock":
            stmt = stmt.where(StockLevel.quantity <= 0)
        elif status == "low_stock":
            stmt = stmt.where(StockLevel.quantity > 0, StockLevel.quantity <= Product.minimum_stock)
        elif status == "in_stock":
            stmt = stmt.where(StockLevel.quantity > Product.minimum_stock)
        return stmt

    async def list_levels(
        self,
        params: PageParams,
        *,
        sort: tuple[Any, bool] | None = None,
        **filters: Any,
    ) -> tuple[Sequence[StockLevel], int]:
        stmt = self.build_list_query(**filters)
        if sort is not None:
            column, descending = sort
            stmt = stmt.order_by(column.desc() if descending else column.asc())
        else:
            stmt = stmt.order_by(Product.name.asc())
        return await self.paginate(stmt, params)

    async def summary(self, *, branch_id: uuid.UUID | None = None) -> dict[str, int | Decimal]:
        stmt = (
            select(
                func.count().label("total"),
                func.count().filter(StockLevel.quantity <= 0).label("out_of_stock"),
                func.count()
                .filter(and_(StockLevel.quantity > 0, StockLevel.quantity <= Product.minimum_stock))
                .label("low_stock"),
                func.coalesce(func.sum(StockLevel.quantity), 0).label("total_quantity"),
            )
            .select_from(StockLevel)
            .join(Product, Product.id == StockLevel.product_id)
            .where(Product.deleted_at.is_(None))
        )
        if branch_id is not None:
            stmt = stmt.where(StockLevel.branch_id == branch_id)

        row = (await self.session.execute(stmt)).one()
        total = int(row.total)
        out_of_stock = int(row.out_of_stock)
        low_stock = int(row.low_stock)
        return {
            "total_levels": total,
            "out_of_stock": out_of_stock,
            "low_stock": low_stock,
            "in_stock": max(total - out_of_stock - low_stock, 0),
            "total_quantity": Decimal(row.total_quantity),
        }
