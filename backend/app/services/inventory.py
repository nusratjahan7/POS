"""Inventory: the one and only writer of stock.

Every change to on-hand quantity goes through :meth:`InventoryService.record_movement`.
That method, in a single transaction:

1. ensures the ``(product, branch)`` level row exists (upsert) and locks it with
   ``SELECT ... FOR UPDATE`` — the serialisation point for concurrent movements;
2. computes ``previous_stock`` and ``new_stock`` from the locked, authoritative
   value and refuses to take stock below zero;
3. adjusts ``Product.stock_quantity`` with an **atomic** ``SET x = x + :delta``
   (no read-modify-write, so the aggregate is correct under concurrency);
4. appends an immutable :class:`StockMovement` row.

Future purchases and sales call the same method with their own
``reference_type``/``reference_id`` — they never touch a level directly.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from decimal import Decimal
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, UnprocessableError
from app.core.permissions import PermissionCode
from app.models.product import Product
from app.models.stock_level import StockLevel
from app.models.stock_movement import StockMovement
from app.repositories.branch import BranchRepository
from app.repositories.product import ProductRepository
from app.repositories.stock_level import StockLevelRepository
from app.repositories.stock_movement import StockMovementRepository
from app.services.audit_log import AuditLogService
from app.services.notification import NotificationService
from app.utils.pagination import PageParams


class InventoryService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.levels = StockLevelRepository(session)
        self.movements = StockMovementRepository(session)
        self.products = ProductRepository(session)
        self.branches = BranchRepository(session)

    # --- Reads -------------------------------------------------------------
    async def list_levels(
        self,
        params: PageParams,
        *,
        sort: tuple[Any, bool] | None = None,
        **filters: Any,
    ) -> tuple[Sequence[StockLevel], int]:
        return await self.levels.list_levels(params, sort=sort, **filters)

    async def list_movements(
        self,
        params: PageParams,
        *,
        sort: tuple[Any, bool] | None = None,
        **filters: Any,
    ) -> tuple[Sequence[StockMovement], int]:
        return await self.movements.list_movements(params, sort=sort, **filters)

    async def summary(self, *, branch_id: uuid.UUID | None = None) -> dict[str, int | Decimal]:
        return await self.levels.summary(branch_id=branch_id)

    async def get_level(self, product_id: uuid.UUID, branch_id: uuid.UUID) -> StockLevel | None:
        stmt = select(StockLevel).where(
            StockLevel.product_id == product_id, StockLevel.branch_id == branch_id
        )
        return (await self.session.execute(stmt)).scalars().one_or_none()

    async def ensure_level(self, *, product_id: uuid.UUID, branch_id: uuid.UUID) -> None:
        """Guarantee a (product, branch) row exists, starting at zero.

        Called when a product is created so it appears in the inventory views
        (out-of-stock included) before it has ever moved.
        """
        await self.session.execute(
            pg_insert(StockLevel)
            .values(product_id=product_id, branch_id=branch_id, quantity=0)
            .on_conflict_do_nothing(index_elements=["product_id", "branch_id"])
        )
        await self.session.commit()

    # --- The write path ----------------------------------------------------
    async def _lock_level(self, product_id: uuid.UUID, branch_id: uuid.UUID) -> StockLevel:
        """Create the level row if absent, then lock it for the transaction."""
        await self.session.execute(
            pg_insert(StockLevel)
            .values(product_id=product_id, branch_id=branch_id, quantity=0)
            .on_conflict_do_nothing(index_elements=["product_id", "branch_id"])
        )
        stmt = (
            select(StockLevel)
            .where(StockLevel.product_id == product_id, StockLevel.branch_id == branch_id)
            .with_for_update()
        )
        return (await self.session.execute(stmt)).scalars().one()

    async def _reload_movement(self, movement_id: uuid.UUID) -> StockMovement:
        stmt = select(StockMovement).where(StockMovement.id == movement_id)
        return (await self.session.execute(stmt)).scalars().one()

    async def apply_movement(
        self,
        *,
        product_id: uuid.UUID,
        branch_id: uuid.UUID,
        quantity: Decimal,
        movement_type: str,
        reference_type: str = "manual",
        reference_id: uuid.UUID | None = None,
        user_id: uuid.UUID | None = None,
        note: str | None = None,
    ) -> StockMovement:
        """Apply a signed stock change and stage the ledger row.

        Does **not** commit: the caller owns the transaction. This is what lets a
        multi-step document (receiving a purchase) move several products and
        update its own records atomically. Use :meth:`record_movement` for a
        standalone, self-committing change.
        """
        if quantity == 0:
            raise UnprocessableError(
                "A movement must change the quantity by a non-zero amount.",
                code="zero_quantity_movement",
            )

        product = await self.products.get(product_id)
        if product is None or product.is_deleted:
            raise NotFoundError("Product not found.", code="product_not_found")
        branch = await self.branches.get(branch_id)
        if branch is None or branch.is_deleted:
            raise NotFoundError("Branch not found.", code="branch_not_found")

        level = await self._lock_level(product_id, branch_id)
        previous = level.quantity
        new = previous + quantity
        if new < 0:
            raise UnprocessableError(
                f"Only {previous} in stock at this branch; cannot remove {-quantity}.",
                code="insufficient_stock",
                details=[{"field": "quantity", "message": "Would take stock below zero."}],
            )

        level.quantity = new

        # Atomic increment: correct even if another branch moves this product
        # concurrently, without contending on the product row.
        await self.session.execute(
            update(Product)
            .where(Product.id == product_id)
            .values(stock_quantity=Product.stock_quantity + quantity)
        )

        movement = StockMovement(
            product_id=product_id,
            branch_id=branch_id,
            quantity=quantity,
            movement_type=movement_type,
            reference_type=reference_type,
            reference_id=reference_id,
            previous_stock=previous,
            new_stock=new,
            note=note,
            user_id=user_id,
        )
        self.session.add(movement)
        await self.session.flush()

        # Alert stock-watchers if this movement pushed the product over a line.
        await self._notify_stock_level(product=product, previous=previous, new=new, user_id=user_id)
        return movement

    async def _notify_stock_level(
        self,
        *,
        product: Product,
        previous: Decimal,
        new: Decimal,
        user_id: uuid.UUID | None,
    ) -> None:
        """Notify when a movement crosses the low / out-of-stock threshold.

        Guarded on the *crossing* (``previous`` vs ``new``), so a product that
        merely sits low does not re-notify on every subsequent movement.
        """
        minimum = product.minimum_stock
        if new <= 0 and previous > 0:
            notification_type, severity = "out_of_stock", "critical"
        elif new <= minimum and previous > minimum:
            notification_type, severity = "low_stock", "warning"
        else:
            return

        label = "Out of stock" if notification_type == "out_of_stock" else "Low stock"
        await NotificationService(self.session).push_to_permission(
            PermissionCode.INVENTORY_READ.value,
            exclude_user_id=user_id,
            type=notification_type,
            severity=severity,
            title=f"{label}: {product.name}",
            body=f"{product.name} ({product.sku}) is down to {new}.",
            entity_type="product",
            entity_id=product.id,
            data={
                "product_name": product.name,
                "sku": product.sku,
                "quantity": new,
                "minimum_stock": minimum,
            },
        )

    async def record_movement(
        self,
        *,
        product_id: uuid.UUID,
        branch_id: uuid.UUID,
        quantity: Decimal,
        movement_type: str,
        reference_type: str = "manual",
        reference_id: uuid.UUID | None = None,
        user_id: uuid.UUID | None = None,
        note: str | None = None,
    ) -> StockMovement:
        """Apply a signed stock change and record it. Commits once, atomically."""
        movement = await self.apply_movement(
            product_id=product_id,
            branch_id=branch_id,
            quantity=quantity,
            movement_type=movement_type,
            reference_type=reference_type,
            reference_id=reference_id,
            user_id=user_id,
            note=note,
        )
        AuditLogService(self.session).record(
            action="inventory.stock.adjust",
            module="inventory",
            entity="product",
            entity_id=movement.product_id,
            user_id=user_id,
            old={"quantity": movement.previous_stock},
            new={"quantity": movement.new_stock, "movement_type": movement.movement_type},
        )
        await self.session.commit()
        return await self._reload_movement(movement.id)

    async def set_opening_stock(
        self,
        *,
        product_id: uuid.UUID,
        branch_id: uuid.UUID,
        quantity: Decimal,
        user_id: uuid.UUID | None = None,
    ) -> StockMovement | None:
        """Record a product's opening balance. No-op for a zero/negative amount."""
        if quantity <= 0:
            return None
        return await self.record_movement(
            product_id=product_id,
            branch_id=branch_id,
            quantity=quantity,
            movement_type="opening",
            reference_type="opening",
            user_id=user_id,
            note="Opening balance",
        )
