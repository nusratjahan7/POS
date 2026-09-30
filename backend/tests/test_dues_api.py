"""MODULE 15 — customer and supplier due management (derived ledgers).

The rules worth protecting: the ledger always reconciles with the stored
balance, a supplier payment can never push the payable negative, and the
statement's opening/closing balances follow the requested date range.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from httpx import AsyncClient

PRODUCTS = "/api/v1/products"
SALES = "/api/v1/sales"
CUSTOMERS = "/api/v1/customers"
SUPPLIERS = "/api/v1/suppliers"
PURCHASES = "/api/v1/purchases"
REGISTER_SESSIONS = "/api/v1/register-sessions"


async def _ensure_session(client: AsyncClient, headers: dict[str, str], seeded: Any) -> None:
    """Sales need an open till; open the seeded register once per test."""
    register_id = str(seeded.register.id)
    current = await client.get(
        f"{REGISTER_SESSIONS}/current", headers=headers, params={"register_id": register_id}
    )
    if current.status_code == 200 and current.json() is None:
        opened = await client.post(
            REGISTER_SESSIONS,
            headers=headers,
            json={"register_id": register_id, "opening_cash": "0"},
        )
        assert opened.status_code == 201, opened.text


# ---------------------------------------------------------------------------
# Factories
# ---------------------------------------------------------------------------
async def _product(
    client: AsyncClient, headers: dict[str, str], **overrides: Any
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "name": "Beans",
        "sku": "BEAN-1",
        "minimum_stock": "0",
        "opening_stock": "10",
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


async def _supplier(
    client: AsyncClient, headers: dict[str, str], **overrides: Any
) -> dict[str, Any]:
    payload: dict[str, Any] = {"name": "Acme Supply"}
    payload.update(overrides)
    response = await client.post(SUPPLIERS, headers=headers, json=payload)
    assert response.status_code == 201, response.text
    return response.json()


async def _credit_sale(
    client: AsyncClient,
    headers: dict[str, str],
    seeded: Any,
    customer_id: str,
    *,
    price: str = "2.00",
    quantity: str = "3",
    pay: str = "1.00",
) -> dict[str, Any]:
    """A sale partly carried on the customer's account."""
    product = await _product(client, headers, selling_price=price)
    await _ensure_session(client, headers, seeded)
    response = await client.post(
        SALES,
        headers=headers,
        json={
            "branch_id": str(seeded.branch.id),
            "register_id": str(seeded.register.id),
            "customer_id": customer_id,
            "items": [{"product_id": product["id"], "quantity": quantity}],
            "payments": [
                {"payment_method_id": str(seeded.payment_methods["CASH"].id), "amount": pay}
            ],
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


async def _received_purchase(
    client: AsyncClient, headers: dict[str, str], seeded: Any, supplier_id: str, *, paid: str
) -> dict[str, Any]:
    product = await _product(client, headers, sku="RM-1", opening_stock="0")
    created = await client.post(
        PURCHASES,
        headers=headers,
        json={
            "supplier_id": supplier_id,
            "branch_id": str(seeded.branch.id),
            "purchase_date": "2026-09-27",
            "paid": paid,
            "items": [{"product_id": product["id"], "quantity": "10", "unit_price": "5.00"}],
        },
    )
    assert created.status_code == 201, created.text
    received = await client.post(
        f"{PURCHASES}/{created.json()['id']}/receive", headers=headers
    )
    assert received.status_code == 200, received.text
    return received.json()


async def _balance(client: AsyncClient, headers: dict[str, str], path: str, party_id: str) -> str:
    response = await client.get(f"{path}/{party_id}", headers=headers)
    assert response.status_code == 200, response.text
    return str(response.json()["balance"])


async def _ledger(
    client: AsyncClient, headers: dict[str, str], path: str, party_id: str, **params: Any
) -> dict[str, Any]:
    response = await client.get(f"{path}/{party_id}/ledger", headers=headers, params=params)
    assert response.status_code == 200, response.text
    return response.json()


# ---------------------------------------------------------------------------
# Supplier payments
# ---------------------------------------------------------------------------
async def test_recording_a_supplier_payment_reduces_the_balance(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    supplier = await _supplier(client, auth_headers, opening_balance="100.00")

    response = await client.post(
        f"{SUPPLIERS}/{supplier['id']}/payments",
        headers=auth_headers,
        json={"amount": "40.00", "method": "bank"},
    )

    assert response.status_code == 201, response.text
    payment = response.json()
    assert payment["amount"] == "40.00"
    assert payment["method"] == "bank"
    assert payment["user"]["full_name"] == "Test Administrator"

    assert await _balance(client, auth_headers, SUPPLIERS, supplier["id"]) == "60.00"

    history = await client.get(f"{SUPPLIERS}/{supplier['id']}/payments", headers=auth_headers)
    assert history.status_code == 200
    assert history.json()["total"] == 1


async def test_a_supplier_payment_cannot_exceed_the_balance(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    supplier = await _supplier(client, auth_headers, opening_balance="30.00")

    response = await client.post(
        f"{SUPPLIERS}/{supplier['id']}/payments",
        headers=auth_headers,
        json={"amount": "40.00"},
    )

    assert response.status_code == 422, response.text
    assert response.json()["error"]["code"] == "payment_exceeds_balance"
    # Nothing moved.
    assert await _balance(client, auth_headers, SUPPLIERS, supplier["id"]) == "30.00"
    history = await client.get(f"{SUPPLIERS}/{supplier['id']}/payments", headers=auth_headers)
    assert history.json()["total"] == 0


# ---------------------------------------------------------------------------
# Supplier ledger
# ---------------------------------------------------------------------------
async def test_supplier_ledger_reconciles_with_the_balance(
    client: AsyncClient, auth_headers: dict[str, str], seeded: Any
) -> None:
    supplier = await _supplier(client, auth_headers, opening_balance="0")
    # 50 total, 20 paid on receipt => the payable grows by 30.
    await _received_purchase(client, auth_headers, seeded, supplier["id"], paid="20.00")
    # Then a later payment of 10 => 20 owed.
    await client.post(
        f"{SUPPLIERS}/{supplier['id']}/payments",
        headers=auth_headers,
        json={"amount": "10.00"},
    )

    balance = await _balance(client, auth_headers, SUPPLIERS, supplier["id"])
    assert balance == "20.00"

    statement = await _ledger(client, auth_headers, SUPPLIERS, supplier["id"])

    assert statement["closing_balance"] == balance
    assert statement["opening_balance"] == "0.00"
    entries = statement["entries"]
    assert [entry["entry_type"] for entry in entries] == ["purchase", "payment", "payment"]
    # The purchase raises the payable; the two payments bring it back down.
    assert entries[0]["credit"] == "50.00"  # the whole payable incurred
    assert entries[0]["debit"] == "0.00"
    assert entries[0]["balance"] == "50.00"
    # The two payments share a timestamp, so their order is not asserted.
    assert sorted(entry["debit"] for entry in entries[1:]) == ["10.00", "20.00"]


# ---------------------------------------------------------------------------
# Customer ledger
# ---------------------------------------------------------------------------
async def test_customer_ledger_reconciles_with_the_balance(
    client: AsyncClient, auth_headers: dict[str, str], seeded: Any
) -> None:
    customer = await _customer(client, auth_headers, opening_balance="5.00")
    # 3 x 2.00 = 6.00, 1.00 paid at the till => 5.00 carried; balance 5 + 5 = 10.
    await _credit_sale(client, auth_headers, seeded, customer["id"])
    # Pay 4.00 off the account => 6.00 outstanding.
    await client.post(
        f"{CUSTOMERS}/{customer['id']}/payments",
        headers=auth_headers,
        json={"amount": "4.00", "method": "cash"},
    )

    balance = await _balance(client, auth_headers, CUSTOMERS, customer["id"])
    assert balance == "6.00"

    statement = await _ledger(client, auth_headers, CUSTOMERS, customer["id"])

    assert statement["closing_balance"] == balance
    assert [entry["entry_type"] for entry in statement["entries"]] == [
        "opening",
        "sale",
        "payment",
    ]
    opening, sale, payment = statement["entries"]
    assert opening["debit"] == "5.00"
    assert sale["debit"] == "5.00"  # the amount charged to the account
    assert payment["credit"] == "4.00"


async def test_a_refund_reverses_the_credit_in_the_customer_ledger(
    client: AsyncClient, auth_headers: dict[str, str], seeded: Any
) -> None:
    customer = await _customer(client, auth_headers, opening_balance="0")
    sale = await _credit_sale(client, auth_headers, seeded, customer["id"])
    assert await _balance(client, auth_headers, CUSTOMERS, customer["id"]) == "5.00"

    returned = await client.post(
        f"{SALES}/{sale['id']}/returns",
        headers=auth_headers,
        json={
            "items": [{"sale_item_id": sale["items"][0]["id"], "quantity": "3"}],
            "payment_method_id": str(seeded.payment_methods["CASH"].id),
        },
    )
    assert returned.status_code == 201, returned.text
    assert returned.json()["credit_reversed"] == "5.00"

    balance = await _balance(client, auth_headers, CUSTOMERS, customer["id"])
    assert balance == "0.00"

    statement = await _ledger(client, auth_headers, CUSTOMERS, customer["id"])
    assert statement["closing_balance"] == balance
    assert [entry["entry_type"] for entry in statement["entries"]] == ["sale", "refund"]
    assert statement["entries"][0]["debit"] == "5.00"
    assert statement["entries"][1]["credit"] == "5.00"


# ---------------------------------------------------------------------------
# Date range
# ---------------------------------------------------------------------------
async def test_the_ledger_date_range_carries_the_opening_balance(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    customer = await _customer(client, auth_headers, opening_balance="5.00")
    today = date.today()

    # Everything happened today, so a window starting tomorrow folds it all into
    # the opening balance.
    future = await _ledger(
        client,
        auth_headers,
        CUSTOMERS,
        customer["id"],
        date_from=(today + timedelta(days=1)).isoformat(),
    )
    assert future["opening_balance"] == "5.00"
    assert future["entries"] == []
    assert future["closing_balance"] == "5.00"

    # A window that ended yesterday saw nothing at all.
    past = await _ledger(
        client,
        auth_headers,
        CUSTOMERS,
        customer["id"],
        date_to=(today - timedelta(days=1)).isoformat(),
    )
    assert past["opening_balance"] == "0.00"
    assert past["entries"] == []
    assert past["closing_balance"] == "0.00"


# ---------------------------------------------------------------------------
# Due filters
# ---------------------------------------------------------------------------
async def test_has_dues_returns_only_parties_who_are_owed(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    await _customer(client, auth_headers, name="Settled", opening_balance="0")
    owing = await _customer(client, auth_headers, name="Owing", opening_balance="25.00")
    await _supplier(client, auth_headers, name="Settled Supply", opening_balance="0")
    owed = await _supplier(client, auth_headers, name="Owed Supply", opening_balance="40.00")

    customers = await client.get(
        CUSTOMERS, headers=auth_headers, params={"has_dues": "true"}
    )
    assert customers.status_code == 200
    assert customers.json()["total"] == 1
    assert customers.json()["items"][0]["id"] == owing["id"]

    suppliers = await client.get(
        SUPPLIERS, headers=auth_headers, params={"has_dues": "true"}
    )
    assert suppliers.status_code == 200
    assert suppliers.json()["total"] == 1
    assert suppliers.json()["items"][0]["id"] == owed["id"]


# ---------------------------------------------------------------------------
# Customer purchase history (the previously stubbed endpoint)
# ---------------------------------------------------------------------------
async def test_customer_purchases_list_their_sales(
    client: AsyncClient, auth_headers: dict[str, str], seeded: Any
) -> None:
    customer = await _customer(client, auth_headers)
    sale = await _credit_sale(client, auth_headers, seeded, customer["id"])

    response = await client.get(f"{CUSTOMERS}/{customer['id']}/purchases", headers=auth_headers)

    assert response.status_code == 200, response.text
    purchases = response.json()
    assert len(purchases) == 1
    assert purchases[0]["reference"] == sale["sale_number"]
    assert purchases[0]["total"] == "6.00"
    assert Decimal(purchases[0]["due"]) > 0


# ---------------------------------------------------------------------------
# Authorization
# ---------------------------------------------------------------------------
async def test_a_cashier_cannot_record_a_supplier_payment(
    client: AsyncClient, auth_headers: dict[str, str], cashier_headers: dict[str, str]
) -> None:
    supplier = await _supplier(client, auth_headers, opening_balance="50.00")

    response = await client.post(
        f"{SUPPLIERS}/{supplier['id']}/payments",
        headers=cashier_headers,
        json={"amount": "10.00"},
    )

    assert response.status_code == 403, response.text
    assert response.json()["error"]["code"] == "insufficient_permissions"
    assert await _balance(client, auth_headers, SUPPLIERS, supplier["id"]) == "50.00"
