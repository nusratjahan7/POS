"""MODULE 16 — expenses: the spend ledger and its drawer effect."""

from __future__ import annotations

from datetime import date
from typing import Any

from httpx import AsyncClient

CATEGORIES = "/api/v1/expense-categories"
EXPENSES = "/api/v1/expenses"
REGISTER_SESSIONS = "/api/v1/register-sessions"


async def _open_session(
    client: AsyncClient, headers: dict[str, str], seeded: Any, opening: str = "0"
) -> dict[str, Any]:
    response = await client.post(
        REGISTER_SESSIONS,
        headers=headers,
        json={"register_id": str(seeded.register.id), "opening_cash": opening},
    )
    assert response.status_code == 201, response.text
    return response.json()["session"]


async def _first_category(client: AsyncClient, headers: dict[str, str]) -> dict[str, Any]:
    response = await client.get(f"{CATEGORIES}/options", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()[0]


def _expense_body(
    seeded: Any, category_id: str, method_id: Any, **overrides: Any
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "branch_id": str(seeded.branch.id),
        "category_id": category_id,
        "payment_method_id": str(method_id),
        "amount": "30.00",
        "description": "Cleaning supplies",
        "spent_at": date.today().isoformat(),
    }
    payload.update(overrides)
    return payload


async def _expected_cash(client: AsyncClient, headers: dict[str, str], session_id: str) -> str:
    response = await client.get(f"{REGISTER_SESSIONS}/{session_id}", headers=headers)
    assert response.status_code == 200, response.text
    return str(response.json()["summary"]["expected_cash"])


# ---------------------------------------------------------------------------
# Categories
# ---------------------------------------------------------------------------
async def test_categories_are_created_listed_and_deleted(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    created = await client.post(
        CATEGORIES, headers=auth_headers, json={"name": "Marketing"}
    )
    assert created.status_code == 201, created.text
    category = created.json()

    duplicate = await client.post(
        CATEGORIES, headers=auth_headers, json={"name": "marketing"}
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "expense_category_name_taken"

    options = (await client.get(f"{CATEGORIES}/options", headers=auth_headers)).json()
    assert any(row["id"] == category["id"] for row in options)

    removed = await client.delete(f"{CATEGORIES}/{category['id']}", headers=auth_headers)
    assert removed.status_code == 204
    remaining = (await client.get(f"{CATEGORIES}/options", headers=auth_headers)).json()
    assert all(row["id"] != category["id"] for row in remaining)


# ---------------------------------------------------------------------------
# Expenses and the drawer
# ---------------------------------------------------------------------------
async def test_a_cash_expense_draws_on_the_open_register(
    client: AsyncClient, auth_headers: dict[str, str], seeded: Any
) -> None:
    session = await _open_session(client, auth_headers, seeded, opening="100.00")
    category = await _first_category(client, auth_headers)

    response = await client.post(
        EXPENSES,
        headers=auth_headers,
        json=_expense_body(
            seeded,
            category["id"],
            seeded.payment_methods["CASH"].id,
            register_session_id=session["id"],
        ),
    )

    assert response.status_code == 201, response.text
    expense = response.json()
    assert expense["amount"] == "30.00"
    assert expense["register_session"]["id"] == session["id"]
    assert expense["created_by"]["full_name"] == "Test Administrator"

    assert await _expected_cash(client, auth_headers, session["id"]) == "70.00"


async def test_a_cash_expense_needs_a_register_session(
    client: AsyncClient, auth_headers: dict[str, str], seeded: Any
) -> None:
    category = await _first_category(client, auth_headers)

    response = await client.post(
        EXPENSES,
        headers=auth_headers,
        json=_expense_body(seeded, category["id"], seeded.payment_methods["CASH"].id),
    )

    assert response.status_code == 422, response.text
    assert response.json()["error"]["code"] == "expense_session_required"


async def test_a_non_cash_expense_touches_no_drawer(
    client: AsyncClient, auth_headers: dict[str, str], seeded: Any
) -> None:
    session = await _open_session(client, auth_headers, seeded, opening="100.00")
    category = await _first_category(client, auth_headers)

    response = await client.post(
        EXPENSES,
        headers=auth_headers,
        json=_expense_body(seeded, category["id"], seeded.payment_methods["CARD"].id),
    )

    assert response.status_code == 201, response.text
    assert response.json()["register_session"] is None
    assert await _expected_cash(client, auth_headers, session["id"]) == "100.00"


async def test_deleting_an_expense_reverses_the_drawer_until_the_till_closes(
    client: AsyncClient, auth_headers: dict[str, str], seeded: Any
) -> None:
    session = await _open_session(client, auth_headers, seeded, opening="100.00")
    category = await _first_category(client, auth_headers)
    created = await client.post(
        EXPENSES,
        headers=auth_headers,
        json=_expense_body(
            seeded,
            category["id"],
            seeded.payment_methods["CASH"].id,
            register_session_id=session["id"],
        ),
    )
    expense_id = created.json()["id"]
    assert await _expected_cash(client, auth_headers, session["id"]) == "70.00"

    removed = await client.delete(f"{EXPENSES}/{expense_id}", headers=auth_headers)
    assert removed.status_code == 204, removed.text
    assert await _expected_cash(client, auth_headers, session["id"]) == "100.00"

    # A second expense is locked once the session is closed.
    locked = await client.post(
        EXPENSES,
        headers=auth_headers,
        json=_expense_body(
            seeded,
            category["id"],
            seeded.payment_methods["CASH"].id,
            register_session_id=session["id"],
        ),
    )
    locked_id = locked.json()["id"]
    await client.post(
        f"{REGISTER_SESSIONS}/{session['id']}/close",
        headers=auth_headers,
        json={"actual_cash": "70.00"},
    )

    refused = await client.delete(f"{EXPENSES}/{locked_id}", headers=auth_headers)
    assert refused.status_code == 409, refused.text
    assert refused.json()["error"]["code"] == "expense_locked"


async def test_expenses_list_and_total(
    client: AsyncClient, auth_headers: dict[str, str], seeded: Any
) -> None:
    category = await _first_category(client, auth_headers)
    for amount in ("10.00", "15.00"):
        created = await client.post(
            EXPENSES,
            headers=auth_headers,
            json=_expense_body(
                seeded, category["id"], seeded.payment_methods["CARD"].id, amount=amount
            ),
        )
        assert created.status_code == 201, created.text

    listing = await client.get(EXPENSES, headers=auth_headers)
    assert listing.status_code == 200, listing.text
    assert listing.json()["total"] == 2

    total = await client.get(f"{EXPENSES}/summary", headers=auth_headers)
    assert total.status_code == 200, total.text
    assert total.json()["amount"] == "25.00"

    filtered = await client.get(
        EXPENSES, headers=auth_headers, params={"category_id": category["id"]}
    )
    assert filtered.json()["total"] == 2


# ---------------------------------------------------------------------------
# Authorization
# ---------------------------------------------------------------------------
async def test_a_cashier_cannot_record_an_expense(
    client: AsyncClient, cashier_headers: dict[str, str], auth_headers: dict[str, str], seeded: Any
) -> None:
    category = await _first_category(client, auth_headers)

    response = await client.post(
        EXPENSES,
        headers=cashier_headers,
        json=_expense_body(seeded, category["id"], seeded.payment_methods["CARD"].id),
    )

    assert response.status_code == 403, response.text
    assert response.json()["error"]["code"] == "insufficient_permissions"
