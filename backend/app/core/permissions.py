"""Canonical permission catalog and default roles.

This module is the single source of truth for RBAC. The seed script
(``app.scripts.seed``) materialises it into the database, and endpoint guards
reference :class:`PermissionCode` — never free-form strings — so a typo becomes
a type error instead of a silently-unenforced rule.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class PermissionCode(StrEnum):
    # Staff & access control
    USERS_READ = "users:read"
    USERS_WRITE = "users:write"
    USERS_DELETE = "users:delete"
    ROLES_READ = "roles:read"
    ROLES_WRITE = "roles:write"

    # Organisation
    BRANCHES_READ = "branches:read"
    BRANCHES_WRITE = "branches:write"

    # Catalog (products, categories, modifiers)
    CATALOG_READ = "catalog:read"
    CATALOG_WRITE = "catalog:write"
    CATALOG_DELETE = "catalog:delete"

    # Inventory
    INVENTORY_READ = "inventory:read"
    INVENTORY_ADJUST = "inventory:adjust"

    # Selling
    SALES_CREATE = "sales:create"
    SALES_READ = "sales:read"
    SALES_VOID = "sales:void"
    SALES_REFUND = "sales:refund"

    # Customers
    CUSTOMERS_READ = "customers:read"
    CUSTOMERS_WRITE = "customers:write"

    # Insight
    REPORTS_VIEW = "reports:view"


@dataclass(frozen=True, slots=True)
class PermissionSpec:
    code: PermissionCode
    description: str

    @property
    def resource(self) -> str:
        return self.code.value.split(":", 1)[0]

    @property
    def action(self) -> str:
        return self.code.value.split(":", 1)[1]


PERMISSIONS: tuple[PermissionSpec, ...] = (
    PermissionSpec(PermissionCode.USERS_READ, "View staff accounts"),
    PermissionSpec(PermissionCode.USERS_WRITE, "Create and edit staff accounts"),
    PermissionSpec(PermissionCode.USERS_DELETE, "Deactivate staff accounts"),
    PermissionSpec(PermissionCode.ROLES_READ, "View roles and their permissions"),
    PermissionSpec(PermissionCode.ROLES_WRITE, "Create and edit roles"),
    PermissionSpec(PermissionCode.BRANCHES_READ, "View branches"),
    PermissionSpec(PermissionCode.BRANCHES_WRITE, "Create and edit branches"),
    PermissionSpec(PermissionCode.CATALOG_READ, "View products and categories"),
    PermissionSpec(PermissionCode.CATALOG_WRITE, "Create and edit products and categories"),
    PermissionSpec(PermissionCode.CATALOG_DELETE, "Delete products and categories"),
    PermissionSpec(PermissionCode.INVENTORY_READ, "View stock levels"),
    PermissionSpec(PermissionCode.INVENTORY_ADJUST, "Adjust and transfer stock"),
    PermissionSpec(PermissionCode.SALES_CREATE, "Ring up sales"),
    PermissionSpec(PermissionCode.SALES_READ, "View sales history"),
    PermissionSpec(PermissionCode.SALES_VOID, "Void sales"),
    PermissionSpec(PermissionCode.SALES_REFUND, "Issue refunds"),
    PermissionSpec(PermissionCode.CUSTOMERS_READ, "View customers"),
    PermissionSpec(PermissionCode.CUSTOMERS_WRITE, "Create and edit customers"),
    PermissionSpec(PermissionCode.REPORTS_VIEW, "View reports and analytics"),
)

ALL_PERMISSION_CODES: frozenset[str] = frozenset(spec.code.value for spec in PERMISSIONS)


@dataclass(frozen=True, slots=True)
class RoleSpec:
    name: str
    description: str
    permissions: frozenset[str]
    is_system: bool = True


DEFAULT_ROLES: tuple[RoleSpec, ...] = (
    RoleSpec(
        name="Administrator",
        description="Full access to every module and setting.",
        permissions=ALL_PERMISSION_CODES,
    ),
    RoleSpec(
        name="Manager",
        description="Runs day-to-day operations; cannot manage roles or delete records.",
        permissions=frozenset(
            {
                PermissionCode.USERS_READ,
                PermissionCode.USERS_WRITE,
                PermissionCode.ROLES_READ,
                PermissionCode.BRANCHES_READ,
                PermissionCode.BRANCHES_WRITE,
                PermissionCode.CATALOG_READ,
                PermissionCode.CATALOG_WRITE,
                PermissionCode.INVENTORY_READ,
                PermissionCode.INVENTORY_ADJUST,
                PermissionCode.SALES_CREATE,
                PermissionCode.SALES_READ,
                PermissionCode.SALES_VOID,
                PermissionCode.SALES_REFUND,
                PermissionCode.CUSTOMERS_READ,
                PermissionCode.CUSTOMERS_WRITE,
                PermissionCode.REPORTS_VIEW,
            }
        ),
    ),
    RoleSpec(
        name="Cashier",
        description="Front-of-house selling only.",
        permissions=frozenset(
            {
                PermissionCode.BRANCHES_READ,
                PermissionCode.CATALOG_READ,
                PermissionCode.INVENTORY_READ,
                PermissionCode.SALES_CREATE,
                PermissionCode.SALES_READ,
                PermissionCode.CUSTOMERS_READ,
                PermissionCode.CUSTOMERS_WRITE,
            }
        ),
    ),
)

DEFAULT_ROLE_NAMES: frozenset[str] = frozenset(role.name for role in DEFAULT_ROLES)
