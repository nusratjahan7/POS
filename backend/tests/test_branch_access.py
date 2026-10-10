"""MODULE 22 — branch-level authorization.

The rule under test: a user restricted to a set of branches is *silently scoped*
to them on reads, and *refused* (403) when they name a branch outside that set or
try to write to one. An administrator (``branches:all``) sees and acts on every
branch. A single-branch user keeps working exactly as before.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from httpx import AsyncClient

BRANCHES = "/api/v1/branches"
USERS = "/api/v1/users"
SALES = "/api/v1/sales"
EXPENSES = "/api/v1/expenses"
PRODUCTS = "/api/v1/products"
REGISTERS = "/api/v1/registers"
SESSIONS = "/api/v1/register-sessions"
MOVEMENTS = "/api/v1/inventory/movements"

MANAGER_PASSWORD = "ScopedManager1!"


async def _branch(client: AsyncClient, headers: dict[str, str], code: str, name: str) -> dict:
    response = await client.post(
        BRANCHES, headers=headers, json={"name": name, "code": code}
    )
    assert response.status_code == 201, response.text
    return response.json()


async def _product(
    client: AsyncClient, headers: dict[str, str], *, opening_stock: str = "20", **overrides: Any
) -> dict:
    payload: dict[str, Any] = {
        "name": "Beans",
        "sku": "BRANCH-BEAN",
        "minimum_stock": "0",
        "opening_stock": opening_stock,
        "purchase_price": "1.00",
        "selling_price": "2.00",
    }
    payload.update(overrides)
    response = await client.post(PRODUCTS, headers=headers, json=payload)
    assert response.status_code == 201, response.text
    return response.json()


async def _stock_at(
    client: AsyncClient, headers: dict[str, str], branch_id: Any, product_id: Any, quantity: str
) -> None:
    response = await client.post(
        MOVEMENTS,
        headers=headers,
        json={
            "product_id": str(product_id),
            "branch_id": str(branch_id),
            "quantity": quantity,
            "movement_type": "adjustment",
            "reference_type": "manual",
        },
    )
    assert response.status_code == 201, response.text


async def _register_id(client: AsyncClient, headers: dict[str, str], branch_id: Any) -> str:
    options = await client.get(
        f"{REGISTERS}/options", headers=headers, params={"branch_id": str(branch_id)}
    )
    assert options.status_code == 200, options.text
    if options.json():
        return str(options.json()[0]["id"])
    created = await client.post(
        REGISTERS, headers=headers, json={"name": "Till", "branch_id": str(branch_id)}
    )
    assert created.status_code == 201, created.text
    return str(created.json()["id"])


async def _open_till(client: AsyncClient, headers: dict[str, str], branch_id: Any) -> str:
    register_id = await _register_id(client, headers, branch_id)
    current = await client.get(
        f"{SESSIONS}/current", headers=headers, params={"register_id": register_id}
    )
    if current.status_code == 200 and current.json() is None:
        opened = await client.post(
            SESSIONS, headers=headers, json={"register_id": register_id, "opening_cash": "0"}
        )
        assert opened.status_code == 201, opened.text
    return register_id


def _sale_body(branch_id: Any, register_id: str, product_id: Any, payment_method_id: Any) -> dict:
    return {
        "branch_id": str(branch_id),
        "register_id": register_id,
        "items": [{"product_id": str(product_id), "quantity": "1"}],
        "payments": [{"payment_method_id": str(payment_method_id), "amount": "2.00"}],
    }


async def _sell(
    client: AsyncClient, headers: dict[str, str], branch_id: Any, product_id: Any, method_id: Any
) -> dict:
    register_id = await _open_till(client, headers, branch_id)
    response = await client.post(
        SALES, headers=headers, json=_sale_body(branch_id, register_id, product_id, method_id)
    )
    assert response.status_code == 201, response.text
    return response.json()


async def _scoped_manager(
    client: AsyncClient,
    headers: dict[str, str],
    seeded: SimpleNamespace,
    branch_ids: list[Any],
    *,
    email: str = "scoped.manager@example.com",
    primary: Any | None = None,
) -> dict:
    payload: dict[str, Any] = {
        "email": email,
        "full_name": "Scoped Manager",
        "password": MANAGER_PASSWORD,
        "role_ids": [str(seeded.roles["Manager"].id)],
        "branch_ids": [str(branch_id) for branch_id in branch_ids],
    }
    if primary is not None:
        payload["branch_id"] = str(primary)
    response = await client.post(USERS, headers=headers, json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def _error_code(response: Any) -> str:
    return response.json()["error"]["code"]


# ---------------------------------------------------------------------------
# The branch selector feed
# ---------------------------------------------------------------------------
async def test_branch_options_offer_only_an_assigned_users_branches(
    client: AsyncClient, auth_headers: dict[str, str], login_as: Any, seeded: SimpleNamespace
) -> None:
    other = await _branch(client, auth_headers, "DHAKA", "Dhaka Branch")
    await _scoped_manager(client, auth_headers, seeded, [seeded.branch.id])

    scoped = await login_as("scoped.manager@example.com", MANAGER_PASSWORD)
    mine = await client.get(f"{BRANCHES}/options", headers=scoped)
    assert mine.status_code == 200, mine.text
    assert [row["id"] for row in mine.json()] == [str(seeded.branch.id)]

    # The administrator is offered everything — including the branch just made.
    admin = await client.get(f"{BRANCHES}/options", headers=auth_headers)
    ids = {row["id"] for row in admin.json()}
    assert {str(seeded.branch.id), other["id"]} <= ids


# ---------------------------------------------------------------------------
# Reads are scoped
# ---------------------------------------------------------------------------
async def test_a_restricted_manager_lists_only_their_branches_sales(
    client: AsyncClient, auth_headers: dict[str, str], login_as: Any, seeded: SimpleNamespace
) -> None:
    other = await _branch(client, auth_headers, "DHAKA", "Dhaka Branch")
    product = await _product(client, auth_headers, opening_stock="0")
    await _stock_at(client, auth_headers, other["id"], product["id"], "10")
    await _stock_at(client, auth_headers, seeded.branch.id, product["id"], "10")

    mine = await _sell(
        client, auth_headers, seeded.branch.id, product["id"], seeded.payment_methods["CASH"].id
    )
    theirs = await _sell(
        client, auth_headers, other["id"], product["id"], seeded.payment_methods["CASH"].id
    )

    await _scoped_manager(client, auth_headers, seeded, [seeded.branch.id])
    scoped = await login_as("scoped.manager@example.com", MANAGER_PASSWORD)

    listed = await client.get(SALES, headers=scoped)
    assert listed.status_code == 200, listed.text
    assert [row["id"] for row in listed.json()["items"]] == [mine["id"]]
    assert theirs["id"] not in {row["id"] for row in listed.json()["items"]}

    # Naming their own branch is fine; naming another is refused, not empty.
    own = await client.get(SALES, headers=scoped, params={"branch_id": str(seeded.branch.id)})
    assert own.status_code == 200
    denied = await client.get(SALES, headers=scoped, params={"branch_id": other["id"]})
    assert denied.status_code == 403
    assert _error_code(denied) == "branch_forbidden"


async def test_an_administrator_lists_every_branch(
    client: AsyncClient, auth_headers: dict[str, str], seeded: SimpleNamespace
) -> None:
    other = await _branch(client, auth_headers, "DHAKA", "Dhaka Branch")
    product = await _product(client, auth_headers, opening_stock="0")
    await _stock_at(client, auth_headers, other["id"], product["id"], "10")
    await _stock_at(client, auth_headers, seeded.branch.id, product["id"], "10")

    mine = await _sell(
        client, auth_headers, seeded.branch.id, product["id"], seeded.payment_methods["CASH"].id
    )
    theirs = await _sell(
        client, auth_headers, other["id"], product["id"], seeded.payment_methods["CASH"].id
    )

    listed = await client.get(SALES, headers=auth_headers)
    ids = {row["id"] for row in listed.json()["items"]}
    assert {mine["id"], theirs["id"]} <= ids

    # A specific branch still narrows.
    narrowed = await client.get(SALES, headers=auth_headers, params={"branch_id": other["id"]})
    assert [row["id"] for row in narrowed.json()["items"]] == [theirs["id"]]


# ---------------------------------------------------------------------------
# Writes are refused outside the scope
# ---------------------------------------------------------------------------
async def test_ringing_a_sale_outside_the_scope_is_forbidden(
    client: AsyncClient, auth_headers: dict[str, str], login_as: Any, seeded: SimpleNamespace
) -> None:
    other = await _branch(client, auth_headers, "DHAKA", "Dhaka Branch")
    product = await _product(client, auth_headers)
    register_id = await _open_till(client, auth_headers, other["id"])

    await _scoped_manager(client, auth_headers, seeded, [seeded.branch.id])
    scoped = await login_as("scoped.manager@example.com", MANAGER_PASSWORD)

    response = await client.post(
        SALES,
        headers=scoped,
        json=_sale_body(other["id"], register_id, product["id"], seeded.payment_methods["CASH"].id),
    )
    assert response.status_code == 403, response.text
    assert _error_code(response) == "branch_forbidden"


async def test_recording_an_expense_outside_the_scope_is_forbidden(
    client: AsyncClient, auth_headers: dict[str, str], login_as: Any, seeded: SimpleNamespace
) -> None:
    other = await _branch(client, auth_headers, "DHAKA", "Dhaka Branch")
    categories = await client.get("/api/v1/expense-categories/options", headers=auth_headers)
    category_id = categories.json()[0]["id"]
    method_id = seeded.payment_methods["OTHER"].id

    await _scoped_manager(client, auth_headers, seeded, [seeded.branch.id])
    scoped = await login_as("scoped.manager@example.com", MANAGER_PASSWORD)

    response = await client.post(
        EXPENSES,
        headers=scoped,
        json={
            "branch_id": other["id"],
            "category_id": str(category_id),
            "payment_method_id": str(method_id),
            "amount": "10.00",
            "spent_at": "2026-01-01",
        },
    )
    assert response.status_code == 403, response.text
    assert _error_code(response) == "branch_forbidden"


# ---------------------------------------------------------------------------
# Branch assignment on the users API
# ---------------------------------------------------------------------------
async def test_users_carry_their_branch_assignments(
    client: AsyncClient, auth_headers: dict[str, str], seeded: SimpleNamespace
) -> None:
    other = await _branch(client, auth_headers, "DHAKA", "Dhaka Branch")
    created = await _scoped_manager(
        client, auth_headers, seeded, [seeded.branch.id], primary=seeded.branch.id
    )

    assert {row["code"] for row in created["branches"]} == {seeded.branch.code}
    assert created["all_branches"] is False

    updated = await client.patch(
        f"{USERS}/{created['id']}",
        headers=auth_headers,
        json={"branch_ids": [str(seeded.branch.id), other["id"]]},
    )
    assert updated.status_code == 200, updated.text
    assert {row["id"] for row in updated.json()["branches"]} == {
        str(seeded.branch.id),
        other["id"],
    }


async def test_a_user_with_only_a_primary_branch_falls_back_to_it(
    client: AsyncClient, auth_headers: dict[str, str], login_as: Any, seeded: SimpleNamespace
) -> None:
    """No assignment list — the primary branch is the scope (pre-existing accounts)."""
    response = await client.post(
        USERS,
        headers=auth_headers,
        json={
            "email": "legacy.user@example.com",
            "full_name": "Legacy User",
            "password": MANAGER_PASSWORD,
            "role_ids": [str(seeded.roles["Manager"].id)],
            "branch_id": str(seeded.branch.id),
        },
    )
    assert response.status_code == 201, response.text
    assert response.json()["branches"] == []

    headers = await login_as("legacy.user@example.com", MANAGER_PASSWORD)
    options = await client.get(f"{BRANCHES}/options", headers=headers)
    assert [row["id"] for row in options.json()] == [str(seeded.branch.id)]


async def test_all_branches_is_a_grant_the_administrator_holds(
    client: AsyncClient, auth_headers: dict[str, str], login_as: Any, administrator: Any
) -> None:
    me = await client.get("/api/v1/auth/me", headers=auth_headers)
    assert me.status_code == 200
    assert me.json()["all_branches"] is True

    admin_headers = await login_as(administrator.email, "ManagerPass1!")
    me = await client.get("/api/v1/auth/me", headers=admin_headers)
    assert me.json()["all_branches"] is True
