"""Idempotent bootstrap.

    uv run python -m app.scripts.seed

Creates/refreshes the permission catalog, the built-in roles, a default branch,
and the initial superuser. Safe to run repeatedly: existing rows are updated in
place and an existing superuser's password is never overwritten.
"""

from __future__ import annotations

import asyncio
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import configure_logging
from app.core.permissions import DEFAULT_ROLES, PERMISSIONS
from app.core.security import hash_password
from app.db.session import SessionFactory
from app.models.branch import Branch
from app.models.permission import Permission
from app.models.role import Role
from app.models.user import User
from app.utils.text import normalize_email

logger = logging.getLogger("app.seed")

DEFAULT_BRANCH_CODE = "MAIN"
DEFAULT_BRANCH_NAME = "Main Branch"
ADMINISTRATOR_ROLE = "Administrator"


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
        await seed_superuser(session, branch=branch, roles=roles)
        await session.commit()
    logger.info("Seed complete. Sign in as %s", settings.FIRST_SUPERUSER_EMAIL)


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
