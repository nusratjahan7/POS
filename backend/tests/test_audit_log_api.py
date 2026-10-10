"""MODULE 20 — audit log: capture, old/new snapshots, redaction, access."""

from __future__ import annotations

import json
from typing import Any

from httpx import AsyncClient

AUDIT = "/api/v1/audit-logs"
PRODUCTS = "/api/v1/products"
USERS = "/api/v1/users"
LOGIN = "/api/v1/auth/login"

SUPERUSER_EMAIL = "admin@example.com"


async def _audit(client: AsyncClient, headers: dict[str, str], **params: Any) -> dict[str, Any]:
    response = await client.get(AUDIT, headers=headers, params={"page_size": 100, **params})
    assert response.status_code == 200, response.text
    return response.json()


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


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------
async def test_login_records_the_client_ip(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    response = await client.post(
        LOGIN,
        json={"email": SUPERUSER_EMAIL, "password": "SuperSecret1!"},
        headers={"x-forwarded-for": "203.0.113.7"},
    )
    assert response.status_code == 200, response.text

    logs = await _audit(client, auth_headers, action="auth.login")
    assert any(entry["ip_address"] == "203.0.113.7" for entry in logs["items"])


async def test_failed_login_is_recorded_despite_the_401(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    response = await client.post(
        LOGIN, json={"email": SUPERUSER_EMAIL, "password": "definitely-wrong"}
    )
    assert response.status_code == 401

    logs = await _audit(client, auth_headers, action="auth.login_failed")
    assert len(logs["items"]) >= 1
    assert logs["items"][0]["user_email"] == SUPERUSER_EMAIL


# ---------------------------------------------------------------------------
# Catalog
# ---------------------------------------------------------------------------
async def test_product_update_captures_old_and_new(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    product = await _product(client, auth_headers, selling_price="2.00")

    updated = await client.patch(
        f"{PRODUCTS}/{product['id']}", headers=auth_headers, json={"selling_price": "9.99"}
    )
    assert updated.status_code == 200, updated.text

    logs = await _audit(client, auth_headers, action="catalog.product.price_change")
    assert len(logs["items"]) == 1
    entry = logs["items"][0]
    assert entry["module"] == "catalog"
    assert entry["entity"] == "product"
    assert entry["old_data"]["selling_price"] == "2.00"
    assert entry["new_data"]["selling_price"] == "9.99"


async def test_product_creation_is_audited(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    product = await _product(client, auth_headers, sku="AUDIT-1")
    logs = await _audit(client, auth_headers, action="catalog.product.create")
    assert any(entry["entity_id"] == product["id"] for entry in logs["items"])


# ---------------------------------------------------------------------------
# Redaction
# ---------------------------------------------------------------------------
async def test_user_creation_never_stores_secrets(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    response = await client.post(
        USERS,
        headers=auth_headers,
        json={
            "email": "fresh@example.com",
            "full_name": "Fresh Hire",
            "password": "Sup3rSecret!",
            "role_ids": [],
        },
    )
    assert response.status_code == 201, response.text

    logs = await _audit(client, auth_headers, action="users.user.create")
    assert len(logs["items"]) == 1
    entry = logs["items"][0]
    # The actor is snapshotted onto the row.
    assert entry["user_email"] == SUPERUSER_EMAIL

    blob = json.dumps({"old": entry["old_data"], "new": entry["new_data"]}).lower()
    assert "sup3rsecret!" not in blob
    assert "password" not in blob
    assert "hashed" not in blob
    assert "token" not in blob


# ---------------------------------------------------------------------------
# Filters and authorization
# ---------------------------------------------------------------------------
async def test_filters_narrow_by_action(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    await _product(client, auth_headers, sku="FILTER-1")
    logs = await _audit(client, auth_headers, action="catalog.product.create")
    assert logs["items"]
    assert all(entry["action"] == "catalog.product.create" for entry in logs["items"])


async def test_cashier_cannot_read_the_audit_log(
    client: AsyncClient, cashier_headers: dict[str, str]
) -> None:
    response = await client.get(AUDIT, headers=cashier_headers)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "insufficient_permissions"


async def test_requires_auth(client: AsyncClient, anon_client: AsyncClient) -> None:
    assert (await anon_client.get(AUDIT)).status_code == 401
