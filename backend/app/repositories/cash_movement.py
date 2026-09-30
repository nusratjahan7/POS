from __future__ import annotations

import uuid
from collections.abc import Sequence
from decimal import Decimal

from sqlalchemy import delete, func, select

from app.models.cash_movement import CashMovement
from app.repositories.base import BaseRepository


class CashMovementRepository(BaseRepository[CashMovement]):
    model = CashMovement

    async def list_for_session(self, session_id: uuid.UUID) -> Sequence[CashMovement]:
        stmt = (
            select(CashMovement)
            .where(CashMovement.session_id == session_id)
            .order_by(CashMovement.created_at.asc(), CashMovement.id.asc())
        )
        return (await self.session.execute(stmt)).scalars().all()

    async def sums_for_session(self, session_id: uuid.UUID) -> dict[str, Decimal]:
        """Signed total per movement type — the reconciliation's breakdown."""
        stmt = (
            select(
                CashMovement.movement_type,
                func.coalesce(func.sum(CashMovement.amount), 0),
            )
            .where(CashMovement.session_id == session_id)
            .group_by(CashMovement.movement_type)
        )
        rows = (await self.session.execute(stmt)).all()
        return {movement_type: Decimal(total) for movement_type, total in rows}

    async def delete_for_reference(
        self, reference_type: str, reference_id: uuid.UUID
    ) -> None:
        await self.session.execute(
            delete(CashMovement).where(
                CashMovement.reference_type == reference_type,
                CashMovement.reference_id == reference_id,
            )
        )
