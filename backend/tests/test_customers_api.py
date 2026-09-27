"""Customers: profile CRUD, receivables and payment history."""

from __future__ import annotations

from typing import Any

from httpx import AsyncClient

CUSTOMERS = "/api/v1/customers"


async def _customer(
    client: AsyncClient, headers: dict[str, str], **overrides: Any
) -> dict[str, Any]:
    payload: dict[str, Any] = {"name": "Jane Doe"}
    payload.update(overrides)
    response = await client.post(CUSTOMERS, headers=headers, json=payload)
    assert response.status_code == 201, response.text
    return response.json()


async def _pay(
    client: AsyncClient, headers: dict[str, str], customer_id: Any, amount: str, **extra: Any
) -> Any:
    payload: dict[str, Any] = {"amount": amount}
    payload.update(extra)
    return await client.post(f"{CUSTOMERS}/{customer_id}/payments", headers=headers, json=payload)


# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------
async def test_customer_balance_starts_at_the_opening_balance(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    customer = await _customer(client, auth_headers, opening_balance="50.00")

    assert customer["opening_balance"] == "50.00"
    assert customer["balance"] == "50.00"
    assert customer["is_active"] is True


async def test_customer_list_search_filter_and_sort(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    await _customer(client, auth_headers, name="Alice")
    await _customer(client, auth_headers, name="Bob", phone="01700000000")
    carol = await _customer(client, auth_headers, name="Carol")
    await client.patch(
        f"{CUSTOMERS}/{carol['id']}", headers=auth_headers, json={"is_active": False}
    )

    async def total(**params: Any) -> int:
        response = await client.get(CUSTOMERS, headers=auth_headers, params=params)
        assert response.status_code == 200, response.text
        return int(response.json()["total"])

    assert await total() == 3
    assert await total(search="alice") == 1  # by name
    assert await total(search="01700") == 1  # by phone
    assert await total(is_active="true") == 2


async def test_customer_can_be_updated(client: AsyncClient, auth_headers: dict[str, str]) -> None:
    customer = await _customer(client, auth_headers)

    response = await client.patch(
        f"{CUSTOMERS}/{customer['id']}",
        headers=auth_headers,
        json={"phone": "01911111111", "address": "12 High St"},
    )

    assert response.status_code == 200
    assert response.json()["phone"] == "01911111111"
    assert response.json()["address"] == "12 High St"


async def test_deactivating_a_customer_hides_it(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    customer = await _customer(client, auth_headers)

    assert (
        await client.delete(f"{CUSTOMERS}/{customer['id']}", headers=auth_headers)
    ).status_code == 204
    assert (
        await client.get(f"{CUSTOMERS}/{customer['id']}", headers=auth_headers)
    ).status_code == 404
    assert (await client.get(CUSTOMERS, headers=auth_headers)).json()["total"] == 0


# ---------------------------------------------------------------------------
# Payments and receivables
# ---------------------------------------------------------------------------
async def test_a_payment_reduces_the_balance_and_appears_in_history(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    customer = await _customer(client, auth_headers, opening_balance="100.00")

    created = await _pay(client, auth_headers, customer["id"], "40.00", method="cash")
    assert created.status_code == 201, created.text
    assert created.json()["amount"] == "40.00"

    refreshed = (await client.get(f"{CUSTOMERS}/{customer['id']}", headers=auth_headers)).json()
    assert refreshed["balance"] == "60.00"

    history = (
        await client.get(f"{CUSTOMERS}/{customer['id']}/payments", headers=auth_headers)
    ).json()
    assert history["total"] == 1
    assert history["items"][0]["method"] == "cash"


async def test_a_payment_larger_than_the_outstanding_due_is_rejected(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    customer = await _customer(client, auth_headers, opening_balance="10.00")

    response = await _pay(client, auth_headers, customer["id"], "25.00")

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "payment_exceeds_balance"


async def test_details_aggregate_the_customer_account(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    customer = await _customer(client, auth_headers, opening_balance="100.00")
    await _pay(client, auth_headers, customer["id"], "30.00")
    await _pay(client, auth_headers, customer["id"], "20.00")

    details = (
        await client.get(f"{CUSTOMERS}/{customer['id']}/details", headers=auth_headers)
    ).json()

    assert details["customer"]["name"] == "Jane Doe"
    assert details["total_paid"] == "50.00"
    assert details["outstanding_due"] == "50.00"
    # No sales module yet.
    assert details["total_orders"] == 0
    assert details["total_purchase_amount"] == "0"
    assert len(details["recent_payments"]) == 2
    assert details["recent_purchases"] == []


async def test_purchase_history_is_empty_until_sales_exist(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    customer = await _customer(client, auth_headers)

    response = await client.get(f"{CUSTOMERS}/{customer['id']}/purchases", headers=auth_headers)

    assert response.status_code == 200
    assert response.json() == []


async def test_customer_options_expose_name_and_balance(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    await _customer(client, auth_headers, name="Jane Doe")

    options = (await client.get(f"{CUSTOMERS}/options", headers=auth_headers)).json()

    assert len(options) == 1
    assert options[0]["name"] == "Jane Doe"
    assert "balance" in options[0]


# ---------------------------------------------------------------------------
# Authorization
# ---------------------------------------------------------------------------
async def test_customer_endpoints_require_authentication(client: AsyncClient) -> None:
    response = await client.get(CUSTOMERS)

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


async def test_inventory_manager_cannot_reach_customers(
    client: AsyncClient, inventory_manager_headers: dict[str, str]
) -> None:
    response = await client.get(CUSTOMERS, headers=inventory_manager_headers)

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "insufficient_permissions"


async def test_a_cashier_can_manage_customers(
    client: AsyncClient, cashier_headers: dict[str, str]
) -> None:
    assert (await client.get(CUSTOMERS, headers=cashier_headers)).status_code == 200

    created = await client.post(
        CUSTOMERS, headers=cashier_headers, json={"name": "Walk-in Regular"}
    )
    assert created.status_code == 201, created.text
