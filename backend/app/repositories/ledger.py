"""Read-only SQL for the derived customer and supplier ledgers.

Repositories own SQL, but a ledger is not a table — it is a projection of rows
that live elsewhere (openings, sales, purchases, payments, refund reversals).
This repository gathers those rows into one neutral shape; the service places
them in order and runs the balance.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer_payment import CustomerPayment
from app.models.purchase import Purchase
from app.models.sale import Sale
from app.models.sale_return import SaleReturn
from app.models.supplier_payment import SupplierPayment


@dataclass(frozen=True, slots=True)
class LedgerRow:
    """One unresolved ledger movement, before the running balance is applied."""

    occurred_at: datetime
    source_id: str
    entry_type: str
    reference: str
    description: str | None
    debit: Decimal
    credit: Decimal


class LedgerRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def customer_rows(self, customer_id: uuid.UUID) -> list[LedgerRow]:
        """Credit sales, payments received and refund reversals for a customer."""
        rows: list[LedgerRow] = []

        sales = await self.session.execute(
            select(Sale.id, Sale.sold_at, Sale.sale_number, Sale.due).where(
                Sale.customer_id == customer_id, Sale.due > 0
            )
        )
        for sale_id, sold_at, number, due in sales.all():
            rows.append(
                LedgerRow(
                    occurred_at=sold_at,
                    source_id=str(sale_id),
                    entry_type="sale",
                    reference=number,
                    description="Sale on account",
                    debit=Decimal(due),
                    credit=Decimal("0.00"),
                )
            )

        payments = await self.session.execute(
            select(
                CustomerPayment.id,
                CustomerPayment.paid_at,
                CustomerPayment.amount,
                CustomerPayment.method,
                CustomerPayment.reference,
                CustomerPayment.note,
            ).where(CustomerPayment.customer_id == customer_id)
        )
        for payment_id, paid_at, amount, method, reference, note in payments.all():
            rows.append(
                LedgerRow(
                    occurred_at=paid_at,
                    source_id=str(payment_id),
                    entry_type="payment",
                    reference=reference or "Payment",
                    description=method or note,
                    debit=Decimal("0.00"),
                    credit=Decimal(amount),
                )
            )

        refunds = await self.session.execute(
            select(
                SaleReturn.id,
                func.coalesce(SaleReturn.completed_at, SaleReturn.created_at),
                SaleReturn.return_number,
                SaleReturn.credit_reversed,
            )
            .join(Sale, Sale.id == SaleReturn.sale_id)
            .where(
                Sale.customer_id == customer_id,
                SaleReturn.status == "completed",
                SaleReturn.credit_reversed > 0,
            )
        )
        for return_id, occurred_at, number, credit_reversed in refunds.all():
            rows.append(
                LedgerRow(
                    occurred_at=occurred_at,
                    source_id=str(return_id),
                    entry_type="refund",
                    reference=number,
                    description="Returned goods",
                    debit=Decimal("0.00"),
                    credit=Decimal(credit_reversed),
                )
            )

        return rows

    async def supplier_rows(self, supplier_id: uuid.UUID) -> list[LedgerRow]:
        """Received purchase dues and payments made to a supplier."""
        rows: list[LedgerRow] = []

        # The payable incurred is the purchase total; the payment made at receipt
        # is recorded separately below, so the two together net to the due the
        # receipt added to the balance.
        purchases = await self.session.execute(
            select(
                Purchase.id,
                Purchase.received_at,
                Purchase.purchase_number,
                Purchase.total,
            ).where(Purchase.supplier_id == supplier_id, Purchase.status == "received")
        )
        for purchase_id, received_at, number, total in purchases.all():
            if received_at is None:  # pragma: no cover - defensive; received sets it
                continue
            rows.append(
                LedgerRow(
                    occurred_at=received_at,
                    source_id=str(purchase_id),
                    entry_type="purchase",
                    reference=number,
                    description="Purchase received",
                    debit=Decimal("0.00"),
                    credit=Decimal(total),
                )
            )

        payments = await self.session.execute(
            select(
                SupplierPayment.id,
                SupplierPayment.paid_at,
                SupplierPayment.amount,
                SupplierPayment.method,
                SupplierPayment.reference,
                SupplierPayment.note,
            ).where(SupplierPayment.supplier_id == supplier_id)
        )
        for payment_id, paid_at, amount, method, reference, note in payments.all():
            rows.append(
                LedgerRow(
                    occurred_at=paid_at,
                    source_id=str(payment_id),
                    entry_type="payment",
                    reference=reference or "Payment",
                    description=method or note,
                    debit=Decimal(amount),
                    credit=Decimal("0.00"),
                )
            )

        return rows
