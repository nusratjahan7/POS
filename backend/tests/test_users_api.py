"""Staff account API: creation, listing, updates, guards and authorization."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from httpx import AsyncClient

from app.models.user import User

USERS = "/api/v1/users"


def _new_user_payload(seeded: SimpleNamespace, **overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "email": "new.hire@example.com",
        "full_name": "New Hire",
        "password": "Str0ngPass!",
        "role_ids": [str(seeded.roles["Cashier"].id)],
        "branch_id": str(seeded.branch.id),
    }
    payload.update(overrides)
    return payload


async def test_create_user(
    client: AsyncClient, auth_headers: dict[str, str], seeded: SimpleNamespace
) -> None:
    response = await client.post(USERS, headers=auth_headers, json=_new_user_payload(seeded))
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["email"] == "new.hire@example.com"
    assert body["is_active"] is True
    assert body["is_superuser"] is False
    assert [role["name"] for role in body["roles"]] == ["Cashier"]
    assert body["branch"]["code"] == seeded.branch.code
    # The role's permissions are surfaced on the created account. Cashiers sell
    # but no longer carry catalogue access (see test_products_api).
    assert "sales:create" in body["permissions"]
    assert "catalog:read" not in body["permissions"]
    assert "users:read" not in body["permissions"]
    assert "hashed_password" not in body


async def test_create_user_rejects_duplicate_email(
    client: AsyncClient, auth_headers: dict[str, str], seeded: SimpleNamespace, superuser: User
) -> None:
    response = await client.post(
        USERS, headers=auth_headers, json=_new_user_payload(seeded, email=superuser.email)
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "email_already_used"


async def test_create_user_validates_input(
    client: AsyncClient, auth_headers: dict[str, str], seeded: SimpleNamespace
) -> None:
    response = await client.post(
        USERS,
        headers=auth_headers,
        json=_new_user_payload(seeded, email="not-an-email", password="weak"),
    )
    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "validation_error"
    fields = {detail["field"] for detail in body["error"]["details"]}
    assert "email" in fields
    assert "password" in fields


async def test_create_user_rejects_unknown_role(
    client: AsyncClient, auth_headers: dict[str, str], seeded: SimpleNamespace
) -> None:
    response = await client.post(
        USERS,
        headers=auth_headers,
        json=_new_user_payload(seeded, role_ids=["00000000-0000-0000-0000-000000000000"]),
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_roles"


async def test_only_superusers_can_grant_superuser(
    client: AsyncClient, login_as: Any, administrator: User, seeded: SimpleNamespace
) -> None:
    headers = await login_as(administrator.email, "ManagerPass1!")
    response = await client.post(
        USERS,
        headers=headers,
        json=_new_user_payload(seeded, email="sneaky.admin@example.com", is_superuser=True),
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "superuser_required"


async def test_list_users_is_paginated(
    client: AsyncClient, auth_headers: dict[str, str], superuser: User
) -> None:
    response = await client.get(USERS, headers=auth_headers, params={"page": 1, "page_size": 1})
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"items", "total", "page", "page_size", "pages"}
    assert body["page"] == 1
    assert body["page_size"] == 1
    assert len(body["items"]) == 1
    assert body["total"] >= 1


async def test_list_users_search_and_sort(
    client: AsyncClient, auth_headers: dict[str, str], superuser: User
) -> None:
    response = await client.get(
        USERS, headers=auth_headers, params={"search": "admin", "sort": "email"}
    )
    assert response.status_code == 200
    emails = [item["email"] for item in response.json()["items"]]
    assert "admin@example.com" in emails


async def test_list_users_rejects_unknown_sort_field(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    response = await client.get(USERS, headers=auth_headers, params={"sort": "password"})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_sort_field"


async def test_permission_denied_for_insufficient_role(
    client: AsyncClient, cashier_headers: dict[str, str]
) -> None:
    response = await client.get(USERS, headers=cashier_headers)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "insufficient_permissions"


async def test_get_unknown_user_returns_not_found(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    response = await client.get(
        f"{USERS}/00000000-0000-0000-0000-000000000000", headers=auth_headers
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "user_not_found"


async def test_update_user_changes_role_and_activation(
    client: AsyncClient, auth_headers: dict[str, str], seeded: SimpleNamespace
) -> None:
    created = await client.post(USERS, headers=auth_headers, json=_new_user_payload(seeded))
    user_id = created.json()["id"]

    response = await client.patch(
        f"{USERS}/{user_id}",
        headers=auth_headers,
        json={
            "full_name": "Promoted Person",
            "role_ids": [str(seeded.roles["Manager"].id)],
            "branch_id": None,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["full_name"] == "Promoted Person"
    assert body["branch"] is None
    assert [role["name"] for role in body["roles"]] == ["Manager"]


async def test_user_cannot_deactivate_themselves(
    client: AsyncClient, auth_headers: dict[str, str], superuser: User
) -> None:
    response = await client.delete(f"{USERS}/{superuser.id}", headers=auth_headers)
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "cannot_deactivate_self"


async def test_last_superuser_cannot_be_deactivated(
    client: AsyncClient, login_as: Any, administrator: User, superuser: User
) -> None:
    headers = await login_as(administrator.email, "ManagerPass1!")
    response = await client.delete(f"{USERS}/{superuser.id}", headers=headers)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "last_superuser"


async def test_deactivate_user_revokes_access(
    client: AsyncClient, auth_headers: dict[str, str], seeded: SimpleNamespace
) -> None:
    created = await client.post(USERS, headers=auth_headers, json=_new_user_payload(seeded))
    user_id = created.json()["id"]

    response = await client.delete(f"{USERS}/{user_id}", headers=auth_headers)
    assert response.status_code == 204

    # Soft-deleted users disappear from reads.
    assert (await client.get(f"{USERS}/{user_id}", headers=auth_headers)).status_code == 404


async def test_admin_can_reset_a_password(
    client: AsyncClient, auth_headers: dict[str, str], seeded: SimpleNamespace
) -> None:
    created = await client.post(USERS, headers=auth_headers, json=_new_user_payload(seeded))
    user_id = created.json()["id"]

    response = await client.post(
        f"{USERS}/{user_id}/password",
        headers=auth_headers,
        json={"password": "ResetPass1!"},
    )
    assert response.status_code == 200

    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "new.hire@example.com", "password": "ResetPass1!"},
    )
    assert login.status_code == 200
