"""Параллельные операции с остатками: реальные транзакции в разных соединениях (п. 3.2 ТЗ)."""

import asyncio
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass

import pytest
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.audit import AuditLog
from app.core.config import get_settings
from app.core.errors import AppError
from app.modules.assets import stock_operations
from app.modules.assets.checkout import checkout
from app.modules.assets.equipment_schemas import CheckoutRequest, StockLine
from app.modules.assets.stock_models import StockItem, StockMovement
from app.modules.assets.stock_schemas import (
    StockOperationRequest,
    StockTransferOperation,
    StockWriteOffOperation,
)
from app.modules.directories.models import (
    IssueReason,
    IssueReasonApplicability,
    Location,
    StockCategory,
)
from app.modules.users_auth.models import User, UserRole
from app.modules.users_auth.service import CurrentUser
from tests.factories import make_user


@dataclass(frozen=True)
class RaceSetup:
    engine: AsyncEngine
    actor: CurrentUser
    category_id: int
    first_location_id: int
    second_location_id: int
    reason_id: int

    async def make_item(self, name: str, location_id: int, quantity: int) -> int:
        async with AsyncSession(self.engine, expire_on_commit=False) as session:
            item = StockItem(
                name=name,
                stock_category_id=self.category_id,
                unit="шт",
                location_id=location_id,
                quantity=quantity,
                min_quantity=0,
                is_active=True,
                version=1,
            )
            session.add(item)
            await session.commit()
            return item.id

    async def run(self, item_id: int, request: StockOperationRequest) -> str:
        async with AsyncSession(self.engine, expire_on_commit=False) as session:
            try:
                await stock_operations.apply_stock_operation(session, self.actor, item_id, request)
            except AppError as exc:
                return exc.code
            return "ok"


@pytest.fixture
async def race() -> AsyncIterator[RaceSetup]:
    engine = create_async_engine(get_settings().database_url, poolclass=NullPool)
    async with AsyncSession(engine, expire_on_commit=False) as setup:
        admin = await make_user(setup, email="stock-race@company.ru", role=UserRole.ADMIN)
        category = StockCategory(name="Гонка: картриджи")
        first = Location(name="Гонка: склад 1")
        second = Location(name="Гонка: склад 2")
        reason = IssueReason(name="Гонка: брак", applicability=IssueReasonApplicability.STOCK)
        setup.add_all([category, first, second, reason])
        await setup.commit()
    actor = CurrentUser(
        id=admin.id,
        email=admin.email,
        full_name=admin.full_name,
        role=UserRole.ADMIN,
        department_id=None,
        must_change_password=False,
    )
    try:
        yield RaceSetup(engine, actor, category.id, first.id, second.id, reason.id)
    finally:
        async with AsyncSession(engine) as cleanup:
            item_ids = select(StockItem.id).where(StockItem.stock_category_id == category.id)
            await cleanup.execute(
                delete(StockMovement).where(StockMovement.stock_item_id.in_(item_ids))
            )
            await cleanup.execute(
                delete(StockItem).where(StockItem.stock_category_id == category.id)
            )
            await cleanup.execute(delete(AuditLog).where(AuditLog.user_id == admin.id))
            await cleanup.execute(delete(StockCategory).where(StockCategory.id == category.id))
            await cleanup.execute(delete(Location).where(Location.id.in_([first.id, second.id])))
            await cleanup.execute(delete(IssueReason).where(IssueReason.id == reason.id))
            await cleanup.execute(delete(User).where(User.id == admin.id))
            await cleanup.commit()
        await engine.dispose()


async def _quantity(engine: AsyncEngine, item_id: int) -> int:
    async with AsyncSession(engine) as session:
        item = await session.get(StockItem, item_id)
        assert item is not None
        return item.quantity


async def _gather(*calls: Callable[[], Awaitable[str]]) -> list[str]:
    return list(await asyncio.gather(*(call() for call in calls)))


async def test_parallel_write_off_of_last_units_one_wins(race: RaceSetup) -> None:
    item_id = await race.make_item("Картридж", race.first_location_id, 3)
    request = StockWriteOffOperation(operation="write_off", quantity=2, reason_id=race.reason_id)

    results = await _gather(lambda: race.run(item_id, request), lambda: race.run(item_id, request))

    assert sorted(results) == ["insufficient_stock", "ok"]
    assert await _quantity(race.engine, item_id) == 1


async def test_opposite_transfers_do_not_deadlock(race: RaceSetup) -> None:
    first = await race.make_item("Бумага A4", race.first_location_id, 10)
    second = await race.make_item("Бумага A4", race.second_location_id, 10)

    results = await asyncio.wait_for(
        _gather(
            lambda: race.run(
                first,
                StockTransferOperation(
                    operation="transfer", quantity=3, to_location_id=race.second_location_id
                ),
            ),
            lambda: race.run(
                second,
                StockTransferOperation(
                    operation="transfer", quantity=4, to_location_id=race.first_location_id
                ),
            ),
        ),
        timeout=10,
    )

    assert results == ["ok", "ok"]
    assert await _quantity(race.engine, first) == 10 - 3 + 4
    assert await _quantity(race.engine, second) == 10 + 3 - 4


async def test_parallel_transfers_create_one_target_item(race: RaceSetup) -> None:
    source = await race.make_item("Мышь USB", race.first_location_id, 10)
    request = StockTransferOperation(
        operation="transfer", quantity=2, to_location_id=race.second_location_id
    )

    results = await _gather(lambda: race.run(source, request), lambda: race.run(source, request))

    assert results == ["ok", "ok"]
    async with AsyncSession(race.engine) as session:
        targets = list(
            await session.scalars(
                select(StockItem).where(
                    StockItem.location_id == race.second_location_id,
                    func.lower(StockItem.name) == "мышь usb",
                )
            )
        )
    assert [target.quantity for target in targets] == [4]
    assert await _quantity(race.engine, source) == 6


async def test_parallel_checkout_of_last_units_one_wins(race: RaceSetup) -> None:
    item_id = await race.make_item("Клавиатура", race.first_location_id, 1)
    request = CheckoutRequest(
        recipient_id=race.actor.id, stock_lines=[StockLine(stock_item_id=item_id, quantity=1)]
    )

    async def run() -> str:
        async with AsyncSession(race.engine, expire_on_commit=False) as session:
            try:
                await checkout(session, race.actor, request)
            except AppError as exc:
                return exc.code
            return "ok"

    results = await _gather(run, run)

    assert sorted(results) == ["checkout_unavailable", "ok"]
    assert await _quantity(race.engine, item_id) == 0
