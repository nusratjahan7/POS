from __future__ import annotations

from collections.abc import Sequence
from typing import Any, ClassVar

from sqlalchemy import Select, or_, select

from app.models.customer import Customer
from app.repositories.base import BaseRepository
from app.utils.pagination import PageParams
from app.utils.text import like_pattern


class CustomerRepository(BaseRepository[Customer]):
    model = Customer

    SORTABLE: ClassVar[dict[str, Any]] = {
        "name": Customer.name,
        "balance": Customer.balance,
        "created_at": Customer.created_at,
        "updated_at": Customer.updated_at,
    }

    def build_list_query(
        self, *, search: str | None = None, is_active: bool | None = None
    ) -> Select[Any]:
        stmt = select(Customer).where(Customer.deleted_at.is_(None))
        if search:
            pattern = like_pattern(search)
            stmt = stmt.where(
                or_(
                    Customer.name.ilike(pattern, escape="\\"),
                    Customer.phone.ilike(pattern, escape="\\"),
                    Customer.email.ilike(pattern, escape="\\"),
                )
            )
        if is_active is not None:
            stmt = stmt.where(Customer.is_active.is_(is_active))
        return stmt

    async def list_customers(
        self,
        params: PageParams,
        *,
        sort: tuple[Any, bool] | None = None,
        **filters: Any,
    ) -> tuple[Sequence[Customer], int]:
        stmt = self.build_list_query(**filters)
        if sort is not None:
            column, descending = sort
            stmt = stmt.order_by(column.desc() if descending else column.asc())
        else:
            stmt = stmt.order_by(Customer.name.asc())
        return await self.paginate(stmt, params)

    async def list_all(self, *, active_only: bool = True) -> Sequence[Customer]:
        stmt = select(Customer).where(Customer.deleted_at.is_(None))
        if active_only:
            stmt = stmt.where(Customer.is_active.is_(True))
        return (await self.session.execute(stmt.order_by(Customer.name.asc()))).scalars().all()
