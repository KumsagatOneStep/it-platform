"""Единая выдача техники и расходников одной транзакцией (п. 4 спецификации 2b)."""

from typing import Any

import pytest
from httpx import AsyncClient, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.assets.models import AssetEvent, AssetStatus
from app.modules.assets.stock_models import StockMovement
from app.modules.users_auth.models import User, UserRole
from tests.factories import login, make_user
from tests.modules.assets.conftest import Refs, StockRefs, make_asset, make_stock_item


async def _checkout(client: AsyncClient, headers: dict[str, str], **body: Any) -> Response:
    return await client.post("/api/equipment/checkout", headers=headers, json=body)


def _error(response: Response) -> tuple[int, str]:
    return response.status_code, response.json()["error"]["code"]


@pytest.fixture
async def employee(db_session: AsyncSession) -> User:
    return await make_user(db_session, full_name="Петров Пётр")


async def test_checkout_issues_assets_and_stock_together(
    client: AsyncClient,
    admin_headers: dict[str, str],
    refs: Refs,
    stock_refs: StockRefs,
    employee: User,
    db_session: AsyncSession,
) -> None:
    first = await make_asset(db_session, refs, inventory_number="INV-1")
    second = await make_asset(db_session, refs, inventory_number="INV-2")
    cartridge = await make_stock_item(db_session, stock_refs, quantity=5)
    paper = await make_stock_item(
        db_session, stock_refs, name="Бумага A4", quantity=10, category=stock_refs.paper
    )

    response = await _checkout(
        client,
        admin_headers,
        recipient_id=employee.id,
        asset_ids=[second.id, first.id],
        stock_lines=[
            {"stock_item_id": cartridge.id, "quantity": 2},
            {"stock_item_id": paper.id, "quantity": 10},
        ],
        reason_id=refs.new_employee.id,
        comment="Новый сотрудник",
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert [asset["inventory_number"] for asset in body["assets"]] == ["INV-1", "INV-2"]
    assert {asset["owner_id"] for asset in body["assets"]} == {employee.id}
    assert {asset["status"] for asset in body["assets"]} == {"in_use"}
    assert [(item["id"], item["quantity"]) for item in body["stock_items"]] == [
        (cartridge.id, 3),
        (paper.id, 0),
    ]
    movements = list(
        await db_session.scalars(select(StockMovement).order_by(StockMovement.stock_item_id))
    )
    assert [(m.movement_type, m.delta, m.recipient_id) for m in movements] == [
        ("issue", -2, employee.id),
        ("issue", -10, employee.id),
    ]
    assert {m.reason_id for m in movements} == {refs.new_employee.id}
    assert {m.comment for m in movements} == {"Новый сотрудник"}
    events = list(
        await db_session.scalars(select(AssetEvent).where(AssetEvent.event_type == "issued"))
    )
    assert {event.asset_id for event in events} == {first.id, second.id}


async def test_checkout_only_stock(
    client: AsyncClient,
    admin_headers: dict[str, str],
    refs: Refs,
    stock_refs: StockRefs,
    employee: User,
    db_session: AsyncSession,
) -> None:
    item = await make_stock_item(db_session, stock_refs, quantity=5)

    response = await _checkout(
        client,
        admin_headers,
        recipient_id=employee.id,
        stock_lines=[{"stock_item_id": item.id, "quantity": 1}],
        reason_id=refs.stock_only.id,
    )

    assert response.status_code == 200, response.text
    assert response.json()["assets"] == []


async def test_checkout_is_all_or_nothing_and_lists_every_problem(
    client: AsyncClient,
    admin_headers: dict[str, str],
    refs: Refs,
    stock_refs: StockRefs,
    employee: User,
    db_session: AsyncSession,
) -> None:
    free = await make_asset(db_session, refs, inventory_number="INV-1")
    taken = await make_asset(
        db_session, refs, inventory_number="INV-2", status=AssetStatus.IN_USE, owner_id=employee.id
    )
    enough = await make_stock_item(db_session, stock_refs, quantity=5)
    short = await make_stock_item(db_session, stock_refs, name="Бумага A4", quantity=1)
    inactive = await make_stock_item(db_session, stock_refs, name="Старый тонер", is_active=False)

    response = await _checkout(
        client,
        admin_headers,
        recipient_id=employee.id,
        asset_ids=[free.id, taken.id, 999999],
        stock_lines=[
            {"stock_item_id": enough.id, "quantity": 2},
            {"stock_item_id": short.id, "quantity": 3},
            {"stock_item_id": inactive.id, "quantity": 1},
            {"stock_item_id": 999999, "quantity": 1},
        ],
    )

    assert _error(response) == (409, "checkout_unavailable")
    assert response.json()["error"]["details"] == {
        "assets": [
            {"asset_id": taken.id, "inventory_number": "INV-2", "status": "in_use"},
            {"asset_id": 999999, "inventory_number": None, "status": None},
        ],
        "stock": [
            {
                "stock_item_id": short.id,
                "name": "Бумага A4",
                "requested": 3,
                "available": 1,
                "is_active": True,
            },
            {
                "stock_item_id": inactive.id,
                "name": "Старый тонер",
                "requested": 1,
                "available": 0,
                "is_active": False,
            },
            {
                "stock_item_id": 999999,
                "name": None,
                "requested": 1,
                "available": None,
                "is_active": None,
            },
        ],
    }
    await db_session.refresh(free)
    await db_session.refresh(enough)
    assert free.status == AssetStatus.IN_STOCK
    assert enough.quantity == 5
    assert await db_session.scalar(select(StockMovement.id)) is None


@pytest.mark.parametrize(
    ("kind", "status", "code"),
    [
        ("empty", 422, "checkout_empty"),
        ("duplicate_stock", 422, "duplicate_stock_line"),
        ("duplicate_asset", 422, "duplicate_asset"),
        ("inactive_recipient", 422, "recipient_invalid"),
        ("asset_reason_for_stock", 422, "reason_invalid"),
        ("stock_reason_for_mixed", 422, "reason_invalid"),
    ],
)
async def test_checkout_validation(
    client: AsyncClient,
    admin_headers: dict[str, str],
    refs: Refs,
    stock_refs: StockRefs,
    employee: User,
    db_session: AsyncSession,
    kind: str,
    status: int,
    code: str,
) -> None:
    asset = await make_asset(db_session, refs, inventory_number="INV-1")
    item = await make_stock_item(db_session, stock_refs, quantity=5)
    inactive = await make_user(db_session, is_active=False)
    line = {"stock_item_id": item.id, "quantity": 1}
    bodies: dict[str, dict[str, Any]] = {
        "empty": {"recipient_id": employee.id},
        "duplicate_stock": {"recipient_id": employee.id, "stock_lines": [line, line]},
        "duplicate_asset": {"recipient_id": employee.id, "asset_ids": [asset.id, asset.id]},
        "inactive_recipient": {"recipient_id": inactive.id, "asset_ids": [asset.id]},
        "asset_reason_for_stock": {
            "recipient_id": employee.id,
            "stock_lines": [line],
            "reason_id": refs.broken.id,
        },
        "stock_reason_for_mixed": {
            "recipient_id": employee.id,
            "asset_ids": [asset.id],
            "stock_lines": [line],
            "reason_id": refs.stock_only.id,
        },
    }

    response = await _checkout(client, admin_headers, **bodies[kind])

    assert _error(response) == (status, code)


async def test_checkout_limits_lines(
    client: AsyncClient, admin_headers: dict[str, str], employee: User
) -> None:
    response = await _checkout(
        client, admin_headers, recipient_id=employee.id, asset_ids=list(range(1, 52))
    )

    assert response.status_code == 422


async def test_checkout_requires_admin(client: AsyncClient, db_session: AsyncSession) -> None:
    manager = await make_user(db_session, role=UserRole.MANAGER)
    headers = await login(client, manager.email)

    response = await _checkout(client, headers, recipient_id=manager.id, asset_ids=[1])

    assert _error(response) == (403, "insufficient_role")
