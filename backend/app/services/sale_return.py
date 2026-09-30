"""Sales returns: goods coming back, and the refund that goes with them.

One transaction, mirroring :class:`~app.services.sale.SaleService` in reverse. The
quantities are checked against what is *still* returnable (sold minus everything
already returned), each line refunds its own net — capped so a sale can never hand
back more than it was worth — every unit goes back into the branch with a
``return`` movement, and the refund clears what the customer still owed before any
cash leaves the drawer.
"""

from __future__ import annotations

import secrets
import uuid
from collections.abc import Sequence
from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import ConflictError, NotFoundError, UnprocessableError
from app.models.sale import Sale
from app.models.sale_item import SaleItem
from app.models.sale_return import SaleReturn
from app.models.sale_return_item import SaleReturnItem
from app.repositories.payment_method import PaymentMethodRepository
from app.repositories.register_session import RegisterSessionRepository
from app.repositories.sale import SaleRepository
from app.repositories.sale_return import SaleReturnRepository
from app.schemas.sale_return import SaleReturnCreate
from app.services.customer import CustomerService
from app.services.inventory import InventoryService
from app.services.register_session import RegisterSessionService
from app.services.sale import money

ZERO = Decimal("0.00")
THOUSANDTH = Decimal("0.001")


def quantity(value: Decimal) -> Decimal:
    """Round a quantity to the thousandth the schema allows."""
    return value.quantize(THOUSANDTH, rounding=ROUND_HALF_UP)


class SaleReturnService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.returns = SaleReturnRepository(session)
        self.sales = SaleRepository(session)
        self.methods = PaymentMethodRepository(session)
        self.inventory = InventoryService(session)
        self.credit = CustomerService(session)
        self.sessions = RegisterSessionRepository(session)
        self.cash = RegisterSessionService(session)

    # --- Reads -------------------------------------------------------------
    def _detail_query(self, return_id: uuid.UUID) -> Any:
        return (
            select(SaleReturn)
            .where(SaleReturn.id == return_id)
            .options(selectinload(SaleReturn.items))
        )

    async def get_or_404(self, return_id: uuid.UUID) -> SaleReturn:
        record = (await self.session.execute(self._detail_query(return_id))).scalars().one_or_none()
        if record is None:
            raise NotFoundError("Return not found.", code="sale_return_not_found")
        return record

    async def _reload(self, return_id: uuid.UUID) -> SaleReturn:
        stmt = self._detail_query(return_id).execution_options(populate_existing=True)
        return (await self.session.execute(stmt)).scalars().one()

    async def _sale_or_404(self, sale_id: uuid.UUID) -> Sale:
        stmt = select(Sale).where(Sale.id == sale_id).options(selectinload(Sale.items))
        sale = (await self.session.execute(stmt)).scalars().one_or_none()
        if sale is None:
            raise NotFoundError("Sale not found.", code="sale_not_found")
        return sale

    async def list_for_sale(self, sale_id: uuid.UUID) -> Sequence[SaleReturn]:
        """Every return against a sale — its return history."""
        await self._sale_or_404(sale_id)
        return await self.returns.list_for_sale(sale_id)

    # --- Internals ---------------------------------------------------------
    async def _unique_number(self) -> str:
        for _ in range(6):
            candidate = f"RET-{datetime.now(UTC):%Y%m%d}-{secrets.token_hex(3).upper()}"
            if not await self.returns.number_exists(candidate):
                return candidate
        raise ConflictError(
            "Could not allocate a return number, please try again.",
            code="return_number_conflict",
        )

    def _line_refund(
        self,
        sale_item: SaleItem,
        remaining_quantity: Decimal,
        returning: Decimal,
        already_refunded: Decimal,
    ) -> Decimal:
        """What returning ``returning`` units of a line is worth.

        Proportional to the line's own net, except when the return takes the last
        of the line — then it refunds exactly what is left of that net, so
        splitting a line across several returns still adds up to its total with no
        rounding drift.
        """
        if returning >= remaining_quantity:
            return money(sale_item.line_total - already_refunded)
        return money(returning * sale_item.line_total / sale_item.quantity)

    # --- Commands ----------------------------------------------------------
    async def create(
        self,
        sale_id: uuid.UUID,
        payload: SaleReturnCreate,
        *,
        actor_id: uuid.UUID | None = None,
    ) -> SaleReturn:
        """Take goods back, restock them and settle the refund — all or nothing."""
        # Lock the sale first so two returns of the same sale cannot both pass
        # the "still returnable" check against stale state and over-return.
        await self.sales.lock(sale_id)
        sale = await self._sale_or_404(sale_id)
        if sale.status != "completed":
            raise ConflictError(
                f"This sale is {sale.status}; only a completed sale can be returned.",
                code="sale_not_returnable",
            )

        lines = {item.id: item for item in sale.items}
        history = await self.returns.history_for_sale(sale.id)

        # --- What can still come back -----------------------------------------
        seen: set[uuid.UUID] = set()
        requested: list[tuple[SaleItem, Decimal, Decimal]] = []
        for row in payload.items:
            if row.sale_item_id in seen:
                raise UnprocessableError(
                    "The same line appears twice on this return.",
                    code="duplicate_return_item",
                    details=[{"field": "items", "message": "Duplicate line."}],
                )
            seen.add(row.sale_item_id)

            sale_item = lines.get(row.sale_item_id)
            if sale_item is None:
                raise UnprocessableError(
                    "A line on this return is not part of the sale.",
                    code="unknown_sale_item",
                    details=[{"field": "items", "message": "Unknown sale line."}],
                )

            returned_quantity, _ = history.get(sale_item.id, (ZERO, ZERO))
            remaining = sale_item.quantity - returned_quantity
            returning = quantity(row.quantity)
            if returning > remaining:
                raise UnprocessableError(
                    f"Only {remaining} of {sale_item.product_name} can still be returned.",
                    code="return_quantity_exceeds_sold",
                    details=[
                        {"field": "items", "message": "More than was sold, or already returned."}
                    ],
                )
            requested.append((sale_item, remaining, returning))

        # --- What it is worth --------------------------------------------------
        # Never more than the sale still has left to give back.
        remaining_refundable = money(sale.total - sale.returned_amount)
        refund_total = ZERO
        return_items: list[SaleReturnItem] = []

        # Product order keeps the stock locks in the same sequence a sale takes
        # them, so a return cannot deadlock a till selling the same goods.
        for sale_item, remaining, returning in sorted(requested, key=lambda row: row[0].product_id):
            _, refunded_amount = history.get(sale_item.id, (ZERO, ZERO))
            line_refund = min(
                self._line_refund(sale_item, remaining, returning, refunded_amount),
                remaining_refundable,
            )
            remaining_refundable = money(remaining_refundable - line_refund)
            refund_total = money(refund_total + line_refund)
            return_items.append(
                SaleReturnItem(
                    sale_item_id=sale_item.id,
                    product_id=sale_item.product_id,
                    product_name=sale_item.product_name,
                    sku=sale_item.sku,
                    quantity=returning,
                    unit_price=sale_item.unit_price,
                    line_total=line_refund,
                )
            )

        if payload.payment_method_id is not None:
            method = await self.methods.get(payload.payment_method_id)
            if method is None or method.is_deleted or not method.is_active:
                raise UnprocessableError(
                    "That refund method is not available.",
                    code="unknown_payment_method",
                    details=[{"field": "payment_method_id", "message": "Unavailable method."}],
                )

        # Goods the customer never paid for clear the debt before any cash moves.
        # Returns apply in order, so what is *still* owed is the sale's due less
        # what earlier returns already cleared.
        outstanding = money(sale.due - min(sale.returned_amount, sale.due))
        credit_reversed = min(refund_total, outstanding)
        cash_refund = money(refund_total - credit_reversed)
        if cash_refund > 0 and payload.payment_method_id is None:
            raise UnprocessableError(
                f"{cash_refund} is being paid back; choose how the refund is settled.",
                code="refund_method_required",
                details=[
                    {"field": "payment_method_id", "message": "Required to pay out a refund."}
                ],
            )

        record = SaleReturn(
            id=uuid.uuid4(),
            sale_id=sale.id,
            return_number=await self._unique_number(),
            status="completed",
            reason=(payload.reason or "").strip() or None,
            note=(payload.note or "").strip() or None,
            payment_method_id=payload.payment_method_id if cash_refund > 0 else None,
            refund_reference=payload.reference,
            refund_amount=refund_total,
            credit_reversed=credit_reversed,
            cash_refund=cash_refund,
            created_by_id=actor_id,
            completed_by_id=actor_id,
            completed_at=datetime.now(UTC),
        )
        for item in return_items:
            item.return_id = record.id
        record.items = return_items
        self.session.add(record)

        try:
            for item in sorted(return_items, key=lambda row: row.product_id):
                await self.inventory.apply_movement(
                    product_id=item.product_id,
                    branch_id=sale.branch_id,
                    quantity=item.quantity,
                    movement_type="return",
                    reference_type="sale_return",
                    reference_id=record.id,
                    user_id=actor_id,
                    note=f"Return {record.return_number} on {sale.sale_number}",
                )

            if credit_reversed > 0 and sale.customer_id is not None:
                await self.credit.reverse_credit(sale.customer_id, credit_reversed)

            # Cash handed back comes out of the drawer of the till the sale was
            # rung on, when that till is still open.
            if record.cash_refund > 0 and sale.register_id is not None:
                open_session = await self.sessions.get_open_for_register(sale.register_id)
                if open_session is not None:
                    await self.cash.record_cash(
                        open_session.id,
                        -record.cash_refund,
                        movement_type="refund",
                        reference_type="sale_return",
                        reference_id=record.id,
                        user_id=actor_id,
                        note=f"Refund {record.return_number} on {sale.sale_number}",
                    )

            sale.returned_amount = money(sale.returned_amount + refund_total)
            if sale.returned_amount >= sale.total:
                # Everything that was sold has come back: the sale is refunded.
                sale.status = "refunded"
                sale.refunded_at = datetime.now(UTC)
                sale.refunded_by_id = actor_id
                sale.refund_reason = record.reason

            await self.session.commit()
        except Exception:
            await self.session.rollback()
            raise

        return await self._reload(record.id)

    async def cancel(
        self, return_id: uuid.UUID, *, actor_id: uuid.UUID | None = None
    ) -> SaleReturn:
        """Cancel a return that has not been applied yet.

        A *completed* return has already restocked and refunded, so it cannot be
        cancelled — that would need the money clawed back too. The statuses exist
        for an approval workflow; today returns complete immediately.
        """
        record = await self.get_or_404(return_id)
        if record.status not in ("requested", "approved"):
            raise ConflictError(
                f"A {record.status} return cannot be cancelled; "
                "its stock and refund are already applied.",
                code="return_not_cancellable",
            )
        record.status = "cancelled"
        record.cancelled_at = datetime.now(UTC)
        record.cancelled_by_id = actor_id
        await self.session.commit()
        return await self._reload(record.id)
