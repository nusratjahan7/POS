"""Point-of-sale reads: the sellable catalogue, priced and stocked per branch.

Cost fields never leave this service — a cashier sees sell prices and stock, not
what the shop paid.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from decimal import Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.repositories.branch import BranchRepository
from app.repositories.category import CategoryRepository
from app.repositories.product import ProductRepository
from app.repositories.stock_level import StockLevelRepository
from app.utils.pagination import PageParams
from app.utils.text import normalize_code

# Matches the Numeric(12,3) scale the database returns, so an absent level and a
# stored zero read the same to the client.
ZERO = Decimal("0.000")


def stock_status(quantity: Decimal, minimum: Decimal) -> str:
    if quantity <= 0:
        return "out_of_stock"
    if quantity <= minimum:
        return "low_stock"
    return "in_stock"


class PosService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.products = ProductRepository(session)
        self.category_repo = CategoryRepository(session)
        self.branches = BranchRepository(session)
        self.stock = StockLevelRepository(session)

    async def resolve_branch_id(
        self, branch_id: uuid.UUID | None, *, fallback: uuid.UUID | None
    ) -> uuid.UUID:
        """Explicit pick → the cashier's own branch → the first active branch."""
        if branch_id is not None:
            return branch_id
        if fallback is not None:
            return fallback
        branches = await self.branches.list_all()
        if not branches:
            raise NotFoundError("No branch is configured.", code="no_branch")
        return branches[0].id

    async def catalog(
        self,
        params: PageParams,
        *,
        branch_id: uuid.UUID,
        search: str | None = None,
        sku: str | None = None,
        barcode: str | None = None,
        category_id: uuid.UUID | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        products, total = await self.products.list_products(
            params,
            search=search,
            sku=normalize_code(sku) if sku else None,
            barcode=normalize_code(barcode) if barcode else None,
            category_id=category_id,
            is_active=True,
        )

        quantities = await self.stock.quantities_for_products(
            [product.id for product in products], branch_id
        )

        items = [
            {
                "id": product.id,
                "name": product.name,
                "sku": product.sku,
                "barcode": product.barcode,
                "unit": product.unit,
                "selling_price": product.selling_price,
                "discount_price": product.discount_price,
                "image_url": product.image_url,
                "category_id": product.category_id,
                "stock_quantity": quantities.get(product.id, ZERO),
                "stock_status": stock_status(
                    quantities.get(product.id, ZERO), product.minimum_stock
                ),
            }
            for product in products
        ]
        return items, total

    async def stock_for(
        self, branch_id: uuid.UUID, product_ids: Sequence[uuid.UUID]
    ) -> list[dict[str, Any]]:
        """Current on-hand per product at one branch (a missing level is zero).

        Drives the till's cart cap and its re-sync on a branch switch.
        """
        ids = list(dict.fromkeys(product_ids))
        if not ids:
            return []

        products = await self.products.list_by_ids(ids)
        minimums = {product.id: product.minimum_stock for product in products}
        quantities = await self.stock.quantities_for_products(ids, branch_id)

        return [
            {
                "product_id": product_id,
                "stock_quantity": quantities.get(product_id, ZERO),
                "stock_status": stock_status(
                    quantities.get(product_id, ZERO), minimums.get(product_id, ZERO)
                ),
            }
            for product_id in ids
        ]

    async def categories(self) -> list[dict[str, Any]]:
        rows: Sequence[tuple[Any, int]] = await self.category_repo.list_with_product_counts()
        return [
            {
                "id": category.id,
                "name": category.name,
                "slug": category.slug,
                "product_count": count,
            }
            for category, count in rows
        ]
