from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import date
from typing import Any, ClassVar

from sqlalchemy import Select, select

from app.models.purchase import Purchase
from app.repositories.base import BaseRepository
from app.utils.pagination import PageParams
from app.utils.text import like_pattern


class PurchaseRepository(BaseRepository[Purchase]):
    model = Purchase

    SORTABLE: ClassVar[dict[str, Any]] = {
        "purchase_number": Purchase.purchase_number,
        "purchase_date": Purchase.purchase_date,
        "total": Purchase.total,
        "created_at": Purchase.created_at,
    }

    async def number_exists(self, number: str) -> bool:
        stmt = select(Purchase.id).where(Purchase.purchase_number == number).limit(1)
        return (await self.session.execute(stmt)).scalar_one_or_none() is not None

    def build_list_query(
        self,
        *,
        search: str | None = None,
        supplier_id: uuid.UUID | None = None,
        branch_id: uuid.UUID | None = None,
        status: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> Select[Any]:
        stmt = select(Purchase)
        if search:
            pattern = like_pattern(search)
            stmt = stmt.where(Purchase.purchase_number.ilike(pattern, escape="\\"))
        if supplier_id is not None:
            stmt = stmt.where(Purchase.supplier_id == supplier_id)
        if branch_id is not None:
            stmt = stmt.where(Purchase.branch_id == branch_id)
        if status is not None:
            stmt = stmt.where(Purchase.status == status)
        if date_from is not None:
            stmt = stmt.where(Purchase.purchase_date >= date_from)
        if date_to is not None:
            stmt = stmt.where(Purchase.purchase_date <= date_to)
        return stmt

    async def list_purchases(
        self,
        params: PageParams,
        *,
        sort: tuple[Any, bool] | None = None,
        **filters: Any,
    ) -> tuple[Sequence[Purchase], int]:
        stmt = self.build_list_query(**filters)
        if sort is not None:
            column, descending = sort
            stmt = stmt.order_by(column.desc() if descending else column.asc())
        else:
            stmt = stmt.order_by(Purchase.created_at.desc())
        return await self.paginate(stmt, params)
