"""Sales: server-side pricing, tendering, and the all-or-nothing transaction."""

from __future__ import annotations

from typing import Any

from httpx import AsyncClient

PRODUCTS = "/api/v1/products"
SALES = "/api/v1/sales"
CUSTOMERS = "/api/v1/customers"
BUSINESS = "/api/v1/business"
POS_STOCK = "/api/v1/pos/stock"
MOVEMENTS = "/api/v1/inventory/movements"
REGISTERS = "/api/v1/registers"
SESSIONS = "/api/v1/register-sessions"


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


async def _customer(
    client: AsyncClient, headers: dict[str, str], **overrides: Any
) -> dict[str, Any]:
    payload: dict[str, Any] = {"name": "Jane Doe"}
    payload.update(overrides)
    response = await client.post(CUSTOMERS, headers=headers, json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def _sale_body(
    branch_id: Any,
    items: list[dict[str, Any]],
    payments: list[dict[str, Any]],
    **overrides: Any,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "branch_id": str(branch_id),
        "items": items,
        "payments": payments,
    }
    payload.update(overrides)
    return payload


async def _register_with_session(
    client: AsyncClient, headers: dict[str, str], branch_id: Any
) -> str:
    """The branch's first register, opened — a sale now needs an open till."""
    options = await client.get(
        f"{REGISTERS}/options", headers=headers, params={"branch_id": str(branch_id)}
    )
    assert options.status_code == 200, options.text
    register_id = str(options.json()[0]["id"])

    current = await client.get(
        f"{SESSIONS}/current", headers=headers, params={"register_id": register_id}
    )
    if current.status_code == 200 and current.json() is None:
        opened = await client.post(
            SESSIONS,
            headers=headers,
            json={"register_id": register_id, "opening_cash": "0"},
        )
        assert opened.status_code == 201, opened.text
    return register_id


async def _sell(
    client: AsyncClient,
    headers: dict[str, str],
    branch_id: Any,
    items: list[dict[str, Any]],
    payments: list[dict[str, Any]],
    **overrides: Any,
) -> Any:
    register_id = await _register_with_session(client, headers, branch_id)
    body = _sale_body(branch_id, items, payments, **overrides)
    body.setdefault("register_id", register_id)
    return await client.post(SALES, headers=headers, json=body)


async def _stock(
    client: AsyncClient, headers: dict[str, str], branch_id: Any, product_id: Any
) -> str:
    response = await client.get(
        POS_STOCK,
        headers=headers,
        params=[("branch_id", str(branch_id)), ("ids", str(product_id))],
    )
    assert response.status_code == 200, response.text
    return str(response.json()[0]["stock_quantity"])


async def _sale_count(client: AsyncClient, headers: dict[str, str]) -> int:
    response = await client.get(SALES, headers=headers)
    assert response.status_code == 200, response.text
    return int(response.json()["total"])


def _cash(payment_methods: dict[str, Any], amount: str, **extra: Any) -> dict[str, Any]:
    return {"payment_method_id": str(payment_methods["CASH"].id), "amount": amount, **extra}


# ---------------------------------------------------------------------------
# Pricing is the server's job
# ---------------------------------------------------------------------------
async def test_a_cash_sale_prices_itself_and_takes_stock(
    client: AsyncClient, auth_headers: dict[str, str], seeded: Any
) -> None:
    product = await _product(
        client, auth_headers, name="Beans", sku="BEAN-1", selling_price="2.00", opening_stock="10"
    )

    response = await _sell(
        client,
        auth_headers,
        seeded.branch.id,
        items=[{"product_id": product["id"], "quantity": "3"}],
        payments=[_cash(seeded.payment_methods, "6.00")],
    )

    assert response.status_code == 201, response.text
    sale = response.json()
    assert sale["sale_number"].startswith("INV-")
    assert sale["subtotal"] == "6.00"
    assert sale["total"] == "6.00"
    assert sale["paid"] == "6.00"
    assert sale["due"] == "0.00"
    assert sale["change_amount"] == "0.00"
    assert sale["status"] == "completed"
    assert sale["items"][0]["unit_price"] == "2.00"
    assert sale["items"][0]["line_total"] == "6.00"
    assert sale["payments"][0]["amount"] == "6.00"

    # The stock left the branch, and the ledger says why.
    assert await _stock(client, auth_headers, seeded.branch.id, product["id"]) == "7.000"
    movements = await client.get(
        MOVEMENTS, headers=auth_headers, params={"product_id": product["id"]}
    )
    assert movements.status_code == 200, movements.text
    sale_movements = [row for row in movements.json()["items"] if row["reference_id"] == sale["id"]]
    assert len(sale_movements) == 1
    movement = sale_movements[0]
    assert movement["movement_type"] == "stock_out"
    assert movement["reference_type"] == "sale"
    assert movement["quantity"] == "-3.000"
    assert movement["previous_stock"] == "10.000"
    assert movement["new_stock"] == "7.000"


async def test_prices_come_from_the_database_not_the_client(
    client: AsyncClient, auth_headers: dict[str, str], seeded: Any
) -> None:
    # A discount price is in force; the till's idea of the price is irrelevant.
    product = await _product(
        client,
        auth_headers,
        name="Beans",
        sku="BEAN-1",
        selling_price="2.00",
        discount_price="1.50",
        opening_stock="10",
    )

    response = await _sell(
        client,
        auth_headers,
        seeded.branch.id,
        items=[
            {
                "product_id": product["id"],
                "quantity": "4",
                # Ignored: the schema takes no price from the client at all.
                "unit_price": "0.01",
                "line_total": "0.04",
            }
        ],
        payments=[_cash(seeded.payment_methods, "6.00")],
    )

    assert response.status_code == 201, response.text
    sale = response.json()
    assert sale["items"][0]["unit_price"] == "1.50"
    assert sale["total"] == "6.00"


async def test_tax_and_discount_are_computed_server_side(
    client: AsyncClient, auth_headers: dict[str, str], seeded: Any
) -> None:
    await client.patch(
        BUSINESS,
        headers=auth_headers,
        json={"tax_enabled": True, "tax_inclusive": False, "default_tax_rate": "10"},
    )
    product = await _product(
        client, auth_headers, name="Beans", sku="BEAN-1", selling_price="10.00", opening_stock="5"
    )

    response = await _sell(
        client,
        auth_headers,
        seeded.branch.id,
        items=[{"product_id": product["id"], "quantity": "2", "discount": "4.00"}],
        payments=[_cash(seeded.payment_methods, "16.50")],
        order_discount="1.00",
    )

    assert response.status_code == 201, response.text
    sale = response.json()
    assert sale["subtotal"] == "20.00"
    assert sale["discount"] == "5.00"  # 4.00 line + 1.00 order
    assert sale["tax"] == "1.50"  # 10% of the 15.00 net
    assert sale["total"] == "16.50"


# ---------------------------------------------------------------------------
# Payment: change, partial, due, mixed
# ---------------------------------------------------------------------------
async def test_cash_over_the_total_is_returned_as_change(
    client: AsyncClient, auth_headers: dict[str, str], seeded: Any
) -> None:
    product = await _product(client, auth_headers, selling_price="2.00", opening_stock="5")

    response = await _sell(
        client,
        auth_headers,
        seeded.branch.id,
        items=[{"product_id": product["id"], "quantity": "3"}],
        payments=[_cash(seeded.payment_methods, "6.00", tendered="10.00")],
    )

    assert response.status_code == 201, response.text
    sale = response.json()
    # Only what is owed counts as paid; the rest went back over the counter.
    assert sale["paid"] == "6.00"
    assert sale["due"] == "0.00"
    assert sale["change_amount"] == "4.00"
    # What the customer actually handed over, not what was applied.
    assert sale["received_amount"] == "10.00"
    assert sale["payments"][0]["tendered"] == "10.00"
    assert sale["payments"][0]["change_given"] == "4.00"


async def test_a_partial_payment_puts_the_balance_on_the_customer(
    client: AsyncClient, auth_headers: dict[str, str], seeded: Any
) -> None:
    product = await _product(client, auth_headers, selling_price="2.00", opening_stock="5")
    customer = await _customer(client, auth_headers, name="Credit Customer")

    response = await _sell(
        client,
        auth_headers,
        seeded.branch.id,
        items=[{"product_id": product["id"], "quantity": "3"}],
        payments=[_cash(seeded.payment_methods, "2.00")],
        customer_id=customer["id"],
    )

    assert response.status_code == 201, response.text
    sale = response.json()
    assert sale["total"] == "6.00"
    assert sale["paid"] == "2.00"
    assert sale["due"] == "4.00"

    refreshed = await client.get(f"{CUSTOMERS}/{customer['id']}", headers=auth_headers)
    assert refreshed.json()["balance"] == "4.00"


async def test_an_unpaid_balance_needs_a_customer(
    client: AsyncClient, auth_headers: dict[str, str], seeded: Any
) -> None:
    product = await _product(client, auth_headers, selling_price="2.00", opening_stock="5")
    before = await _sale_count(client, auth_headers)

    response = await _sell(
        client,
        auth_headers,
        seeded.branch.id,
        items=[{"product_id": product["id"], "quantity": "3"}],
        payments=[_cash(seeded.payment_methods, "2.00")],
    )

    assert response.status_code == 422, response.text
    assert response.json()["error"]["code"] == "credit_sale_requires_customer"
    assert await _sale_count(client, auth_headers) == before
    assert await _stock(client, auth_headers, seeded.branch.id, product["id"]) == "5.000"


async def test_a_sale_can_be_split_across_several_methods(
    client: AsyncClient, auth_headers: dict[str, str], seeded: Any
) -> None:
    product = await _product(client, auth_headers, selling_price="10.00", opening_stock="5")

    response = await _sell(
        client,
        auth_headers,
        seeded.branch.id,
        items=[{"product_id": product["id"], "quantity": "1"}],
        payments=[
            _cash(seeded.payment_methods, "4.00"),
            {
                "payment_method_id": str(seeded.payment_methods["CARD"].id),
                "amount": "6.00",
                "reference": "AUTH-123456",
            },
        ],
    )

    assert response.status_code == 201, response.text
    sale = response.json()
    assert sale["total"] == "10.00"
    assert sale["paid"] == "10.00"
    assert sale["due"] == "0.00"
    assert len(sale["payments"]) == 2
    assert {payment["amount"] for payment in sale["payments"]} == {"4.00", "6.00"}


async def test_a_reference_is_required_where_the_method_demands_one(
    client: AsyncClient, auth_headers: dict[str, str], seeded: Any
) -> None:
    product = await _product(client, auth_headers, selling_price="10.00", opening_stock="5")

    response = await _sell(
        client,
        auth_headers,
        seeded.branch.id,
        items=[{"product_id": product["id"], "quantity": "1"}],
        payments=[{"payment_method_id": str(seeded.payment_methods["CARD"].id), "amount": "10.00"}],
    )

    assert response.status_code == 422, response.text
    assert response.json()["error"]["code"] == "payment_reference_required"


async def test_payments_cannot_exceed_the_total(
    client: AsyncClient, auth_headers: dict[str, str], seeded: Any
) -> None:
    product = await _product(client, auth_headers, selling_price="10.00", opening_stock="5")

    response = await _sell(
        client,
        auth_headers,
        seeded.branch.id,
        items=[{"product_id": product["id"], "quantity": "1"}],
        payments=[_cash(seeded.payment_methods, "15.00")],
    )

    assert response.status_code == 422, response.text
    assert response.json()["error"]["code"] == "payments_exceed_total"


# ---------------------------------------------------------------------------
# Stock and atomicity
# ---------------------------------------------------------------------------
async def test_a_sale_cannot_take_more_than_the_branch_holds(
    client: AsyncClient, auth_headers: dict[str, str], seeded: Any
) -> None:
    product = await _product(client, auth_headers, selling_price="2.00", opening_stock="2")
    before = await _sale_count(client, auth_headers)

    response = await _sell(
        client,
        auth_headers,
        seeded.branch.id,
        items=[{"product_id": product["id"], "quantity": "3"}],
        payments=[_cash(seeded.payment_methods, "6.00")],
    )

    assert response.status_code == 422, response.text
    assert response.json()["error"]["code"] == "insufficient_stock"
    # Nothing at all was written.
    assert await _sale_count(client, auth_headers) == before
    assert await _stock(client, auth_headers, seeded.branch.id, product["id"]) == "2.000"


async def test_a_failed_sale_rolls_back_the_lines_that_already_succeeded(
    client: AsyncClient, auth_headers: dict[str, str], seeded: Any
) -> None:
    """The second line is short; the first must not keep its decrement."""
    ok = await _product(
        client, auth_headers, name="Rice", sku="RICE-1", selling_price="5.00", opening_stock="10"
    )
    short = await _product(
        client, auth_headers, name="Oil", sku="OIL-1", selling_price="5.00", opening_stock="1"
    )
    before = await _sale_count(client, auth_headers)

    response = await _sell(
        client,
        auth_headers,
        seeded.branch.id,
        items=[
            {"product_id": ok["id"], "quantity": "4"},
            {"product_id": short["id"], "quantity": "5"},
        ],
        payments=[_cash(seeded.payment_methods, "45.00")],
    )

    assert response.status_code == 422, response.text
    assert response.json()["error"]["code"] == "insufficient_stock"

    assert await _sale_count(client, auth_headers) == before
    assert await _stock(client, auth_headers, seeded.branch.id, ok["id"]) == "10.000"
    assert await _stock(client, auth_headers, seeded.branch.id, short["id"]) == "1.000"


async def test_the_same_product_cannot_appear_twice(
    client: AsyncClient, auth_headers: dict[str, str], seeded: Any
) -> None:
    product = await _product(client, auth_headers, selling_price="2.00", opening_stock="10")

    response = await _sell(
        client,
        auth_headers,
        seeded.branch.id,
        items=[
            {"product_id": product["id"], "quantity": "1"},
            {"product_id": product["id"], "quantity": "1"},
        ],
        payments=[_cash(seeded.payment_methods, "4.00")],
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "duplicate_sale_item"


# ---------------------------------------------------------------------------
# Reads, receipt and access
# ---------------------------------------------------------------------------
async def test_the_receipt_bundles_the_sale_and_the_business(
    client: AsyncClient, auth_headers: dict[str, str], seeded: Any
) -> None:
    product = await _product(
        client, auth_headers, name="Beans", selling_price="2.00", opening_stock="5"
    )
    created = await _sell(
        client,
        auth_headers,
        seeded.branch.id,
        items=[{"product_id": product["id"], "quantity": "1"}],
        payments=[_cash(seeded.payment_methods, "2.00")],
    )
    sale_id = created.json()["id"]

    response = await client.get(f"{SALES}/{sale_id}/receipt", headers=auth_headers)

    assert response.status_code == 200, response.text
    receipt = response.json()
    assert receipt["sale"]["id"] == sale_id
    assert receipt["sale"]["items"][0]["product_name"] == "Beans"
    assert receipt["business"]["name"]
    assert receipt["business"]["currency"]
    # The branch travels with its contact details so a receipt can print them.
    assert receipt["branch"]["id"] == str(seeded.branch.id)
    assert receipt["branch"]["name"] == seeded.branch.name
    assert "address" in receipt["branch"]
    assert "phone" in receipt["branch"]


async def test_customer_details_now_show_their_sales(
    client: AsyncClient, auth_headers: dict[str, str], seeded: Any
) -> None:
    product = await _product(client, auth_headers, selling_price="2.00", opening_stock="5")
    customer = await _customer(client, auth_headers, name="Repeat Buyer")

    await _sell(
        client,
        auth_headers,
        seeded.branch.id,
        items=[{"product_id": product["id"], "quantity": "2"}],
        payments=[_cash(seeded.payment_methods, "4.00")],
        customer_id=customer["id"],
    )

    response = await client.get(f"{CUSTOMERS}/{customer['id']}/details", headers=auth_headers)

    assert response.status_code == 200, response.text
    details = response.json()
    assert details["total_orders"] == 1
    assert details["total_purchase_amount"] == "4.00"
    assert details["recent_purchases"][0]["reference"].startswith("INV-")


async def test_a_cashier_can_ring_up_a_sale(
    client: AsyncClient, auth_headers: dict[str, str], cashier_headers: dict[str, str], seeded: Any
) -> None:
    product = await _product(client, auth_headers, selling_price="2.00", opening_stock="5")

    response = await _sell(
        client,
        cashier_headers,
        seeded.branch.id,
        items=[{"product_id": product["id"], "quantity": "1"}],
        payments=[_cash(seeded.payment_methods, "2.00")],
    )

    assert response.status_code == 201, response.text


async def test_the_sale_endpoints_need_the_right_permission(
    client: AsyncClient, anon_client: AsyncClient, inventory_manager_headers: dict[str, str]
) -> None:
    assert (await client.get(SALES)).status_code == 401
    assert (await anon_client.post(SALES, json={})).status_code == 401

    forbidden = await client.get(SALES, headers=inventory_manager_headers)
    assert forbidden.status_code == 403
    assert forbidden.json()["error"]["code"] == "insufficient_permissions"


# ---------------------------------------------------------------------------
# MODULE 13 — management list: item count, filtering and sorting
# ---------------------------------------------------------------------------
async def test_the_list_reports_item_count_and_filters_by_payment_status(
    client: AsyncClient, auth_headers: dict[str, str], seeded: Any
) -> None:
    beans = await _product(
        client, auth_headers, name="Beans", sku="BEAN-1", selling_price="2.00", opening_stock="20"
    )
    rice = await _product(
        client, auth_headers, name="Rice", sku="RICE-1", selling_price="1.00", opening_stock="20"
    )
    customer = await _customer(client, auth_headers, name="Credit Customer")

    settled = await _sell(
        client,
        auth_headers,
        seeded.branch.id,
        items=[
            {"product_id": beans["id"], "quantity": "1"},
            {"product_id": rice["id"], "quantity": "1"},
        ],
        payments=[_cash(seeded.payment_methods, "3.00")],
    )
    on_account = await _sell(
        client,
        auth_headers,
        seeded.branch.id,
        items=[{"product_id": beans["id"], "quantity": "3"}],
        payments=[_cash(seeded.payment_methods, "2.00")],
        customer_id=customer["id"],
    )
    assert settled.status_code == 201 and on_account.status_code == 201
    settled_id = settled.json()["id"]
    on_account_id = on_account.json()["id"]

    listed = await client.get(SALES, headers=auth_headers)
    rows = {row["id"]: row for row in listed.json()["items"]}
    assert rows[settled_id]["item_count"] == 2
    assert rows[on_account_id]["item_count"] == 1

    partial = await client.get(SALES, headers=auth_headers, params={"payment_status": "partial"})
    assert [row["id"] for row in partial.json()["items"]] == [on_account_id]

    paid = await client.get(SALES, headers=auth_headers, params={"payment_status": "paid"})
    paid_ids = [row["id"] for row in paid.json()["items"]]
    assert settled_id in paid_ids
    assert on_account_id not in paid_ids


async def test_the_list_searches_by_invoice_and_sorts(
    client: AsyncClient, auth_headers: dict[str, str], seeded: Any
) -> None:
    product = await _product(
        client, auth_headers, name="Beans", sku="BEAN-1", selling_price="1.00", opening_stock="50"
    )

    small = (
        await _sell(
            client,
            auth_headers,
            seeded.branch.id,
            items=[{"product_id": product["id"], "quantity": "1"}],
            payments=[_cash(seeded.payment_methods, "1.00")],
        )
    ).json()
    big = (
        await _sell(
            client,
            auth_headers,
            seeded.branch.id,
            items=[{"product_id": product["id"], "quantity": "10"}],
            payments=[_cash(seeded.payment_methods, "10.00")],
        )
    ).json()

    found = await client.get(SALES, headers=auth_headers, params={"search": small["sale_number"]})
    assert [row["id"] for row in found.json()["items"]] == [small["id"]]

    by_total = await client.get(SALES, headers=auth_headers, params={"sort": "-total"})
    assert by_total.json()["items"][0]["id"] == big["id"]


async def test_the_filter_lists_only_cashiers_who_have_sales(
    client: AsyncClient,
    auth_headers: dict[str, str],
    superuser: Any,
    seeded: Any,
) -> None:
    product = await _product(client, auth_headers, selling_price="2.00", opening_stock="5")
    await _sell(
        client,
        auth_headers,
        seeded.branch.id,
        items=[{"product_id": product["id"], "quantity": "1"}],
        payments=[_cash(seeded.payment_methods, "2.00")],
    )

    response = await client.get(f"{SALES}/cashiers", headers=auth_headers)

    assert response.status_code == 200, response.text
    assert response.json() == [{"id": str(superuser.id), "full_name": "Test Administrator"}]
