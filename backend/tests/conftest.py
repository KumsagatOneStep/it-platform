import os

os.environ["APP_ENV"] = "test"
os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+asyncpg://app:app@localhost:5432/it_platform_test"
)
os.environ["REDIS_URL"] = os.environ.get("TEST_REDIS_URL", "redis://localhost:6379/15")
os.environ["COOKIE_SECURE"] = "false"

from collections.abc import AsyncIterator

import pytest
from alembic import command
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import get_settings
from app.core.db import get_session
from app.core.redis import get_redis, resolve
from app.main import create_app
from app.modules.users_auth.models import User, UserRole
from tests.db_utils import alembic_config
from tests.factories import login, make_user


@pytest.fixture(scope="session", autouse=True)
def _migrated_database() -> None:
    config = alembic_config()
    command.downgrade(config, "base")
    command.upgrade(config, "head")


@pytest.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    """Сессия внутри внешней транзакции, которая откатывается после теста."""
    engine = create_async_engine(get_settings().database_url, poolclass=NullPool)
    async with engine.connect() as connection:
        transaction = await connection.begin()
        session = AsyncSession(
            bind=connection,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint",
        )
        try:
            yield session
        finally:
            await session.close()
            await transaction.rollback()
    await engine.dispose()


@pytest.fixture
async def redis_client() -> AsyncIterator[Redis]:
    client = Redis.from_url(get_settings().redis_url, decode_responses=True)
    await resolve(client.flushdb())
    try:
        yield client
    finally:
        await resolve(client.flushdb())
        await client.aclose()


@pytest.fixture
def app(db_session: AsyncSession, redis_client: Redis) -> FastAPI:
    application = create_app()

    async def _session_override() -> AsyncIterator[AsyncSession]:
        yield db_session

    application.dependency_overrides[get_session] = _session_override
    application.dependency_overrides[get_redis] = lambda: redis_client
    return application


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as http_client:
        yield http_client


@pytest.fixture
async def admin_user(db_session: AsyncSession) -> User:
    return await make_user(
        db_session, email="admin@company.ru", full_name="Админов Админ", role=UserRole.ADMIN
    )


@pytest.fixture
async def admin_headers(client: AsyncClient, admin_user: User) -> dict[str, str]:
    return await login(client, admin_user.email)
