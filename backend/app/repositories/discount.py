from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import Any, ClassVar

from sqlalchemy import Select, func, select

from app.models.discount import Discount
from app.models.discount_redemption import DiscountRedemption
from app.repositories.base import BaseRepository
from app.utils.pagination import PageParams
from app.utils.text import like_pattern


class DiscountRepository(BaseRepository[Discount]):
    model = Discount

    SORTABLE: ClassVar[dict[str, Any]] = {
        "name": Discount.name,
        "value": Discount.value,
        "created_at": Discount.created_at,
        "updated_at": Discount.updated_at,
    }

    async def get_by_code(self, code: str) -> Discount | None:
        stmt = select(Discount).where(
            func.lower(Discount.code) == code.strip().lower(),
            Discount.deleted_at.is_(None),
        )
        return (await self.session.execute(stmt)).scalars().one_or_none()

    async def code_exists(self, code: str, *, exclude_id: uuid.UUID | None = None) -> bool:
        stmt = select(Discount.id).where(
            func.lower(Discount.code) == code.strip().lower(),
            Discount.deleted_at.is_(None),
        )
        if exclude_id is not None:
            stmt = stmt.where(Discount.id != exclude_id)
        return (await self.session.execute(stmt.limit(1))).scalar_one_or_none() is not None

    def build_list_query(
        self,
        *,
        search: str | None = None,
        scope: str | None = None,
        is_active: bool | None = None,
        coupons_only: bool | None = None,
    ) -> Select[Any]:
        stmt = select(Discount).where(Discount.deleted_at.is_(None))
        if search:
            pattern = like_pattern(search)
            stmt = stmt.where(
                Discount.name.ilike(pattern, escape="\\")
                | Discount.code.ilike(pattern, escape="\\")
            )
        if scope is not None:
            stmt = stmt.where(Discount.scope == scope)
        if is_active is not None:
            stmt = stmt.where(Discount.is_active.is_(is_active))
        # Tri-state: True keeps coded coupons, False keeps automatic offers
        # (no code), None leaves both in.
        if coupons_only is not None:
            stmt = stmt.where(
                Discount.code.is_not(None) if coupons_only else Discount.code.is_(None)
            )
        return stmt

    async def list_discounts(
        self,
        params: PageParams,
        *,
        sort: tuple[Any, bool] | None = None,
        **filters: Any,
    ) -> tuple[Sequence[Discount], int]:
        stmt = self.build_list_query(**filters)
        if sort is not None:
            column, descending = sort
            stmt = stmt.order_by(column.desc() if descending else column.asc())
        else:
            stmt = stmt.order_by(Discount.name.asc())
        return await self.paginate(stmt, params)

    async def list_priced_candidates(self) -> Sequence[Discount]:
        """Every live, active discount — the engine narrows by window/scope itself.

        Links are loaded eagerly (``selectin``), so targeting costs no extra query.
        """
        stmt = select(Discount).where(
            Discount.deleted_at.is_(None), Discount.is_active.is_(True)
        )
        return (await self.session.execute(stmt)).scalars().all()


class DiscountRedemptionRepository(BaseRepository[DiscountRedemption]):
    model = DiscountRedemption

    async def count_for_discount(self, discount_id: uuid.UUID) -> int:
        stmt = select(func.count(DiscountRedemption.id)).where(
            DiscountRedemption.discount_id == discount_id
        )
        return int((await self.session.execute(stmt)).scalar_one())

    async def counts_for_discounts(
        self, discount_ids: Sequence[uuid.UUID]
    ) -> dict[uuid.UUID, int]:
        """Redemption counts for a page of discounts, in one grouped query."""
        if not discount_ids:
            return {}
        stmt = (
            select(DiscountRedemption.discount_id, func.count(DiscountRedemption.id))
            .where(DiscountRedemption.discount_id.in_(discount_ids))
            .group_by(DiscountRedemption.discount_id)
        )
        rows = await self.session.execute(stmt)
        return {discount_id: int(count) for discount_id, count in rows.all()}

    async def count_for_customer(self, discount_id: uuid.UUID, customer_id: uuid.UUID) -> int:
        stmt = select(func.count(DiscountRedemption.id)).where(
            DiscountRedemption.discount_id == discount_id,
            DiscountRedemption.customer_id == customer_id,
        )
        return int((await self.session.execute(stmt)).scalar_one())

    async def list_for_sale(self, sale_id: uuid.UUID) -> Sequence[DiscountRedemption]:
        stmt = (
            select(DiscountRedemption)
            .where(DiscountRedemption.sale_id == sale_id)
            .order_by(DiscountRedemption.created_at.asc())
        )
        return (await self.session.execute(stmt)).scalars().all()
