"""Response shapes for the reporting module.

Pure data: the service derives every figure from SQL aggregates and fills these
in. Money is ``Decimal`` and serialises as a string, as everywhere else.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel


class ReportRange(BaseModel):
    """The resolved window a report covers, echoed back for display."""

    start: date
    end: date
    preset: str


# --- Sales -----------------------------------------------------------------
class SalesSummary(BaseModel):
    total_sales: Decimal
    order_count: int
    average_order_value: Decimal
    items_sold: Decimal
    discount: Decimal
    tax: Decimal
    refunded_amount: Decimal
    returns_count: int


class SalesDailyPoint(BaseModel):
    day: date
    total: Decimal
    orders: int


class ProductSalesRow(BaseModel):
    product_id: uuid.UUID | None
    name: str
    sku: str
    quantity: Decimal
    net: Decimal
    cost: Decimal
    profit: Decimal


class CategorySalesRow(BaseModel):
    category_id: uuid.UUID | None
    name: str
    quantity: Decimal
    net: Decimal


class CashierSalesRow(BaseModel):
    cashier_id: uuid.UUID | None
    name: str
    order_count: int
    total: Decimal


class BranchSalesRow(BaseModel):
    branch_id: uuid.UUID | None
    name: str
    order_count: int
    total: Decimal


class PaymentMethodSalesRow(BaseModel):
    payment_method_id: uuid.UUID | None
    name: str
    kind: str
    count: int
    amount: Decimal


class SalesReport(BaseModel):
    range: ReportRange
    summary: SalesSummary
    daily: list[SalesDailyPoint]
    by_product: list[ProductSalesRow]
    by_category: list[CategorySalesRow]
    by_cashier: list[CashierSalesRow]
    by_branch: list[BranchSalesRow]
    by_payment_method: list[PaymentMethodSalesRow]


# --- Purchases -------------------------------------------------------------
class PurchaseSummary(BaseModel):
    total_purchases: Decimal
    purchase_count: int
    paid: Decimal
    outstanding_due: Decimal


class SupplierPurchaseRow(BaseModel):
    supplier_id: uuid.UUID | None
    name: str
    count: int
    total: Decimal
    due: Decimal


class PurchaseReport(BaseModel):
    range: ReportRange
    summary: PurchaseSummary
    by_supplier: list[SupplierPurchaseRow]


# --- Inventory -------------------------------------------------------------
class InventoryTotals(BaseModel):
    product_count: int
    stock_value_cost: Decimal
    stock_value_retail: Decimal
    total_quantity: Decimal
    in_stock: int
    low_stock: int
    out_of_stock: int


class StockStatusRow(BaseModel):
    product_id: uuid.UUID
    name: str
    sku: str
    unit: str
    quantity: Decimal
    minimum_stock: Decimal
    stock_status: str


class MovementTypeRow(BaseModel):
    movement_type: str
    count: int
    net_quantity: Decimal


class AdjustmentSummary(BaseModel):
    count: int
    net_quantity: Decimal
    damage_count: int
    damage_quantity: Decimal


class InventoryReport(BaseModel):
    as_of: datetime
    #: Stock value is as-of-now; movements and adjustments cover this window.
    range: ReportRange
    totals: InventoryTotals
    low_stock: list[StockStatusRow]
    out_of_stock: list[StockStatusRow]
    movements: list[MovementTypeRow]
    adjustments: AdjustmentSummary


# --- Financial -------------------------------------------------------------
class FinancialReport(BaseModel):
    range: ReportRange
    revenue: Decimal
    cost: Decimal
    gross_profit: Decimal
    gross_margin: Decimal
    expenses: Decimal
    net_profit: Decimal
    customer_due: Decimal
    supplier_due: Decimal
