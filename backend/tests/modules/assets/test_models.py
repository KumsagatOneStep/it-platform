"""Ограничения БД страхуют правила владельца независимо от кода (п. 2.1 спецификации)."""

from datetime import date

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.assets.models import Asset, AssetStatus
from app.modules.directories.models import AssetType, Location
from tests.factories import make_user


async def _refs(session: AsyncSession) -> tuple[int, int]:
    asset_type = AssetType(name="Монитор")
    location = Location(name="Склад")
    session.add_all([asset_type, location])
    await session.flush()
    return asset_type.id, location.id


def _asset(type_id: int, location_id: int, **overrides: object) -> Asset:
    values: dict[str, object] = {
        "asset_type_id": type_id,
        "inventory_number": "INV-1",
        "model": "Dell P2422H",
        "status": AssetStatus.IN_STOCK,
        "location_id": location_id,
        "accepted_at": date(2026, 1, 1),
        "needs_review": False,
        "version": 1,
    }
    values.update(overrides)
    return Asset(**values)


@pytest.mark.parametrize(
    ("status", "with_owner"),
    [
        (AssetStatus.IN_USE, False),
        (AssetStatus.IN_STOCK, True),
        (AssetStatus.RESERVED, True),
        (AssetStatus.WRITTEN_OFF, True),
    ],
)
async def test_owner_rules_enforced_by_database(
    db_session: AsyncSession, status: AssetStatus, with_owner: bool
) -> None:
    type_id, location_id = await _refs(db_session)
    owner = await make_user(db_session)

    with pytest.raises(IntegrityError):
        async with db_session.begin_nested():
            db_session.add(
                _asset(
                    type_id, location_id, status=status, owner_id=owner.id if with_owner else None
                )
            )


async def test_in_repair_allows_owner_or_none(db_session: AsyncSession) -> None:
    type_id, location_id = await _refs(db_session)
    owner = await make_user(db_session)

    db_session.add_all(
        [
            _asset(type_id, location_id, status=AssetStatus.IN_REPAIR, owner_id=owner.id),
            _asset(type_id, location_id, inventory_number="INV-2", status=AssetStatus.IN_REPAIR),
        ]
    )
    await db_session.flush()


async def test_negative_cost_rejected(db_session: AsyncSession) -> None:
    type_id, location_id = await _refs(db_session)

    with pytest.raises(IntegrityError):
        async with db_session.begin_nested():
            db_session.add(_asset(type_id, location_id, initial_cost=-1))
