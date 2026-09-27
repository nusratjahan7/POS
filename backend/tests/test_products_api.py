"""Product catalog: money exactness, search/filter/sort, and permissions."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from httpx import AsyncClient

PRODUCTS = "/api/v1/products"
CATEGORIES = "/api/v1/categories"
BRANDS = "/api/v1/brands"
UPLOADS = "/api/v1/uploads/images"


def _product(**overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "name": "Espresso Beans 1kg",
        "sku": "BEAN-1KG",
        "barcode": "8901234567890",
        "purchase_price": "8.50",
        "selling_price": "12.99",
        "unit": "kg",
        "minimum_stock": "5",
        "opening_stock": "24",
    }
    payload.update(overrides)
    return payload


async def _create(client: AsyncClient, headers: dict[str, str], **overrides: Any) -> dict[str, Any]:
    response = await client.post(PRODUCTS, headers=headers, json=_product(**overrides))
    assert response.status_code == 201, response.text
    return response.json()


# ---------------------------------------------------------------------------
# Money
# ---------------------------------------------------------------------------
async def test_prices_round_trip_exactly_as_decimal(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    body = await _create(client, auth_headers)

    # Serialised as a string: a float would be at risk of 12.990000000000002.
    assert body["selling_price"] == "12.99"
    assert body["purchase_price"] == "8.50"
    assert Decimal(body["selling_price"]) == Decimal("12.99")


async def test_awkward_decimal_survives_the_round_trip(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    body = await _create(
        client, auth_headers, sku="ODD-1", selling_price="0.10", purchase_price="0.30"
    )
    fetched = (await client.get(f"{PRODUCTS}/{body['id']}", headers=auth_headers)).json()

    assert fetched["selling_price"] == "0.10"
    assert fetched["purchase_price"] == "0.30"


async def test_discount_price_may_not_exceed_selling_price(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    response = await client.post(
        PRODUCTS, headers=auth_headers, json=_product(discount_price="99.00")
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


async def test_discount_is_validated_against_the_stored_price_on_update(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    created = await _create(client, auth_headers)

    # Sending only the discount can still be wrong once merged with the stored price.
    response = await client.patch(
        f"{PRODUCTS}/{created['id']}", headers=auth_headers, json={"discount_price": "50.00"}
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_discount_price"


# ---------------------------------------------------------------------------
# Uniqueness and normalisation
# ---------------------------------------------------------------------------
async def test_sku_is_normalised_and_unique(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    created = await _create(client, auth_headers, sku="bean-1kg")
    assert created["sku"] == "BEAN-1KG"

    duplicate = await client.post(PRODUCTS, headers=auth_headers, json=_product(name="Other"))
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "sku_taken"


async def test_barcode_must_be_unique(client: AsyncClient, auth_headers: dict[str, str]) -> None:
    await _create(client, auth_headers)

    duplicate = await client.post(
        PRODUCTS, headers=auth_headers, json=_product(name="Other", sku="OTHER-1")
    )

    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "barcode_taken"


async def test_slug_is_generated_and_disambiguated(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    first = await _create(client, auth_headers, name="Café Crème", sku="A1", barcode=None)
    second = await _create(client, auth_headers, name="Café Crème", sku="A2", barcode=None)

    assert first["slug"] == "cafe-creme"
    assert second["slug"] == "cafe-creme-2"


# ---------------------------------------------------------------------------
# Inventory placeholder
# ---------------------------------------------------------------------------
async def test_opening_stock_sets_the_quantity_cache(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    body = await _create(client, auth_headers, opening_stock="24", minimum_stock="5")
    assert body["stock_quantity"] == "24.000"
    assert body["stock_status"] == "in_stock"
    assert body["is_low_stock"] is False


async def test_stock_status_reflects_the_minimum(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    low = await _create(
        client, auth_headers, sku="LOW-1", barcode=None, opening_stock="3", minimum_stock="5"
    )
    out = await _create(
        client, auth_headers, sku="OUT-1", barcode=None, opening_stock="0", minimum_stock="5"
    )

    assert low["stock_status"] == "low_stock"
    assert out["stock_status"] == "out_of_stock"


async def test_stock_cannot_be_set_through_the_update_endpoint(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    created = await _create(client, auth_headers)

    response = await client.patch(
        f"{PRODUCTS}/{created['id']}",
        headers=auth_headers,
        json={"stock_quantity": "999"},
    )

    assert response.status_code == 200
    # Unknown fields are ignored: stock only moves through inventory transactions.
    assert response.json()["stock_quantity"] == created["stock_quantity"]


# ---------------------------------------------------------------------------
# Search, filter, sort, paginate
# ---------------------------------------------------------------------------
async def test_search_covers_name_sku_and_barcode(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    await _create(client, auth_headers, name="Arabica Beans", sku="ARB-1", barcode="111111")
    await _create(client, auth_headers, name="Robusta", sku="ROB-9", barcode="222222")

    async def total_for(term: str) -> int:
        response = await client.get(PRODUCTS, headers=auth_headers, params={"search": term})
        return response.json()["total"]

    assert await total_for("arabica") == 1  # by name
    assert await total_for("ROB-9") == 1  # by SKU
    assert await total_for("222222") == 1  # by barcode
    assert await total_for("beans") == 1
    assert await total_for("nothing-matches") == 0


async def test_exact_sku_and_barcode_lookup(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    await _create(client, auth_headers, name="Arabica Beans", sku="ARB-1", barcode="111111")

    by_sku = await client.get(PRODUCTS, headers=auth_headers, params={"sku": "arb-1"})
    by_barcode = await client.get(PRODUCTS, headers=auth_headers, params={"barcode": "111111"})

    assert by_sku.json()["total"] == 1
    assert by_barcode.json()["total"] == 1


async def test_category_and_brand_filters(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    category = (await client.post(CATEGORIES, headers=auth_headers, json={"name": "Coffee"})).json()
    brand = (await client.post(BRANDS, headers=auth_headers, json={"name": "Lavazza"})).json()

    await _create(
        client, auth_headers, name="Filtered", category_id=category["id"], brand_id=brand["id"]
    )
    await _create(client, auth_headers, name="Unfiltered", sku="UF-1", barcode=None)

    by_category = await client.get(
        PRODUCTS, headers=auth_headers, params={"category_id": category["id"]}
    )
    by_brand = await client.get(PRODUCTS, headers=auth_headers, params={"brand_id": brand["id"]})

    assert by_category.json()["total"] == 1
    assert by_brand.json()["items"][0]["brand"]["name"] == "Lavazza"


async def test_active_filter_and_soft_delete(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    created = await _create(client, auth_headers)
    await client.patch(
        f"{PRODUCTS}/{created['id']}", headers=auth_headers, json={"is_active": False}
    )

    inactive = await client.get(PRODUCTS, headers=auth_headers, params={"is_active": False})
    assert inactive.json()["total"] == 1

    assert (
        await client.delete(f"{PRODUCTS}/{created['id']}", headers=auth_headers)
    ).status_code == 204
    assert (
        await client.get(f"{PRODUCTS}/{created['id']}", headers=auth_headers)
    ).status_code == 404
    assert (await client.get(PRODUCTS, headers=auth_headers)).json()["total"] == 0


async def test_sorting_and_pagination(client: AsyncClient, auth_headers: dict[str, str]) -> None:
    for index, price in enumerate(["30.00", "10.00", "20.00"]):
        await _create(
            client,
            auth_headers,
            name=f"Product {index}",
            sku=f"SORT-{index}",
            barcode=None,
            selling_price=price,
        )

    descending = await client.get(PRODUCTS, headers=auth_headers, params={"sort": "-selling_price"})
    prices = [item["selling_price"] for item in descending.json()["items"]]
    assert prices == ["30.00", "20.00", "10.00"]

    paged = await client.get(PRODUCTS, headers=auth_headers, params={"page_size": 2, "page": 2})
    assert paged.json()["total"] == 3
    assert paged.json()["pages"] == 2
    assert len(paged.json()["items"]) == 1


async def test_unknown_sort_field_is_rejected(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    response = await client.get(PRODUCTS, headers=auth_headers, params={"sort": "password_hash"})

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_sort_field"


async def test_a_deleted_product_frees_its_sku_and_barcode(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    """Soft delete must not reserve the SKU/barcode forever (partial unique index)."""
    created = await _create(client, auth_headers, sku="REUSE-1", barcode="555000555")
    assert (
        await client.delete(f"{PRODUCTS}/{created['id']}", headers=auth_headers)
    ).status_code == 204

    again = await client.post(
        PRODUCTS,
        headers=auth_headers,
        json=_product(name="Reused", sku="REUSE-1", barcode="555000555"),
    )

    assert again.status_code == 201, again.text


async def test_unknown_category_is_rejected(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    response = await client.post(
        PRODUCTS,
        headers=auth_headers,
        json=_product(category_id="00000000-0000-0000-0000-000000000000"),
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "unknown_category"


# ---------------------------------------------------------------------------
# Taxonomy guards
# ---------------------------------------------------------------------------
async def test_category_in_use_cannot_be_deleted(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    category = (await client.post(CATEGORIES, headers=auth_headers, json={"name": "Coffee"})).json()
    await _create(client, auth_headers, category_id=category["id"])

    response = await client.delete(f"{CATEGORIES}/{category['id']}", headers=auth_headers)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "category_in_use"


async def test_category_name_must_be_unique(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    await client.post(CATEGORIES, headers=auth_headers, json={"name": "Coffee"})

    response = await client.post(CATEGORIES, headers=auth_headers, json={"name": "coffee"})

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "category_name_taken"


# ---------------------------------------------------------------------------
# Permissions
# ---------------------------------------------------------------------------
async def test_catalog_endpoints_require_authentication(client: AsyncClient) -> None:
    for path in (PRODUCTS, CATEGORIES, BRANDS):
        assert (await client.get(path)).status_code == 401


async def test_cashier_cannot_read_the_catalog(
    client: AsyncClient, cashier_headers: dict[str, str]
) -> None:
    response = await client.get(PRODUCTS, headers=cashier_headers)

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "insufficient_permissions"


async def test_inventory_manager_can_read_but_not_write(
    client: AsyncClient, inventory_manager_headers: dict[str, str]
) -> None:
    assert (await client.get(PRODUCTS, headers=inventory_manager_headers)).status_code == 200

    denied = await client.post(
        PRODUCTS, headers=inventory_manager_headers, json=_product(sku="IM-1")
    )
    assert denied.status_code == 403
    assert denied.json()["error"]["code"] == "insufficient_permissions"


async def test_deleting_a_product_needs_the_delete_permission(
    client: AsyncClient, login_as: Any, administrator: Any
) -> None:
    """The Administrator role holds catalog:delete; a read-only custom role does not."""
    headers = await login_as(administrator.email, "ManagerPass1!")
    created = await _create(client, headers)

    assert (await client.delete(f"{PRODUCTS}/{created['id']}", headers=headers)).status_code == 204


# ---------------------------------------------------------------------------
# Image upload
# ---------------------------------------------------------------------------
async def test_image_upload_returns_a_site_relative_url(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    png = b"\x89PNG\r\n\x1a\n" + b"0" * 32

    response = await client.post(
        UPLOADS, headers=auth_headers, files={"file": ("photo.png", png, "image/png")}
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["url"].startswith("/media/")
    assert body["url"].endswith(".png")
    # The client filename is never echoed back into the stored path.
    assert "photo" not in body["url"]
    assert body["size"] == len(png)


async def test_non_image_upload_is_rejected(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    response = await client.post(
        UPLOADS,
        headers=auth_headers,
        files={"file": ("payload.svg", b"<svg/>", "image/svg+xml")},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "unsupported_image_type"


async def test_upload_requires_write_permission(
    client: AsyncClient, inventory_manager_headers: dict[str, str]
) -> None:
    response = await client.post(
        UPLOADS,
        headers=inventory_manager_headers,
        files={"file": ("photo.png", b"\x89PNG", "image/png")},
    )

    assert response.status_code == 403
