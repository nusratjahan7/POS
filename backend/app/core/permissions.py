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
    USERS_RESET_PASSWORD = "users:reset_password"
    ROLES_READ = "roles:read"
    ROLES_WRITE = "roles:write"

    # Organisation
    BRANCHES_READ = "branches:read"
    BRANCHES_WRITE = "branches:write"

    # Store settings (the business entity, its registers and payment methods)
    BUSINESS_READ = "business:read"
    BUSINESS_WRITE = "business:write"
    REGISTERS_READ = "registers:read"
    REGISTERS_WRITE = "registers:write"
    PAYMENTS_READ = "payments:read"
    PAYMENTS_WRITE = "payments:write"

    # Catalog (products, categories, modifiers)
    CATALOG_READ = "catalog:read"
    CATALOG_WRITE = "catalog:write"
    CATALOG_DELETE = "catalog:delete"

    # Inventory
    INVENTORY_READ = "inventory:read"
    INVENTORY_ADJUST = "inventory:adjust"

    # Purchasing (suppliers and purchase orders)
    SUPPLIERS_READ = "suppliers:read"
    SUPPLIERS_WRITE = "suppliers:write"
    PURCHASES_VIEW = "purchases:view"
    PURCHASES_CREATE = "purchases:create"
    PURCHASES_UPDATE = "purchases:update"

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

    # Platform administration
    SETTINGS_READ = "settings:read"
    SETTINGS_MANAGE = "settings:manage"


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
    PermissionSpec(
        PermissionCode.USERS_RESET_PASSWORD, "Reset another user's password (Administrator only)"
    ),
    PermissionSpec(PermissionCode.ROLES_READ, "View roles and their permissions"),
    PermissionSpec(PermissionCode.ROLES_WRITE, "Create and edit roles"),
    PermissionSpec(PermissionCode.BRANCHES_READ, "View branches"),
    PermissionSpec(PermissionCode.BRANCHES_WRITE, "Create and edit branches"),
    PermissionSpec(PermissionCode.BUSINESS_READ, "View the business profile and tax settings"),
    PermissionSpec(PermissionCode.BUSINESS_WRITE, "Edit the business profile and tax settings"),
    PermissionSpec(PermissionCode.REGISTERS_READ, "View registers"),
    PermissionSpec(PermissionCode.REGISTERS_WRITE, "Create and edit registers"),
    PermissionSpec(PermissionCode.PAYMENTS_READ, "View payment methods"),
    PermissionSpec(PermissionCode.PAYMENTS_WRITE, "Create and edit payment methods"),
    PermissionSpec(PermissionCode.CATALOG_READ, "View products and categories"),
    PermissionSpec(PermissionCode.CATALOG_WRITE, "Create and edit products and categories"),
    PermissionSpec(PermissionCode.CATALOG_DELETE, "Delete products and categories"),
    PermissionSpec(PermissionCode.INVENTORY_READ, "View stock levels"),
    PermissionSpec(PermissionCode.INVENTORY_ADJUST, "Adjust and transfer stock"),
    PermissionSpec(PermissionCode.SUPPLIERS_READ, "View suppliers and their balances"),
    PermissionSpec(PermissionCode.SUPPLIERS_WRITE, "Create and edit suppliers"),
    PermissionSpec(PermissionCode.PURCHASES_VIEW, "View purchase orders and receipts"),
    PermissionSpec(PermissionCode.PURCHASES_CREATE, "Raise purchase orders"),
    PermissionSpec(PermissionCode.PURCHASES_UPDATE, "Edit, receive and cancel purchase orders"),
    PermissionSpec(PermissionCode.SALES_CREATE, "Ring up sales"),
    PermissionSpec(PermissionCode.SALES_READ, "View sales history"),
    PermissionSpec(PermissionCode.SALES_VOID, "Void sales"),
    PermissionSpec(PermissionCode.SALES_REFUND, "Issue refunds"),
    PermissionSpec(PermissionCode.CUSTOMERS_READ, "View customers"),
    PermissionSpec(PermissionCode.CUSTOMERS_WRITE, "Create and edit customers"),
    PermissionSpec(PermissionCode.REPORTS_VIEW, "View reports and analytics"),
    PermissionSpec(PermissionCode.SETTINGS_READ, "Access the organisation settings area"),
    PermissionSpec(PermissionCode.SETTINGS_MANAGE, "Manage organisation-wide settings"),
)

ALL_PERMISSION_CODES: frozenset[str] = frozenset(spec.code.value for spec in PERMISSIONS)

# The built-in role that owns the whole catalog. It is protected from edits, and
# an account holding it (or a superuser) is treated as an *administrator* by the
# password-protection guards — one shared name, referenced in one place.
ADMINISTRATOR_ROLE_NAME = "Administrator"


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
                PermissionCode.BUSINESS_READ,
                PermissionCode.REGISTERS_READ,
                PermissionCode.REGISTERS_WRITE,
                PermissionCode.PAYMENTS_READ,
                PermissionCode.PAYMENTS_WRITE,
                PermissionCode.SETTINGS_READ,
                PermissionCode.CATALOG_READ,
                PermissionCode.CATALOG_WRITE,
                PermissionCode.INVENTORY_READ,
                PermissionCode.INVENTORY_ADJUST,
                PermissionCode.SUPPLIERS_READ,
                PermissionCode.SUPPLIERS_WRITE,
                PermissionCode.PURCHASES_VIEW,
                PermissionCode.PURCHASES_CREATE,
                PermissionCode.PURCHASES_UPDATE,
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
        name="Inventory Manager",
        description="Owns stock levels and supplier orders; no access to selling or staff.",
        permissions=frozenset(
            {
                PermissionCode.BRANCHES_READ,
                PermissionCode.CATALOG_READ,
                PermissionCode.INVENTORY_READ,
                PermissionCode.INVENTORY_ADJUST,
                PermissionCode.SUPPLIERS_READ,
                PermissionCode.SUPPLIERS_WRITE,
                PermissionCode.PURCHASES_VIEW,
                PermissionCode.PURCHASES_CREATE,
                PermissionCode.PURCHASES_UPDATE,
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
                PermissionCode.BUSINESS_READ,
                PermissionCode.REGISTERS_READ,
                PermissionCode.PAYMENTS_READ,
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
