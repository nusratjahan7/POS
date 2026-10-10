"""MODULE 20 — notifications: fan-out, unread count, read state, isolation."""

from __future__ import annotations

from typing import Any

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.role import Role
from app.models.user import User

NOTIFICATIONS = "/api/v1/notifications"
UNREAD = "/api/v1/notifications/unread-count"
READ_ALL = "/api/v1/notifications/read-all"
PRODUCTS = "/api/v1/products"
MOVEMENTS = "/api/v1/inventory/movements"
SALES = "/api/v1/sales"
REGISTER_SESSIONS = "/api/v1/register-sessions"
ROLES = "/api/v1/roles"
USERS = "/api/v1/users"


# ---------------------------------------------------------------------------
# Helpers
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


async def _adjust(
    client: AsyncClient,
    headers: dict[str, str],
    seeded: Any,
    product_id: str,
    quantity: str,
) -> dict[str, Any]:
    response = await client.post(
        MOVEMENTS,
        headers=headers,
        json={
            "product_id": product_id,
            "branch_id": str(seeded.branch.id),
            "movement_type": "adjustment",
            "quantity": quantity,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


async def _notifications(
    client: AsyncClient, headers: dict[str, str], **params: Any
) -> dict[str, Any]:
    response = await client.get(
        NOTIFICATIONS, headers=headers, params={"page_size": 100, **params}
    )
    assert response.status_code == 200, response.text
    return response.json()


async def _unread(client: AsyncClient, headers: dict[str, str]) -> int:
    response = await client.get(UNREAD, headers=headers)
    assert response.status_code == 200, response.text
    return response.json()["unread"]


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


async def _only_notification_role(
    db_session: AsyncSession, seeded: Any, codes: list[str]
) -> str:
    """Create a role with exactly *codes* and a user holding it; return the email."""
    slug = ("-".join(codes) or "none").replace(":", "-")
    permissions = []
    if codes:
        from app.repositories.permission import PermissionRepository

        permissions = list(await PermissionRepository(db_session).get_by_codes(codes))

    role = Role(
        name=f"Watcher-{slug}",
        description=None,
        is_system=False,
        permissions=permissions,
    )
    db_session.add(role)

    email = f"watcher-{slug}@example.com"
    user = User(
        email=email,
        hashed_password=hash_password("Watcher123!"),
        full_name="Watcher",
        is_active=True,
        branch=seeded.branch,
    )
    user.roles = [role]
    db_session.add(user)
    await db_session.commit()
    return email


# ---------------------------------------------------------------------------
# Stock alerts
# ---------------------------------------------------------------------------
async def test_low_stock_crossing_notifies_watchers_but_not_the_actor(
    client: AsyncClient, auth_headers: dict[str, str], manager_headers: dict[str, str], seeded: Any
) -> None:
    product = await _product(client, auth_headers, minimum_stock="5", opening_stock="10")
    await _adjust(client, auth_headers, seeded, product["id"], "-6")  # 10 -> 4 (crosses)

    manager = await _notifications(client, manager_headers)
    assert any(item["type"] == "low_stock" for item in manager["items"])

    # The person who made the adjustment is never a recipient of their own action.
    actor = await _notifications(client, auth_headers)
    assert all(item["type"] != "low_stock" for item in actor["items"])


async def test_staying_low_does_not_renotify(
    client: AsyncClient, auth_headers: dict[str, str], manager_headers: dict[str, str], seeded: Any
) -> None:
    product = await _product(client, auth_headers, minimum_stock="5", opening_stock="10")
    await _adjust(client, auth_headers, seeded, product["id"], "-6")  # crosses into low
    await _adjust(client, auth_headers, seeded, product["id"], "-1")  # stays low

    manager = await _notifications(client, manager_headers)
    lows = [item for item in manager["items"] if item["type"] == "low_stock"]
    assert len(lows) == 1


async def test_out_of_stock_is_critical(
    client: AsyncClient, auth_headers: dict[str, str], manager_headers: dict[str, str], seeded: Any
) -> None:
    product = await _product(client, auth_headers, minimum_stock="0", opening_stock="3")
    await _adjust(client, auth_headers, seeded, product["id"], "-3")  # 3 -> 0

    manager = await _notifications(client, manager_headers)
    out = [item for item in manager["items"] if item["type"] == "out_of_stock"]
    assert len(out) == 1
    assert out[0]["severity"] == "critical"


# ---------------------------------------------------------------------------
# Unread count and read state
# ---------------------------------------------------------------------------
async def test_unread_count_mark_one_and_mark_all(
    client: AsyncClient, auth_headers: dict[str, str], manager_headers: dict[str, str], seeded: Any
) -> None:
    first = await _product(client, auth_headers, sku="LOW-1", minimum_stock="5", opening_stock="10")
    await _adjust(client, auth_headers, seeded, first["id"], "-6")

    assert await _unread(client, manager_headers) == 1

    listed = await _notifications(client, manager_headers, unread="true")
    notification_id = listed["items"][0]["id"]
    marked = await client.post(f"{NOTIFICATIONS}/{notification_id}/read", headers=manager_headers)
    assert marked.status_code == 200, marked.text
    assert marked.json()["read_at"] is not None
    assert await _unread(client, manager_headers) == 0

    second = await _product(
        client, auth_headers, sku="LOW-2", minimum_stock="5", opening_stock="10"
    )
    await _adjust(client, auth_headers, seeded, second["id"], "-6")
    assert await _unread(client, manager_headers) == 1

    cleared = await client.post(READ_ALL, headers=manager_headers)
    assert cleared.status_code == 200, cleared.text
    assert cleared.json()["unread"] == 0
    assert await _unread(client, manager_headers) == 0


async def test_notifications_are_isolated_per_user(
    client: AsyncClient, auth_headers: dict[str, str], db_session: AsyncSession, seeded: Any
) -> None:
    # Only the actor (a superuser) can adjust stock; the watcher lacks inventory:read.
    await _only_notification_role(db_session, seeded, ["notifications:read"])
    product = await _product(client, auth_headers, minimum_stock="5", opening_stock="10")
    await _adjust(client, auth_headers, seeded, product["id"], "-6")

    headers = await _login(client, "watcher-notifications-read@example.com", "Watcher123!")
    listed = await _notifications(client, headers)
    assert listed["items"] == []
    assert await _unread(client, headers) == 0


# ---------------------------------------------------------------------------
# Sales and refunds
# ---------------------------------------------------------------------------
async def test_new_sale_notifies_the_floor_but_not_the_cashier(
    client: AsyncClient,
    auth_headers: dict[str, str],
    cashier_headers: dict[str, str],
    manager_headers: dict[str, str],
    seeded: Any,
) -> None:
    product = await _product(client, auth_headers, minimum_stock="0", opening_stock="10")
    await _ensure_session(client, cashier_headers, seeded)

    sale = await client.post(
        SALES,
        headers=cashier_headers,
        json={
            "branch_id": str(seeded.branch.id),
            "register_id": str(seeded.register.id),
            "items": [{"product_id": product["id"], "quantity": "1"}],
            "payments": [
                {"payment_method_id": str(seeded.payment_methods["CASH"].id), "amount": "2.00"}
            ],
        },
    )
    assert sale.status_code == 201, sale.text

    manager = await _notifications(client, manager_headers)
    assert any(item["type"] == "new_sale" for item in manager["items"])

    cashier = await _notifications(client, cashier_headers)
    assert all(item["type"] != "new_sale" for item in cashier["items"])


# ---------------------------------------------------------------------------
# Authorization
# ---------------------------------------------------------------------------
async def test_requires_auth(client: AsyncClient, anon_client: AsyncClient) -> None:
    assert (await anon_client.get(NOTIFICATIONS)).status_code == 401


async def test_without_the_permission_is_refused(
    client: AsyncClient, db_session: AsyncSession, seeded: Any
) -> None:
    await _only_notification_role(db_session, seeded, [])
    headers = await _login(client, "watcher-none@example.com", "Watcher123!")
    response = await client.get(NOTIFICATIONS, headers=headers)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "insufficient_permissions"


async def _login(client: AsyncClient, email: str, password: str) -> dict[str, str]:
    response = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}
