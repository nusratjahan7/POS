"""Suppliers and purchases — especially the atomic receive operation."""

from __future__ import annotations

from typing import Any

from httpx import AsyncClient

PRODUCTS = "/api/v1/products"
INVENTORY = "/api/v1/inventory"
SUPPLIERS = "/api/v1/suppliers"
PURCHASES = "/api/v1/purchases"


async def _product(
    client: AsyncClient, headers: dict[str, str], **overrides: Any
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "name": "Beans",
        "sku": "BEAN-1",
        "minimum_stock": "0",
        "opening_stock": "0",
        "purchase_price": "1.00",
        "selling_price": "2.00",
    }
    payload.update(overrides)
    response = await client.post(PRODUCTS, headers=headers, json=payload)
    assert response.status_code == 201, response.text
    return response.json()


async def _supplier(
    client: AsyncClient, headers: dict[str, str], **overrides: Any
) -> dict[str, Any]:
    payload: dict[str, Any] = {"name": "Acme Supply"}
    payload.update(overrides)
    response = await client.post(SUPPLIERS, headers=headers, json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def _purchase_body(
    supplier_id: Any, branch_id: Any, items: list[dict[str, Any]], **overrides: Any
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "supplier_id": str(supplier_id),
        "branch_id": str(branch_id),
        "purchase_date": "2026-09-27",
        "items": items,
    }
    payload.update(overrides)
    return payload


async def _purchase(
    client: AsyncClient,
    headers: dict[str, str],
    supplier_id: Any,
    branch_id: Any,
    items: list[dict[str, Any]],
    **overrides: Any,
) -> dict[str, Any]:
    response = await client.post(
        PURCHASES, headers=headers, json=_purchase_body(supplier_id, branch_id, items, **overrides)
    )
    assert response.status_code == 201, response.text
    return response.json()


def _line(product_id: Any, quantity: str = "10", unit_price: str = "5.00") -> dict[str, Any]:
    return {"product_id": str(product_id), "quantity": quantity, "unit_price": unit_price}


# ---------------------------------------------------------------------------
# Suppliers
# ---------------------------------------------------------------------------
async def test_supplier_balance_starts_at_the_opening_balance(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    supplier = await _supplier(client, auth_headers, opening_balance="100.00")

    assert supplier["opening_balance"] == "100.00"
    assert supplier["balance"] == "100.00"


async def test_supplier_names_are_unique(client: AsyncClient, auth_headers: dict[str, str]) -> None:
    await _supplier(client, auth_headers, name="Acme")

    duplicate = await client.post(SUPPLIERS, headers=auth_headers, json={"name": "acme"})

    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "supplier_name_taken"


# ---------------------------------------------------------------------------
# Raising a purchase never moves stock
# ---------------------------------------------------------------------------
async def test_creating_a_purchase_computes_totals_without_touching_stock(
    client: AsyncClient, auth_headers: dict[str, str], seeded: Any
) -> None:
    product = await _product(client, auth_headers)
    supplier = await _supplier(client, auth_headers)

    purchase = await _purchase(
        client,
        auth_headers,
        supplier["id"],
        seeded.branch.id,
        [_line(product["id"], quantity="10", unit_price="5.00")],
        discount="2.00",
        tax="1.00",
        paid="20.00",
    )

    assert purchase["status"] == "draft"
    assert purchase["subtotal"] == "50.00"
    assert purchase["total"] == "49.00"  # 50 - 2 + 1
    assert purchase["due"] == "29.00"  # 49 - 20
    assert purchase["items"][0]["subtotal"] == "50.00"
    assert purchase["purchase_number"].startswith("PO-")

    # No stock effect yet.
    refreshed = (await client.get(f"{PRODUCTS}/{product['id']}", headers=auth_headers)).json()
    assert refreshed["stock_quantity"] == "0.000"


# ---------------------------------------------------------------------------
# Receiving — the transactional core
# ---------------------------------------------------------------------------
async def test_receiving_a_purchase_increases_stock_and_records_a_movement(
    client: AsyncClient, auth_headers: dict[str, str], seeded: Any
) -> None:
    product = await _product(client, auth_headers)
    supplier = await _supplier(client, auth_headers)
    purchase = await _purchase(
        client, auth_headers, supplier["id"], seeded.branch.id, [_line(product["id"], "10", "5.00")]
    )

    response = await client.post(f"{PURCHASES}/{purchase['id']}/receive", headers=auth_headers)

    assert response.status_code == 200, response.text
    received = response.json()
    assert received["status"] == "received"
    assert received["received_at"] is not None

    refreshed = (await client.get(f"{PRODUCTS}/{product['id']}", headers=auth_headers)).json()
    assert refreshed["stock_quantity"] == "10.000"

    movements = (
        await client.get(
            INVENTORY + "/movements", headers=auth_headers, params={"product_id": product["id"]}
        )
    ).json()
    assert movements["total"] == 1
    movement = movements["items"][0]
    assert movement["movement_type"] == "stock_in"
    assert movement["reference_type"] == "purchase"
    assert movement["reference_id"] == purchase["id"]
    assert movement["previous_stock"] == "0.000"
    assert movement["new_stock"] == "10.000"

    level = (
        await client.get(INVENTORY + "/stock", headers=auth_headers, params={"search": "BEAN-1"})
    ).json()["items"][0]
    assert level["quantity"] == "10.000"
    assert level["branch"]["id"] == str(seeded.branch.id)


async def test_receiving_updates_the_supplier_balance_by_the_amount_owed(
    client: AsyncClient, auth_headers: dict[str, str], seeded: Any
) -> None:
    product = await _product(client, auth_headers)
    supplier = await _supplier(client, auth_headers, opening_balance="100.00")
    purchase = await _purchase(
        client,
        auth_headers,
        supplier["id"],
        seeded.branch.id,
        [_line(product["id"], "10", "5.00")],
        paid="20.00",
    )

    await client.post(f"{PURCHASES}/{purchase['id']}/receive", headers=auth_headers)

    refreshed = (await client.get(f"{SUPPLIERS}/{supplier['id']}", headers=auth_headers)).json()
    # 100 opening + (50 total - 20 paid) = 130 owed.
    assert refreshed["balance"] == "130.00"


async def test_fully_paid_purchase_leaves_the_balance_unchanged(
    client: AsyncClient, auth_headers: dict[str, str], seeded: Any
) -> None:
    product = await _product(client, auth_headers)
    supplier = await _supplier(client, auth_headers, opening_balance="0")
    purchase = await _purchase(
        client,
        auth_headers,
        supplier["id"],
        seeded.branch.id,
        [_line(product["id"], "4", "5.00")],
        paid="20.00",
    )

    await client.post(f"{PURCHASES}/{purchase['id']}/receive", headers=auth_headers)

    refreshed = (await client.get(f"{SUPPLIERS}/{supplier['id']}", headers=auth_headers)).json()
    assert refreshed["balance"] == "0.00"


async def test_receiving_rolls_back_entirely_when_a_line_cannot_be_applied(
    client: AsyncClient, auth_headers: dict[str, str], seeded: Any
) -> None:
    """A failure mid-receive must leave purchase, stock and balance untouched."""
    product = await _product(client, auth_headers)
    supplier = await _supplier(client, auth_headers, opening_balance="0")
    purchase = await _purchase(
        client, auth_headers, supplier["id"], seeded.branch.id, [_line(product["id"], "10", "5.00")]
    )

    # Remove the product so the inventory step fails inside the transaction.
    assert (
        await client.delete(f"{PRODUCTS}/{product['id']}", headers=auth_headers)
    ).status_code == 204

    failed = await client.post(f"{PURCHASES}/{purchase['id']}/receive", headers=auth_headers)
    assert failed.status_code == 404
    assert failed.json()["error"]["code"] == "product_not_found"

    # Nothing was committed.
    still = (await client.get(f"{PURCHASES}/{purchase['id']}", headers=auth_headers)).json()
    assert still["status"] == "draft"
    assert still["received_at"] is None
    refreshed = (await client.get(f"{SUPPLIERS}/{supplier['id']}", headers=auth_headers)).json()
    assert refreshed["balance"] == "0.00"


async def test_a_purchase_cannot_be_received_twice(
    client: AsyncClient, auth_headers: dict[str, str], seeded: Any
) -> None:
    product = await _product(client, auth_headers)
    supplier = await _supplier(client, auth_headers)
    purchase = await _purchase(
        client, auth_headers, supplier["id"], seeded.branch.id, [_line(product["id"])]
    )
    assert (
        await client.post(f"{PURCHASES}/{purchase['id']}/receive", headers=auth_headers)
    ).status_code == 200

    again = await client.post(f"{PURCHASES}/{purchase['id']}/receive", headers=auth_headers)

    assert again.status_code == 400
    assert again.json()["error"]["code"] == "purchase_not_receivable"


# ---------------------------------------------------------------------------
# Lifecycle guards & validation
# ---------------------------------------------------------------------------
async def test_a_received_purchase_cannot_be_edited_or_cancelled(
    client: AsyncClient, auth_headers: dict[str, str], seeded: Any
) -> None:
    product = await _product(client, auth_headers)
    supplier = await _supplier(client, auth_headers)
    purchase = await _purchase(
        client, auth_headers, supplier["id"], seeded.branch.id, [_line(product["id"])]
    )
    await client.post(f"{PURCHASES}/{purchase['id']}/receive", headers=auth_headers)

    edit = await client.patch(
        f"{PURCHASES}/{purchase['id']}", headers=auth_headers, json={"note": "changed"}
    )
    cancel = await client.post(f"{PURCHASES}/{purchase['id']}/cancel", headers=auth_headers)

    assert edit.status_code == 400
    assert edit.json()["error"]["code"] == "purchase_not_editable"
    assert cancel.status_code == 400
    assert cancel.json()["error"]["code"] == "purchase_not_cancellable"


async def test_a_draft_purchase_can_be_cancelled(
    client: AsyncClient, auth_headers: dict[str, str], seeded: Any
) -> None:
    product = await _product(client, auth_headers)
    supplier = await _supplier(client, auth_headers)
    purchase = await _purchase(
        client, auth_headers, supplier["id"], seeded.branch.id, [_line(product["id"])]
    )

    response = await client.post(f"{PURCHASES}/{purchase['id']}/cancel", headers=auth_headers)

    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"


async def test_discount_cannot_exceed_the_subtotal(
    client: AsyncClient, auth_headers: dict[str, str], seeded: Any
) -> None:
    product = await _product(client, auth_headers)
    supplier = await _supplier(client, auth_headers)

    response = await client.post(
        PURCHASES,
        headers=auth_headers,
        json=_purchase_body(
            supplier["id"], seeded.branch.id, [_line(product["id"], "1", "5.00")], discount="9.00"
        ),
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "discount_exceeds_subtotal"


async def test_paid_cannot_exceed_the_total(
    client: AsyncClient, auth_headers: dict[str, str], seeded: Any
) -> None:
    product = await _product(client, auth_headers)
    supplier = await _supplier(client, auth_headers)

    response = await client.post(
        PURCHASES,
        headers=auth_headers,
        json=_purchase_body(
            supplier["id"], seeded.branch.id, [_line(product["id"], "1", "5.00")], paid="9.00"
        ),
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "paid_exceeds_total"


async def test_the_same_product_cannot_appear_twice(
    client: AsyncClient, auth_headers: dict[str, str], seeded: Any
) -> None:
    product = await _product(client, auth_headers)
    supplier = await _supplier(client, auth_headers)

    response = await client.post(
        PURCHASES,
        headers=auth_headers,
        json=_purchase_body(
            supplier["id"],
            seeded.branch.id,
            [_line(product["id"], "1", "5.00"), _line(product["id"], "2", "5.00")],
        ),
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "duplicate_purchase_item"


# ---------------------------------------------------------------------------
# Listing
# ---------------------------------------------------------------------------
async def test_purchase_list_filters(
    client: AsyncClient, auth_headers: dict[str, str], seeded: Any
) -> None:
    product = await _product(client, auth_headers)
    supplier = await _supplier(client, auth_headers)
    created = await _purchase(
        client, auth_headers, supplier["id"], seeded.branch.id, [_line(product["id"])]
    )
    await client.post(f"{PURCHASES}/{created['id']}/cancel", headers=auth_headers)
    await _purchase(client, auth_headers, supplier["id"], seeded.branch.id, [_line(product["id"])])

    async def total(**params: Any) -> int:
        response = await client.get(PURCHASES, headers=auth_headers, params=params)
        assert response.status_code == 200, response.text
        return int(response.json()["total"])

    assert await total() == 2
    assert await total(status="cancelled") == 1
    assert await total(status="draft") == 1
    assert await total(supplier_id=str(supplier["id"])) == 2
    assert await total(search=created["purchase_number"]) == 1
    assert await total(date_from="2026-09-27", date_to="2026-09-27") == 2


# ---------------------------------------------------------------------------
# Authorization
# ---------------------------------------------------------------------------
async def test_purchase_endpoints_require_authentication(client: AsyncClient) -> None:
    for path in (SUPPLIERS, PURCHASES):
        response = await client.get(path)
        assert response.status_code == 401, path
        assert response.json()["error"]["code"] == "unauthorized"


async def test_cashier_cannot_reach_purchasing(
    client: AsyncClient, cashier_headers: dict[str, str]
) -> None:
    response = await client.get(PURCHASES, headers=cashier_headers)

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "insufficient_permissions"


async def test_inventory_manager_can_manage_suppliers_and_purchases(
    client: AsyncClient,
    auth_headers: dict[str, str],
    inventory_manager_headers: dict[str, str],
    seeded: Any,
) -> None:
    product = await _product(client, auth_headers)
    supplier = await _supplier(client, inventory_manager_headers, name="Manager Supply")
    purchase = await _purchase(
        client,
        inventory_manager_headers,
        supplier["id"],
        seeded.branch.id,
        [_line(product["id"], "3", "4.00")],
    )

    response = await client.post(
        f"{PURCHASES}/{purchase['id']}/receive", headers=inventory_manager_headers
    )

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "received"
