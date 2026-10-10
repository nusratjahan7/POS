"""Dashboard aggregates.

The dashboard is a read-only snapshot: today's trade, as-of-now standing counts,
and the window's trends, distributions and recent activity. The bulk of the
aggregation is delegated to :class:`ReportRepository`; this repository adds only
the queries the dashboard needs that reporting does not already answer.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import date
from typing import Any

from sqlalchemy import Row, func, select

from app.models.customer import Customer
from app.models.expense import Expense
from app.models.payment_method import PaymentMethod
from app.models.product import Product
from app.models.sale import Sale
from app.models.sale_item import SaleItem
from app.models.sale_payment import SalePayment
from app.repositories.base import BaseRepository
from app.repositories.report import _day_bounds


class DashboardRepository(BaseRepository[Sale]):
    model = Sale

    @staticmethod
    def _sales_conditions(start: date, end: date, branch_id: uuid.UUID | None) -> list[Any]:
        lower, upper = _day_bounds(start, end)
        conditions: list[Any] = [
            Sale.status == "completed",
            Sale.sold_at >= lower,
            Sale.sold_at < upper,
        ]
        if branch_id is not None:
            conditions.append(Sale.branch_id == branch_id)
        return conditions

    # --- Standing counts ---------------------------------------------------
    async def customer_count(self) -> int:
        stmt = select(func.count(Customer.id)).where(Customer.deleted_at.is_(None))
        return int((await self.session.execute(stmt)).scalar_one())

    async def product_count(self) -> int:
        stmt = select(func.count(Product.id)).where(Product.deleted_at.is_(None))
        return int((await self.session.execute(stmt)).scalar_one())

    # --- Trend components --------------------------------------------------
    async def daily_cost(
        self, start: date, end: date, branch_id: uuid.UUID | None
    ) -> Sequence[Row[Any]]:
        """Cost of goods sold per calendar day: captured cost x quantity."""
        day = func.date(Sale.sold_at).label("day")
        stmt = (
            select(day, func.coalesce(func.sum(SaleItem.cost_price * SaleItem.quantity), 0))
            .select_from(SaleItem)
            .join(Sale, Sale.id == SaleItem.sale_id)
            .where(*self._sales_conditions(start, end, branch_id))
            .group_by(day)
            .order_by(day)
        )
        return (await self.session.execute(stmt)).all()

    async def daily_expenses(
        self, start: date, end: date, branch_id: uuid.UUID | None
    ) -> Sequence[Row[Any]]:
        day = Expense.spent_at.label("day")
        stmt = (
            select(day, func.coalesce(func.sum(Expense.amount), 0))
            .where(Expense.spent_at >= start, Expense.spent_at <= end)
            .group_by(day)
            .order_by(day)
        )
        if branch_id is not None:
            stmt = stmt.where(Expense.branch_id == branch_id)
        return (await self.session.execute(stmt)).all()

    # --- Recent activity ---------------------------------------------------
    async def recent_sales(self, branch_id: uuid.UUID | None, limit: int) -> Sequence[Row[Any]]:
        stmt = (
            select(
                Sale.id,
                Sale.sale_number,
                Customer.name,
                Sale.total,
                Sale.status,
                Sale.sold_at,
            )
            .select_from(Sale)
            .outerjoin(Customer, Customer.id == Sale.customer_id)
            .order_by(Sale.sold_at.desc())
            .limit(limit)
        )
        if branch_id is not None:
            stmt = stmt.where(Sale.branch_id == branch_id)
        return (await self.session.execute(stmt)).all()

    async def recent_payments(self, branch_id: uuid.UUID | None, limit: int) -> Sequence[Row[Any]]:
        stmt = (
            select(
                SalePayment.id,
                Sale.sale_number,
                PaymentMethod.name,
                SalePayment.amount,
                SalePayment.paid_at,
            )
            .select_from(SalePayment)
            .join(Sale, Sale.id == SalePayment.sale_id)
            .outerjoin(PaymentMethod, PaymentMethod.id == SalePayment.payment_method_id)
            .order_by(SalePayment.paid_at.desc())
            .limit(limit)
        )
        if branch_id is not None:
            stmt = stmt.where(Sale.branch_id == branch_id)
        return (await self.session.execute(stmt)).all()


__all__ = ["DashboardRepository"]
