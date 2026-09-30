from __future__ import annotations

import uuid
from collections.abc import Sequence
from decimal import Decimal

from sqlalchemy import func, select

from app.models.supplier_payment import SupplierPayment
from app.repositories.base import BaseRepository
from app.utils.pagination import PageParams


class SupplierPaymentRepository(BaseRepository[SupplierPayment]):
    model = SupplierPayment

    async def list_for_supplier(
        self, params: PageParams, supplier_id: uuid.UUID
    ) -> tuple[Sequence[SupplierPayment], int]:
        stmt = (
            select(SupplierPayment)
            .where(SupplierPayment.supplier_id == supplier_id)
            .order_by(SupplierPayment.paid_at.desc())
        )
        return await self.paginate(stmt, params)

    async def recent_for_supplier(
        self, supplier_id: uuid.UUID, *, limit: int = 5
    ) -> Sequence[SupplierPayment]:
        stmt = (
            select(SupplierPayment)
            .where(SupplierPayment.supplier_id == supplier_id)
            .order_by(SupplierPayment.paid_at.desc())
            .limit(limit)
        )
        return (await self.session.execute(stmt)).scalars().all()

    async def total_for_supplier(self, supplier_id: uuid.UUID) -> Decimal:
        stmt = select(func.coalesce(func.sum(SupplierPayment.amount), 0)).where(
            SupplierPayment.supplier_id == supplier_id
        )
        return Decimal((await self.session.execute(stmt)).scalar_one())
