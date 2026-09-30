"""Idempotent bootstrap.

    uv run python -m app.scripts.seed

Creates/refreshes the permission catalog, the built-in roles, a default branch,
and the initial superuser. Safe to run repeatedly: existing rows are updated in
place and an existing superuser's password is never overwritten.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TypedDict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import configure_logging
from app.core.permissions import DEFAULT_ROLES, PERMISSIONS
from app.core.security import hash_password
from app.db.session import SessionFactory
from app.models.branch import Branch
from app.models.business import Business
from app.models.expense_category import ExpenseCategory
from app.models.payment_method import PaymentMethod
from app.models.permission import Permission
from app.models.register import Register
from app.models.role import Role
from app.models.user import User
from app.utils.text import normalize_email

logger = logging.getLogger("app.seed")

DEFAULT_BRANCH_CODE = "MAIN"
DEFAULT_BRANCH_NAME = "Main Branch"
DEFAULT_BUSINESS_NAME = "My Business"
DEFAULT_REGISTER_NAME = "Front Counter"
ADMINISTRATOR_ROLE = "Administrator"

# The buckets a new installation files expenses under.
DEFAULT_EXPENSE_CATEGORIES: tuple[str, ...] = (
    "Rent",
    "Utilities",
    "Salaries",
    "Supplies",
    "Other",
)


# The payment methods a new installation can tender with. `is_system` rows are
# protected from deletion and re-coding (see PaymentMethodService).
class _PaymentMethodSeed(TypedDict, total=False):
    name: str
    code: str
    kind: str
    opens_cash_drawer: bool
    requires_reference: bool
    sort_order: int


DEFAULT_PAYMENT_METHODS: tuple[_PaymentMethodSeed, ...] = (
    {
        "name": "Cash",
        "code": "CASH",
        "kind": "cash",
        "opens_cash_drawer": True,
        "sort_order": 1,
    },
    {"name": "Card", "code": "CARD", "kind": "card", "requires_reference": True, "sort_order": 2},
    {
        "name": "bKash",
        "code": "BKASH",
        "kind": "mobile",
        "requires_reference": True,
        "sort_order": 3,
    },
    {
        "name": "Nagad",
        "code": "NAGAD",
        "kind": "mobile",
        "requires_reference": True,
        "sort_order": 4,
    },
    {"name": "Bank", "code": "BANK", "kind": "bank", "requires_reference": True, "sort_order": 5},
    {"name": "Other", "code": "OTHER", "kind": "other", "sort_order": 6},
)


async def seed_permissions(session: AsyncSession) -> dict[str, Permission]:
    existing = {p.code: p for p in (await session.execute(select(Permission))).scalars()}

    created = 0
    for spec in PERMISSIONS:
        code = spec.code.value
        permission = existing.get(code)
        if permission is None:
            permission = Permission(
                code=code,
                resource=spec.resource,
                action=spec.action,
                description=spec.description,
            )
            session.add(permission)
            existing[code] = permission
            created += 1
        else:
            permission.resource = spec.resource
            permission.action = spec.action
            permission.description = spec.description

    await session.flush()
    logger.info("Permissions: %d total (%d created)", len(existing), created)
    return existing


async def seed_roles(session: AsyncSession, permissions: dict[str, Permission]) -> dict[str, Role]:
    existing = {r.name: r for r in (await session.execute(select(Role))).scalars()}

    created = 0
    for spec in DEFAULT_ROLES:
        role = existing.get(spec.name)
        if role is None:
            role = Role(name=spec.name, is_system=spec.is_system)
            session.add(role)
            existing[spec.name] = role
            created += 1
        role.description = spec.description
        role.is_system = spec.is_system
        codes = sorted(str(code) for code in spec.permissions)
        role.permissions = [permissions[code] for code in codes]

    await session.flush()
    logger.info("Roles: %d total (%d created)", len(existing), created)
    return existing


async def seed_branch(session: AsyncSession) -> Branch:
    branch = (
        await session.execute(select(Branch).where(Branch.code == DEFAULT_BRANCH_CODE))
    ).scalar_one_or_none()
    if branch is None:
        branch = Branch(name=DEFAULT_BRANCH_NAME, code=DEFAULT_BRANCH_CODE, is_active=True)
        session.add(branch)
        await session.flush()
        logger.info("Created default branch %s", DEFAULT_BRANCH_CODE)
    return branch


async def seed_business(session: AsyncSession, *, branch: Branch) -> Business:
    business = (
        (await session.execute(select(Business).order_by(Business.created_at.asc()).limit(1)))
        .scalars()
        .first()
    )
    if business is None:
        business = Business(name=DEFAULT_BUSINESS_NAME, currency="USD", timezone="UTC")
        session.add(business)
        await session.flush()
        logger.info("Created default business %s", DEFAULT_BUSINESS_NAME)
    if branch.business_id is None:
        branch.business_id = business.id
    return business


async def seed_payment_methods(session: AsyncSession) -> dict[str, PaymentMethod]:
    existing = {
        method.code: method for method in (await session.execute(select(PaymentMethod))).scalars()
    }

    created = 0
    for spec in DEFAULT_PAYMENT_METHODS:
        code = str(spec["code"])
        method = existing.get(code)
        if method is None:
            method = PaymentMethod(code=code, is_system=True)
            session.add(method)
            existing[code] = method
            created += 1
        method.name = str(spec["name"])
        method.kind = str(spec["kind"])
        method.opens_cash_drawer = bool(spec.get("opens_cash_drawer", False))
        method.requires_reference = bool(spec.get("requires_reference", False))
        method.sort_order = int(spec.get("sort_order", 0))
        method.is_system = True

    await session.flush()
    logger.info("Payment methods: %d total (%d created)", len(existing), created)
    return existing


async def seed_register(session: AsyncSession, *, branch: Branch) -> Register:
    register = (
        await session.execute(
            select(Register).where(
                Register.branch_id == branch.id, Register.name == DEFAULT_REGISTER_NAME
            )
        )
    ).scalar_one_or_none()
    if register is None:
        register = Register(name=DEFAULT_REGISTER_NAME, branch=branch, is_active=True)
        session.add(register)
        await session.flush()
        logger.info("Created default register %s", DEFAULT_REGISTER_NAME)
    return register


async def seed_expense_categories(session: AsyncSession) -> None:
    existing = {
        category.name
        for category in (
            await session.execute(
                select(ExpenseCategory).where(ExpenseCategory.deleted_at.is_(None))
            )
        ).scalars()
    }
    created = 0
    for name in DEFAULT_EXPENSE_CATEGORIES:
        if name not in existing:
            session.add(ExpenseCategory(name=name, is_active=True))
            created += 1
    await session.flush()
    logger.info("Expense categories: %d total (%d created)", len(existing) + created, created)


async def seed_superuser(
    session: AsyncSession,
    *,
    branch: Branch,
    roles: dict[str, Role],
) -> User:
    email = normalize_email(str(settings.FIRST_SUPERUSER_EMAIL))
    user = (await session.execute(select(User).where(User.email == email))).scalar_one_or_none()

    administrator = roles.get(ADMINISTRATOR_ROLE)
    if user is None:
        user = User(
            email=email,
            hashed_password=hash_password(settings.FIRST_SUPERUSER_PASSWORD),
            full_name=settings.FIRST_SUPERUSER_FULL_NAME,
            is_active=True,
            is_superuser=True,
            branch=branch,
        )
        if administrator is not None:
            user.roles = [administrator]
        session.add(user)
        await session.flush()
        logger.info("Created superuser %s", email)
    else:
        user.is_superuser = True
        if administrator is not None and administrator not in user.roles:
            user.roles = [*user.roles, administrator]
        logger.info("Superuser %s already exists (password untouched)", email)
    return user


async def run() -> None:
    configure_logging()
    async with SessionFactory() as session:
        permissions = await seed_permissions(session)
        roles = await seed_roles(session, permissions)
        branch = await seed_branch(session)
        await seed_business(session, branch=branch)
        await seed_payment_methods(session)
        await seed_register(session, branch=branch)
        await seed_expense_categories(session)
        await seed_superuser(session, branch=branch, roles=roles)
        await session.commit()
    logger.info("Seed complete. Sign in as %s", settings.FIRST_SUPERUSER_EMAIL)


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
