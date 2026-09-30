from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import date
from decimal import Decimal
from typing import Any, ClassVar

from sqlalchemy import Select, func, select

from app.models.expense import Expense
from app.repositories.base import BaseRepository
from app.utils.pagination import PageParams
from app.utils.text import like_pattern


class ExpenseRepository(BaseRepository[Expense]):
    model = Expense

    SORTABLE: ClassVar[dict[str, Any]] = {
        "spent_at": Expense.spent_at,
        "amount": Expense.amount,
        "created_at": Expense.created_at,
    }

    def _apply_filters(
        self,
        stmt: Select[Any],
        *,
        search: str | None = None,
        branch_id: uuid.UUID | None = None,
        category_id: uuid.UUID | None = None,
        payment_method_id: uuid.UUID | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> Select[Any]:
        if search:
            pattern = like_pattern(search)
            stmt = stmt.where(
                Expense.description.ilike(pattern, escape="\\")
                | Expense.reference.ilike(pattern, escape="\\")
            )
        if branch_id is not None:
            stmt = stmt.where(Expense.branch_id == branch_id)
        if category_id is not None:
            stmt = stmt.where(Expense.category_id == category_id)
        if payment_method_id is not None:
            stmt = stmt.where(Expense.payment_method_id == payment_method_id)
        if date_from is not None:
            stmt = stmt.where(Expense.spent_at >= date_from)
        if date_to is not None:
            stmt = stmt.where(Expense.spent_at <= date_to)
        return stmt

    async def list_expenses(
        self,
        params: PageParams,
        *,
        sort: tuple[Any, bool] | None = None,
        **filters: Any,
    ) -> tuple[Sequence[Expense], int]:
        stmt = self._apply_filters(select(Expense), **filters)
        if sort is not None:
            column, descending = sort
            stmt = stmt.order_by(column.desc() if descending else column.asc())
        else:
            stmt = stmt.order_by(Expense.spent_at.desc(), Expense.created_at.desc())
        return await self.paginate(stmt, params)

    async def sum_amount(self, **filters: Any) -> Decimal:
        """Total spend for the current filters — the page's summary figure."""
        stmt = self._apply_filters(
            select(func.coalesce(func.sum(Expense.amount), 0)), **filters
        )
        return Decimal((await self.session.execute(stmt)).scalar_one())
