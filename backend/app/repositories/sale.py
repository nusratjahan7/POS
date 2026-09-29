from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import date
from decimal import Decimal
from typing import Any, ClassVar

from sqlalchemy import Select, func, select

from app.models.sale import Sale
from app.models.user import User
from app.repositories.base import BaseRepository
from app.utils.pagination import PageParams
from app.utils.text import like_pattern


class SaleRepository(BaseRepository[Sale]):
    model = Sale

    SORTABLE: ClassVar[dict[str, Any]] = {
        "sale_number": Sale.sale_number,
        "sold_at": Sale.sold_at,
        "total": Sale.total,
        "paid": Sale.paid,
        "due": Sale.due,
        "status": Sale.status,
        "created_at": Sale.created_at,
    }

    async def number_exists(self, number: str) -> bool:
        stmt = select(Sale.id).where(Sale.sale_number == number).limit(1)
        return (await self.session.execute(stmt)).scalar_one_or_none() is not None

    async def cashiers(self) -> Sequence[tuple[uuid.UUID, str]]:
        """Distinct staff who have rung up sales, ordered by name."""
        stmt = (
            select(User.id, User.full_name)
            .join(Sale, Sale.cashier_id == User.id)
            .distinct()
            .order_by(User.full_name)
        )
        return [(row[0], row[1]) for row in (await self.session.execute(stmt)).all()]

    def build_list_query(
        self,
        *,
        search: str | None = None,
        branch_id: uuid.UUID | None = None,
        customer_id: uuid.UUID | None = None,
        cashier_id: uuid.UUID | None = None,
        status: str | None = None,
        payment_status: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> Select[Any]:
        stmt = select(Sale)
        if search:
            pattern = like_pattern(search)
            stmt = stmt.where(Sale.sale_number.ilike(pattern, escape="\\"))
        if branch_id is not None:
            stmt = stmt.where(Sale.branch_id == branch_id)
        if customer_id is not None:
            stmt = stmt.where(Sale.customer_id == customer_id)
        if cashier_id is not None:
            stmt = stmt.where(Sale.cashier_id == cashier_id)
        if status is not None:
            stmt = stmt.where(Sale.status == status)
        # Settlement is derived from the arithmetic the DB already enforces
        # (``due = total - paid``), so no extra column or join is needed.
        if payment_status == "paid":
            stmt = stmt.where(Sale.due == 0)
        elif payment_status == "unpaid":
            stmt = stmt.where(Sale.paid == 0, Sale.due > 0)
        elif payment_status == "partial":
            stmt = stmt.where(Sale.paid > 0, Sale.due > 0)
        if date_from is not None:
            stmt = stmt.where(func.date(Sale.sold_at) >= date_from)
        if date_to is not None:
            stmt = stmt.where(func.date(Sale.sold_at) <= date_to)
        return stmt

    async def list_sales(
        self,
        params: PageParams,
        *,
        sort: tuple[Any, bool] | None = None,
        **filters: Any,
    ) -> tuple[Sequence[Sale], int]:
        stmt = self.build_list_query(**filters)
        if sort is not None:
            column, descending = sort
            stmt = stmt.order_by(column.desc() if descending else column.asc())
        else:
            stmt = stmt.order_by(Sale.sold_at.desc())
        return await self.paginate(stmt, params)

    async def totals_for_customer(self, customer_id: uuid.UUID) -> tuple[int, Decimal]:
        """How many completed sales a customer has, and what they came to."""
        stmt = select(func.count(Sale.id), func.coalesce(func.sum(Sale.total), 0)).where(
            Sale.customer_id == customer_id, Sale.status == "completed"
        )
        count, total = (await self.session.execute(stmt)).one()
        return int(count), Decimal(total)

    async def recent_for_customer(
        self, customer_id: uuid.UUID, *, limit: int = 5
    ) -> Sequence[Sale]:
        stmt = (
            select(Sale)
            .where(Sale.customer_id == customer_id, Sale.status == "completed")
            .order_by(Sale.sold_at.desc())
            .limit(limit)
        )
        return (await self.session.execute(stmt)).scalars().all()
