from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import Any, ClassVar

from sqlalchemy import Select, func, select

from app.models.purchase import Purchase
from app.models.supplier import Supplier
from app.repositories.base import BaseRepository
from app.utils.pagination import PageParams
from app.utils.text import like_pattern


class SupplierRepository(BaseRepository[Supplier]):
    model = Supplier

    SORTABLE: ClassVar[dict[str, Any]] = {
        "name": Supplier.name,
        "balance": Supplier.balance,
        "created_at": Supplier.created_at,
        "updated_at": Supplier.updated_at,
    }

    async def name_exists(self, name: str, *, exclude_id: uuid.UUID | None = None) -> bool:
        stmt = select(Supplier.id).where(
            func.lower(Supplier.name) == name.strip().lower(), Supplier.deleted_at.is_(None)
        )
        if exclude_id is not None:
            stmt = stmt.where(Supplier.id != exclude_id)
        return (await self.session.execute(stmt.limit(1))).scalar_one_or_none() is not None

    async def count_purchases(self, supplier_id: uuid.UUID) -> int:
        stmt = select(func.count(Purchase.id)).where(Purchase.supplier_id == supplier_id)
        return int((await self.session.execute(stmt)).scalar_one())

    def build_list_query(
        self, *, search: str | None = None, is_active: bool | None = None
    ) -> Select[Any]:
        stmt = select(Supplier).where(Supplier.deleted_at.is_(None))
        if search:
            pattern = like_pattern(search)
            stmt = stmt.where(
                Supplier.name.ilike(pattern, escape="\\")
                | Supplier.company.ilike(pattern, escape="\\")
                | Supplier.phone.ilike(pattern, escape="\\")
            )
        if is_active is not None:
            stmt = stmt.where(Supplier.is_active.is_(is_active))
        return stmt

    async def list_suppliers(
        self,
        params: PageParams,
        *,
        sort: tuple[Any, bool] | None = None,
        **filters: Any,
    ) -> tuple[Sequence[Supplier], int]:
        stmt = self.build_list_query(**filters)
        if sort is not None:
            column, descending = sort
            stmt = stmt.order_by(column.desc() if descending else column.asc())
        else:
            stmt = stmt.order_by(Supplier.name.asc())
        return await self.paginate(stmt, params)

    async def list_all(self, *, active_only: bool = True) -> Sequence[Supplier]:
        stmt = select(Supplier).where(Supplier.deleted_at.is_(None))
        if active_only:
            stmt = stmt.where(Supplier.is_active.is_(True))
        return (await self.session.execute(stmt.order_by(Supplier.name.asc()))).scalars().all()
