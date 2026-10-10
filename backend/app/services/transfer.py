"""Stock transfers between branches.

A transfer is a two-leg stock movement wrapped in an approval workflow. Stock
moves at exactly two steps, and only through :class:`InventoryService` — the one
writer of stock:

* **ship** takes the goods out of the source branch (``transfer_out``);
* **receive** puts them into the destination branch (``transfer_in``).

The intervening statuses (draft, requested, approved) hold no stock, so nothing
is reserved or lost before a physical shipment. Each transition runs inside one
database transaction together with its status change, audit entry and
notification — it either fully happens or fully rolls back.
"""

from __future__ import annotations

import secrets
import uuid
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    BadRequestError,
    ConflictError,
    NotFoundError,
    UnprocessableError,
)
from app.core.permissions import PermissionCode
from app.models.branch import Branch
from app.models.stock_transfer import PRE_SHIP_STATUSES, StockTransfer, StockTransferLine
from app.repositories.branch import BranchRepository
from app.repositories.product import ProductRepository
from app.repositories.stock_transfer import StockTransferRepository
from app.schemas.transfer import TransferCreate, TransferLineCreate, TransferUpdate
from app.services.audit_log import AuditLogService
from app.services.inventory import InventoryService
from app.services.notification import NotificationService
from app.utils.pagination import PageParams


def _snapshot(transfer: StockTransfer) -> dict[str, Any]:
    """The editable transfer fields, for the audit log."""
    return {
        "transfer_number": transfer.transfer_number,
        "status": transfer.status,
        "from_branch_id": str(transfer.from_branch_id),
        "to_branch_id": str(transfer.to_branch_id),
        "reference": transfer.reference,
        "items": [
            {"product_id": str(line.product_id), "quantity": str(line.quantity)}
            for line in transfer.items
        ],
    }


class TransferService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.transfers = StockTransferRepository(session)
        self.branches = BranchRepository(session)
        self.products = ProductRepository(session)
        self.inventory = InventoryService(session)

    # --- Reads -------------------------------------------------------------
    async def get_or_404(self, transfer_id: uuid.UUID) -> StockTransfer:
        transfer = await self.transfers.get_detailed(transfer_id)
        if transfer is None:
            raise NotFoundError("Transfer not found.", code="transfer_not_found")
        return transfer

    async def list_transfers(
        self,
        params: PageParams,
        *,
        sort: tuple[Any, bool] | None = None,
        **filters: Any,
    ) -> tuple[Sequence[StockTransfer], int]:
        return await self.transfers.list_transfers(params, sort=sort, **filters)

    # --- Internals ---------------------------------------------------------
    async def _unique_number(self) -> str:
        for _ in range(6):
            candidate = f"TRF-{datetime.now(UTC):%Y%m%d}-{secrets.token_hex(3).upper()}"
            if not await self.transfers.number_exists(candidate):
                return candidate
        raise ConflictError(
            "Could not allocate a transfer number, please try again.",
            code="transfer_number_conflict",
        )

    async def _resolve_branch(self, branch_id: uuid.UUID) -> Branch:
        branch = await self.branches.get(branch_id)
        if branch is None or branch.is_deleted:
            raise UnprocessableError(
                "The selected branch does not exist.",
                code="unknown_branch",
                details=[{"field": "branch_id", "message": "Unknown branch."}],
            )
        return branch

    async def _build_items(self, rows: Sequence[TransferLineCreate]) -> list[StockTransferLine]:
        seen: set[uuid.UUID] = set()
        items: list[StockTransferLine] = []
        for row in rows:
            if row.product_id in seen:
                raise UnprocessableError(
                    "The same product appears twice on this transfer.",
                    code="duplicate_transfer_item",
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
                StockTransferLine(
                    product_id=product.id,
                    product_name=product.name,
                    sku=product.sku,
                    quantity=row.quantity,
                )
            )
        return items

    @staticmethod
    def _assert_status(transfer: StockTransfer, allowed: tuple[str, ...], action: str) -> None:
        if transfer.status not in allowed:
            raise BadRequestError(
                f"A {transfer.status} transfer cannot be {action}.",
                code="transfer_invalid_transition",
                details=[{"field": "status", "message": f"Allowed from: {', '.join(allowed)}."}],
            )

    # --- Commands ----------------------------------------------------------
    async def create(
        self, payload: TransferCreate, *, actor_id: uuid.UUID | None = None
    ) -> StockTransfer:
        from_branch = await self._resolve_branch(payload.from_branch_id)
        to_branch = await self._resolve_branch(payload.to_branch_id)
        if from_branch.id == to_branch.id:
            raise UnprocessableError(
                "A transfer's source and destination branches must differ.",
                code="transfer_same_branch",
                details=[{"field": "to_branch_id", "message": "Same as the source branch."}],
            )
        items = await self._build_items(payload.items)

        transfer = StockTransfer(
            id=uuid.uuid4(),
            transfer_number=await self._unique_number(),
            from_branch=from_branch,
            to_branch=to_branch,
            reference=(payload.reference or "").strip() or None,
            note=(payload.note or "").strip() or None,
            status="requested" if payload.submit else "draft",
            created_by_id=actor_id,
        )
        if payload.submit:
            transfer.requested_by_id = actor_id
            transfer.requested_at = datetime.now(UTC)
        transfer.items = items

        self.session.add(transfer)
        AuditLogService(self.session).record(
            action="transfers.create",
            module="transfers",
            entity="stock_transfer",
            entity_id=transfer.id,
            user_id=actor_id,
            new=_snapshot(transfer),
        )
        await self.session.commit()
        return await self.get_or_404(transfer.id)

    async def update(
        self, transfer_id: uuid.UUID, payload: TransferUpdate
    ) -> StockTransfer:
        transfer = await self.get_or_404(transfer_id)
        self._assert_status(transfer, ("draft",), "edited")
        before = _snapshot(transfer)
        provided = payload.model_fields_set

        if payload.from_branch_id is not None:
            transfer.from_branch = await self._resolve_branch(payload.from_branch_id)
        if payload.to_branch_id is not None:
            transfer.to_branch = await self._resolve_branch(payload.to_branch_id)
        if "reference" in provided:
            transfer.reference = (payload.reference or "").strip() or None
        if "note" in provided:
            transfer.note = (payload.note or "").strip() or None
        if payload.items is not None:
            if not payload.items:
                raise UnprocessableError(
                    "A transfer needs at least one item.",
                    code="empty_transfer",
                    details=[{"field": "items", "message": "Add at least one product."}],
                )
            new_items = await self._build_items(payload.items)
            # Replace atomically: clear + flush deletes the old lines before the
            # new ones are inserted, so the (transfer, product) unique constraint
            # is never transiently violated.
            transfer.items.clear()
            await self.session.flush()
            transfer.items = new_items

        if transfer.from_branch_id == transfer.to_branch_id:
            raise UnprocessableError(
                "A transfer's source and destination branches must differ.",
                code="transfer_same_branch",
                details=[{"field": "to_branch_id", "message": "Same as the source branch."}],
            )

        AuditLogService(self.session).record(
            action="transfers.update",
            module="transfers",
            entity="stock_transfer",
            entity_id=transfer.id,
            old=before,
            new=_snapshot(transfer),
        )
        await self.session.commit()
        return await self.get_or_404(transfer.id)

    async def request(
        self, transfer_id: uuid.UUID, *, actor_id: uuid.UUID | None = None
    ) -> StockTransfer:
        transfer = await self.get_or_404(transfer_id)
        self._assert_status(transfer, ("draft",), "submitted")
        transfer.status = "requested"
        transfer.requested_by_id = actor_id
        transfer.requested_at = datetime.now(UTC)
        await self._commit_transition(transfer, "transfers.request", actor_id, "draft", "requested")
        return await self.get_or_404(transfer.id)

    async def approve(
        self, transfer_id: uuid.UUID, *, actor_id: uuid.UUID | None = None
    ) -> StockTransfer:
        transfer = await self.get_or_404(transfer_id)
        self._assert_status(transfer, ("draft", "requested"), "approved")
        previous = transfer.status
        transfer.status = "approved"
        transfer.approved_by_id = actor_id
        transfer.approved_at = datetime.now(UTC)
        await self._commit_transition(
            transfer, "transfers.approve", actor_id, previous, "approved"
        )
        return await self.get_or_404(transfer.id)

    async def ship(
        self, transfer_id: uuid.UUID, *, actor_id: uuid.UUID | None = None
    ) -> StockTransfer:
        """Ship the goods: decrease the source branch, one movement per line."""
        transfer = await self.get_or_404(transfer_id)
        self._assert_status(transfer, ("approved",), "shipped")

        try:
            # Deterministic order keeps concurrent shipments from deadlocking on
            # the per-level row locks.
            for line in sorted(transfer.items, key=lambda row: row.product_id):
                await self.inventory.apply_movement(
                    product_id=line.product_id,
                    branch_id=transfer.from_branch_id,
                    quantity=-line.quantity,
                    movement_type="transfer_out",
                    reference_type="transfer",
                    reference_id=transfer.id,
                    user_id=actor_id,
                    note=f"Transfer {transfer.transfer_number} to {transfer.to_branch.name}",
                )

            transfer.status = "shipped"
            transfer.shipped_by_id = actor_id
            transfer.shipped_at = datetime.now(UTC)

            AuditLogService(self.session).record(
                action="transfers.ship",
                module="transfers",
                entity="stock_transfer",
                entity_id=transfer.id,
                user_id=actor_id,
                old={"status": "approved"},
                new={"status": "shipped", "from_branch_id": str(transfer.from_branch_id)},
            )
            await NotificationService(self.session).push_to_permission(
                PermissionCode.TRANSFERS_RECEIVE.value,
                exclude_user_id=actor_id,
                branch_id=transfer.to_branch_id,
                type="transfer_shipped",
                severity="info",
                title=f"Transfer {transfer.transfer_number} is on its way",
                body=(
                    f"{len(transfer.items)} item(s) shipped from "
                    f"{transfer.from_branch.name} for {transfer.to_branch.name}."
                ),
                entity_type="stock_transfer",
                entity_id=transfer.id,
                data={
                    "transfer_number": transfer.transfer_number,
                    "from_branch_id": str(transfer.from_branch_id),
                    "to_branch_id": str(transfer.to_branch_id),
                },
            )
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            raise

        return await self.get_or_404(transfer.id)

    async def receive(
        self, transfer_id: uuid.UUID, *, actor_id: uuid.UUID | None = None
    ) -> StockTransfer:
        """Receive the goods: increase the destination branch."""
        transfer = await self.get_or_404(transfer_id)
        self._assert_status(transfer, ("shipped",), "received")

        try:
            for line in sorted(transfer.items, key=lambda row: row.product_id):
                await self.inventory.apply_movement(
                    product_id=line.product_id,
                    branch_id=transfer.to_branch_id,
                    quantity=line.quantity,
                    movement_type="transfer_in",
                    reference_type="transfer",
                    reference_id=transfer.id,
                    user_id=actor_id,
                    note=f"Transfer {transfer.transfer_number} from {transfer.from_branch.name}",
                )

            transfer.status = "received"
            transfer.received_by_id = actor_id
            transfer.received_at = datetime.now(UTC)

            AuditLogService(self.session).record(
                action="transfers.receive",
                module="transfers",
                entity="stock_transfer",
                entity_id=transfer.id,
                user_id=actor_id,
                old={"status": "shipped"},
                new={"status": "received", "to_branch_id": str(transfer.to_branch_id)},
            )
            await NotificationService(self.session).push_to_permission(
                PermissionCode.TRANSFERS_READ.value,
                exclude_user_id=actor_id,
                branch_id=transfer.from_branch_id,
                type="transfer_received",
                severity="info",
                title=f"Transfer {transfer.transfer_number} was received",
                body=f"{transfer.to_branch.name} confirmed receipt of the shipment.",
                entity_type="stock_transfer",
                entity_id=transfer.id,
                data={
                    "transfer_number": transfer.transfer_number,
                    "to_branch_id": str(transfer.to_branch_id),
                },
            )
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            raise

        return await self.get_or_404(transfer.id)

    async def cancel(
        self,
        transfer_id: uuid.UUID,
        *,
        reason: str | None = None,
        actor_id: uuid.UUID | None = None,
    ) -> StockTransfer:
        """Cancel a transfer that has not shipped (no stock has moved yet)."""
        transfer = await self.get_or_404(transfer_id)
        self._assert_status(transfer, PRE_SHIP_STATUSES, "cancelled")
        previous = transfer.status
        transfer.status = "cancelled"
        transfer.cancel_reason = (reason or "").strip() or None
        transfer.cancelled_by_id = actor_id
        transfer.cancelled_at = datetime.now(UTC)
        await self._commit_transition(
            transfer, "transfers.cancel", actor_id, previous, "cancelled"
        )
        return await self.get_or_404(transfer.id)

    # --- Shared transition tail -------------------------------------------
    async def _commit_transition(
        self,
        transfer: StockTransfer,
        action: str,
        actor_id: uuid.UUID | None,
        previous: str,
        current: str,
    ) -> None:
        AuditLogService(self.session).record(
            action=action,
            module="transfers",
            entity="stock_transfer",
            entity_id=transfer.id,
            user_id=actor_id,
            old={"status": previous},
            new={"status": current},
        )
        await self.session.commit()
