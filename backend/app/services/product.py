"""Product management.

Money handling rule: prices are ``Decimal`` from the schema layer down to
``Numeric`` columns. They are never converted to ``float`` anywhere in this
module, so no rounding error can creep into a stored price.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import ConflictError, NotFoundError, UnprocessableError
from app.models.branch import Branch
from app.models.product import Product
from app.repositories.branch import BranchRepository
from app.repositories.brand import BrandRepository
from app.repositories.category import CategoryRepository
from app.repositories.product import ProductRepository
from app.schemas.product import ProductCreate, ProductUpdate
from app.services.inventory import InventoryService
from app.utils.pagination import PageParams
from app.utils.text import normalize_code, slugify

SLUG_MAX_LENGTH = 200


class ProductService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.products = ProductRepository(session)
        self.categories = CategoryRepository(session)
        self.brands = BrandRepository(session)
        self.branches = BranchRepository(session)

    async def get_or_404(self, product_id: uuid.UUID) -> Product:
        product = await self.products.get(product_id)
        if product is None or product.is_deleted:
            raise NotFoundError("Product not found.", code="product_not_found")
        return product

    async def list_products(
        self,
        params: PageParams,
        *,
        sort: tuple[Any, bool] | None = None,
        **filters: Any,
    ) -> tuple[Sequence[Product], int]:
        if filters.get("sku"):
            filters["sku"] = normalize_code(filters["sku"])
        if filters.get("barcode"):
            filters["barcode"] = normalize_code(filters["barcode"])
        return await self.products.list_products(params, sort=sort, **filters)

    async def list_options(self) -> Sequence[Product]:
        return await self.products.list_all(active_only=True)

    # --- Internals ---------------------------------------------------------
    async def _primary_branch(self) -> Branch | None:
        """Where a new product's opening stock lands in a single-branch setup.

        Multi-branch stock is managed per branch through the inventory module;
        product creation has no branch context, so it seeds the default one.
        """
        branches = await self.branches.list_all()
        return branches[0] if branches else None

    async def _reload(self, product_id: uuid.UUID) -> Product:
        """Re-read a product after a write.

        Two reasons this exists rather than returning the in-memory instance:

        * ``Numeric`` columns come back at their stored scale (``24`` becomes
          ``24.000``), so the response matches what was persisted;
        * ``category``/``brand`` are eager-loaded here, so serialising the
          response never triggers a lazy load outside the greenlet context.
        """
        stmt = (
            select(Product)
            .where(Product.id == product_id)
            .options(selectinload(Product.category), selectinload(Product.brand))
            .execution_options(populate_existing=True)
        )
        return (await self.session.execute(stmt)).scalars().one()

    async def _unique_slug(self, name: str, *, exclude_id: uuid.UUID | None = None) -> str:
        base = slugify(name, max_length=SLUG_MAX_LENGTH)
        candidate, suffix = base, 2
        while await self.products.slug_exists(candidate, exclude_id=exclude_id):
            candidate = f"{base}-{suffix}"
            suffix += 1
        return candidate

    async def _assert_sku_free(self, sku: str, *, exclude_id: uuid.UUID | None = None) -> None:
        if await self.products.sku_exists(sku, exclude_id=exclude_id):
            raise ConflictError(
                "A product with that SKU already exists.",
                code="sku_taken",
                details=[{"field": "sku", "message": "Already in use."}],
            )

    async def _assert_barcode_free(
        self, barcode: str, *, exclude_id: uuid.UUID | None = None
    ) -> None:
        if await self.products.barcode_exists(barcode, exclude_id=exclude_id):
            raise ConflictError(
                "A product with that barcode already exists.",
                code="barcode_taken",
                details=[{"field": "barcode", "message": "Already in use."}],
            )

    async def _resolve_category(self, category_id: uuid.UUID | None) -> None:
        if category_id is None:
            return
        category = await self.categories.get(category_id)
        if category is None or category.is_deleted:
            raise UnprocessableError(
                "The selected category does not exist.",
                code="unknown_category",
                details=[{"field": "category_id", "message": "Unknown category."}],
            )

    async def _resolve_brand(self, brand_id: uuid.UUID | None) -> None:
        if brand_id is None:
            return
        brand = await self.brands.get(brand_id)
        if brand is None or brand.is_deleted:
            raise UnprocessableError(
                "The selected brand does not exist.",
                code="unknown_brand",
                details=[{"field": "brand_id", "message": "Unknown brand."}],
            )

    @staticmethod
    def _assert_discount_valid(selling: Decimal, discount: Decimal | None) -> None:
        if discount is not None and discount > selling:
            raise UnprocessableError(
                "The discount price cannot exceed the selling price.",
                code="invalid_discount_price",
                details=[
                    {"field": "discount_price", "message": "Must not exceed the selling price."}
                ],
            )

    # --- Commands ----------------------------------------------------------
    async def create(self, payload: ProductCreate, *, actor_id: uuid.UUID | None = None) -> Product:
        sku = normalize_code(payload.sku)
        barcode = normalize_code(payload.barcode) if payload.barcode else None

        await self._assert_sku_free(sku)
        if barcode:
            await self._assert_barcode_free(barcode)
        await self._resolve_category(payload.category_id)
        await self._resolve_brand(payload.brand_id)

        product = Product(
            name=payload.name.strip(),
            slug=await self._unique_slug(payload.name),
            sku=sku,
            barcode=barcode,
            category_id=payload.category_id,
            brand_id=payload.brand_id,
            purchase_price=payload.purchase_price,
            selling_price=payload.selling_price,
            discount_price=payload.discount_price,
            unit=payload.unit.strip(),
            minimum_stock=payload.minimum_stock,
            # Stock starts at zero. Opening stock is applied by the inventory
            # service below, so it is never a direct write to a stock field.
            stock_quantity=Decimal("0"),
            description=payload.description,
            image_url=payload.image_url,
            is_active=payload.is_active,
        )
        await self.products.add(product)

        branch = await self._primary_branch()
        if branch is not None:
            inventory = InventoryService(self.session)
            if payload.opening_stock > 0:
                # A movement, exactly like every other stock change. Commits here.
                await inventory.set_opening_stock(
                    product_id=product.id,
                    branch_id=branch.id,
                    quantity=payload.opening_stock,
                    user_id=actor_id,
                )
            else:
                # Still give it a zero level so it shows in the inventory table.
                await inventory.ensure_level(product_id=product.id, branch_id=branch.id)
        else:
            await self.session.commit()

        return await self._reload(product.id)

    async def update(self, product_id: uuid.UUID, payload: ProductUpdate) -> Product:
        product = await self.get_or_404(product_id)
        provided = payload.model_fields_set

        if payload.name is not None:
            name = payload.name.strip()
            if name.lower() != product.name.lower():
                product.name = name
                product.slug = await self._unique_slug(name, exclude_id=product.id)

        if payload.sku is not None:
            sku = normalize_code(payload.sku)
            if sku != product.sku:
                await self._assert_sku_free(sku, exclude_id=product.id)
                product.sku = sku

        if "barcode" in provided:
            barcode = normalize_code(payload.barcode) if payload.barcode else None
            if barcode != product.barcode:
                if barcode:
                    await self._assert_barcode_free(barcode, exclude_id=product.id)
                product.barcode = barcode

        if "category_id" in provided:
            await self._resolve_category(payload.category_id)
            product.category_id = payload.category_id
        if "brand_id" in provided:
            await self._resolve_brand(payload.brand_id)
            product.brand_id = payload.brand_id

        if payload.purchase_price is not None:
            product.purchase_price = payload.purchase_price
        if payload.selling_price is not None:
            product.selling_price = payload.selling_price
        if "discount_price" in provided:
            product.discount_price = payload.discount_price

        # Validated against the merged state, not just the request body.
        self._assert_discount_valid(product.selling_price, product.discount_price)

        if payload.unit is not None:
            product.unit = payload.unit.strip()
        if payload.minimum_stock is not None:
            product.minimum_stock = payload.minimum_stock
        if "description" in provided:
            product.description = payload.description
        if "image_url" in provided:
            product.image_url = payload.image_url
        if payload.is_active is not None:
            product.is_active = payload.is_active

        await self.session.commit()
        return await self._reload(product.id)

    async def delete(self, product_id: uuid.UUID) -> None:
        """Soft delete: historical sales must still resolve the product later."""
        product = await self.get_or_404(product_id)
        product.is_active = False
        product.deleted_at = datetime.now(UTC)
        await self.session.commit()
