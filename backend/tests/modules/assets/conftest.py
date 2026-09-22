from dataclasses import dataclass
from datetime import date
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.assets.models import Asset, AssetStatus
from app.modules.directories.models import (
    AssetType,
    IssueReason,
    IssueReasonApplicability,
    Location,
)


@dataclass(frozen=True)
class Refs:
    laptop: AssetType
    office: Location
    warehouse: Location
    new_employee: IssueReason
    broken: IssueReason
    stock_only: IssueReason


@pytest.fixture
async def refs(db_session: AsyncSession) -> Refs:
    laptop = AssetType(name="Ноутбук")
    office = Location(name="Офис, каб. 101")
    warehouse = Location(name="Склад")
    new_employee = IssueReason(name="Новый сотрудник", applicability=IssueReasonApplicability.BOTH)
    broken = IssueReason(name="Неисправность", applicability=IssueReasonApplicability.ASSETS)
    stock_only = IssueReason(name="Заправка", applicability=IssueReasonApplicability.STOCK)
    db_session.add_all([laptop, office, warehouse, new_employee, broken, stock_only])
    await db_session.flush()
    return Refs(laptop, office, warehouse, new_employee, broken, stock_only)


async def make_asset(
    session: AsyncSession,
    refs: Refs,
    *,
    inventory_number: str,
    status: AssetStatus = AssetStatus.IN_STOCK,
    owner_id: int | None = None,
    serial_number: str | None = None,
    model: str = "Lenovo ThinkPad T14",
) -> Asset:
    asset = Asset(
        asset_type_id=refs.laptop.id,
        inventory_number=inventory_number,
        serial_number=serial_number,
        model=model,
        status=status,
        location_id=refs.warehouse.id,
        owner_id=owner_id,
        accepted_at=date(2026, 1, 15),
        needs_review=False,
        version=1,
    )
    session.add(asset)
    await session.flush()
    return asset


def asset_payload(refs: Refs, **overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "asset_type_id": refs.laptop.id,
        "inventory_number": "INV-001",
        "serial_number": "SN-001",
        "model": "Lenovo ThinkPad T14",
        "location_id": refs.warehouse.id,
        "accepted_at": "2026-01-15",
        "warranty_until": "2028-01-15",
        "initial_cost": "95000.00",
    }
    payload.update(overrides)
    return payload


async def create_via_api(
    client: AsyncClient, headers: dict[str, str], refs: Refs, **overrides: object
) -> dict[str, Any]:
    response = await client.post(
        "/api/assets", headers=headers, json=asset_payload(refs, **overrides)
    )
    assert response.status_code == 201, response.text
    body: dict[str, Any] = response.json()
    return body
