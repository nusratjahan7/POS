"""Customer management, their running balance, and payments.

``Customer.balance`` is the receivable (what the customer owes). It is written
only here — payments decrease it, :meth:`charge_credit` increases it — and every
change is kept in step with the payment history in one transaction.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, UnprocessableError
from app.models.customer import Customer
from app.models.customer_payment import CustomerPayment
from app.repositories.customer import CustomerRepository
from app.repositories.customer_payment import CustomerPaymentRepository
from app.schemas.customer import CustomerCreate, CustomerPaymentCreate, CustomerUpdate
from app.utils.pagination import PageParams

ZERO = Decimal("0")
RECENT_LIMIT = 5


class CustomerService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.customers = CustomerRepository(session)
        self.payments = CustomerPaymentRepository(session)

    # --- Reads -------------------------------------------------------------
    async def get_or_404(self, customer_id: uuid.UUID) -> Customer:
        customer = await self.customers.get(customer_id)
        if customer is None or customer.is_deleted:
            raise NotFoundError("Customer not found.", code="customer_not_found")
        return customer

    async def list_customers(
        self,
        params: PageParams,
        *,
        search: str | None = None,
        is_active: bool | None = None,
        sort: tuple[Any, bool] | None = None,
    ) -> tuple[Sequence[Customer], int]:
        return await self.customers.list_customers(
            params, sort=sort, search=search, is_active=is_active
        )

    async def list_all(self) -> Sequence[Customer]:
        return await self.customers.list_all()

    async def list_payments(
        self, customer_id: uuid.UUID, params: PageParams
    ) -> tuple[Sequence[CustomerPayment], int]:
        await self.get_or_404(customer_id)
        return await self.payments.list_for_customer(params, customer_id)

    async def details(self, customer_id: uuid.UUID) -> dict[str, Any]:
        """Aggregates for the detail screen.

        ``total_orders``/``total_purchase_amount``/``recent_purchases`` are 0/[  ]
        until the sales module exists — the shape is final, only the data is
        pending.
        """
        customer = await self.get_or_404(customer_id)
        total_paid = await self.payments.total_for_customer(customer.id)
        recent = await self.payments.recent_for_customer(customer.id, limit=RECENT_LIMIT)
        return {
            "customer": customer,
            "total_orders": 0,
            "total_purchase_amount": ZERO,
            "total_paid": total_paid,
            "outstanding_due": customer.balance,
            "recent_payments": recent,
            "recent_purchases": [],
        }

    # --- Commands ----------------------------------------------------------
    async def create(self, payload: CustomerCreate) -> Customer:
        customer = Customer(
            name=payload.name.strip(),
            phone=payload.phone,
            email=str(payload.email) if payload.email else None,
            address=payload.address,
            opening_balance=payload.opening_balance,
            # What they already owed before using this system.
            balance=payload.opening_balance,
            is_active=payload.is_active,
        )
        await self.customers.add(customer)
        await self.session.commit()
        return customer

    async def update(self, customer_id: uuid.UUID, payload: CustomerUpdate) -> Customer:
        customer = await self.get_or_404(customer_id)
        provided = payload.model_fields_set

        if payload.name is not None:
            customer.name = payload.name.strip()
        if "phone" in provided:
            customer.phone = payload.phone
        if "email" in provided:
            customer.email = str(payload.email) if payload.email else None
        if "address" in provided:
            customer.address = payload.address
        if payload.is_active is not None:
            customer.is_active = payload.is_active

        await self.session.commit()
        return customer

    async def deactivate(self, customer_id: uuid.UUID) -> None:
        customer = await self.get_or_404(customer_id)
        customer.is_active = False
        customer.deleted_at = datetime.now(UTC)
        await self.session.commit()

    async def record_payment(
        self,
        customer_id: uuid.UUID,
        payload: CustomerPaymentCreate,
        *,
        actor_id: uuid.UUID | None = None,
    ) -> CustomerPayment:
        customer = await self.get_or_404(customer_id)

        if payload.amount > customer.balance:
            raise UnprocessableError(
                f"The customer only owes {customer.balance}; cannot record a larger payment.",
                code="payment_exceeds_balance",
                details=[{"field": "amount", "message": "Greater than the outstanding due."}],
            )

        payment = CustomerPayment(
            customer_id=customer.id,
            amount=payload.amount,
            method=payload.method,
            reference=payload.reference,
            note=payload.note,
            user_id=actor_id,
        )
        self.session.add(payment)

        # Atomic decrement: the receivable and the ledger move together.
        await self.session.execute(
            update(Customer)
            .where(Customer.id == customer.id)
            .values(balance=Customer.balance - payload.amount)
        )

        await self.session.commit()
        return await self._reload_payment(payment.id)

    async def charge_credit(
        self,
        customer_id: uuid.UUID,
        amount: Decimal,
        *,
        reference: str | None = None,
        note: str | None = None,
    ) -> None:
        """Add a credit sale to the customer's account.

        Not exposed over HTTP yet — the sales module will call this when it takes
        payment on account. Kept here so credit sales land through one code path.
        """
        if amount <= 0:
            raise UnprocessableError(
                "A credit charge must be a positive amount.", code="invalid_credit_amount"
            )
        await self.get_or_404(customer_id)
        await self.session.execute(
            update(Customer)
            .where(Customer.id == customer_id)
            .values(balance=Customer.balance + amount)
        )
        await self.session.commit()

    # --- Internals ---------------------------------------------------------
    async def _reload_payment(self, payment_id: uuid.UUID) -> CustomerPayment:
        stmt = select(CustomerPayment).where(CustomerPayment.id == payment_id)
        return (await self.session.execute(stmt)).scalars().one()
