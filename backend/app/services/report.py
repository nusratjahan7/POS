"""The reporting service: it resolves the window and turns SQL aggregates into
the report shapes the API returns.

Every figure is derived from :class:`ReportRepository` queries (or an existing
repository where one already answers the question). The service owns the
arithmetic that is *not* a single aggregate — averages, gross profit, margins,
net profit — so no endpoint or client ever computes a business number.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, tzinfo
from decimal import Decimal
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import Row
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.business import BusinessRepository
from app.repositories.expense import ExpenseRepository
from app.repositories.report import ReportRepository
from app.repositories.stock_level import StockLevelRepository
from app.schemas.report import (
    AdjustmentSummary,
    BranchSalesRow,
    CashierSalesRow,
    CategorySalesRow,
    FinancialReport,
    InventoryReport,
    InventoryTotals,
    MovementTypeRow,
    PaymentMethodSalesRow,
    ProductSalesRow,
    PurchaseReport,
    PurchaseSummary,
    ReportRange,
    SalesDailyPoint,
    SalesReport,
    SalesSummary,
    StockStatusRow,
    SupplierPurchaseRow,
)
from app.services.report_export import ReportSection
from app.utils.daterange import ReportWindow, WindowRequest, resolve_window
from app.utils.money import ZERO, money

HUNDRED = Decimal("100")
STOCK_LIST_LIMIT = 50


class ReportService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.reports = ReportRepository(session)
        self.business = BusinessRepository(session)
        self.stock_levels = StockLevelRepository(session)
        self.expenses = ExpenseRepository(session)

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

    # --- Reports -----------------------------------------------------------
    async def sales(
        self, request: WindowRequest, *, branch_id: uuid.UUID | None = None
    ) -> SalesReport:
        window = await self.resolve(request)
        totals = await self.reports.sales_totals(window.start, window.end, branch_id)
        items_sold = await self.reports.sales_items_sold(window.start, window.end, branch_id)
        returns = await self.reports.returns_count(window.start, window.end, branch_id)
        daily = await self.reports.sales_daily(window.start, window.end, branch_id)
        by_product = await self.reports.sales_by_product(window.start, window.end, branch_id)
        by_category = await self.reports.sales_by_category(window.start, window.end, branch_id)
        by_cashier = await self.reports.sales_by_cashier(window.start, window.end, branch_id)
        by_branch = await self.reports.sales_by_branch(window.start, window.end)
        by_method = await self.reports.sales_by_payment_method(window.start, window.end, branch_id)

        order_count = int(totals["order_count"])
        net_sales = money(Decimal(totals["net_sales"]))
        average = money(net_sales / order_count) if order_count else ZERO

        return SalesReport(
            range=self._range(window),
            summary=SalesSummary(
                total_sales=net_sales,
                order_count=order_count,
                average_order_value=average,
                items_sold=Decimal(items_sold),
                discount=money(Decimal(totals["discount"])),
                tax=money(Decimal(totals["tax"])),
                refunded_amount=money(Decimal(totals["refunded_amount"])),
                returns_count=returns,
            ),
            daily=[
                SalesDailyPoint(day=row[0], total=money(Decimal(row[2])), orders=int(row[1]))
                for row in daily
            ],
            by_product=[
                ProductSalesRow(
                    product_id=row[0],
                    name=row[1] or "—",
                    sku=row[2] or "",
                    quantity=Decimal(row[3]),
                    net=money(Decimal(row[4])),
                    cost=money(Decimal(row[5])),
                    profit=money(Decimal(row[4]) - Decimal(row[5])),
                )
                for row in by_product
            ],
            by_category=[
                CategorySalesRow(
                    category_id=row[0],
                    name=row[1] or "Uncategorised",
                    quantity=Decimal(row[2]),
                    net=money(Decimal(row[3])),
                )
                for row in by_category
            ],
            by_cashier=[
                CashierSalesRow(
                    cashier_id=row[0],
                    name=row[1] or "Unassigned",
                    order_count=int(row[2]),
                    total=money(Decimal(row[3])),
                )
                for row in by_cashier
            ],
            by_branch=[
                BranchSalesRow(
                    branch_id=row[0],
                    name=row[1] or "—",
                    order_count=int(row[2]),
                    total=money(Decimal(row[3])),
                )
                for row in by_branch
            ],
            by_payment_method=[
                PaymentMethodSalesRow(
                    payment_method_id=row[0],
                    name=row[1] or "Unknown",
                    kind=row[2] or "",
                    count=int(row[3]),
                    amount=money(Decimal(row[4])),
                )
                for row in by_method
            ],
        )

    async def purchases(
        self, request: WindowRequest, *, branch_id: uuid.UUID | None = None
    ) -> PurchaseReport:
        window = await self.resolve(request)
        totals = await self.reports.purchases_totals(window.start, window.end, branch_id)
        outstanding = await self.reports.outstanding_purchase_due(branch_id)
        by_supplier = await self.reports.purchases_by_supplier(
            window.start, window.end, branch_id
        )

        return PurchaseReport(
            range=self._range(window),
            summary=PurchaseSummary(
                total_purchases=money(Decimal(totals["total_purchases"])),
                purchase_count=int(totals["purchase_count"]),
                paid=money(Decimal(totals["paid"])),
                outstanding_due=money(outstanding),
            ),
            by_supplier=[
                SupplierPurchaseRow(
                    supplier_id=row[0],
                    name=row[1] or "—",
                    count=int(row[2]),
                    total=money(Decimal(row[3])),
                    due=money(Decimal(row[4])),
                )
                for row in by_supplier
            ],
        )

    async def inventory(
        self, request: WindowRequest, *, branch_id: uuid.UUID | None = None
    ) -> InventoryReport:
        window = await self.resolve(request)
        valuation = await self.reports.inventory_valuation(branch_id)
        summary = await self.stock_levels.summary(branch_id=branch_id)
        low = await self.reports.stock_rows(
            status="low_stock", branch_id=branch_id, limit=STOCK_LIST_LIMIT
        )
        out = await self.reports.stock_rows(
            status="out_of_stock", branch_id=branch_id, limit=STOCK_LIST_LIMIT
        )
        movements = await self.reports.movements_by_type(window.start, window.end, branch_id)
        adjustments = await self.reports.adjustments(window.start, window.end, branch_id)

        return InventoryReport(
            as_of=datetime.now(UTC),
            range=self._range(window),
            totals=InventoryTotals(
                product_count=int(valuation["product_count"]),
                stock_value_cost=money(Decimal(valuation["stock_value_cost"])),
                stock_value_retail=money(Decimal(valuation["stock_value_retail"])),
                total_quantity=Decimal(valuation["total_quantity"]),
                in_stock=int(summary["in_stock"]),
                low_stock=int(summary["low_stock"]),
                out_of_stock=int(summary["out_of_stock"]),
            ),
            low_stock=[self._stock_row(row) for row in low],
            out_of_stock=[self._stock_row(row) for row in out],
            movements=[
                MovementTypeRow(
                    movement_type=row[0],
                    count=int(row[1]),
                    net_quantity=Decimal(row[2]),
                )
                for row in movements
            ],
            adjustments=AdjustmentSummary(
                count=int(adjustments["count"]),
                net_quantity=Decimal(adjustments["net_quantity"]),
                damage_count=int(adjustments["damage_count"]),
                damage_quantity=Decimal(adjustments["damage_quantity"]),
            ),
        )

    async def financial(
        self, request: WindowRequest, *, branch_id: uuid.UUID | None = None
    ) -> FinancialReport:
        window = await self.resolve(request)
        totals = await self.reports.sales_totals(window.start, window.end, branch_id)
        cost = await self.reports.sales_cost(window.start, window.end, branch_id)
        expenses = await self.expenses.sum_amount(
            date_from=window.start, date_to=window.end, branch_id=branch_id
        )
        customer_due = await self.reports.customer_dues()
        supplier_due = await self.reports.supplier_dues()

        revenue = money(Decimal(totals["net_sales"]))
        cost_amount = money(Decimal(cost))
        gross_profit = money(revenue - cost_amount)
        margin = money(gross_profit / revenue * HUNDRED) if revenue else ZERO
        expenses_amount = money(Decimal(expenses))

        return FinancialReport(
            range=self._range(window),
            revenue=revenue,
            cost=cost_amount,
            gross_profit=gross_profit,
            gross_margin=margin,
            expenses=expenses_amount,
            net_profit=money(gross_profit - expenses_amount),
            customer_due=money(customer_due),
            supplier_due=money(supplier_due),
        )

    # --- Export ------------------------------------------------------------
    async def export(
        self, report: str, request: WindowRequest, *, branch_id: uuid.UUID | None = None
    ) -> tuple[list[ReportSection], ReportRange]:
        """Build the exportable sections for a report, plus the window it covered."""
        if report == "sales":
            sales = await self.sales(request, branch_id=branch_id)
            return self._sales_sections(sales), sales.range
        if report == "purchases":
            purchases = await self.purchases(request, branch_id=branch_id)
            return self._purchase_sections(purchases), purchases.range
        if report == "inventory":
            inventory = await self.inventory(request, branch_id=branch_id)
            return self._inventory_sections(inventory), inventory.range
        financial = await self.financial(request, branch_id=branch_id)
        return self._financial_sections(financial), financial.range

    @staticmethod
    def _sales_sections(data: SalesReport) -> list[ReportSection]:
        summary = data.summary
        return [
            ReportSection(
                title="Summary",
                columns=["Metric", "Value"],
                rows=[
                    ["Total sales", summary.total_sales],
                    ["Orders", summary.order_count],
                    ["Average order value", summary.average_order_value],
                    ["Items sold", summary.items_sold],
                    ["Discount", summary.discount],
                    ["Tax", summary.tax],
                    ["Refunded", summary.refunded_amount],
                    ["Returns", summary.returns_count],
                ],
            ),
            ReportSection(
                title="Daily",
                columns=["Date", "Sales", "Orders"],
                rows=[[point.day.isoformat(), point.total, point.orders] for point in data.daily],
            ),
            ReportSection(
                title="By product",
                columns=["Product", "SKU", "Quantity", "Net", "Cost", "Profit"],
                rows=[
                    [row.name, row.sku, row.quantity, row.net, row.cost, row.profit]
                    for row in data.by_product
                ],
            ),
            ReportSection(
                title="By category",
                columns=["Category", "Quantity", "Net"],
                rows=[[row.name, row.quantity, row.net] for row in data.by_category],
            ),
            ReportSection(
                title="By cashier",
                columns=["Cashier", "Orders", "Sales"],
                rows=[[row.name, row.order_count, row.total] for row in data.by_cashier],
            ),
            ReportSection(
                title="By branch",
                columns=["Branch", "Orders", "Sales"],
                rows=[[row.name, row.order_count, row.total] for row in data.by_branch],
            ),
            ReportSection(
                title="By payment method",
                columns=["Method", "Kind", "Count", "Amount"],
                rows=[
                    [row.name, row.kind, row.count, row.amount]
                    for row in data.by_payment_method
                ],
            ),
        ]

    @staticmethod
    def _purchase_sections(data: PurchaseReport) -> list[ReportSection]:
        summary = data.summary
        return [
            ReportSection(
                title="Summary",
                columns=["Metric", "Value"],
                rows=[
                    ["Total purchases", summary.total_purchases],
                    ["Orders", summary.purchase_count],
                    ["Paid", summary.paid],
                    ["Outstanding due", summary.outstanding_due],
                ],
            ),
            ReportSection(
                title="By supplier",
                columns=["Supplier", "Orders", "Total", "Due"],
                rows=[[row.name, row.count, row.total, row.due] for row in data.by_supplier],
            ),
        ]

    @staticmethod
    def _inventory_sections(data: InventoryReport) -> list[ReportSection]:
        totals = data.totals
        return [
            ReportSection(
                title="Totals",
                columns=["Metric", "Value"],
                rows=[
                    ["Products", totals.product_count],
                    ["Stock value (cost)", totals.stock_value_cost],
                    ["Stock value (retail)", totals.stock_value_retail],
                    ["Total quantity", totals.total_quantity],
                    ["In stock", totals.in_stock],
                    ["Low stock", totals.low_stock],
                    ["Out of stock", totals.out_of_stock],
                ],
            ),
            ReportSection(
                title="Low stock",
                columns=["Product", "SKU", "Quantity", "Minimum"],
                rows=[
                    [row.name, row.sku, row.quantity, row.minimum_stock]
                    for row in data.low_stock
                ],
            ),
            ReportSection(
                title="Out of stock",
                columns=["Product", "SKU", "Quantity", "Minimum"],
                rows=[
                    [row.name, row.sku, row.quantity, row.minimum_stock]
                    for row in data.out_of_stock
                ],
            ),
            ReportSection(
                title="Movements",
                columns=["Type", "Count", "Net quantity"],
                rows=[
                    [row.movement_type, row.count, row.net_quantity] for row in data.movements
                ],
            ),
            ReportSection(
                title="Adjustments",
                columns=["Metric", "Value"],
                rows=[
                    ["Adjustments", data.adjustments.count],
                    ["Adjustment quantity", data.adjustments.net_quantity],
                    ["Damages", data.adjustments.damage_count],
                    ["Damage quantity", data.adjustments.damage_quantity],
                ],
            ),
        ]

    @staticmethod
    def _financial_sections(data: FinancialReport) -> list[ReportSection]:
        return [
            ReportSection(
                title="Financial summary",
                columns=["Metric", "Value"],
                rows=[
                    ["Revenue", data.revenue],
                    ["Cost of goods", data.cost],
                    ["Gross profit", data.gross_profit],
                    ["Gross margin (%)", data.gross_margin],
                    ["Expenses", data.expenses],
                    ["Net profit", data.net_profit],
                    ["Customer due", data.customer_due],
                    ["Supplier due", data.supplier_due],
                ],
            )
        ]

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
