from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import Any, ClassVar

from sqlalchemy import Select, func, select

from app.models.payment_method import PaymentMethod
from app.repositories.base import BaseRepository
from app.utils.pagination import PageParams
from app.utils.text import like_pattern


class PaymentMethodRepository(BaseRepository[PaymentMethod]):
    model = PaymentMethod

    SORTABLE: ClassVar[dict[str, Any]] = {
        "sort_order": PaymentMethod.sort_order,
        "name": PaymentMethod.name,
        "created_at": PaymentMethod.created_at,
        "updated_at": PaymentMethod.updated_at,
    }

    async def get_by_code(self, code: str) -> PaymentMethod | None:
        stmt = select(PaymentMethod).where(
            PaymentMethod.code == code, PaymentMethod.deleted_at.is_(None)
        )
        return (await self.session.execute(stmt)).scalars().one_or_none()

    async def code_exists(self, code: str, *, exclude_id: uuid.UUID | None = None) -> bool:
        stmt = select(PaymentMethod.id).where(PaymentMethod.code == code)
        if exclude_id is not None:
            stmt = stmt.where(PaymentMethod.id != exclude_id)
        return (await self.session.execute(stmt.limit(1))).scalar_one_or_none() is not None

    async def name_exists(self, name: str, *, exclude_id: uuid.UUID | None = None) -> bool:
        stmt = select(PaymentMethod.id).where(
            func.lower(PaymentMethod.name) == name.strip().lower()
        )
        if exclude_id is not None:
            stmt = stmt.where(PaymentMethod.id != exclude_id)
        return (await self.session.execute(stmt.limit(1))).scalar_one_or_none() is not None

    def build_list_query(
        self,
        *,
        search: str | None = None,
        is_active: bool | None = None,
        kind: str | None = None,
    ) -> Select[Any]:
        stmt = select(PaymentMethod).where(PaymentMethod.deleted_at.is_(None))
        if search:
            pattern = like_pattern(search)
            stmt = stmt.where(
                PaymentMethod.name.ilike(pattern, escape="\\")
                | PaymentMethod.code.ilike(pattern, escape="\\")
            )
        if is_active is not None:
            stmt = stmt.where(PaymentMethod.is_active.is_(is_active))
        if kind is not None:
            stmt = stmt.where(PaymentMethod.kind == kind)
        return stmt

    async def list_payment_methods(
        self,
        params: PageParams,
        *,
        sort: tuple[Any, bool] | None = None,
        **filters: Any,
    ) -> tuple[Sequence[PaymentMethod], int]:
        stmt = self.build_list_query(**filters)
        if sort is not None:
            column, descending = sort
            stmt = stmt.order_by(column.desc() if descending else column.asc())
        else:
            stmt = stmt.order_by(PaymentMethod.sort_order.asc(), PaymentMethod.name.asc())
        return await self.paginate(stmt, params)

    async def list_all(self, *, active_only: bool = True) -> Sequence[PaymentMethod]:
        stmt = select(PaymentMethod).where(PaymentMethod.deleted_at.is_(None))
        if active_only:
            stmt = stmt.where(PaymentMethod.is_active.is_(True))
        stmt = stmt.order_by(PaymentMethod.sort_order.asc(), PaymentMethod.name.asc())
        return (await self.session.execute(stmt)).scalars().all()
