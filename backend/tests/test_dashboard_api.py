"""MODULE 19 — dashboard: one snapshot, aggregated server-side."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.role import Role
from app.models.user import User

PRODUCTS = "/api/v1/products"
CATEGORIES = "/api/v1/categories"
CUSTOMERS = "/api/v1/customers"
SALES = "/api/v1/sales"
EXPENSES = "/api/v1/expenses"
EXPENSE_CATEGORIES = "/api/v1/expense-categories"
REGISTER_SESSIONS = "/api/v1/register-sessions"
DASHBOARD = "/api/v1/dashboard"


# ---------------------------------------------------------------------------
# Factories (mirroring the reporting suite)
# ---------------------------------------------------------------------------
async def _product(
    client: AsyncClient, headers: dict[str, str], **overrides: Any
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "name": "Beans",
        "sku": "BEAN-1",
        "minimum_stock": "0",
        "opening_stock": "20",
        "purchase_price": "1.00",
        "selling_price": "2.00",
    }
    payload.update(overrides)
    response = await client.post(PRODUCTS, headers=headers, json=payload)
    assert response.status_code == 201, response.text
    return response.json()


async def _category(client: AsyncClient, headers: dict[str, str], name: str) -> dict[str, Any]:
    response = await client.post(CATEGORIES, headers=headers, json={"name": name})
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


async def _ensure_session(client: AsyncClient, headers: dict[str, str], seeded: Any) -> None:
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


async def _sell(
    client: AsyncClient,
    headers: dict[str, str],
    seeded: Any,
    items: list[dict[str, Any]],
    *,
    pay: str,
) -> dict[str, Any]:
    await _ensure_session(client, headers, seeded)
    response = await client.post(
        SALES,
        headers=headers,
        json={
            "branch_id": str(seeded.branch.id),
            "register_id": str(seeded.register.id),
            "items": items,
            "payments": [
                {"payment_method_id": str(seeded.payment_methods["CASH"].id), "amount": pay}
            ],
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


async def _expense(
    client: AsyncClient, headers: dict[str, str], seeded: Any, amount: str
) -> dict[str, Any]:
    categories = await client.get(f"{EXPENSE_CATEGORIES}/options", headers=headers)
    assert categories.status_code == 200, categories.text
    response = await client.post(
        EXPENSES,
        headers=headers,
        json={
            "branch_id": str(seeded.branch.id),
            "category_id": categories.json()[0]["id"],
            "payment_method_id": str(seeded.payment_methods["CARD"].id),
            "amount": amount,
            "spent_at": date.today().isoformat(),
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


async def _dashboard(client: AsyncClient, headers: dict[str, str], **params: Any) -> dict[str, Any]:
    response = await client.get(DASHBOARD, headers=headers, params=params)
    assert response.status_code == 200, response.text
    return response.json()


# ---------------------------------------------------------------------------
# Shape and figures
# ---------------------------------------------------------------------------
async def test_dashboard_snapshot_ties_out(
    client: AsyncClient, auth_headers: dict[str, str], seeded: Any
) -> None:
    drinks = await _category(client, auth_headers, "Drinks")
    product = await _product(client, auth_headers, category_id=drinks["id"])
    await _product(
        client, auth_headers, name="Low", sku="LOW-1", minimum_stock="10", opening_stock="4"
    )
    await _sell(
        client, auth_headers, seeded, [{"product_id": product["id"], "quantity": "3"}], pay="6.00"
    )
    await _expense(client, auth_headers, seeded, amount="1.50")
    await _customer(client, auth_headers, name="Owing", opening_balance="10.00")

    snapshot = await _dashboard(client, auth_headers)

    today = snapshot["today"]
    assert Decimal(today["sales"]) == Decimal("6.00")
    assert today["orders"] == 1
    # Cost is the captured 1.00 x 3; net profit subtracts today's expenses.
    assert Decimal(today["gross_profit"]) == Decimal("3.00")
    assert Decimal(today["net_profit"]) == Decimal("1.50")

    standing = snapshot["standing"]
    assert standing["products"] == 2
    assert standing["low_stock"] == 1
    assert Decimal(standing["outstanding_due"]) == Decimal("10.00")

    assert snapshot["top_products"][0]["sku"] == "BEAN-1"
    assert snapshot["category_performance"][0]["name"] == "Drinks"
    assert snapshot["payment_methods"][0]["kind"] == "cash"
    assert Decimal(snapshot["payment_methods"][0]["amount"]) == Decimal("6.00")

    assert snapshot["recent_sales"][0]["sale_number"]
    assert Decimal(snapshot["recent_payments"][0]["amount"]) == Decimal("6.00")
    assert snapshot["low_stock"][0]["sku"] == "LOW-1"

    # The trend's last point is today, and it carries today's orders and revenue.
    last = snapshot["trends"][-1]
    assert last["day"] == date.today().isoformat()
    assert last["orders"] == 1
    assert Decimal(last["revenue"]) == Decimal("6.00")


async def test_dashboard_defaults_to_this_week(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    snapshot = await _dashboard(client, auth_headers)
    today = date.today()
    assert snapshot["range"]["preset"] == "this_week"
    assert snapshot["range"]["start"] == (today - timedelta(days=today.weekday())).isoformat()
    assert snapshot["range"]["end"] == today.isoformat()


async def test_empty_dashboard_returns_zeros_and_no_lists(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    snapshot = await _dashboard(client, auth_headers, preset="today")
    assert Decimal(snapshot["today"]["sales"]) == Decimal("0.00")
    assert snapshot["today"]["orders"] == 0
    assert snapshot["recent_sales"] == []
    assert snapshot["recent_payments"] == []
    assert snapshot["top_products"] == []
    # The window is still zero-filled so the chart has a continuous axis.
    assert len(snapshot["trends"]) == 1


# ---------------------------------------------------------------------------
# Date ranges
# ---------------------------------------------------------------------------
async def test_presets_and_custom_ranges_resolve(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    today = date.today()

    month = await _dashboard(client, auth_headers, preset="this_month")
    assert month["range"]["preset"] == "this_month"
    assert month["range"]["start"] == today.replace(day=1).isoformat()
    assert month["range"]["end"] == today.isoformat()

    custom = await _dashboard(
        client,
        auth_headers,
        preset="custom",
        date_from="2026-01-01",
        date_to="2026-01-31",
    )
    assert custom["range"]["preset"] == "custom"
    assert custom["range"]["start"] == "2026-01-01"
    assert custom["range"]["end"] == "2026-01-31"
    assert len(custom["trends"]) == 31


async def test_a_custom_range_needs_both_ends(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    response = await client.get(
        DASHBOARD,
        headers=auth_headers,
        params={"preset": "custom", "date_from": "2026-01-01"},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_date_range"


async def test_branch_filter_narrows_today(
    client: AsyncClient, auth_headers: dict[str, str], seeded: Any
) -> None:
    product = await _product(client, auth_headers)
    await _sell(
        client, auth_headers, seeded, [{"product_id": product["id"], "quantity": "1"}], pay="2.00"
    )

    other = "00000000-0000-0000-0000-0000000000ff"
    narrowed = await _dashboard(client, auth_headers, preset="today", branch_id=other)
    assert narrowed["today"]["orders"] == 0
    assert narrowed["recent_sales"] == []


# ---------------------------------------------------------------------------
# Authorization
# ---------------------------------------------------------------------------
async def test_dashboard_requires_a_token(client: AsyncClient, anon_client: AsyncClient) -> None:
    response = await anon_client.get(DASHBOARD)
    assert response.status_code == 401


async def test_a_user_without_the_permission_is_refused(
    client: AsyncClient, db_session: AsyncSession, seeded: Any, login_as: Any
) -> None:
    role = Role(name="Auditor", description="No dashboard access.", is_system=False)
    db_session.add(role)
    await db_session.flush()
    user = User(
        email="auditor@example.com",
        hashed_password=hash_password("AuditorPass1!"),
        full_name="Test Auditor",
        is_active=True,
        branch=seeded.branch,
    )
    user.roles = [role]
    db_session.add(user)
    await db_session.commit()

    headers = await login_as("auditor@example.com", "AuditorPass1!")
    response = await client.get(DASHBOARD, headers=headers)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "insufficient_permissions"
