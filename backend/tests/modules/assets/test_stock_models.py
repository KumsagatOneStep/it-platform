"""Ограничения БД страхуют правила остатков и движений независимо от кода (п. 2 спецификации 2b)."""

import uuid
from datetime import date

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.assets.stock_models import StockItem, StockMovement, StockMovementType
from app.modules.directories.models import Location, StockCategory
from tests.factories import make_user


async def _item(session: AsyncSession, **overrides: object) -> StockItem:
    category = StockCategory(name="Картриджи")
    location = Location(name="Склад")
    session.add_all([category, location])
    await session.flush()
    values: dict[str, object] = {
        "name": "Картридж HP 85A",
        "stock_category_id": category.id,
        "unit": "шт",
        "location_id": location.id,
        "quantity": 5,
        "min_quantity": 0,
        "is_active": True,
        "version": 1,
    }
    values.update(overrides)
    item = StockItem(**values)
    session.add(item)
    await session.flush()
    return item


async def test_quantity_cannot_go_negative(db_session: AsyncSession) -> None:
    item = await _item(db_session)

    with pytest.raises(IntegrityError):
        async with db_session.begin_nested():
            await db_session.execute(
                text("UPDATE equipment.stock_items SET quantity = -1 WHERE id = :id"),
                {"id": item.id},
            )


async def test_inactive_item_must_be_empty(db_session: AsyncSession) -> None:
    item = await _item(db_session)

    with pytest.raises(IntegrityError):
        async with db_session.begin_nested():
            await db_session.execute(
                text("UPDATE equipment.stock_items SET is_active = false WHERE id = :id"),
                {"id": item.id},
            )


async def test_name_unique_per_location_ignoring_case(db_session: AsyncSession) -> None:
    item = await _item(db_session)

    with pytest.raises(IntegrityError):
        async with db_session.begin_nested():
            db_session.add(
                StockItem(
                    name="КАРТРИДЖ hp 85a",
                    stock_category_id=item.stock_category_id,
                    unit="шт",
                    location_id=item.location_id,
                    quantity=0,
                    min_quantity=0,
                    is_active=True,
                    version=1,
                )
            )


def _movement(item: StockItem, actor_id: int, **overrides: object) -> StockMovement:
    values: dict[str, object] = {
        "stock_item_id": item.id,
        "movement_type": StockMovementType.WRITE_OFF,
        "delta": -1,
        "quantity_after": 4,
        "performed_by": actor_id,
    }
    values.update(overrides)
    return StockMovement(**values)


@pytest.mark.parametrize(
    "overrides",
    [
        pytest.param({"movement_type": StockMovementType.RECEIPT, "delta": -1}, id="receipt-sign"),
        pytest.param({"delta": 1}, id="write-off-sign"),
        pytest.param({"delta": 0, "movement_type": StockMovementType.ADJUSTMENT}, id="zero"),
        pytest.param({"quantity_after": -1}, id="negative-after"),
        pytest.param(
            {"movement_type": StockMovementType.RECEIPT, "delta": 1}, id="receipt-no-date"
        ),
        pytest.param({"document_date": date(2026, 9, 1)}, id="date-not-receipt"),
        pytest.param({"movement_type": StockMovementType.ISSUE}, id="issue-no-recipient"),
        pytest.param({"movement_type": StockMovementType.TRANSFER_OUT}, id="transfer-no-id"),
        pytest.param({"transfer_id": uuid.uuid4()}, id="transfer-id-not-transfer"),
        pytest.param(
            {"movement_type": StockMovementType.ADJUSTMENT, "comment": None}, id="adjust-comment"
        ),
    ],
)
async def test_movement_rules_enforced_by_database(
    db_session: AsyncSession, overrides: dict[str, object]
) -> None:
    item = await _item(db_session)
    actor = await make_user(db_session)

    with pytest.raises(IntegrityError):
        async with db_session.begin_nested():
            db_session.add(_movement(item, actor.id, **overrides))


async def test_recipient_only_on_issue(db_session: AsyncSession) -> None:
    item = await _item(db_session)
    actor = await make_user(db_session)

    with pytest.raises(IntegrityError):
        async with db_session.begin_nested():
            db_session.add(_movement(item, actor.id, recipient_id=actor.id))


async def test_valid_movements_accepted(db_session: AsyncSession) -> None:
    item = await _item(db_session)
    actor = await make_user(db_session)
    transfer_id = uuid.uuid4()

    db_session.add_all(
        [
            _movement(
                item,
                actor.id,
                movement_type=StockMovementType.RECEIPT,
                delta=3,
                quantity_after=8,
                document_date=date(2026, 9, 1),
            ),
            _movement(item, actor.id, movement_type=StockMovementType.ISSUE, recipient_id=actor.id),
            _movement(
                item,
                actor.id,
                movement_type=StockMovementType.ADJUSTMENT,
                delta=-2,
                comment="Инвентаризация",
            ),
            _movement(
                item,
                actor.id,
                movement_type=StockMovementType.TRANSFER_OUT,
                transfer_id=transfer_id,
            ),
            _movement(
                item,
                actor.id,
                movement_type=StockMovementType.TRANSFER_IN,
                delta=1,
                transfer_id=transfer_id,
            ),
        ]
    )
    await db_session.flush()
