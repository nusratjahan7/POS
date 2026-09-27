"""Role-based access control: the permission registry, the built-in roles, and
what each role may actually do over HTTP.

The database is the enforcement point. Every assertion about a denial below is
made against the API, not against a UI helper — hiding a button is presentation,
not authorization.
"""

from __future__ import annotations

from typing import Any

from httpx import AsyncClient

from app.core.permissions import ALL_PERMISSION_CODES, DEFAULT_ROLES, PERMISSIONS
from app.models.user import User

USERS = "/api/v1/users"
ROLES = "/api/v1/roles"
PERMISSIONS_URL = "/api/v1/permissions"
BRANCHES = "/api/v1/branches"
ME = "/api/v1/auth/me"

NEW_DOMAINS = {"purchases:view", "purchases:create", "settings:manage"}

INVENTORY_MANAGER_PERMISSIONS = {
    "branches:read",
    "catalog:read",
    "inventory:read",
    "inventory:adjust",
    "suppliers:read",
    "suppliers:write",
    "purchases:view",
    "purchases:create",
    "purchases:update",
    "reports:view",
}


def _role(name: str) -> Any:
    return next(spec for spec in DEFAULT_ROLES if spec.name == name)


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------
async def test_new_permission_domains_are_registered() -> None:
    codes = {spec.code.value for spec in PERMISSIONS}
    assert codes >= NEW_DOMAINS


async def test_every_permission_code_is_a_resource_action_pair() -> None:
    for spec in PERMISSIONS:
        assert spec.code.value == f"{spec.resource}:{spec.action}", spec.code


async def test_permission_codes_are_unique() -> None:
    codes = [spec.code.value for spec in PERMISSIONS]
    assert len(codes) == len(set(codes))


async def test_administrator_role_holds_every_permission() -> None:
    assert _role("Administrator").permissions == ALL_PERMISSION_CODES


async def test_inventory_manager_role_has_a_least_privilege_profile() -> None:
    spec = _role("Inventory Manager")
    assert spec.is_system is True
    assert set(spec.permissions) == INVENTORY_MANAGER_PERMISSIONS
    # It must not creep into selling, staff management or platform settings.
    for forbidden in ("sales:create", "sales:refund", "users:write", "settings:manage"):
        assert forbidden not in spec.permissions


async def test_builtin_roles_escalate_in_the_expected_direction() -> None:
    admin = set(_role("Administrator").permissions)
    manager = set(_role("Manager").permissions)
    inventory = set(_role("Inventory Manager").permissions)
    cashier = set(_role("Cashier").permissions)

    # Narrower roles are strict subsets of wider ones.
    assert cashier < manager < admin
    assert inventory < manager

    # The privileged capabilities stay with the Administrator alone.
    assert "settings:manage" not in manager
    assert "roles:write" not in manager
    assert "users:read" not in cashier
    assert "inventory:adjust" not in cashier


# ---------------------------------------------------------------------------
# Materialised in the database
# ---------------------------------------------------------------------------
async def test_all_builtin_roles_are_seeded(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    options = (await client.get(f"{ROLES}/options", headers=auth_headers)).json()
    names = {role["name"] for role in options}
    assert {"Administrator", "Manager", "Inventory Manager", "Cashier"} <= names


async def test_inventory_manager_role_row_carries_its_permissions(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    items = (await client.get(ROLES, headers=auth_headers)).json()["items"]
    role = next(item for item in items if item["name"] == "Inventory Manager")
    assert {permission["code"] for permission in role["permissions"]} == (
        INVENTORY_MANAGER_PERMISSIONS
    )


# ---------------------------------------------------------------------------
# Access matrix over HTTP
# ---------------------------------------------------------------------------
async def test_superuser_bypasses_permission_checks(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    assert (await client.get(USERS, headers=auth_headers)).status_code == 200
    assert (await client.get(PERMISSIONS_URL, headers=auth_headers)).status_code == 200
    created = await client.post(
        ROLES, headers=auth_headers, json={"name": "Floor Lead", "permission_codes": []}
    )
    assert created.status_code == 201


async def test_superuser_reports_a_wildcard_permission(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    body = (await client.get(ME, headers=auth_headers)).json()
    assert body["is_superuser"] is True
    assert body["permissions"] == ["*"]


async def test_administrator_role_can_manage_staff_and_roles(
    client: AsyncClient, login_as: Any, administrator: User
) -> None:
    headers = await login_as(administrator.email, "ManagerPass1!")

    assert (await client.get(USERS, headers=headers)).status_code == 200
    created = await client.post(
        ROLES, headers=headers, json={"name": "Shift Supervisor", "permission_codes": []}
    )
    assert created.status_code == 201


async def test_manager_can_manage_staff_but_not_roles(
    client: AsyncClient, manager_headers: dict[str, str]
) -> None:
    assert (await client.get(USERS, headers=manager_headers)).status_code == 200

    denied = await client.post(
        ROLES, headers=manager_headers, json={"name": "Shadow Admin", "permission_codes": []}
    )
    assert denied.status_code == 403
    assert denied.json()["error"]["code"] == "insufficient_permissions"


async def test_manager_cannot_reach_platform_settings(
    client: AsyncClient, manager_headers: dict[str, str]
) -> None:
    # settings:manage is Administrator-only; the Manager role must not hold it.
    me = (await client.get(ME, headers=manager_headers)).json()
    assert "settings:manage" not in me["permissions"]


async def test_cashier_cannot_read_staff_or_roles(
    client: AsyncClient, cashier_headers: dict[str, str]
) -> None:
    for path in (USERS, ROLES, PERMISSIONS_URL):
        denied = await client.get(path, headers=cashier_headers)
        assert denied.status_code == 403, path
        assert denied.json()["error"]["code"] == "insufficient_permissions"


async def test_cashier_can_read_what_the_role_allows(
    client: AsyncClient, cashier_headers: dict[str, str]
) -> None:
    assert (await client.get(BRANCHES, headers=cashier_headers)).status_code == 200


async def test_inventory_manager_cannot_reach_staff_or_selling_endpoints(
    client: AsyncClient, inventory_manager_headers: dict[str, str]
) -> None:
    denied = await client.get(USERS, headers=inventory_manager_headers)
    assert denied.status_code == 403
    assert denied.json()["error"]["code"] == "insufficient_permissions"

    assert (await client.get(BRANCHES, headers=inventory_manager_headers)).status_code == 200


async def test_effective_permissions_reported_for_a_roled_user(
    client: AsyncClient, inventory_manager_headers: dict[str, str]
) -> None:
    body = (await client.get(ME, headers=inventory_manager_headers)).json()

    assert body["is_superuser"] is False
    assert body["roles"][0]["name"] == "Inventory Manager"

    granted = set(body["permissions"])
    assert {"inventory:adjust", "purchases:create"} <= granted
    assert "sales:create" not in granted
    assert "users:write" not in granted
    assert "settings:manage" not in granted


async def test_denial_names_the_missing_permission(
    client: AsyncClient, cashier_headers: dict[str, str]
) -> None:
    denied = await client.get(USERS, headers=cashier_headers)
    details = denied.json()["error"]["details"]

    assert details
    assert "users:read" in details[0]["message"]


async def test_anonymous_requests_are_rejected_everywhere(
    client: AsyncClient,
) -> None:
    for path in (USERS, ROLES, PERMISSIONS_URL, BRANCHES):
        response = await client.get(path)
        assert response.status_code == 401, path
        assert response.json()["error"]["code"] == "unauthorized"


async def test_a_user_with_no_roles_is_denied_everything(
    client: AsyncClient, login_as: Any, db_session: Any
) -> None:
    """Permissions come from roles only — an unroled account has no implicit access."""
    from app.core.security import hash_password

    user = User(
        email="no-roles@example.com",
        hashed_password=hash_password("NoRolesPass1!"),
        full_name="Test Unroled",
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()

    headers = await login_as(user.email, "NoRolesPass1!")
    me = (await client.get(ME, headers=headers)).json()
    assert me["permissions"] == []
    assert me["roles"] == []

    denied = await client.get(USERS, headers=headers)
    assert denied.status_code == 403
    assert denied.json()["error"]["code"] == "insufficient_permissions"
