"""Role & permission API: catalog access, system-role protection, referential guards."""

from __future__ import annotations

from types import SimpleNamespace

from httpx import AsyncClient

from app.core.permissions import PERMISSIONS
from app.models.user import User

ROLES = "/api/v1/roles"
PERMISSIONS_URL = "/api/v1/permissions"
USERS = "/api/v1/users"


async def test_list_roles_includes_seeded_roles(
    client: AsyncClient, auth_headers: dict[str, str], seeded: SimpleNamespace
) -> None:
    response = await client.get(ROLES, headers=auth_headers)
    assert response.status_code == 200
    names = {role["name"] for role in response.json()["items"]}
    assert {"Administrator", "Manager", "Cashier"} <= names


async def test_role_options_is_a_lightweight_list(
    client: AsyncClient, auth_headers: dict[str, str], seeded: SimpleNamespace
) -> None:
    response = await client.get(f"{ROLES}/options", headers=auth_headers)
    assert response.status_code == 200
    options = response.json()
    assert options
    assert set(options[0]) == {"id", "name"}


async def test_create_custom_role_with_permissions(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    response = await client.post(
        ROLES,
        headers=auth_headers,
        json={
            "name": "Stock Clerk",
            "description": "Receives stock",
            "permission_codes": ["catalog:read", "inventory:read"],
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["is_system"] is False
    assert sorted(permission["code"] for permission in body["permissions"]) == [
        "catalog:read",
        "inventory:read",
    ]


async def test_create_role_rejects_duplicate_name(
    client: AsyncClient, auth_headers: dict[str, str], seeded: SimpleNamespace
) -> None:
    response = await client.post(
        ROLES, headers=auth_headers, json={"name": "Cashier", "permission_codes": []}
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "role_name_taken"


async def test_create_role_rejects_unknown_permission(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    response = await client.post(
        ROLES,
        headers=auth_headers,
        json={"name": "Broken", "permission_codes": ["does:not-exist"]},
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_permissions"


async def test_system_role_cannot_be_renamed(
    client: AsyncClient, auth_headers: dict[str, str], seeded: SimpleNamespace
) -> None:
    role_id = seeded.roles["Cashier"].id
    response = await client.patch(
        f"{ROLES}/{role_id}", headers=auth_headers, json={"name": "Renamed"}
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "system_role_immutable"


async def test_system_role_permissions_can_be_updated(
    client: AsyncClient, auth_headers: dict[str, str], seeded: SimpleNamespace
) -> None:
    role_id = seeded.roles["Cashier"].id
    response = await client.patch(
        f"{ROLES}/{role_id}",
        headers=auth_headers,
        json={"permission_codes": ["sales:create"]},
    )
    assert response.status_code == 200
    assert [p["code"] for p in response.json()["permissions"]] == ["sales:create"]


async def test_role_in_use_cannot_be_deleted(
    client: AsyncClient, auth_headers: dict[str, str], cashier: User
) -> None:
    """A deletable role still assigned to someone is blocked by the referential guard.

    System roles are protected earlier and rejected with 403, so this exercises
    the `role_in_use` branch using a custom role that would otherwise be deletable.
    """
    created = await client.post(
        ROLES, headers=auth_headers, json={"name": "Shift Lead", "permission_codes": []}
    )
    assert created.status_code == 201
    role_id = created.json()["id"]

    assigned = await client.patch(
        f"{USERS}/{cashier.id}", headers=auth_headers, json={"role_ids": [role_id]}
    )
    assert assigned.status_code == 200

    response = await client.delete(f"{ROLES}/{role_id}", headers=auth_headers)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "role_in_use"


async def test_unused_custom_role_can_be_deleted(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    created = await client.post(
        ROLES, headers=auth_headers, json={"name": "Temporary", "permission_codes": []}
    )
    role_id = created.json()["id"]

    response = await client.delete(f"{ROLES}/{role_id}", headers=auth_headers)
    assert response.status_code == 204

    # Soft-deleted roles are no longer readable.
    assert (await client.get(f"{ROLES}/{role_id}", headers=auth_headers)).status_code == 404


async def test_permission_catalog_matches_the_registry(
    client: AsyncClient, auth_headers: dict[str, str], seeded: SimpleNamespace
) -> None:
    response = await client.get(PERMISSIONS_URL, headers=auth_headers)
    assert response.status_code == 200
    codes = {permission["code"] for permission in response.json()}
    assert codes == {spec.code.value for spec in PERMISSIONS}


async def test_cashier_cannot_manage_roles(
    client: AsyncClient, cashier_headers: dict[str, str]
) -> None:
    assert (await client.get(ROLES, headers=cashier_headers)).status_code == 403
    assert (await client.get(PERMISSIONS_URL, headers=cashier_headers)).status_code == 403
