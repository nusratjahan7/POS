"""Purchase orders and the atomic receive operation.

The single most important rule in this module: **stock only moves when a purchase
is received**, and that happens inside one database transaction together with the
ledger entries, the supplier balance and the payment record. If any step fails,
nothing is written.
"""

from __future__ import annotations

import secrets
import uuid
from collections.abc import Sequence
from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import (
    BadRequestError,
    ConflictError,
    NotFoundError,
    UnprocessableError,
)
from app.models.branch import Branch
from app.models.purchase import Purchase
from app.models.purchase_item import PurchaseItem
from app.models.supplier import Supplier
from app.models.supplier_payment import SupplierPayment
from app.repositories.branch import BranchRepository
from app.repositories.product import ProductRepository
from app.repositories.purchase import PurchaseRepository
from app.repositories.supplier import SupplierRepository
from app.schemas.purchase import PurchaseCreate, PurchaseItemCreate, PurchaseUpdate
from app.services.inventory import InventoryService
from app.utils.pagination import PageParams

CENT = Decimal("0.01")
EDITABLE = ("draft", "pending")


class PurchaseService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.purchases = PurchaseRepository(session)
        self.suppliers = SupplierRepository(session)
        self.branches = BranchRepository(session)
        self.products = ProductRepository(session)
        self.inventory = InventoryService(session)

    # --- Reads -------------------------------------------------------------
    def _detail_query(self, purchase_id: uuid.UUID) -> Any:
        return (
            select(Purchase)
            .where(Purchase.id == purchase_id)
            .options(selectinload(Purchase.items).selectinload(PurchaseItem.product))
        )

    async def get_or_404(self, purchase_id: uuid.UUID) -> Purchase:
        purchase = (
            (await self.session.execute(self._detail_query(purchase_id))).scalars().one_or_none()
        )
        if purchase is None:
            raise NotFoundError("Purchase not found.", code="purchase_not_found")
        return purchase

    async def _reload(self, purchase_id: uuid.UUID) -> Purchase:
        stmt = self._detail_query(purchase_id).execution_options(populate_existing=True)
        return (await self.session.execute(stmt)).scalars().one()

    async def list_purchases(
        self,
        params: PageParams,
        *,
        sort: tuple[Any, bool] | None = None,
        **filters: Any,
    ) -> tuple[Sequence[Purchase], int]:
        return await self.purchases.list_purchases(params, sort=sort, **filters)

    # --- Internals ---------------------------------------------------------
    async def _unique_number(self) -> str:
        for _ in range(6):
            candidate = f"PO-{datetime.now(UTC):%Y%m%d}-{secrets.token_hex(3).upper()}"
            if not await self.purchases.number_exists(candidate):
                return candidate
        raise ConflictError(
            "Could not allocate a purchase number, please try again.",
            code="purchase_number_conflict",
        )

    async def _resolve_supplier(self, supplier_id: uuid.UUID) -> Supplier:
        supplier = await self.suppliers.get(supplier_id)
        if supplier is None or supplier.is_deleted:
            raise UnprocessableError(
                "The selected supplier does not exist.",
                code="unknown_supplier",
                details=[{"field": "supplier_id", "message": "Unknown supplier."}],
            )
        return supplier

    async def _resolve_branch(self, branch_id: uuid.UUID) -> Branch:
        branch = await self.branches.get(branch_id)
        if branch is None or branch.is_deleted:
            raise UnprocessableError(
                "The selected branch does not exist.",
                code="unknown_branch",
                details=[{"field": "branch_id", "message": "Unknown branch."}],
            )
        return branch

    async def _build_items(self, rows: Sequence[PurchaseItemCreate]) -> list[PurchaseItem]:
        seen: set[uuid.UUID] = set()
        items: list[PurchaseItem] = []
        for row in rows:
            if row.product_id in seen:
                raise UnprocessableError(
                    "The same product appears twice on this purchase.",
                    code="duplicate_purchase_item",
                    details=[{"field": "items", "message": "Duplicate product."}],
                )
            seen.add(row.product_id)

            product = await self.products.get(row.product_id)
            if product is None or product.is_deleted:
                raise UnprocessableError(
                    "A selected product does not exist.",
                    code="unknown_product",
                    details=[{"field": "items", "message": f"Unknown product {row.product_id}."}],
                )
            items.append(
                PurchaseItem(
                    product_id=product.id,
                    quantity=row.quantity,
                    unit_price=row.unit_price,
                    subtotal=(row.quantity * row.unit_price).quantize(CENT, rounding=ROUND_HALF_UP),
                )
            )
        return items

    @staticmethod
    def _apply_totals(
        purchase: Purchase,
        items: Sequence[PurchaseItem],
        *,
        discount: Decimal,
        tax: Decimal,
        paid: Decimal,
    ) -> None:
        subtotal = sum((item.subtotal for item in items), Decimal("0"))
        if discount > subtotal:
            raise UnprocessableError(
                "The discount cannot exceed the subtotal.",
                code="discount_exceeds_subtotal",
                details=[{"field": "discount", "message": "Greater than the subtotal."}],
            )
        total = subtotal - discount + tax
        if paid > total:
            raise UnprocessableError(
                "The amount paid cannot exceed the total.",
                code="paid_exceeds_total",
                details=[{"field": "paid", "message": "Greater than the total."}],
            )
        purchase.subtotal = subtotal
        purchase.discount = discount
        purchase.tax = tax
        purchase.total = total
        purchase.paid = paid
        purchase.due = total - paid

    # --- Commands ----------------------------------------------------------
    async def create(
        self, payload: PurchaseCreate, *, actor_id: uuid.UUID | None = None
    ) -> Purchase:
        supplier = await self._resolve_supplier(payload.supplier_id)
        branch = await self._resolve_branch(payload.branch_id)
        items = await self._build_items(payload.items)

        purchase = Purchase(
            purchase_number=await self._unique_number(),
            supplier=supplier,
            branch=branch,
            purchase_date=payload.purchase_date,
            status=payload.status,
            note=payload.note,
            created_by_id=actor_id,
        )
        self._apply_totals(
            purchase, items, discount=payload.discount, tax=payload.tax, paid=payload.paid
        )
        purchase.items = items

        await self.purchases.add(purchase)
        await self.session.commit()
        return await self._reload(purchase.id)

    async def update(self, purchase_id: uuid.UUID, payload: PurchaseUpdate) -> Purchase:
        purchase = await self.get_or_404(purchase_id)
        if purchase.status not in EDITABLE:
            raise BadRequestError(
                "Only draft or pending purchases can be edited.",
                code="purchase_not_editable",
            )
        provided = payload.model_fields_set

        if payload.supplier_id is not None:
            purchase.supplier = await self._resolve_supplier(payload.supplier_id)
        if payload.branch_id is not None:
            purchase.branch = await self._resolve_branch(payload.branch_id)
        if payload.purchase_date is not None:
            purchase.purchase_date = payload.purchase_date
        if payload.status is not None:
            purchase.status = payload.status
        if "note" in provided:
            purchase.note = payload.note

        items = list(purchase.items)
        if payload.items is not None:
            items = await self._build_items(payload.items)
            purchase.items = items

        self._apply_totals(
            purchase,
            items,
            discount=payload.discount if payload.discount is not None else purchase.discount,
            tax=payload.tax if payload.tax is not None else purchase.tax,
            paid=payload.paid if payload.paid is not None else purchase.paid,
        )

        await self.session.commit()
        return await self._reload(purchase.id)

    async def receive(
        self, purchase_id: uuid.UUID, *, actor_id: uuid.UUID | None = None
    ) -> Purchase:
        """Receive a purchase — the one operation that moves stock.

        Steps 1-6 of the spec, all in a single transaction:
        inventory is increased (with a stock movement per line), the supplier
        balance grows by the amount still owed, and any payment made on receipt
        is recorded. Nothing here is committed until every step succeeds.
        """
        purchase = await self.get_or_404(purchase_id)
        if purchase.status not in EDITABLE:
            raise BadRequestError(
                "Only draft or pending purchases can be received.",
                code="purchase_not_receivable",
            )
        if not purchase.items:
            raise UnprocessableError(
                "A purchase needs at least one item before it can be received.",
                code="purchase_has_no_items",
            )

        # Increase inventory + write a stock movement per line. Deterministic order
        # keeps concurrent receives from deadlocking on the per-level row locks.
        for item in sorted(purchase.items, key=lambda row: row.product_id):
            await self.inventory.apply_movement(
                product_id=item.product_id,
                branch_id=purchase.branch_id,
                quantity=item.quantity,
                movement_type="stock_in",
                reference_type="purchase",
                reference_id=purchase.id,
                user_id=actor_id,
                note=f"Received {purchase.purchase_number}",
            )

        # Update the supplier balance by the amount still owed (atomic increment).
        await self.session.execute(
            update(Supplier)
            .where(Supplier.id == purchase.supplier_id)
            .values(balance=Supplier.balance + purchase.due)
        )

        # Record the payment made at receipt, if any, for the supplier ledger.
        if purchase.paid > 0:
            self.session.add(
                SupplierPayment(
                    supplier_id=purchase.supplier_id,
                    purchase_id=purchase.id,
                    amount=purchase.paid,
                    note=f"Paid on receipt of {purchase.purchase_number}",
                    user_id=actor_id,
                )
            )

        purchase.status = "received"
        purchase.received_at = datetime.now(UTC)

        await self.session.commit()
        return await self._reload(purchase.id)

    async def cancel(self, purchase_id: uuid.UUID) -> Purchase:
        purchase = await self.get_or_404(purchase_id)
        if purchase.status not in EDITABLE:
            raise BadRequestError(
                "Only draft or pending purchases can be cancelled.",
                code="purchase_not_cancellable",
            )
        purchase.status = "cancelled"
        purchase.cancelled_at = datetime.now(UTC)
        await self.session.commit()
        return await self._reload(purchase.id)

    async def delete(self, purchase_id: uuid.UUID) -> None:
        purchase = await self.get_or_404(purchase_id)
        if purchase.status != "draft":
            raise BadRequestError(
                "Only draft purchases can be deleted.",
                code="purchase_not_deletable",
            )
        await self.purchases.delete(purchase)
        await self.session.commit()
