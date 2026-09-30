"""Supplier management and their running balance."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError, UnprocessableError
from app.models.supplier import Supplier
from app.models.supplier_payment import SupplierPayment
from app.repositories.supplier import SupplierRepository
from app.repositories.supplier_payment import SupplierPaymentRepository
from app.schemas.ledger import LedgerStatement
from app.schemas.supplier import SupplierCreate, SupplierPaymentCreate, SupplierUpdate
from app.services.ledger import LedgerService
from app.utils.pagination import PageParams


class SupplierService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.suppliers = SupplierRepository(session)
        self.payments = SupplierPaymentRepository(session)

    async def get_or_404(self, supplier_id: uuid.UUID) -> Supplier:
        supplier = await self.suppliers.get(supplier_id)
        if supplier is None or supplier.is_deleted:
            raise NotFoundError("Supplier not found.", code="supplier_not_found")
        return supplier

    async def list_suppliers(
        self,
        params: PageParams,
        *,
        search: str | None = None,
        is_active: bool | None = None,
        has_dues: bool | None = None,
        sort: tuple[Any, bool] | None = None,
    ) -> tuple[Sequence[Supplier], int]:
        return await self.suppliers.list_suppliers(
            params, sort=sort, search=search, is_active=is_active, has_dues=has_dues
        )

    async def list_all(self) -> Sequence[Supplier]:
        return await self.suppliers.list_all()

    async def list_payments(
        self, supplier_id: uuid.UUID, params: PageParams
    ) -> tuple[Sequence[SupplierPayment], int]:
        await self.get_or_404(supplier_id)
        return await self.payments.list_for_supplier(params, supplier_id)

    async def ledger(
        self,
        supplier_id: uuid.UUID,
        *,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> LedgerStatement:
        await self.get_or_404(supplier_id)
        return await LedgerService(self.session).supplier_statement(
            supplier_id, date_from=date_from, date_to=date_to
        )

    async def record_payment(
        self,
        supplier_id: uuid.UUID,
        payload: SupplierPaymentCreate,
        *,
        actor_id: uuid.UUID | None = None,
    ) -> SupplierPayment:
        """Pay down what we owe a supplier.

        A payment can never exceed the outstanding balance, so the payable is
        protected from going negative — the mirror of a customer overpaying.
        """
        supplier = await self.get_or_404(supplier_id)

        if payload.amount > supplier.balance:
            raise UnprocessableError(
                f"Only {supplier.balance} is owed to this supplier; that payment is too large.",
                code="payment_exceeds_balance",
                details=[{"field": "amount", "message": "Greater than the outstanding balance."}],
            )

        payment = SupplierPayment(
            supplier_id=supplier.id,
            amount=payload.amount,
            method=payload.method,
            reference=payload.reference,
            note=payload.note,
            user_id=actor_id,
        )
        self.session.add(payment)

        # Atomic decrement: the payable and the ledger move together.
        await self.session.execute(
            update(Supplier)
            .where(Supplier.id == supplier.id)
            .values(balance=Supplier.balance - payload.amount)
        )

        await self.session.commit()
        return await self._reload_payment(payment.id)

    async def _assert_name_free(self, name: str, *, exclude_id: uuid.UUID | None = None) -> None:
        if await self.suppliers.name_exists(name, exclude_id=exclude_id):
            raise ConflictError(
                "A supplier with that name already exists.",
                code="supplier_name_taken",
                details=[{"field": "name", "message": "Already in use."}],
            )

    async def create(self, payload: SupplierCreate) -> Supplier:
        name = payload.name.strip()
        await self._assert_name_free(name)

        supplier = Supplier(
            name=name,
            company=payload.company,
            phone=payload.phone,
            email=str(payload.email) if payload.email else None,
            address=payload.address,
            opening_balance=payload.opening_balance,
            # The balance starts at whatever was already owed.
            balance=payload.opening_balance,
            is_active=payload.is_active,
        )
        await self.suppliers.add(supplier)
        await self.session.commit()
        return supplier

    async def update(self, supplier_id: uuid.UUID, payload: SupplierUpdate) -> Supplier:
        supplier = await self.get_or_404(supplier_id)
        provided = payload.model_fields_set

        if payload.name is not None:
            name = payload.name.strip()
            if name.lower() != supplier.name.lower():
                await self._assert_name_free(name, exclude_id=supplier.id)
                supplier.name = name

        if "company" in provided:
            supplier.company = payload.company
        if "phone" in provided:
            supplier.phone = payload.phone
        if "email" in provided:
            supplier.email = str(payload.email) if payload.email else None
        if "address" in provided:
            supplier.address = payload.address
        if payload.is_active is not None:
            supplier.is_active = payload.is_active

        await self.session.commit()
        return supplier

    async def delete(self, supplier_id: uuid.UUID) -> None:
        supplier = await self.get_or_404(supplier_id)
        purchases = await self.suppliers.count_purchases(supplier.id)
        if purchases:
            raise ConflictError(
                f"{purchases} purchase(s) reference this supplier.",
                code="supplier_in_use",
            )
        supplier.is_active = False
        supplier.deleted_at = datetime.now(UTC)
        await self.session.commit()

    async def _reload_payment(self, payment_id: uuid.UUID) -> SupplierPayment:
        stmt = select(SupplierPayment).where(SupplierPayment.id == payment_id)
        return (await self.session.execute(stmt)).scalars().one()
