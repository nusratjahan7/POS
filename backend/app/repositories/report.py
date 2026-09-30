"""Reporting aggregates.

Every figure a report shows is computed in the database — ``GROUP BY`` and
``SUM`` over a date window — never by loading rows into Python. Dates are turned
into half-open timestamp bounds so the range scans use the indexes on
``sales.sold_at``, ``stock_movements.created_at`` and friends.

Conventions applied here (and relied on by the service):
* sales count only ``status='completed'`` rows — voided sales are excluded;
* revenue is **net of returns**: ``sum(total - returned_amount)``;
* purchases count only ``status='received'`` rows.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import Row, and_, func, select

from app.models.branch import Branch
from app.models.category import Category
from app.models.customer import Customer
from app.models.payment_method import PaymentMethod
from app.models.product import Product
from app.models.purchase import Purchase
from app.models.sale import Sale
from app.models.sale_item import SaleItem
from app.models.sale_payment import SalePayment
from app.models.sale_return import SaleReturn
from app.models.stock_level import StockLevel
from app.models.stock_movement import StockMovement
from app.models.supplier import Supplier
from app.models.user import User
from app.repositories.base import BaseRepository

ZERO = Decimal("0")


def _day_bounds(start: date, end: date) -> tuple[datetime, datetime]:
    """Inclusive calendar days as a half-open ``[start, end)`` UTC instant pair."""
    lower = datetime.combine(start, time.min, tzinfo=UTC)
    upper = datetime.combine(end + timedelta(days=1), time.min, tzinfo=UTC)
    return lower, upper


class ReportRepository(BaseRepository[Sale]):
    """Aggregate queries spanning sales, purchasing, stock and finance."""

    model = Sale

    # --- Shared filters ----------------------------------------------------
    @staticmethod
    def _sales_conditions(
        start: date, end: date, branch_id: uuid.UUID | None
    ) -> list[Any]:
        lower, upper = _day_bounds(start, end)
        conditions: list[Any] = [
            Sale.status == "completed",
            Sale.sold_at >= lower,
            Sale.sold_at < upper,
        ]
        if branch_id is not None:
            conditions.append(Sale.branch_id == branch_id)
        return conditions

    @staticmethod
    def _movement_conditions(
        start: date, end: date, branch_id: uuid.UUID | None
    ) -> list[Any]:
        lower, upper = _day_bounds(start, end)
        conditions: list[Any] = [
            StockMovement.created_at >= lower,
            StockMovement.created_at < upper,
        ]
        if branch_id is not None:
            conditions.append(StockMovement.branch_id == branch_id)
        return conditions

    # --- Sales -------------------------------------------------------------
    async def sales_totals(
        self, start: date, end: date, branch_id: uuid.UUID | None
    ) -> dict[str, Decimal | int]:
        stmt = select(
            func.count(Sale.id),
            func.coalesce(func.sum(Sale.total), 0),
            func.coalesce(func.sum(Sale.total - Sale.returned_amount), 0),
            func.coalesce(func.sum(Sale.returned_amount), 0),
            func.coalesce(func.sum(Sale.discount), 0),
            func.coalesce(func.sum(Sale.tax), 0),
        ).where(*self._sales_conditions(start, end, branch_id))
        row = (await self.session.execute(stmt)).one()
        return {
            "order_count": int(row[0]),
            "gross_sales": Decimal(row[1]),
            "net_sales": Decimal(row[2]),
            "refunded_amount": Decimal(row[3]),
            "discount": Decimal(row[4]),
            "tax": Decimal(row[5]),
        }

    async def sales_items_sold(
        self, start: date, end: date, branch_id: uuid.UUID | None
    ) -> Decimal:
        stmt = (
            select(func.coalesce(func.sum(SaleItem.quantity), 0))
            .select_from(SaleItem)
            .join(Sale, Sale.id == SaleItem.sale_id)
            .where(*self._sales_conditions(start, end, branch_id))
        )
        return Decimal((await self.session.execute(stmt)).scalar_one())

    async def sales_cost(self, start: date, end: date, branch_id: uuid.UUID | None) -> Decimal:
        """Cost of goods sold: captured cost x quantity, over the window."""
        stmt = (
            select(func.coalesce(func.sum(SaleItem.cost_price * SaleItem.quantity), 0))
            .select_from(SaleItem)
            .join(Sale, Sale.id == SaleItem.sale_id)
            .where(*self._sales_conditions(start, end, branch_id))
        )
        return Decimal((await self.session.execute(stmt)).scalar_one())

    async def returns_count(
        self, start: date, end: date, branch_id: uuid.UUID | None
    ) -> int:
        """Completed returns against sales in the window (same population as refunds)."""
        stmt = (
            select(func.count(SaleReturn.id))
            .select_from(SaleReturn)
            .join(Sale, Sale.id == SaleReturn.sale_id)
            .where(*self._sales_conditions(start, end, branch_id), SaleReturn.status == "completed")
        )
        return int((await self.session.execute(stmt)).scalar_one())

    async def sales_daily(
        self, start: date, end: date, branch_id: uuid.UUID | None
    ) -> Sequence[Row[Any]]:
        day = func.date(Sale.sold_at).label("day")
        stmt = (
            select(
                day,
                func.count(Sale.id),
                func.coalesce(func.sum(Sale.total - Sale.returned_amount), 0),
            )
            .where(*self._sales_conditions(start, end, branch_id))
            .group_by(day)
            .order_by(day)
        )
        return (await self.session.execute(stmt)).all()

    async def sales_by_product(
        self, start: date, end: date, branch_id: uuid.UUID | None
    ) -> Sequence[Row[Any]]:
        stmt = (
            select(
                SaleItem.product_id,
                func.max(SaleItem.product_name).label("name"),
                func.max(SaleItem.sku).label("sku"),
                func.coalesce(func.sum(SaleItem.quantity), 0),
                func.coalesce(func.sum(SaleItem.line_total), 0),
                func.coalesce(func.sum(SaleItem.cost_price * SaleItem.quantity), 0),
            )
            .select_from(SaleItem)
            .join(Sale, Sale.id == SaleItem.sale_id)
            .where(*self._sales_conditions(start, end, branch_id))
            .group_by(SaleItem.product_id)
            .order_by(func.sum(SaleItem.line_total).desc())
        )
        return (await self.session.execute(stmt)).all()

    async def sales_by_category(
        self, start: date, end: date, branch_id: uuid.UUID | None
    ) -> Sequence[Row[Any]]:
        stmt = (
            select(
                Product.category_id,
                Category.name,
                func.coalesce(func.sum(SaleItem.quantity), 0),
                func.coalesce(func.sum(SaleItem.line_total), 0),
            )
            .select_from(SaleItem)
            .join(Sale, Sale.id == SaleItem.sale_id)
            .join(Product, Product.id == SaleItem.product_id)
            .outerjoin(Category, Category.id == Product.category_id)
            .where(*self._sales_conditions(start, end, branch_id))
            .group_by(Product.category_id, Category.name)
            .order_by(func.sum(SaleItem.line_total).desc())
        )
        return (await self.session.execute(stmt)).all()

    async def sales_by_cashier(
        self, start: date, end: date, branch_id: uuid.UUID | None
    ) -> Sequence[Row[Any]]:
        net = func.coalesce(func.sum(Sale.total - Sale.returned_amount), 0)
        stmt = (
            select(Sale.cashier_id, User.full_name, func.count(Sale.id), net)
            .select_from(Sale)
            .outerjoin(User, User.id == Sale.cashier_id)
            .where(*self._sales_conditions(start, end, branch_id))
            .group_by(Sale.cashier_id, User.full_name)
            .order_by(net.desc())
        )
        return (await self.session.execute(stmt)).all()

    async def sales_by_branch(self, start: date, end: date) -> Sequence[Row[Any]]:
        net = func.coalesce(func.sum(Sale.total - Sale.returned_amount), 0)
        stmt = (
            select(Sale.branch_id, Branch.name, func.count(Sale.id), net)
            .select_from(Sale)
            .join(Branch, Branch.id == Sale.branch_id)
            .where(*self._sales_conditions(start, end, None))
            .group_by(Sale.branch_id, Branch.name)
            .order_by(net.desc())
        )
        return (await self.session.execute(stmt)).all()

    async def sales_by_payment_method(
        self, start: date, end: date, branch_id: uuid.UUID | None
    ) -> Sequence[Row[Any]]:
        stmt = (
            select(
                SalePayment.payment_method_id,
                PaymentMethod.name,
                PaymentMethod.kind,
                func.count(func.distinct(SalePayment.sale_id)),
                func.coalesce(func.sum(SalePayment.amount), 0),
            )
            .select_from(SalePayment)
            .join(Sale, Sale.id == SalePayment.sale_id)
            .outerjoin(PaymentMethod, PaymentMethod.id == SalePayment.payment_method_id)
            .where(*self._sales_conditions(start, end, branch_id))
            .group_by(SalePayment.payment_method_id, PaymentMethod.name, PaymentMethod.kind)
            .order_by(func.sum(SalePayment.amount).desc())
        )
        return (await self.session.execute(stmt)).all()

    # --- Purchases ---------------------------------------------------------
    @staticmethod
    def _purchase_conditions(
        start: date | None, end: date | None, branch_id: uuid.UUID | None
    ) -> list[Any]:
        conditions: list[Any] = [Purchase.status == "received"]
        if start is not None:
            conditions.append(Purchase.purchase_date >= start)
        if end is not None:
            conditions.append(Purchase.purchase_date <= end)
        if branch_id is not None:
            conditions.append(Purchase.branch_id == branch_id)
        return conditions

    async def purchases_totals(
        self, start: date, end: date, branch_id: uuid.UUID | None
    ) -> dict[str, Decimal | int]:
        stmt = select(
            func.count(Purchase.id),
            func.coalesce(func.sum(Purchase.total), 0),
            func.coalesce(func.sum(Purchase.paid), 0),
            func.coalesce(func.sum(Purchase.due), 0),
        ).where(*self._purchase_conditions(start, end, branch_id))
        row = (await self.session.execute(stmt)).one()
        return {
            "purchase_count": int(row[0]),
            "total_purchases": Decimal(row[1]),
            "paid": Decimal(row[2]),
            "period_due": Decimal(row[3]),
        }

    async def outstanding_purchase_due(self, branch_id: uuid.UUID | None) -> Decimal:
        """Everything still owed to suppliers on received purchases (all time)."""
        stmt = select(func.coalesce(func.sum(Purchase.due), 0)).where(
            *self._purchase_conditions(None, None, branch_id)
        )
        return Decimal((await self.session.execute(stmt)).scalar_one())

    async def purchases_by_supplier(
        self, start: date, end: date, branch_id: uuid.UUID | None
    ) -> Sequence[Row[Any]]:
        stmt = (
            select(
                Purchase.supplier_id,
                Supplier.name,
                func.count(Purchase.id),
                func.coalesce(func.sum(Purchase.total), 0),
                func.coalesce(func.sum(Purchase.due), 0),
            )
            .select_from(Purchase)
            .join(Supplier, Supplier.id == Purchase.supplier_id)
            .where(*self._purchase_conditions(start, end, branch_id))
            .group_by(Purchase.supplier_id, Supplier.name)
            .order_by(func.sum(Purchase.total).desc())
        )
        return (await self.session.execute(stmt)).all()

    # --- Inventory ---------------------------------------------------------
    async def inventory_valuation(self, branch_id: uuid.UUID | None) -> dict[str, Any]:
        stmt = (
            select(
                func.coalesce(func.sum(StockLevel.quantity * Product.purchase_price), 0),
                func.coalesce(func.sum(StockLevel.quantity * Product.selling_price), 0),
                func.coalesce(func.sum(StockLevel.quantity), 0),
                func.count(func.distinct(StockLevel.product_id)),
            )
            .select_from(StockLevel)
            .join(Product, Product.id == StockLevel.product_id)
            .where(Product.deleted_at.is_(None))
        )
        if branch_id is not None:
            stmt = stmt.where(StockLevel.branch_id == branch_id)
        row = (await self.session.execute(stmt)).one()
        return {
            "stock_value_cost": Decimal(row[0]),
            "stock_value_retail": Decimal(row[1]),
            "total_quantity": Decimal(row[2]),
            "product_count": int(row[3]),
        }

    async def stock_rows(
        self, *, status: str, branch_id: uuid.UUID | None, limit: int
    ) -> Sequence[Row[Any]]:
        if status == "out_of_stock":
            condition = StockLevel.quantity <= 0
        else:
            condition = and_(
                StockLevel.quantity > 0, StockLevel.quantity <= Product.minimum_stock
            )
        stmt = (
            select(
                StockLevel.product_id,
                Product.name,
                Product.sku,
                Product.unit,
                StockLevel.quantity,
                Product.minimum_stock,
            )
            .select_from(StockLevel)
            .join(Product, Product.id == StockLevel.product_id)
            .where(Product.deleted_at.is_(None), condition)
            .order_by(StockLevel.quantity.asc(), Product.name.asc())
            .limit(limit)
        )
        if branch_id is not None:
            stmt = stmt.where(StockLevel.branch_id == branch_id)
        return (await self.session.execute(stmt)).all()

    async def movements_by_type(
        self, start: date, end: date, branch_id: uuid.UUID | None
    ) -> Sequence[Row[Any]]:
        stmt = (
            select(
                StockMovement.movement_type,
                func.count(StockMovement.id),
                func.coalesce(func.sum(StockMovement.quantity), 0),
            )
            .select_from(StockMovement)
            .where(*self._movement_conditions(start, end, branch_id))
            .group_by(StockMovement.movement_type)
            .order_by(StockMovement.movement_type.asc())
        )
        return (await self.session.execute(stmt)).all()

    async def adjustments(
        self, start: date, end: date, branch_id: uuid.UUID | None
    ) -> dict[str, Decimal | int]:
        conditions = self._movement_conditions(start, end, branch_id)
        adjustment_amount = func.coalesce(
            func.sum(StockMovement.quantity).filter(
                StockMovement.movement_type == "adjustment"
            ),
            0,
        )
        damage_amount = func.coalesce(
            func.sum(StockMovement.quantity).filter(StockMovement.movement_type == "damage"),
            0,
        )
        stmt = select(
            func.count().filter(StockMovement.movement_type == "adjustment"),
            adjustment_amount,
            func.count().filter(StockMovement.movement_type == "damage"),
            damage_amount,
        ).where(*conditions)
        row = (await self.session.execute(stmt)).one()
        return {
            "count": int(row[0]),
            "net_quantity": Decimal(row[1]),
            "damage_count": int(row[2]),
            "damage_quantity": Decimal(row[3]),
        }

    # --- Dues --------------------------------------------------------------
    async def customer_dues(self) -> Decimal:
        stmt = select(func.coalesce(func.sum(Customer.balance), 0)).where(
            Customer.deleted_at.is_(None)
        )
        return Decimal((await self.session.execute(stmt)).scalar_one())

    async def supplier_dues(self) -> Decimal:
        stmt = select(func.coalesce(func.sum(Supplier.balance), 0)).where(
            Supplier.deleted_at.is_(None)
        )
        return Decimal((await self.session.execute(stmt)).scalar_one())


__all__ = ["ReportRepository"]
