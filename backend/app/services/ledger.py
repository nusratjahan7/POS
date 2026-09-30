"""Account statements for customers and suppliers.

Both statements are **derived**: the entries are projected from the rows that
already moved the balance (opening balance, credit sales, purchase receipts,
payments and refund reversals), and the running balance is computed here. The
closing balance therefore always equals the account's stored balance — the tests
assert exactly that.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from datetime import date
from decimal import Decimal
from typing import cast

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.repositories.customer import CustomerRepository
from app.repositories.ledger import LedgerRepository, LedgerRow
from app.repositories.supplier import SupplierRepository
from app.schemas.ledger import LedgerEntry, LedgerEntryType, LedgerStatement
from app.utils.money import ZERO, money

# A statement reads by day, and within a day a document lands before the
# settlement that pays it off — so a charge and its same-instant payment (a
# purchase and the amount paid on receipt share a timestamp) never read as a
# negative dip, and application/DB clock skew cannot reorder them.
_TYPE_ORDER = {"opening": 0, "sale": 1, "purchase": 1, "payment": 2, "refund": 3}


class LedgerService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.rows = LedgerRepository(session)
        self.customers = CustomerRepository(session)
        self.suppliers = SupplierRepository(session)

    async def customer_statement(
        self,
        customer_id: uuid.UUID,
        *,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> LedgerStatement:
        """What the customer owes, movement by movement (debit = owes more)."""
        customer = await self.customers.get(customer_id)
        if customer is None or customer.is_deleted:
            raise NotFoundError("Customer not found.", code="customer_not_found")

        rows = await self.rows.customer_rows(customer_id)
        if customer.opening_balance:
            rows.append(
                LedgerRow(
                    occurred_at=customer.created_at,
                    source_id=str(customer.id),
                    entry_type="opening",
                    reference="Opening balance",
                    description="Balance brought forward",
                    debit=Decimal(customer.opening_balance),
                    credit=ZERO,
                )
            )
        return self._statement(rows, lambda row: row.debit - row.credit, date_from, date_to)

    async def supplier_statement(
        self,
        supplier_id: uuid.UUID,
        *,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> LedgerStatement:
        """What we owe the supplier (credit = owe more, debit = paid)."""
        supplier = await self.suppliers.get(supplier_id)
        if supplier is None or supplier.is_deleted:
            raise NotFoundError("Supplier not found.", code="supplier_not_found")

        rows = await self.rows.supplier_rows(supplier_id)
        if supplier.opening_balance:
            rows.append(
                LedgerRow(
                    occurred_at=supplier.created_at,
                    source_id=str(supplier.id),
                    entry_type="opening",
                    reference="Opening balance",
                    description="Balance brought forward",
                    debit=ZERO,
                    credit=Decimal(supplier.opening_balance),
                )
            )
        return self._statement(rows, lambda row: row.credit - row.debit, date_from, date_to)

    @staticmethod
    def _statement(
        rows: list[LedgerRow],
        delta: Callable[[LedgerRow], Decimal],
        date_from: date | None,
        date_to: date | None,
    ) -> LedgerStatement:
        rows.sort(
            key=lambda row: (
                row.occurred_at.date(),
                _TYPE_ORDER.get(row.entry_type, 9),
                row.occurred_at,
                row.source_id,
            )
        )

        running = ZERO
        opening_balance = ZERO
        entries: list[LedgerEntry] = []
        for row in rows:
            running = money(running + delta(row))
            # Everything before the window folds into the opening balance; the
            # running balance is still accumulated so each in-range entry is
            # placed correctly.
            if date_from is not None and row.occurred_at.date() < date_from:
                opening_balance = running
                continue
            if date_to is not None and row.occurred_at.date() > date_to:
                continue
            entries.append(
                LedgerEntry(
                    occurred_at=row.occurred_at,
                    entry_type=cast(LedgerEntryType, row.entry_type),
                    reference=row.reference,
                    description=row.description,
                    debit=money(row.debit),
                    credit=money(row.credit),
                    balance=running,
                )
            )

        closing_balance = entries[-1].balance if entries else opening_balance
        return LedgerStatement(
            opening_balance=opening_balance,
            entries=entries,
            closing_balance=closing_balance,
        )
