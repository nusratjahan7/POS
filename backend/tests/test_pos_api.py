"""POS catalogue: what the till may see, and what it must never see."""

from __future__ import annotations

import uuid
from typing import Any

from httpx import AsyncClient

PRODUCTS = "/api/v1/products"
CATEGORIES = "/api/v1/categories"
POS_CATALOG = "/api/v1/pos/catalog"
POS_CATEGORIES = "/api/v1/pos/categories"
POS_STOCK = "/api/v1/pos/stock"


async def _product(
    client: AsyncClient, headers: dict[str, str], **overrides: Any
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "name": "Beans",
        "sku": "BEAN-1",
        "purchase_price": "4.00",
        "selling_price": "9.99",
        "minimum_stock": "5",
        "opening_stock": "24",
    }
    payload.update(overrides)
    response = await client.post(PRODUCTS, headers=headers, json=payload)
    assert response.status_code == 201, response.text
    return response.json()


async def test_a_cashier_can_load_the_till_catalogue(
    client: AsyncClient, auth_headers: dict[str, str], cashier_headers: dict[str, str], seeded: Any
) -> None:
    await _product(client, auth_headers)

    response = await client.get(POS_CATALOG, headers=cashier_headers)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total"] == 1
    item = body["items"][0]
    assert item["name"] == "Beans"
    assert item["selling_price"] == "9.99"


async def test_the_till_catalogue_never_exposes_cost(
    client: AsyncClient, auth_headers: dict[str, str], cashier_headers: dict[str, str]
) -> None:
    await _product(client, auth_headers, purchase_price="4.00")

    item = (await client.get(POS_CATALOG, headers=cashier_headers)).json()["items"][0]

    assert "purchase_price" not in item
    assert "4.00" not in item.values()


async def test_search_covers_name_sku_and_barcode(
    client: AsyncClient, auth_headers: dict[str, str], cashier_headers: dict[str, str]
) -> None:
    await _product(client, auth_headers, name="Arabica Beans", sku="ARB-1", barcode="111111")
    await _product(client, auth_headers, name="Robusta", sku="ROB-9", barcode="222222")

    async def total(**params: Any) -> int:
        response = await client.get(POS_CATALOG, headers=cashier_headers, params=params)
        assert response.status_code == 200, response.text
        return int(response.json()["total"])

    assert await total(search="arabica") == 1  # name
    assert await total(search="ROB-9") == 1  # sku
    assert await total(search="222222") == 1  # barcode
    assert await total(barcode="111111") == 1  # scanner-exact
    assert await total(sku="arb-1") == 1  # normalised


async def test_stock_is_reported_for_the_selected_branch(
    client: AsyncClient, auth_headers: dict[str, str], cashier_headers: dict[str, str], seeded: Any
) -> None:
    await _product(client, auth_headers, opening_stock="24", minimum_stock="5")
    await _product(
        client, auth_headers, name="Sold Out", sku="OUT-1", opening_stock="0", minimum_stock="5"
    )

    items = (
        await client.get(
            POS_CATALOG, headers=cashier_headers, params={"branch_id": str(seeded.branch.id)}
        )
    ).json()["items"]
    by_sku = {item["sku"]: item for item in items}

    assert by_sku["BEAN-1"]["stock_quantity"] == "24.000"
    assert by_sku["BEAN-1"]["stock_status"] == "in_stock"
    assert by_sku["OUT-1"]["stock_quantity"] == "0.000"
    assert by_sku["OUT-1"]["stock_status"] == "out_of_stock"


async def test_the_catalogue_can_be_filtered_by_category(
    client: AsyncClient, auth_headers: dict[str, str], cashier_headers: dict[str, str]
) -> None:
    coffee = (await client.post(CATEGORIES, headers=auth_headers, json={"name": "Coffee"})).json()
    await _product(client, auth_headers, name="Filtered", category_id=coffee["id"])
    await _product(client, auth_headers, name="Loose", sku="LOOSE-1")

    body = (
        await client.get(POS_CATALOG, headers=cashier_headers, params={"category_id": coffee["id"]})
    ).json()

    assert body["total"] == 1
    assert body["items"][0]["name"] == "Filtered"


async def test_inactive_products_are_hidden_from_the_till(
    client: AsyncClient, auth_headers: dict[str, str], cashier_headers: dict[str, str]
) -> None:
    created = await _product(client, auth_headers)
    await client.patch(
        f"{PRODUCTS}/{created['id']}", headers=auth_headers, json={"is_active": False}
    )

    assert (await client.get(POS_CATALOG, headers=cashier_headers)).json()["total"] == 0


async def test_till_categories_expose_product_counts(
    client: AsyncClient, auth_headers: dict[str, str], cashier_headers: dict[str, str]
) -> None:
    coffee = (await client.post(CATEGORIES, headers=auth_headers, json={"name": "Coffee"})).json()
    await _product(client, auth_headers, category_id=coffee["id"])

    rows = (await client.get(POS_CATEGORIES, headers=cashier_headers)).json()

    assert len(rows) == 1
    assert rows[0]["name"] == "Coffee"
    assert rows[0]["product_count"] == 1


async def test_the_till_needs_a_sales_permission(
    client: AsyncClient, inventory_manager_headers: dict[str, str]
) -> None:
    for path in (POS_CATALOG, POS_STOCK):
        response = await client.get(path, headers=inventory_manager_headers)
        assert response.status_code == 403, path
        assert response.json()["error"]["code"] == "insufficient_permissions"


async def test_the_till_requires_authentication(client: AsyncClient) -> None:
    for path in (POS_CATALOG, POS_CATEGORIES, POS_STOCK):
        response = await client.get(path)
        assert response.status_code == 401, path


# ---------------------------------------------------------------------------
# Stock for a set of products (the cart cap)
# ---------------------------------------------------------------------------
async def test_stock_is_returned_per_product_for_a_branch(
    client: AsyncClient, auth_headers: dict[str, str], cashier_headers: dict[str, str], seeded: Any
) -> None:
    stocked = await _product(client, auth_headers, name="Stocked", sku="STK-1", opening_stock="10")
    empty = await _product(client, auth_headers, name="Empty", sku="EMP-1", opening_stock="0")

    response = await client.get(
        POS_STOCK,
        headers=cashier_headers,
        params=[
            ("branch_id", str(seeded.branch.id)),
            ("ids", stocked["id"]),
            ("ids", empty["id"]),
        ],
    )
    assert response.status_code == 200, response.text

    rows = {row["product_id"]: row for row in response.json()}
    assert rows[stocked["id"]]["stock_quantity"] == "10.000"
    assert rows[stocked["id"]]["stock_status"] == "in_stock"
    assert rows[empty["id"]]["stock_quantity"] == "0.000"
    assert rows[empty["id"]]["stock_status"] == "out_of_stock"


async def test_stock_for_an_unknown_product_is_zero(
    client: AsyncClient, cashier_headers: dict[str, str]
) -> None:
    response = await client.get(
        POS_STOCK, headers=cashier_headers, params=[("ids", str(uuid.uuid4()))]
    )

    assert response.status_code == 200
    assert response.json()[0]["stock_quantity"] == "0.000"
