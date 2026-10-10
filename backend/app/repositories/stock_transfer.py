from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import date
from typing import Any, ClassVar

from sqlalchemy import Select, func, or_, select

from app.models.stock_transfer import StockTransfer
from app.repositories.base import BaseRepository
from app.utils.pagination import PageParams
from app.utils.text import like_pattern


class StockTransferRepository(BaseRepository[StockTransfer]):
    model = StockTransfer

    SORTABLE: ClassVar[dict[str, Any]] = {
        "transfer_number": StockTransfer.transfer_number,
        "status": StockTransfer.status,
        "created_at": StockTransfer.created_at,
        "updated_at": StockTransfer.updated_at,
        "shipped_at": StockTransfer.shipped_at,
        "received_at": StockTransfer.received_at,
    }

    async def number_exists(self, number: str) -> bool:
        stmt = select(StockTransfer.id).where(StockTransfer.transfer_number == number).limit(1)
        return (await self.session.execute(stmt)).scalar_one_or_none() is not None

    def build_list_query(
        self,
        *,
        search: str | None = None,
        status: str | None = None,
        branch_ids: Sequence[uuid.UUID] | None = None,
        from_branch_id: uuid.UUID | None = None,
        to_branch_id: uuid.UUID | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> Select[Any]:
        stmt = select(StockTransfer)
        if search:
            pattern = like_pattern(search)
            stmt = stmt.where(
                or_(
                    StockTransfer.transfer_number.ilike(pattern, escape="\\"),
                    StockTransfer.reference.ilike(pattern, escape="\\"),
                )
            )
        if status is not None:
            stmt = stmt.where(StockTransfer.status == status)
        # A transfer is visible when either of its branches is in scope.
        if branch_ids is not None:
            stmt = stmt.where(
                or_(
                    StockTransfer.from_branch_id.in_(branch_ids),
                    StockTransfer.to_branch_id.in_(branch_ids),
                )
            )
        if from_branch_id is not None:
            stmt = stmt.where(StockTransfer.from_branch_id == from_branch_id)
        if to_branch_id is not None:
            stmt = stmt.where(StockTransfer.to_branch_id == to_branch_id)
        if date_from is not None:
            stmt = stmt.where(func.date(StockTransfer.created_at) >= date_from)
        if date_to is not None:
            stmt = stmt.where(func.date(StockTransfer.created_at) <= date_to)
        return stmt

    async def list_transfers(
        self,
        params: PageParams,
        *,
        sort: tuple[Any, bool] | None = None,
        **filters: Any,
    ) -> tuple[Sequence[StockTransfer], int]:
        stmt = self.build_list_query(**filters)
        if sort is not None:
            column, descending = sort
            stmt = stmt.order_by(column.desc() if descending else column.asc())
        else:
            stmt = stmt.order_by(StockTransfer.created_at.desc())
        return await self.paginate(stmt, params)

    async def get_detailed(self, transfer_id: uuid.UUID) -> StockTransfer | None:
        """A transfer with its items refreshed from the database."""
        stmt = (
            select(StockTransfer)
            .where(StockTransfer.id == transfer_id)
            .execution_options(populate_existing=True)
        )
        return (await self.session.execute(stmt)).scalars().unique().one_or_none()
