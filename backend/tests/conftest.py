"""Shared pytest fixtures.

The suite runs against a real PostgreSQL database (``TEST_DATABASE_URL``) — the
models use PostgreSQL-specific types, so SQLite would give false confidence.

Each test is isolated inside an outer transaction that is rolled back
afterwards; service-level ``commit()`` calls only release a SAVEPOINT, so nothing
leaks between tests.
"""

from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncIterator, Iterator
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from alembic import command
from alembic.config import Config
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

BACKEND_DIR = Path(__file__).resolve().parents[1]
TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+asyncpg://pos:pos@localhost:5432/pos_test"
)

# The application and Alembic both read DATABASE_URL, so redirect them before any
# application module is imported.
os.environ["ENVIRONMENT"] = "test"
os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ["RATE_LIMIT_ENABLED"] = "false"

from app.core.rate_limit import rate_limiter  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.db.session import get_session  # noqa: E402
from app.main import app  # noqa: E402
from app.models.user import User  # noqa: E402
from app.scripts.seed import (  # noqa: E402
    seed_branch,
    seed_business,
    seed_expense_categories,
    seed_payment_methods,
    seed_permissions,
    seed_register,
    seed_roles,
)

SUPERUSER_PASSWORD = "SuperSecret1!"
CASHIER_PASSWORD = "CashierPass1!"


def _run_async(coro: Any) -> Any:
    return asyncio.run(coro)


def _database_reachable() -> bool:
    async def _probe() -> None:
        engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)
        try:
            async with engine.connect() as connection:
                await connection.execute(text("SELECT 1"))
        finally:
            await engine.dispose()

    try:
        _run_async(_probe())
    except Exception:  # pragma: no cover - environment dependent
        return False
    return True


def _reset_schema_and_migrate() -> None:
    """Drop and recreate the ``public`` schema, then apply all migrations.

    Recreating the schema (rather than dropping tables) also clears
    ``alembic_version``, so every run starts from a genuine empty state.
    """

    async def _reset() -> None:
        engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)
        try:
            async with engine.begin() as connection:
                await connection.execute(text("DROP SCHEMA public CASCADE"))
                await connection.execute(text("CREATE SCHEMA public"))
        finally:
            await engine.dispose()

    _run_async(_reset())

    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    command.upgrade(config, "head")


@pytest.fixture(scope="session", autouse=True)
def prepared_database() -> Iterator[None]:
    if not _database_reachable():
        pytest.skip(
            f"PostgreSQL is not reachable at {TEST_DATABASE_URL}. "
            "Start it with `docker compose up -d` and run `uv run pytest` again.",
            allow_module_level=True,
        )
    _reset_schema_and_migrate()
    yield


@pytest.fixture
async def connection() -> AsyncIterator[AsyncConnection]:
    engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)
    async with engine.connect() as conn:
        transaction = await conn.begin()
        try:
            yield conn
        finally:
            await transaction.rollback()
            await engine.dispose()


@pytest.fixture
async def db_session(connection: AsyncConnection) -> AsyncIterator[AsyncSession]:
    session = AsyncSession(
        bind=connection,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    )
    try:
        yield session
    finally:
        await session.close()


@pytest.fixture
async def client(db_session: AsyncSession) -> AsyncIterator[AsyncClient]:
    async def _override_session() -> AsyncIterator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_session] = _override_session
    rate_limiter.reset()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as http:
        yield http
    app.dependency_overrides.clear()


@pytest.fixture
async def seeded(db_session: AsyncSession) -> SimpleNamespace:
    """Materialise the permission catalog, built-in roles, a branch and store settings."""
    permissions = await seed_permissions(db_session)
    roles = await seed_roles(db_session, permissions)
    branch = await seed_branch(db_session)
    business = await seed_business(db_session, branch=branch)
    payment_methods = await seed_payment_methods(db_session)
    register = await seed_register(db_session, branch=branch)
    await seed_expense_categories(db_session)
    await db_session.commit()
    return SimpleNamespace(
        permissions=permissions,
        roles=roles,
        branch=branch,
        business=business,
        payment_methods=payment_methods,
        register=register,
    )


@pytest.fixture
async def superuser(db_session: AsyncSession, seeded: SimpleNamespace) -> User:
    user = User(
        email="admin@example.com",
        hashed_password=hash_password(SUPERUSER_PASSWORD),
        full_name="Test Administrator",
        is_active=True,
        is_superuser=True,
        branch=seeded.branch,
    )
    user.roles = [seeded.roles["Administrator"]]
    db_session.add(user)
    await db_session.commit()
    return user


async def _login(client: AsyncClient, email: str, password: str) -> dict[str, str]:
    response = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture
def login_as(client: AsyncClient) -> Any:
    """Return an async helper that logs a user in and yields auth headers."""

    async def _login_as(email: str, password: str) -> dict[str, str]:
        return await _login(client, email, password)

    return _login_as


@pytest.fixture
async def anon_client(client: AsyncClient) -> AsyncIterator[AsyncClient]:
    """A cookie-less client (depends on ``client`` so overrides are installed)."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as http:
        yield http


@pytest.fixture
async def auth_headers(client: AsyncClient, superuser: User) -> dict[str, str]:
    return await _login(client, superuser.email, SUPERUSER_PASSWORD)


@pytest.fixture
async def cashier(db_session: AsyncSession, seeded: SimpleNamespace) -> User:
    """A user with the built-in Cashier role: no staff-management permissions."""
    user = User(
        email="cashier@example.com",
        hashed_password=hash_password(CASHIER_PASSWORD),
        full_name="Test Cashier",
        is_active=True,
        branch=seeded.branch,
    )
    user.roles = [seeded.roles["Cashier"]]
    db_session.add(user)
    await db_session.commit()
    return user


@pytest.fixture
async def cashier_headers(client: AsyncClient, cashier: User) -> dict[str, str]:
    return await _login(client, cashier.email, CASHIER_PASSWORD)


@pytest.fixture
async def administrator(db_session: AsyncSession, seeded: SimpleNamespace) -> User:
    """A non-superuser holding the Administrator role (permission-driven access)."""
    user = User(
        email="manager@example.com",
        hashed_password=hash_password("ManagerPass1!"),
        full_name="Test Manager",
        is_active=True,
        branch=seeded.branch,
    )
    user.roles = [seeded.roles["Administrator"]]
    db_session.add(user)
    await db_session.commit()
    return user


MANAGER_ROLE_PASSWORD = "OpsManager1!"
INVENTORY_PASSWORD = "InventoryRole1!"


@pytest.fixture
async def manager_user(db_session: AsyncSession, seeded: SimpleNamespace) -> User:
    """A user holding the built-in Manager role: operations, but not roles/settings."""
    user = User(
        email="ops-manager@example.com",
        hashed_password=hash_password(MANAGER_ROLE_PASSWORD),
        full_name="Test Operations Manager",
        is_active=True,
        branch=seeded.branch,
    )
    user.roles = [seeded.roles["Manager"]]
    db_session.add(user)
    await db_session.commit()
    return user


@pytest.fixture
async def manager_headers(client: AsyncClient, manager_user: User) -> dict[str, str]:
    return await _login(client, manager_user.email, MANAGER_ROLE_PASSWORD)


@pytest.fixture
async def inventory_manager(db_session: AsyncSession, seeded: SimpleNamespace) -> User:
    """A user holding the built-in Inventory Manager role: stock and purchasing only."""
    user = User(
        email="inventory@example.com",
        hashed_password=hash_password(INVENTORY_PASSWORD),
        full_name="Test Inventory Manager",
        is_active=True,
        branch=seeded.branch,
    )
    user.roles = [seeded.roles["Inventory Manager"]]
    db_session.add(user)
    await db_session.commit()
    return user


@pytest.fixture
async def inventory_manager_headers(client: AsyncClient, inventory_manager: User) -> dict[str, str]:
    return await _login(client, inventory_manager.email, INVENTORY_PASSWORD)
