"""MODULE 14 — sales returns and refunds.

The rules worth protecting: you cannot return more than was sold (or more than
remains after earlier returns), a line refunds its own net but the sale never
gives back more than it was worth, the refund clears debt before cash, and the
whole thing is one transaction.
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any

from httpx import AsyncClient

PRODUCTS = "/api/v1/products"
SALES = "/api/v1/sales"
CUSTOMERS = "/api/v1/customers"
POS_STOCK = "/api/v1/pos/stock"
MOVEMENTS = "/api/v1/inventory/movements"
REGISTER_SESSIONS = "/api/v1/register-sessions"


async def _ensure_session(
    client: AsyncClient, headers: dict[str, str], seeded: Any
) -> None:
    """Sales need an open till; open the seeded register once per test."""
    register_id = str(seeded.register.id)
    current = await client.get(
        f"{REGISTER_SESSIONS}/current",
        headers=headers,
        params={"register_id": register_id},
    )
    if current.status_code == 200 and current.json() is None:
        opened = await client.post(
            REGISTER_SESSIONS,
            headers=headers,
            json={"register_id": register_id, "opening_cash": "0"},
        )
        assert opened.status_code == 201, opened.text


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


def _cash(payment_methods: dict[str, Any], amount: str, **extra: Any) -> dict[str, Any]:
    return {"payment_method_id": str(payment_methods["CASH"].id), "amount": amount, **extra}


async def _sale(
    client: AsyncClient,
    headers: dict[str, str],
    seeded: Any,
    *,
    price: str = "2.00",
    quantity: str = "3",
    opening: str = "10",
    pay: str | None = None,
    customer_id: str | None = None,
    order_discount: str | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Ring up a one-line sale and return ``(product, sale)``."""
    product = await _product(client, headers, selling_price=price, opening_stock=opening)
    amount = pay or str(Decimal(price) * Decimal(quantity) - Decimal(order_discount or "0"))
    body: dict[str, Any] = {
        "branch_id": str(seeded.branch.id),
        "register_id": str(seeded.register.id),
        "items": [{"product_id": product["id"], "quantity": quantity}],
        "payments": [_cash(seeded.payment_methods, amount)],
    }
    if customer_id is not None:
        body["customer_id"] = customer_id
    if order_discount is not None:
        body["order_discount"] = order_discount

    await _ensure_session(client, headers, seeded)
    response = await client.post(SALES, headers=headers, json=body)
    assert response.status_code == 201, response.text
    return product, response.json()


async def _return(
    client: AsyncClient,
    headers: dict[str, str],
    sale_id: str,
    items: list[dict[str, Any]],
    **extra: Any,
) -> Any:
    return await client.post(
        f"{SALES}/{sale_id}/returns", headers=headers, json={"items": items, **extra}
    )


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


async def _balance(client: AsyncClient, headers: dict[str, str], customer_id: str) -> str:
    response = await client.get(f"{CUSTOMERS}/{customer_id}", headers=headers)
    assert response.status_code == 200, response.text
    return str(response.json()["balance"])


# ---------------------------------------------------------------------------
# The happy path
# ---------------------------------------------------------------------------
async def test_a_partial_return_restocks_and_refunds_the_line_net(
    client: AsyncClient, auth_headers: dict[str, str], seeded: Any
) -> None:
    product, sale = await _sale(client, auth_headers, seeded)
    assert await _stock(client, auth_headers, seeded.branch.id, product["id"]) == "7.000"

    response = await _return(
        client,
        auth_headers,
        sale["id"],
        [{"sale_item_id": sale["items"][0]["id"], "quantity": "1"}],
        reason="Damaged",
        payment_method_id=str(seeded.payment_methods["CASH"].id),
    )

    assert response.status_code == 201, response.text
    record = response.json()
    assert record["status"] == "completed"
    assert record["return_number"].startswith("RET-")
    assert record["reason"] == "Damaged"
    assert record["refund_amount"] == "2.00"  # one unit of a 2.00 line
    assert record["cash_refund"] == "2.00"
    assert record["credit_reversed"] == "0.00"
    assert record["items"][0]["quantity"] == "1.000"
    assert record["items"][0]["line_total"] == "2.00"
    assert record["completed_by"]["full_name"] == "Test Administrator"

    # The unit is back on the shelf, with a ledger row that says why.
    assert await _stock(client, auth_headers, seeded.branch.id, product["id"]) == "8.000"
    movements = await client.get(
        MOVEMENTS, headers=auth_headers, params={"product_id": product["id"]}
    )
    rows = [row for row in movements.json()["items"] if row["reference_id"] == record["id"]]
    assert len(rows) == 1
    assert rows[0]["movement_type"] == "return"
    assert rows[0]["reference_type"] == "sale_return"
    assert rows[0]["quantity"] == "1.000"

    # The sale keeps its own figures and records what came back.
    refreshed = (await client.get(f"{SALES}/{sale['id']}", headers=auth_headers)).json()
    assert refreshed["returned_amount"] == "2.00"
    assert refreshed["status"] == "completed"


async def test_a_return_cannot_exceed_what_is_still_returnable(
    client: AsyncClient, auth_headers: dict[str, str], seeded: Any
) -> None:
    product, sale = await _sale(client, auth_headers, seeded)
    sale_item_id = sale["items"][0]["id"]

    too_many = await _return(
        client, auth_headers, sale["id"], [{"sale_item_id": sale_item_id, "quantity": "4"}]
    )
    assert too_many.status_code == 422, too_many.text
    assert too_many.json()["error"]["code"] == "return_quantity_exceeds_sold"
    # Nothing moved.
    assert await _stock(client, auth_headers, seeded.branch.id, product["id"]) == "7.000"

    first = await _return(
        client,
        auth_headers,
        sale["id"],
        [{"sale_item_id": sale_item_id, "quantity": "2"}],
        payment_method_id=str(seeded.payment_methods["CASH"].id),
    )
    assert first.status_code == 201, first.text

    # Only one unit is left returnable now.
    again = await _return(
        client, auth_headers, sale["id"], [{"sale_item_id": sale_item_id, "quantity": "2"}]
    )
    assert again.status_code == 422, again.text
    assert again.json()["error"]["code"] == "return_quantity_exceeds_sold"


async def test_returning_everything_marks_the_sale_refunded(
    client: AsyncClient, auth_headers: dict[str, str], seeded: Any
) -> None:
    _product_row, sale = await _sale(client, auth_headers, seeded)

    response = await _return(
        client,
        auth_headers,
        sale["id"],
        [{"sale_item_id": sale["items"][0]["id"], "quantity": "3"}],
        payment_method_id=str(seeded.payment_methods["CASH"].id),
    )

    assert response.status_code == 201, response.text
    assert response.json()["refund_amount"] == "6.00"

    refreshed = (await client.get(f"{SALES}/{sale['id']}", headers=auth_headers)).json()
    assert refreshed["status"] == "refunded"
    assert refreshed["returned_amount"] == "6.00"
    assert refreshed["refunded_at"] is not None

    # A refunded sale is closed to further returns.
    again = await _return(
        client,
        auth_headers,
        sale["id"],
        [{"sale_item_id": sale["items"][0]["id"], "quantity": "1"}],
    )
    assert again.status_code == 409, again.text
    assert again.json()["error"]["code"] == "sale_not_returnable"


# ---------------------------------------------------------------------------
# Money
# ---------------------------------------------------------------------------
async def test_a_refund_clears_what_the_customer_still_owes_before_cash(
    client: AsyncClient, auth_headers: dict[str, str], seeded: Any
) -> None:
    customer = await _customer(client, auth_headers, name="Credit Customer")
    _product_row, sale = await _sale(
        client, auth_headers, seeded, pay="2.00", customer_id=customer["id"]
    )
    assert await _balance(client, auth_headers, customer["id"]) == "4.00"

    response = await _return(
        client,
        auth_headers,
        sale["id"],
        [{"sale_item_id": sale["items"][0]["id"], "quantity": "3"}],
        payment_method_id=str(seeded.payment_methods["CASH"].id),
    )

    assert response.status_code == 201, response.text
    record = response.json()
    assert record["refund_amount"] == "6.00"
    # 4.00 of it cleared the debt; only 2.00 went back over the counter.
    assert record["credit_reversed"] == "4.00"
    assert record["cash_refund"] == "2.00"
    assert await _balance(client, auth_headers, customer["id"]) == "0.00"


async def test_a_paid_out_refund_must_say_how_it_is_settled(
    client: AsyncClient, auth_headers: dict[str, str], seeded: Any
) -> None:
    product, sale = await _sale(client, auth_headers, seeded)

    response = await _return(
        client,
        auth_headers,
        sale["id"],
        [{"sale_item_id": sale["items"][0]["id"], "quantity": "1"}],
    )

    assert response.status_code == 422, response.text
    assert response.json()["error"]["code"] == "refund_method_required"
    # Rejected before anything moved.
    assert await _stock(client, auth_headers, seeded.branch.id, product["id"]) == "7.000"


async def test_a_refund_is_capped_at_what_the_sale_was_worth(
    client: AsyncClient, auth_headers: dict[str, str], seeded: Any
) -> None:
    """An order discount means the lines' nets exceed the total — the cap holds."""
    _product_row, sale = await _sale(
        client, auth_headers, seeded, price="10.00", quantity="2", order_discount="5.00"
    )
    assert sale["total"] == "15.00"

    response = await _return(
        client,
        auth_headers,
        sale["id"],
        [{"sale_item_id": sale["items"][0]["id"], "quantity": "2"}],
        payment_method_id=str(seeded.payment_methods["CASH"].id),
    )

    assert response.status_code == 201, response.text
    assert response.json()["refund_amount"] == "15.00"

    refreshed = (await client.get(f"{SALES}/{sale['id']}", headers=auth_headers)).json()
    assert refreshed["returned_amount"] == "15.00"
    assert refreshed["status"] == "refunded"


# ---------------------------------------------------------------------------
# Validation and access
# ---------------------------------------------------------------------------
async def test_a_line_cannot_appear_twice_and_must_belong_to_the_sale(
    client: AsyncClient, auth_headers: dict[str, str], seeded: Any
) -> None:
    _product_row, sale = await _sale(client, auth_headers, seeded)
    sale_item_id = sale["items"][0]["id"]

    duplicate = await _return(
        client,
        auth_headers,
        sale["id"],
        [
            {"sale_item_id": sale_item_id, "quantity": "1"},
            {"sale_item_id": sale_item_id, "quantity": "1"},
        ],
    )
    assert duplicate.status_code == 422, duplicate.text
    assert duplicate.json()["error"]["code"] == "duplicate_return_item"

    unknown = await _return(
        client,
        auth_headers,
        sale["id"],
        [{"sale_item_id": str(uuid.uuid4()), "quantity": "1"}],
    )
    assert unknown.status_code == 422, unknown.text
    assert unknown.json()["error"]["code"] == "unknown_sale_item"


async def test_the_return_history_lists_every_return(
    client: AsyncClient, auth_headers: dict[str, str], seeded: Any
) -> None:
    _product_row, sale = await _sale(client, auth_headers, seeded)
    sale_item_id = sale["items"][0]["id"]

    for quantity in ("1", "1"):
        created = await _return(
            client,
            auth_headers,
            sale["id"],
            [{"sale_item_id": sale_item_id, "quantity": quantity}],
            payment_method_id=str(seeded.payment_methods["CASH"].id),
        )
        assert created.status_code == 201, created.text

    history = await client.get(f"{SALES}/{sale['id']}/returns", headers=auth_headers)

    assert history.status_code == 200, history.text
    records = history.json()
    assert len(records) == 2
    assert all(record["refund_amount"] == "2.00" for record in records)


async def test_a_completed_return_cannot_be_cancelled(
    client: AsyncClient, auth_headers: dict[str, str], seeded: Any
) -> None:
    _product_row, sale = await _sale(client, auth_headers, seeded)
    created = await _return(
        client,
        auth_headers,
        sale["id"],
        [{"sale_item_id": sale["items"][0]["id"], "quantity": "1"}],
        payment_method_id=str(seeded.payment_methods["CASH"].id),
    )
    return_id = created.json()["id"]

    response = await client.post(
        f"{SALES}/{sale['id']}/returns/{return_id}/cancel", headers=auth_headers
    )

    assert response.status_code == 409, response.text
    assert response.json()["error"]["code"] == "return_not_cancellable"


async def test_returning_needs_the_refund_permission(
    client: AsyncClient,
    auth_headers: dict[str, str],
    cashier_headers: dict[str, str],
    seeded: Any,
) -> None:
    product = await _product(client, auth_headers, selling_price="2.00", opening_stock="5")
    await _ensure_session(client, cashier_headers, seeded)
    created = await client.post(
        SALES,
        headers=cashier_headers,
        json={
            "branch_id": str(seeded.branch.id),
            "register_id": str(seeded.register.id),
            "items": [{"product_id": product["id"], "quantity": "1"}],
            "payments": [_cash(seeded.payment_methods, "2.00")],
        },
    )
    assert created.status_code == 201, created.text
    sale = created.json()

    forbidden = await _return(
        client,
        cashier_headers,
        sale["id"],
        [{"sale_item_id": sale["items"][0]["id"], "quantity": "1"}],
    )

    assert forbidden.status_code == 403, forbidden.text
    assert forbidden.json()["error"]["code"] == "insufficient_permissions"
    assert await _stock(client, auth_headers, seeded.branch.id, product["id"]) == "4.000"
