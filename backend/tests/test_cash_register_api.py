"""MODULE 16 — the cash register: open, ring, adjust, close and reconcile."""

from __future__ import annotations

from typing import Any

from httpx import AsyncClient

PRODUCTS = "/api/v1/products"
SALES = "/api/v1/sales"
REGISTERS = "/api/v1/registers"
SESSIONS = "/api/v1/register-sessions"


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


def _cash(payment_methods: dict[str, Any], amount: str, **extra: Any) -> dict[str, Any]:
    return {"payment_method_id": str(payment_methods["CASH"].id), "amount": amount, **extra}


async def _open(
    client: AsyncClient, headers: dict[str, str], seeded: Any, opening: str = "0"
) -> dict[str, Any]:
    response = await client.post(
        SESSIONS,
        headers=headers,
        json={"register_id": str(seeded.register.id), "opening_cash": opening},
    )
    assert response.status_code == 201, response.text
    return response.json()["session"]


async def _detail(client: AsyncClient, headers: dict[str, str], session_id: str) -> dict[str, Any]:
    response = await client.get(f"{SESSIONS}/{session_id}", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


async def _current(
    client: AsyncClient, headers: dict[str, str], seeded: Any
) -> dict[str, Any] | None:
    response = await client.get(
        f"{SESSIONS}/current",
        headers=headers,
        params={"register_id": str(seeded.register.id)},
    )
    assert response.status_code == 200, response.text
    return response.json()


async def _sell_cash(
    client: AsyncClient,
    headers: dict[str, str],
    seeded: Any,
    *,
    pay: str = "6.00",
    quantity: str = "3",
) -> dict[str, Any]:
    product = await _product(client, headers)
    response = await client.post(
        SALES,
        headers=headers,
        json={
            "branch_id": str(seeded.branch.id),
            "register_id": str(seeded.register.id),
            "items": [{"product_id": product["id"], "quantity": quantity}],
            "payments": [_cash(seeded.payment_methods, pay)],
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


# ---------------------------------------------------------------------------
# The reconciliation
# ---------------------------------------------------------------------------
async def test_opening_ringing_adjusting_and_closing_reconciles(
    client: AsyncClient, auth_headers: dict[str, str], seeded: Any
) -> None:
    session = await _open(client, auth_headers, seeded, opening="100.00")
    session_id = session["id"]

    await _sell_cash(client, auth_headers, seeded)  # 6.00 cash in
    await client.post(
        f"{SESSIONS}/{session_id}/cash-in",
        headers=auth_headers,
        json={"amount": "20.00", "note": "float top-up"},
    )
    await client.post(
        f"{SESSIONS}/{session_id}/cash-out",
        headers=auth_headers,
        json={"amount": "5.00", "note": "petty"},
    )

    summary = (await _detail(client, auth_headers, session_id))["summary"]
    assert summary["opening_cash"] == "100.00"
    assert summary["cash_sales"] == "6.00"
    assert summary["cash_in"] == "20.00"
    assert summary["cash_out"] == "5.00"
    assert summary["expected_cash"] == "121.00"

    closed = await client.post(
        f"{SESSIONS}/{session_id}/close",
        headers=auth_headers,
        json={"actual_cash": "120.00", "note": "one short"},
    )
    assert closed.status_code == 200, closed.text
    record = closed.json()["session"]
    assert record["status"] == "closed"
    assert record["expected_cash"] == "121.00"
    assert record["actual_cash"] == "120.00"
    assert record["difference"] == "-1.00"
    assert record["closed_by"]["full_name"] == "Test Administrator"

    # A closed register no longer has a current session.
    assert await _current(client, auth_headers, seeded) is None


async def test_cash_in_and_out_move_the_expected_drawer(
    client: AsyncClient, auth_headers: dict[str, str], seeded: Any
) -> None:
    session = await _open(client, auth_headers, seeded, opening="0")
    session_id = session["id"]

    await client.post(
        f"{SESSIONS}/{session_id}/cash-in", headers=auth_headers, json={"amount": "50.00"}
    )
    await client.post(
        f"{SESSIONS}/{session_id}/cash-out", headers=auth_headers, json={"amount": "30.00"}
    )

    summary = (await _detail(client, auth_headers, session_id))["summary"]
    assert summary["expected_cash"] == "20.00"


async def test_a_cash_refund_comes_out_of_the_drawer(
    client: AsyncClient, auth_headers: dict[str, str], seeded: Any
) -> None:
    session = await _open(client, auth_headers, seeded, opening="0")
    sale = await _sell_cash(client, auth_headers, seeded)

    returned = await client.post(
        f"{SALES}/{sale['id']}/returns",
        headers=auth_headers,
        json={
            "items": [{"sale_item_id": sale["items"][0]["id"], "quantity": "3"}],
            "payment_method_id": str(seeded.payment_methods["CASH"].id),
        },
    )
    assert returned.status_code == 201, returned.text
    assert returned.json()["cash_refund"] == "6.00"

    summary = (await _detail(client, auth_headers, session["id"]))["summary"]
    assert summary["cash_sales"] == "6.00"
    assert summary["cash_refunds"] == "6.00"
    assert summary["expected_cash"] == "0.00"


# ---------------------------------------------------------------------------
# Guards
# ---------------------------------------------------------------------------
async def test_only_one_open_session_per_register(
    client: AsyncClient, auth_headers: dict[str, str], seeded: Any
) -> None:
    await _open(client, auth_headers, seeded)

    again = await client.post(
        SESSIONS,
        headers=auth_headers,
        json={"register_id": str(seeded.register.id), "opening_cash": "0"},
    )

    assert again.status_code == 409, again.text
    assert again.json()["error"]["code"] == "register_already_open"


async def test_a_sale_needs_an_open_register(
    client: AsyncClient, auth_headers: dict[str, str], seeded: Any
) -> None:
    product = await _product(client, auth_headers)

    response = await client.post(
        SALES,
        headers=auth_headers,
        json={
            "branch_id": str(seeded.branch.id),
            "register_id": str(seeded.register.id),
            "items": [{"product_id": product["id"], "quantity": "1"}],
            "payments": [_cash(seeded.payment_methods, "2.00")],
        },
    )

    assert response.status_code == 409, response.text
    assert response.json()["error"]["code"] == "register_not_open"


async def test_a_closed_session_cannot_be_adjusted(
    client: AsyncClient, auth_headers: dict[str, str], seeded: Any
) -> None:
    session = await _open(client, auth_headers, seeded)
    await client.post(
        f"{SESSIONS}/{session['id']}/close",
        headers=auth_headers,
        json={"actual_cash": "0"},
    )

    response = await client.post(
        f"{SESSIONS}/{session['id']}/cash-in",
        headers=auth_headers,
        json={"amount": "10.00"},
    )

    assert response.status_code == 409, response.text
    assert response.json()["error"]["code"] == "session_not_open"


# ---------------------------------------------------------------------------
# Opening rules
# ---------------------------------------------------------------------------
async def test_a_required_opening_balance_must_be_positive(
    client: AsyncClient, auth_headers: dict[str, str], seeded: Any
) -> None:
    updated = await client.patch(
        f"{REGISTERS}/{seeded.register.id}",
        headers=auth_headers,
        json={"require_opening_balance": True},
    )
    assert updated.status_code == 200, updated.text

    response = await client.post(
        SESSIONS,
        headers=auth_headers,
        json={"register_id": str(seeded.register.id), "opening_cash": "0"},
    )

    assert response.status_code == 422, response.text
    assert response.json()["error"]["code"] == "opening_balance_required"


async def test_a_fixed_float_cannot_be_overridden(
    client: AsyncClient, auth_headers: dict[str, str], seeded: Any
) -> None:
    await client.patch(
        f"{REGISTERS}/{seeded.register.id}",
        headers=auth_headers,
        json={"default_opening_balance": "50.00", "allow_opening_balance_override": False},
    )

    response = await client.post(
        SESSIONS,
        headers=auth_headers,
        json={"register_id": str(seeded.register.id), "opening_cash": "10.00"},
    )

    assert response.status_code == 422, response.text
    assert response.json()["error"]["code"] == "opening_balance_override_denied"


# ---------------------------------------------------------------------------
# Authorization
# ---------------------------------------------------------------------------
async def test_a_cashier_can_operate_their_till(
    client: AsyncClient, cashier_headers: dict[str, str], seeded: Any
) -> None:
    session = await _open(client, cashier_headers, seeded, opening="20.00")

    closed = await client.post(
        f"{SESSIONS}/{session['id']}/close",
        headers=cashier_headers,
        json={"actual_cash": "20.00"},
    )

    assert closed.status_code == 200, closed.text
    assert closed.json()["session"]["status"] == "closed"


async def test_operating_a_register_needs_the_permission(
    client: AsyncClient, inventory_manager_headers: dict[str, str], seeded: Any
) -> None:
    response = await client.post(
        SESSIONS,
        headers=inventory_manager_headers,
        json={"register_id": str(seeded.register.id), "opening_cash": "0"},
    )

    assert response.status_code == 403, response.text
    assert response.json()["error"]["code"] == "insufficient_permissions"
