"""Product endpoints.

Searching supports three entry points, because staff reach a product three
different ways: free text, a typed SKU, or a scanned barcode. All three are
filter parameters on the collection, so one code path serves the product list
and the till.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import CurrentUser, Pagination, SessionDep, require_permissions
from app.core.permissions import PermissionCode
from app.repositories.product import ProductRepository
from app.schemas.common import Page
from app.schemas.product import ProductCreate, ProductOption, ProductRead, ProductUpdate
from app.services.product import ProductService
from app.utils.sorting import parse_sort

router = APIRouter(prefix="/products", tags=["products"])


@router.get(
    "",
    response_model=Page[ProductRead],
    dependencies=[Depends(require_permissions(PermissionCode.CATALOG_READ))],
)
async def list_products(
    session: SessionDep,
    params: Pagination,
    search: Annotated[str | None, Query(max_length=120, description="Name, SKU or barcode")] = None,
    sku: Annotated[str | None, Query(max_length=64, description="Exact SKU match")] = None,
    barcode: Annotated[str | None, Query(max_length=64, description="Exact barcode match")] = None,
    category_id: Annotated[uuid.UUID | None, Query()] = None,
    brand_id: Annotated[uuid.UUID | None, Query()] = None,
    is_active: Annotated[bool | None, Query()] = None,
    sort: Annotated[str | None, Query(description="e.g. name, -created_at, selling_price")] = None,
) -> Page[ProductRead]:
    products, total = await ProductService(session).list_products(
        params,
        sort=parse_sort(sort, ProductRepository.SORTABLE, default="name"),
        search=search,
        sku=sku,
        barcode=barcode,
        category_id=category_id,
        brand_id=brand_id,
        is_active=is_active,
    )
    return Page.build(
        [ProductRead.model_validate(product) for product in products],
        total=total,
        page=params.page,
        page_size=params.page_size,
    )


@router.get(
    "/options",
    response_model=list[ProductOption],
    dependencies=[Depends(require_permissions(PermissionCode.CATALOG_READ))],
)
async def product_options(session: SessionDep) -> list[ProductOption]:
    """Lightweight active-only list for pickers (e.g. stock adjustments)."""
    products = await ProductService(session).list_options()
    return [ProductOption.model_validate(product) for product in products]


@router.post(
    "",
    response_model=ProductRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permissions(PermissionCode.CATALOG_WRITE))],
)
async def create_product(
    session: SessionDep, actor: CurrentUser, payload: ProductCreate
) -> ProductRead:
    return ProductRead.model_validate(
        await ProductService(session).create(payload, actor_id=actor.id)
    )


@router.get(
    "/{product_id}",
    response_model=ProductRead,
    dependencies=[Depends(require_permissions(PermissionCode.CATALOG_READ))],
)
async def get_product(session: SessionDep, product_id: uuid.UUID) -> ProductRead:
    return ProductRead.model_validate(await ProductService(session).get_or_404(product_id))


@router.patch(
    "/{product_id}",
    response_model=ProductRead,
    dependencies=[Depends(require_permissions(PermissionCode.CATALOG_WRITE))],
)
async def update_product(
    session: SessionDep, product_id: uuid.UUID, payload: ProductUpdate
) -> ProductRead:
    return ProductRead.model_validate(await ProductService(session).update(product_id, payload))


@router.delete(
    "/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permissions(PermissionCode.CATALOG_DELETE))],
)
async def delete_product(session: SessionDep, product_id: uuid.UUID) -> None:
    await ProductService(session).delete(product_id)
