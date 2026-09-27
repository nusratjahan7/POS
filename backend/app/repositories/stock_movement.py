from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import Any, ClassVar

from sqlalchemy import Select, or_, select
from sqlalchemy.orm import contains_eager

from app.models.product import Product
from app.models.stock_movement import StockMovement
from app.repositories.base import BaseRepository
from app.utils.pagination import PageParams
from app.utils.text import like_pattern


class StockMovementRepository(BaseRepository[StockMovement]):
    model = StockMovement

    SORTABLE: ClassVar[dict[str, Any]] = {
        "created_at": StockMovement.created_at,
        "quantity": StockMovement.quantity,
    }

    def build_list_query(
        self,
        *,
        search: str | None = None,
        product_id: uuid.UUID | None = None,
        branch_id: uuid.UUID | None = None,
        movement_type: str | None = None,
        reference_type: str | None = None,
    ) -> Select[Any]:
        stmt = (
            select(StockMovement)
            .join(StockMovement.product)
            .options(contains_eager(StockMovement.product))
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
        if product_id is not None:
            stmt = stmt.where(StockMovement.product_id == product_id)
        if branch_id is not None:
            stmt = stmt.where(StockMovement.branch_id == branch_id)
        if movement_type is not None:
            stmt = stmt.where(StockMovement.movement_type == movement_type)
        if reference_type is not None:
            stmt = stmt.where(StockMovement.reference_type == reference_type)
        return stmt

    async def list_movements(
        self,
        params: PageParams,
        *,
        sort: tuple[Any, bool] | None = None,
        **filters: Any,
    ) -> tuple[Sequence[StockMovement], int]:
        stmt = self.build_list_query(**filters)
        if sort is not None:
            column, descending = sort
            stmt = stmt.order_by(column.desc() if descending else column.asc())
        else:
            stmt = stmt.order_by(StockMovement.created_at.desc())
        return await self.paginate(stmt, params)
