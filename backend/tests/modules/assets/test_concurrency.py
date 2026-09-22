"""Параллельная выдача одного актива: реальные транзакции в двух соединениях (п. 3.2 ТЗ)."""

import asyncio
from collections.abc import AsyncIterator
from datetime import date

import pytest
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.audit import AuditLog
from app.core.config import get_settings
from app.core.errors import ConflictError
from app.modules.assets import operations
from app.modules.assets.models import Asset, AssetEvent, AssetStatus
from app.modules.assets.schemas import IssueOperation
from app.modules.assets.transitions import Operation
from app.modules.directories.models import AssetType, Location
from app.modules.users_auth.models import User, UserRole
from app.modules.users_auth.service import CurrentUser
from tests.factories import make_user


@pytest.fixture
async def engine() -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(get_settings().database_url, poolclass=NullPool)
    yield engine
    await engine.dispose()


async def test_parallel_issue_of_same_asset_one_wins(engine: AsyncEngine) -> None:
    async with AsyncSession(engine, expire_on_commit=False) as setup:
        admin = await make_user(setup, email="race-admin@company.ru", role=UserRole.ADMIN)
        first = await make_user(setup, email="race-1@company.ru")
        second = await make_user(setup, email="race-2@company.ru")
        asset_type = AssetType(name="Гонка: ноутбук")
        location = Location(name="Гонка: склад")
        setup.add_all([asset_type, location])
        await setup.flush()
        asset = Asset(
            asset_type_id=asset_type.id,
            inventory_number="RACE-1",
            model="Модель",
            status=AssetStatus.IN_STOCK,
            location_id=location.id,
            accepted_at=date(2026, 1, 1),
            needs_review=False,
            version=1,
        )
        setup.add(asset)
        await setup.commit()

    actor = CurrentUser(
        id=admin.id,
        email=admin.email,
        full_name=admin.full_name,
        role=UserRole.ADMIN,
        department_id=None,
        must_change_password=False,
    )

    async def issue_to(owner: User) -> str:
        async with AsyncSession(engine, expire_on_commit=False) as session:
            try:
                await operations.apply_operation(
                    session,
                    actor,
                    asset.id,
                    IssueOperation(operation=Operation.ISSUE, owner_id=owner.id),
                )
            except ConflictError as exc:
                return exc.code
            return "ok"

    try:
        results = await asyncio.gather(issue_to(first), issue_to(second))

        assert sorted(results) == ["ok", "operation_not_allowed"]
        async with AsyncSession(engine) as check:
            stored = await check.get(Asset, asset.id)
            assert stored is not None
            assert stored.status == AssetStatus.IN_USE
            assert stored.version == 2
    finally:
        async with AsyncSession(engine) as cleanup:
            await cleanup.execute(delete(AssetEvent).where(AssetEvent.asset_id == asset.id))
            await cleanup.execute(delete(AuditLog).where(AuditLog.user_id == admin.id))
            await cleanup.execute(delete(Asset).where(Asset.id == asset.id))
            await cleanup.execute(delete(AssetType).where(AssetType.id == asset_type.id))
            await cleanup.execute(delete(Location).where(Location.id == location.id))
            await cleanup.execute(delete(User).where(User.id.in_([admin.id, first.id, second.id])))
            await cleanup.commit()
