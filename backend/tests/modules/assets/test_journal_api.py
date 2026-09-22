"""Журнал движений: техника и расходники одним списком (п. 5 спецификации 2b)."""

from datetime import UTC, datetime
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.assets.models import AssetEvent, AssetEventType, AssetStatus
from app.modules.assets.stock_models import StockMovement, StockMovementType
from app.modules.users_auth.models import User, UserRole
from tests.factories import login, make_user
from tests.modules.assets.conftest import Refs, StockRefs, make_asset, make_stock_item

Params = dict[str, str | int | list[str]]


async def _journal(
    client: AsyncClient, headers: dict[str, str], params: Params | None = None
) -> dict[str, Any]:
    response = await client.get("/api/equipment/movements", headers=headers, params=params)
    assert response.status_code == 200, response.text
    body: dict[str, Any] = response.json()
    return body


def _keys(body: dict[str, Any]) -> list[tuple[str, int]]:
    return [(entry["kind"], entry["id"]) for entry in body["items"]]


async def test_journal_combines_asset_events_and_stock_movements(
    client: AsyncClient,
    admin_headers: dict[str, str],
    admin_user: User,
    refs: Refs,
    stock_refs: StockRefs,
    db_session: AsyncSession,
) -> None:
    employee = await make_user(db_session, full_name="Петров Пётр")
    asset = await make_asset(db_session, refs, inventory_number="INV-1")
    item = await make_stock_item(db_session, stock_refs, quantity=5)
    checkout = await client.post(
        "/api/equipment/checkout",
        headers=admin_headers,
        json={
            "recipient_id": employee.id,
            "asset_ids": [asset.id],
            "stock_lines": [{"stock_item_id": item.id, "quantity": 2}],
            "reason_id": refs.new_employee.id,
        },
    )
    transfer = await client.post(
        f"/api/stock-items/{item.id}/operations",
        headers=admin_headers,
        json={"operation": "transfer", "quantity": 1, "to_location_id": stock_refs.office.id},
    )
    assert checkout.status_code == 200, checkout.text
    assert transfer.status_code == 200, transfer.text

    issues = await _journal(client, admin_headers, {"group": "issue"})
    transfers = await _journal(client, admin_headers, {"group": "transfer"})

    assert issues["total"] == 2
    by_kind = {entry["kind"]: entry for entry in issues["items"]}
    asset_entry, stock_entry = by_kind["asset"], by_kind["stock"]
    assert asset_entry["asset_event_type"] == "issued"
    assert asset_entry["asset_operation"] == "issue"
    assert asset_entry["object_id"] == asset.id
    assert asset_entry["object_label"] == "INV-1 — Lenovo ThinkPad T14"
    assert asset_entry["to_owner_name"] == "Петров Пётр"
    assert asset_entry["from_status"] == "in_stock"
    assert asset_entry["to_status"] == "in_use"
    assert stock_entry["movement_type"] == "issue"
    assert stock_entry["object_id"] == item.id
    assert stock_entry["object_label"] == "Картридж HP 85A"
    assert stock_entry["delta"] == -2
    assert stock_entry["quantity_after"] == 3
    assert stock_entry["unit"] == "шт"
    assert stock_entry["to_owner_name"] == "Петров Пётр"
    assert stock_entry["to_location_name"] == "Склад"
    assert stock_entry["reason_name"] == "Новый сотрудник"
    assert stock_entry["performed_by_name"] == admin_user.full_name

    assert {entry["movement_type"] for entry in transfers["items"]} == {
        "transfer_out",
        "transfer_in",
    }
    for entry in transfers["items"]:
        assert entry["from_location_name"] == "Склад"
        assert entry["to_location_name"] == "Офис, каб. 101"


async def _asset_event(
    session: AsyncSession, asset_id: int, actor_id: int, at: datetime, **values: Any
) -> AssetEvent:
    event = AssetEvent(
        asset_id=asset_id,
        event_type=values.pop("event_type", AssetEventType.EDITED),
        performed_by=actor_id,
        created_at=at,
        **values,
    )
    session.add(event)
    await session.flush()
    return event


async def _movement(
    session: AsyncSession, item_id: int, actor_id: int, at: datetime, **values: Any
) -> StockMovement:
    movement = StockMovement(
        stock_item_id=item_id,
        movement_type=values.pop("movement_type", StockMovementType.ADJUSTMENT),
        delta=values.pop("delta", 1),
        quantity_after=values.pop("quantity_after", 1),
        comment=values.pop("comment", "Пересчёт"),
        performed_by=actor_id,
        created_at=at,
        **values,
    )
    session.add(movement)
    await session.flush()
    return movement


def _utc(day: int, hour: int, minute: int, second: int = 0) -> datetime:
    """Сентябрь 2026, UTC."""
    return datetime(2026, 9, day, hour, minute, second, tzinfo=UTC)


async def test_journal_period_in_company_timezone_and_order(
    client: AsyncClient,
    admin_headers: dict[str, str],
    admin_user: User,
    refs: Refs,
    stock_refs: StockRefs,
    db_session: AsyncSession,
) -> None:
    asset = await make_asset(db_session, refs, inventory_number="INV-1")
    item = await make_stock_item(db_session, stock_refs)
    actor = admin_user.id
    # Europe/Moscow = UTC+3: 22.09 по Москве — [21.09 21:00, 22.09 21:00) UTC.
    before = await _asset_event(db_session, asset.id, actor, _utc(21, 20, 59))
    first = await _movement(db_session, item.id, actor, _utc(21, 21, 0))
    same_time = await _asset_event(db_session, asset.id, actor, _utc(22, 12, 0))
    same_time_stock = await _movement(db_session, item.id, actor, _utc(22, 12, 0))
    last = await _asset_event(db_session, asset.id, actor, _utc(22, 20, 59, 59))
    after = await _movement(db_session, item.id, actor, _utc(22, 21, 0))

    everything = await _journal(client, admin_headers)
    day = await _journal(
        client, admin_headers, {"date_from": "2026-09-22", "date_to": "2026-09-22"}
    )
    since = await _journal(client, admin_headers, {"date_from": "2026-09-22"})
    page = await _journal(client, admin_headers, {"limit": 2, "offset": 1})

    assert _keys(everything) == [
        ("stock", after.id),
        ("asset", last.id),
        ("asset", same_time.id),
        ("stock", same_time_stock.id),
        ("stock", first.id),
        ("asset", before.id),
    ]
    assert _keys(day) == _keys(everything)[1:5]
    assert _keys(since) == _keys(everything)[:5]
    assert page["total"] == 6
    assert _keys(page) == _keys(everything)[1:3]


async def test_journal_filters(
    client: AsyncClient,
    admin_headers: dict[str, str],
    admin_user: User,
    refs: Refs,
    stock_refs: StockRefs,
    db_session: AsyncSession,
) -> None:
    employee = await make_user(db_session)
    other_admin = await make_user(db_session, role=UserRole.ADMIN)
    asset = await make_asset(db_session, refs, inventory_number="INV-1")
    item = await make_stock_item(db_session, stock_refs)
    moment = _utc(22, 9, 0)
    returned = await _asset_event(
        db_session,
        asset.id,
        admin_user.id,
        moment,
        event_type=AssetEventType.RETURNED,
        from_owner_id=employee.id,
        from_status=AssetStatus.IN_USE,
        to_status=AssetStatus.IN_STOCK,
        from_location_id=refs.office.id,
        to_location_id=refs.warehouse.id,
    )
    status = await _asset_event(
        db_session,
        asset.id,
        other_admin.id,
        moment,
        event_type=AssetEventType.STATUS_CHANGED,
        operation="reserve",
        from_status=AssetStatus.IN_STOCK,
        to_status=AssetStatus.RESERVED,
    )
    issued = await _movement(
        db_session,
        item.id,
        admin_user.id,
        moment,
        movement_type=StockMovementType.ISSUE,
        delta=-1,
        recipient_id=employee.id,
        comment=None,
    )
    receipt = await _movement(
        db_session,
        item.id,
        other_admin.id,
        moment,
        movement_type=StockMovementType.RECEIPT,
        document_date=datetime(2026, 9, 20).date(),
        comment=None,
    )

    async def keys(params: Params) -> set[tuple[str, int]]:
        return set(_keys(await _journal(client, admin_headers, params)))

    assert await keys({"kind": "asset"}) == {("asset", returned.id), ("asset", status.id)}
    assert await keys({"group": ["return", "receipt"]}) == {
        ("asset", returned.id),
        ("stock", receipt.id),
    }
    assert await keys({"group": "status"}) == {("asset", status.id)}
    assert await keys({"person_id": employee.id}) == {
        ("asset", returned.id),
        ("stock", issued.id),
    }
    assert await keys({"performed_by": other_admin.id}) == {
        ("asset", status.id),
        ("stock", receipt.id),
    }
    assert await keys({"location_id": refs.office.id}) == {("asset", returned.id)}
    assert await keys({"location_id": refs.warehouse.id}) == {
        ("asset", returned.id),
        ("stock", issued.id),
        ("stock", receipt.id),
    }
    [receipt_entry] = (await _journal(client, admin_headers, {"group": "receipt"}))["items"]
    assert receipt_entry["document_date"] == "2026-09-20"


async def test_journal_rejects_reversed_period(
    client: AsyncClient, admin_headers: dict[str, str]
) -> None:
    response = await client.get(
        "/api/equipment/movements",
        headers=admin_headers,
        params={"date_from": "2026-09-22", "date_to": "2026-09-21"},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "date_range_invalid"


@pytest.mark.parametrize("role", [UserRole.EMPLOYEE, UserRole.MANAGER])
async def test_journal_admin_only(
    client: AsyncClient, db_session: AsyncSession, role: UserRole
) -> None:
    user = await make_user(db_session, role=role)
    headers = await login(client, user.email)

    response = await client.get("/api/equipment/movements", headers=headers)

    assert response.status_code == 403
