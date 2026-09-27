"""Supplier management and their running balance."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.models.supplier import Supplier
from app.repositories.supplier import SupplierRepository
from app.schemas.supplier import SupplierCreate, SupplierUpdate
from app.utils.pagination import PageParams


class SupplierService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.suppliers = SupplierRepository(session)

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
        sort: tuple[Any, bool] | None = None,
    ) -> tuple[Sequence[Supplier], int]:
        return await self.suppliers.list_suppliers(
            params, sort=sort, search=search, is_active=is_active
        )

    async def list_all(self) -> Sequence[Supplier]:
        return await self.suppliers.list_all()

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
