"""Inventory: the stock ledger, its invariants and its authorization.

The point of this module is that stock is never changed without a movement, and
that concurrent movement is safe. These tests assert the arithmetic chain
(previous -> new), the guards, the aggregate cache, and the views.
"""

from __future__ import annotations

import uuid
from typing import Any

from httpx import AsyncClient

PRODUCTS = "/api/v1/products"
STOCK = "/api/v1/inventory/stock"
SUMMARY = "/api/v1/inventory/stock/summary"
MOVEMENTS = "/api/v1/inventory/movements"


async def _product(
    client: AsyncClient, headers: dict[str, str], **overrides: Any
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "name": "Beans",
        "sku": "BEAN-1",
        "unit": "kg",
        "minimum_stock": "5",
        "opening_stock": "0",
        "purchase_price": "1.00",
        "selling_price": "2.00",
    }
    payload.update(overrides)
    response = await client.post(PRODUCTS, headers=headers, json=payload)
    assert response.status_code == 201, response.text
    return response.json()


async def _move(
    client: AsyncClient,
    headers: dict[str, str],
    product_id: Any,
    branch_id: Any,
    **overrides: Any,
) -> Any:
    payload: dict[str, Any] = {
        "product_id": str(product_id),
        "branch_id": str(branch_id),
        "movement_type": "stock_in",
        "quantity": "1",
    }
    payload.update(overrides)
    return await client.post(MOVEMENTS, headers=headers, json=payload)


# ---------------------------------------------------------------------------
# The ledger
# ---------------------------------------------------------------------------
async def test_opening_stock_is_recorded_as_a_movement(
    client: AsyncClient, auth_headers: dict[str, str], seeded: Any
) -> None:
    product = await _product(client, auth_headers, opening_stock="24")

    body = (
        await client.get(MOVEMENTS, headers=auth_headers, params={"product_id": product["id"]})
    ).json()

    assert body["total"] == 1
    movement = body["items"][0]
    assert movement["movement_type"] == "opening"
    assert movement["reference_type"] == "opening"
    assert movement["quantity"] == "24.000"
    assert movement["previous_stock"] == "0.000"
    assert movement["new_stock"] == "24.000"
    assert movement["branch"]["id"] == str(seeded.branch.id)
    assert movement["user"]["full_name"] == "Test Administrator"


async def test_stock_in_and_out_chain_previous_to_new(
    client: AsyncClient, auth_headers: dict[str, str], seeded: Any
) -> None:
    product = await _product(client, auth_headers, opening_stock="24")

    stock_in = await _move(
        client,
        auth_headers,
        product["id"],
        seeded.branch.id,
        movement_type="stock_in",
        quantity="10",
    )
    assert stock_in.status_code == 201, stock_in.text
    assert stock_in.json()["previous_stock"] == "24.000"
    assert stock_in.json()["new_stock"] == "34.000"

    stock_out = await _move(
        client,
        auth_headers,
        product["id"],
        seeded.branch.id,
        movement_type="stock_out",
        quantity="-5",
    )
    assert stock_out.json()["previous_stock"] == "34.000"
    assert stock_out.json()["new_stock"] == "29.000"

    # The aggregate cache on the product tracks the ledger.
    refreshed = (await client.get(f"{PRODUCTS}/{product['id']}", headers=auth_headers)).json()
    assert refreshed["stock_quantity"] == "29.000"


async def test_damage_reduces_stock(
    client: AsyncClient, auth_headers: dict[str, str], seeded: Any
) -> None:
    product = await _product(client, auth_headers, opening_stock="10")

    response = await _move(
        client, auth_headers, product["id"], seeded.branch.id, movement_type="damage", quantity="-3"
    )

    assert response.status_code == 201, response.text
    assert response.json()["new_stock"] == "7.000"


async def test_adjustment_can_raise_and_lower_stock(
    client: AsyncClient, auth_headers: dict[str, str], seeded: Any
) -> None:
    product = await _product(client, auth_headers, opening_stock="10")

    up = await _move(
        client,
        auth_headers,
        product["id"],
        seeded.branch.id,
        movement_type="adjustment",
        quantity="5",
    )
    down = await _move(
        client,
        auth_headers,
        product["id"],
        seeded.branch.id,
        movement_type="adjustment",
        quantity="-2",
    )

    assert up.json()["new_stock"] == "15.000"
    assert down.json()["new_stock"] == "13.000"


# ---------------------------------------------------------------------------
# Guards
# ---------------------------------------------------------------------------
async def test_stock_cannot_go_below_zero(
    client: AsyncClient, auth_headers: dict[str, str], seeded: Any
) -> None:
    product = await _product(client, auth_headers, opening_stock="2")

    response = await _move(
        client,
        auth_headers,
        product["id"],
        seeded.branch.id,
        movement_type="stock_out",
        quantity="-5",
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "insufficient_stock"


async def test_the_sign_must_match_the_movement_type(
    client: AsyncClient, auth_headers: dict[str, str], seeded: Any
) -> None:
    product = await _product(client, auth_headers, opening_stock="10")

    wrong_in = await _move(
        client,
        auth_headers,
        product["id"],
        seeded.branch.id,
        movement_type="stock_in",
        quantity="-5",
    )
    wrong_out = await _move(
        client,
        auth_headers,
        product["id"],
        seeded.branch.id,
        movement_type="stock_out",
        quantity="5",
    )

    assert wrong_in.status_code == 422
    assert wrong_out.status_code == 422
    assert wrong_in.json()["error"]["code"] == "validation_error"


async def test_a_zero_quantity_is_rejected(
    client: AsyncClient, auth_headers: dict[str, str], seeded: Any
) -> None:
    product = await _product(client, auth_headers, opening_stock="10")

    response = await _move(
        client,
        auth_headers,
        product["id"],
        seeded.branch.id,
        movement_type="adjustment",
        quantity="0",
    )

    assert response.status_code == 422


async def test_unknown_product_or_branch_is_not_found(
    client: AsyncClient, auth_headers: dict[str, str], seeded: Any
) -> None:
    product = await _product(client, auth_headers, opening_stock="1")

    missing_product = await _move(client, auth_headers, uuid.uuid4(), seeded.branch.id)
    missing_branch = await _move(client, auth_headers, product["id"], uuid.uuid4())

    assert missing_product.status_code == 404
    assert missing_product.json()["error"]["code"] == "product_not_found"
    assert missing_branch.status_code == 404
    assert missing_branch.json()["error"]["code"] == "branch_not_found"


# ---------------------------------------------------------------------------
# Views: stock list, status filters, summary, history
# ---------------------------------------------------------------------------
async def _three_levels(client: AsyncClient, headers: dict[str, str]) -> None:
    await _product(
        client, headers, name="Plenty", sku="PLENTY", opening_stock="20", minimum_stock="5"
    )
    await _product(
        client, headers, name="Scarce", sku="SCARCE", opening_stock="3", minimum_stock="5"
    )
    await _product(client, headers, name="Gone", sku="GONE", opening_stock="0", minimum_stock="5")


async def test_stock_list_and_status_filters(
    client: AsyncClient, auth_headers: dict[str, str], seeded: Any
) -> None:
    await _three_levels(client, auth_headers)

    async def total(**params: Any) -> int:
        response = await client.get(STOCK, headers=auth_headers, params=params)
        assert response.status_code == 200, response.text
        return int(response.json()["total"])

    assert await total() == 3
    assert await total(status="in_stock") == 1
    assert await total(status="low_stock") == 1
    assert await total(status="out_of_stock") == 1
    assert await total(search="scarce") == 1  # by name
    assert await total(search="GONE") == 1  # by sku
    assert await total(branch_id=str(seeded.branch.id)) == 3


async def test_stock_list_reports_status_and_low_flag(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    await _three_levels(client, auth_headers)

    body = (await client.get(STOCK, headers=auth_headers, params={"status": "low_stock"})).json()
    level = body["items"][0]

    assert level["product"]["name"] == "Scarce"
    assert level["quantity"] == "3.000"
    assert level["stock_status"] == "low_stock"
    assert level["is_low_stock"] is True


async def test_summary_counts_the_views(client: AsyncClient, auth_headers: dict[str, str]) -> None:
    await _three_levels(client, auth_headers)

    body = (await client.get(SUMMARY, headers=auth_headers)).json()

    assert body["total_levels"] == 3
    assert body["in_stock"] == 1
    assert body["low_stock"] == 1
    assert body["out_of_stock"] == 1


async def test_movement_history_filters(
    client: AsyncClient, auth_headers: dict[str, str], seeded: Any
) -> None:
    product = await _product(client, auth_headers, name="Beans", sku="BEAN-1", opening_stock="10")
    await _move(
        client,
        auth_headers,
        product["id"],
        seeded.branch.id,
        movement_type="stock_in",
        quantity="5",
    )
    await _move(
        client,
        auth_headers,
        product["id"],
        seeded.branch.id,
        movement_type="stock_out",
        quantity="-2",
    )

    async def total(**params: Any) -> int:
        response = await client.get(MOVEMENTS, headers=auth_headers, params=params)
        return int(response.json()["total"])

    assert await total() == 3
    assert await total(movement_type="opening") == 1
    assert await total(movement_type="stock_out") == 1
    assert await total(search="BEAN-1") == 3
    assert await total(sort="-quantity") == 3


# ---------------------------------------------------------------------------
# Authorization
# ---------------------------------------------------------------------------
async def test_inventory_endpoints_require_authentication(client: AsyncClient) -> None:
    for path in (STOCK, SUMMARY, MOVEMENTS):
        response = await client.get(path)
        assert response.status_code == 401, path
        assert response.json()["error"]["code"] == "unauthorized"


async def test_cashier_can_view_but_not_move_stock(
    client: AsyncClient, auth_headers: dict[str, str], cashier_headers: dict[str, str], seeded: Any
) -> None:
    product = await _product(client, auth_headers, opening_stock="10")

    assert (await client.get(STOCK, headers=cashier_headers)).status_code == 200

    denied = await _move(
        client,
        cashier_headers,
        product["id"],
        seeded.branch.id,
        movement_type="stock_in",
        quantity="1",
    )
    assert denied.status_code == 403
    assert denied.json()["error"]["code"] == "insufficient_permissions"


async def test_inventory_manager_can_adjust_stock(
    client: AsyncClient,
    auth_headers: dict[str, str],
    inventory_manager_headers: dict[str, str],
    seeded: Any,
) -> None:
    product = await _product(client, auth_headers, opening_stock="10")

    response = await _move(
        client,
        inventory_manager_headers,
        product["id"],
        seeded.branch.id,
        movement_type="stock_in",
        quantity="4",
    )

    assert response.status_code == 201, response.text
    assert response.json()["new_stock"] == "14.000"
