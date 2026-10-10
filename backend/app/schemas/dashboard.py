"""Response shape for the dashboard snapshot.

Pure data: the service derives every figure from SQL aggregates and fills these
in. Row shapes are reused from the reporting module so a product, category,
payment-method or stock row is identical wherever it appears.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel

from app.schemas.report import (
    CategorySalesRow,
    PaymentMethodSalesRow,
    ProductSalesRow,
    ReportRange,
    StockStatusRow,
)


class DashboardToday(BaseModel):
    """Today's trade, independent of the selected period."""

    sales: Decimal
    orders: int
    gross_profit: Decimal
    net_profit: Decimal


class DashboardStanding(BaseModel):
    """As-of-now figures that do not vary with the date window."""

    customers: int
    products: int
    low_stock: int
    outstanding_due: Decimal
    supplier_due: Decimal


class TrendPoint(BaseModel):
    """One calendar day of the window, zero-filled when nothing happened."""

    day: date
    orders: int
    revenue: Decimal
    profit: Decimal


class RecentSaleRow(BaseModel):
    id: uuid.UUID
    sale_number: str
    customer_name: str | None
    total: Decimal
    status: str
    sold_at: datetime


class RecentPaymentRow(BaseModel):
    id: uuid.UUID
    sale_number: str
    method_name: str
    amount: Decimal
    paid_at: datetime


class DashboardSnapshot(BaseModel):
    as_of: datetime
    range: ReportRange
    today: DashboardToday
    standing: DashboardStanding
    trends: list[TrendPoint]
    category_performance: list[CategorySalesRow]
    payment_methods: list[PaymentMethodSalesRow]
    top_products: list[ProductSalesRow]
    recent_sales: list[RecentSaleRow]
    low_stock: list[StockStatusRow]
    recent_payments: list[RecentPaymentRow]
