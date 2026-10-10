"""The dashboard service: one snapshot of the business, assembled server-side.

It resolves the period window, fans out the aggregates (reusing the reporting
repository for the sales-shaped numbers) and composes them into the dashboard
shape. As in reporting, the service owns every figure the client shows — the
client only formats and displays.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import UTC, date, datetime, timedelta, tzinfo
from decimal import Decimal
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import Row
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.business import BusinessRepository
from app.repositories.dashboard import DashboardRepository
from app.repositories.expense import ExpenseRepository
from app.repositories.report import ReportRepository
from app.repositories.stock_level import StockLevelRepository
from app.schemas.dashboard import (
    DashboardSnapshot,
    DashboardStanding,
    DashboardToday,
    RecentPaymentRow,
    RecentSaleRow,
    TrendPoint,
)
from app.schemas.report import (
    CategorySalesRow,
    PaymentMethodSalesRow,
    ProductSalesRow,
    ReportRange,
    StockStatusRow,
)
from app.utils.daterange import ReportWindow, WindowRequest, resolve_window
from app.utils.money import ZERO, money

RECENT_LIMIT = 5
TOP_PRODUCT_LIMIT = 5
CATEGORY_LIMIT = 8


class DashboardService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.dashboard = DashboardRepository(session)
        self.reports = ReportRepository(session)
        self.stock_levels = StockLevelRepository(session)
        self.expenses = ExpenseRepository(session)
        self.business = BusinessRepository(session)

    # --- Window ------------------------------------------------------------
    async def _today(self) -> date:
        """Today in the business's time zone, not the server's."""
        business = await self.business.get_default()
        tz: tzinfo = UTC
        if business is not None:
            try:
                tz = ZoneInfo(business.timezone)
            except (ZoneInfoNotFoundError, ValueError):
                tz = UTC
        return datetime.now(tz).date()

    async def resolve(self, request: WindowRequest) -> ReportWindow:
        return resolve_window(request, today=await self._today())

    @staticmethod
    def _range(window: ReportWindow) -> ReportRange:
        return ReportRange(start=window.start, end=window.end, preset=window.preset)

    # --- Snapshot ----------------------------------------------------------
    async def snapshot(
        self, request: WindowRequest, *, branch_id: uuid.UUID | None = None
    ) -> DashboardSnapshot:
        window = await self.resolve(request)
        today = await self._today()

        today_totals = await self.reports.sales_totals(today, today, branch_id)
        today_cost = await self.reports.sales_cost(today, today, branch_id)
        today_expenses = await self.expenses.sum_amount(
            date_from=today, date_to=today, branch_id=branch_id
        )

        sales = money(Decimal(today_totals["net_sales"]))
        gross_profit = money(sales - money(Decimal(today_cost)))
        net_profit = money(gross_profit - money(Decimal(today_expenses)))

        customers = await self.dashboard.customer_count()
        products = await self.dashboard.product_count()
        stock = await self.stock_levels.summary(branch_id=branch_id)
        customer_due = await self.reports.customer_dues()
        supplier_due = await self.reports.supplier_dues()

        daily = await self.reports.sales_daily(window.start, window.end, branch_id)
        costs = await self.dashboard.daily_cost(window.start, window.end, branch_id)
        expenses = await self.dashboard.daily_expenses(window.start, window.end, branch_id)

        categories = await self.reports.sales_by_category(window.start, window.end, branch_id)
        methods = await self.reports.sales_by_payment_method(window.start, window.end, branch_id)

        by_product = await self.reports.sales_by_product(window.start, window.end, branch_id)
        recent_sales = await self.dashboard.recent_sales(branch_id, RECENT_LIMIT)
        low = await self.reports.stock_rows(
            status="low_stock", branch_id=branch_id, limit=RECENT_LIMIT
        )
        recent_payments = await self.dashboard.recent_payments(branch_id, RECENT_LIMIT)

        return DashboardSnapshot(
            as_of=datetime.now(UTC),
            range=self._range(window),
            today=DashboardToday(
                sales=sales,
                orders=int(today_totals["order_count"]),
                gross_profit=gross_profit,
                net_profit=net_profit,
            ),
            standing=DashboardStanding(
                customers=customers,
                products=products,
                low_stock=int(stock["low_stock"]),
                outstanding_due=money(customer_due),
                supplier_due=money(supplier_due),
            ),
            trends=self._trends(daily, costs, expenses, window),
            category_performance=[
                CategorySalesRow(
                    category_id=row[0],
                    name=row[1] or "Uncategorised",
                    quantity=Decimal(row[2]),
                    net=money(Decimal(row[3])),
                )
                for row in categories[:CATEGORY_LIMIT]
            ],
            payment_methods=[
                PaymentMethodSalesRow(
                    payment_method_id=row[0],
                    name=row[1] or "Unknown",
                    kind=row[2] or "",
                    count=int(row[3]),
                    amount=money(Decimal(row[4])),
                )
                for row in methods
            ],
            top_products=[
                ProductSalesRow(
                    product_id=row[0],
                    name=row[1] or "—",
                    sku=row[2] or "",
                    quantity=Decimal(row[3]),
                    net=money(Decimal(row[4])),
                    cost=money(Decimal(row[5])),
                    profit=money(Decimal(row[4]) - Decimal(row[5])),
                )
                for row in by_product[:TOP_PRODUCT_LIMIT]
            ],
            recent_sales=[
                RecentSaleRow(
                    id=row[0],
                    sale_number=row[1],
                    customer_name=row[2],
                    total=money(Decimal(row[3])),
                    status=row[4],
                    sold_at=row[5],
                )
                for row in recent_sales
            ],
            low_stock=[self._stock_row(row) for row in low],
            recent_payments=[
                RecentPaymentRow(
                    id=row[0],
                    sale_number=row[1],
                    method_name=row[2] or "Unknown",
                    amount=money(Decimal(row[3])),
                    paid_at=row[4],
                )
                for row in recent_payments
            ],
        )

    @staticmethod
    def _trends(
        daily: Sequence[Row[Any]],
        costs: Sequence[Row[Any]],
        expenses: Sequence[Row[Any]],
        window: ReportWindow,
    ) -> list[TrendPoint]:
        """One point per calendar day of the window, zero-filled when idle."""
        revenue_by_day = {row[0]: Decimal(row[2]) for row in daily}
        orders_by_day = {row[0]: int(row[1]) for row in daily}
        cost_by_day = {row[0]: Decimal(row[1]) for row in costs}
        expense_by_day = {row[0]: Decimal(row[1]) for row in expenses}

        points: list[TrendPoint] = []
        day = window.start
        while day <= window.end:
            revenue = revenue_by_day.get(day, ZERO)
            profit = revenue - cost_by_day.get(day, ZERO) - expense_by_day.get(day, ZERO)
            points.append(
                TrendPoint(
                    day=day,
                    orders=orders_by_day.get(day, 0),
                    revenue=money(revenue),
                    profit=money(profit),
                )
            )
            day += timedelta(days=1)
        return points

    @staticmethod
    def _stock_row(row: Row[Any]) -> StockStatusRow:
        quantity = Decimal(row[4])
        minimum = Decimal(row[5])
        if quantity <= 0:
            status = "out_of_stock"
        elif quantity <= minimum:
            status = "low_stock"
        else:
            status = "in_stock"
        return StockStatusRow(
            product_id=row[0],
            name=row[1],
            sku=row[2],
            unit=row[3],
            quantity=quantity,
            minimum_stock=minimum,
            stock_status=status,
        )
