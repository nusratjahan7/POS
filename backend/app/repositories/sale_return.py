from __future__ import annotations

import uuid
from collections.abc import Sequence
from decimal import Decimal

from sqlalchemy import func, select

from app.models.sale_return import SaleReturn
from app.models.sale_return_item import SaleReturnItem
from app.repositories.base import BaseRepository


class SaleReturnRepository(BaseRepository[SaleReturn]):
    model = SaleReturn

    async def number_exists(self, number: str) -> bool:
        stmt = select(SaleReturn.id).where(SaleReturn.return_number == number).limit(1)
        return (await self.session.execute(stmt)).scalar_one_or_none() is not None

    async def list_for_sale(self, sale_id: uuid.UUID) -> Sequence[SaleReturn]:
        """A sale's returns, newest first."""
        stmt = (
            select(SaleReturn)
            .where(SaleReturn.sale_id == sale_id)
            .order_by(SaleReturn.created_at.desc())
        )
        return (await self.session.execute(stmt)).scalars().unique().all()

    async def history_for_sale(
        self, sale_id: uuid.UUID
    ) -> dict[uuid.UUID, tuple[Decimal, Decimal]]:
        """Per sale line: ``(quantity already returned, amount already refunded)``.

        Counts only ``completed`` returns — a cancelled one never moved stock or
        money, so it must not consume the line's returnable quantity.
        """
        stmt = (
            select(
                SaleReturnItem.sale_item_id,
                func.coalesce(func.sum(SaleReturnItem.quantity), 0),
                func.coalesce(func.sum(SaleReturnItem.line_total), 0),
            )
            .join(SaleReturn, SaleReturn.id == SaleReturnItem.return_id)
            .where(SaleReturn.sale_id == sale_id, SaleReturn.status == "completed")
            .group_by(SaleReturnItem.sale_item_id)
        )
        rows = (await self.session.execute(stmt)).all()
        return {
            sale_item_id: (Decimal(quantity), Decimal(amount))
            for sale_item_id, quantity, amount in rows
        }
