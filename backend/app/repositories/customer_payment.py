from __future__ import annotations

import uuid
from collections.abc import Sequence
from decimal import Decimal

from sqlalchemy import func, select

from app.models.customer_payment import CustomerPayment
from app.repositories.base import BaseRepository
from app.utils.pagination import PageParams


class CustomerPaymentRepository(BaseRepository[CustomerPayment]):
    model = CustomerPayment

    async def list_for_customer(
        self, params: PageParams, customer_id: uuid.UUID
    ) -> tuple[Sequence[CustomerPayment], int]:
        stmt = (
            select(CustomerPayment)
            .where(CustomerPayment.customer_id == customer_id)
            .order_by(CustomerPayment.paid_at.desc())
        )
        return await self.paginate(stmt, params)

    async def recent_for_customer(
        self, customer_id: uuid.UUID, *, limit: int = 5
    ) -> Sequence[CustomerPayment]:
        stmt = (
            select(CustomerPayment)
            .where(CustomerPayment.customer_id == customer_id)
            .order_by(CustomerPayment.paid_at.desc())
            .limit(limit)
        )
        return (await self.session.execute(stmt)).scalars().all()

    async def total_for_customer(self, customer_id: uuid.UUID) -> Decimal:
        stmt = select(func.coalesce(func.sum(CustomerPayment.amount), 0)).where(
            CustomerPayment.customer_id == customer_id
        )
        return Decimal((await self.session.execute(stmt)).scalar_one())

    async def count_for_customer(self, customer_id: uuid.UUID) -> int:
        stmt = select(func.count(CustomerPayment.id)).where(
            CustomerPayment.customer_id == customer_id
        )
        return int((await self.session.execute(stmt)).scalar_one())
