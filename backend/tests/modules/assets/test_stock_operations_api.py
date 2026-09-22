"""Операции с расходниками: приход, списание, корректировка, перемещение (п. 3 спецификации 2b)."""

from datetime import timedelta
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import AuditLog
from app.core.timezone import company_today
from app.modules.assets.stock_models import StockItem, StockMovement
from app.modules.users_auth.models import User, UserRole
from tests.factories import login, make_user
from tests.modules.assets.conftest import Refs, StockRefs, make_stock_item


async def _operate(
    client: AsyncClient, headers: dict[str, str], item_id: int, **body: Any
) -> tuple[int, dict[str, Any]]:
    response = await client.post(
        f"/api/stock-items/{item_id}/operations", headers=headers, json=body
    )
    payload: dict[str, Any] = response.json()
    return response.status_code, payload


async def _movements(
    client: AsyncClient, headers: dict[str, str], item_id: int
) -> list[dict[str, Any]]:
    response = await client.get(f"/api/stock-items/{item_id}/movements", headers=headers)
    assert response.status_code == 200, response.text
    items: list[dict[str, Any]] = response.json()["items"]
    return items


async def test_receipt_adds_quantity_with_document_date(
    client: AsyncClient,
    admin_headers: dict[str, str],
    admin_user: User,
    stock_refs: StockRefs,
    db_session: AsyncSession,
) -> None:
    item = await make_stock_item(db_session, stock_refs, quantity=2)

    status, body = await _operate(
        client,
        admin_headers,
        item.id,
        operation="receipt",
        quantity=10,
        document_date="2026-09-01",
        comment="Накладная 15",
    )
    _, default_date = await _operate(
        client, admin_headers, item.id, operation="receipt", quantity=1
    )

    assert status == 200, body
    assert body["quantity"] == 10 + 2
    assert body["version"] == 2
    assert default_date["quantity"] == 13
    newest, first = await _movements(client, admin_headers, item.id)
    assert first["movement_type"] == "receipt"
    assert first["delta"] == 10
    assert first["quantity_after"] == 12
    assert first["document_date"] == "2026-09-01"
    assert first["comment"] == "Накладная 15"
    assert first["performed_by_name"] == admin_user.full_name
    assert newest["document_date"] == company_today().isoformat()
    audit = await db_session.scalars(
        select(AuditLog.diff)
        .where(
            AuditLog.entity_type == "stock_item",
            AuditLog.entity_id == str(item.id),
            AuditLog.action == "receipt",
        )
        .order_by(AuditLog.id)
    )
    assert list(audit) == [{"quantity": [2, 12]}, {"quantity": [12, 13]}]


async def test_receipt_rejects_future_date_and_inactive_item(
    client: AsyncClient,
    admin_headers: dict[str, str],
    stock_refs: StockRefs,
    db_session: AsyncSession,
) -> None:
    item = await make_stock_item(db_session, stock_refs)
    inactive = await make_stock_item(db_session, stock_refs, name="Старый тонер", is_active=False)
    tomorrow = (company_today() + timedelta(days=1)).isoformat()

    future_status, future = await _operate(
        client, admin_headers, item.id, operation="receipt", quantity=1, document_date=tomorrow
    )
    inactive_status, inactive_body = await _operate(
        client, admin_headers, inactive.id, operation="receipt", quantity=1
    )

    assert future_status == 422
    assert future["error"]["code"] == "document_date_in_future"
    assert inactive_status == 409
    assert inactive_body["error"]["code"] == "stock_item_inactive"


async def test_write_off_requires_stock_reason_and_quantity(
    client: AsyncClient,
    admin_headers: dict[str, str],
    stock_refs: StockRefs,
    refs: Refs,
    db_session: AsyncSession,
) -> None:
    item = await make_stock_item(db_session, stock_refs, quantity=3)

    no_reason = await _operate(client, admin_headers, item.id, operation="write_off", quantity=1)
    asset_reason = await _operate(
        client, admin_headers, item.id, operation="write_off", quantity=1, reason_id=refs.broken.id
    )
    too_many = await _operate(
        client,
        admin_headers,
        item.id,
        operation="write_off",
        quantity=4,
        reason_id=refs.stock_only.id,
    )
    ok = await _operate(
        client,
        admin_headers,
        item.id,
        operation="write_off",
        quantity=3,
        reason_id=refs.stock_only.id,
    )

    assert no_reason[0] == 422
    assert no_reason[1]["error"]["code"] == "reason_required"
    assert asset_reason[0] == 422
    assert asset_reason[1]["error"]["code"] == "reason_invalid"
    assert too_many[0] == 409
    assert too_many[1]["error"]["code"] == "insufficient_stock"
    assert too_many[1]["error"]["details"] == {
        "stock_item_id": item.id,
        "requested": 4,
        "available": 3,
    }
    assert ok[0] == 200
    assert ok[1]["quantity"] == 0
    [movement] = await _movements(client, admin_headers, item.id)
    assert movement["delta"] == -3
    assert movement["reason_name"] == "Заправка"


async def test_adjustment_sets_actual_quantity(
    client: AsyncClient,
    admin_headers: dict[str, str],
    stock_refs: StockRefs,
    db_session: AsyncSession,
) -> None:
    item = await make_stock_item(db_session, stock_refs, quantity=7)

    down = await _operate(
        client,
        admin_headers,
        item.id,
        operation="adjustment",
        actual_quantity=5,
        comment="Инвентаризация",
    )
    same = await _operate(
        client, admin_headers, item.id, operation="adjustment", actual_quantity=5, comment="Снова"
    )
    no_comment = await _operate(
        client, admin_headers, item.id, operation="adjustment", actual_quantity=6, comment="  "
    )

    assert down[0] == 200
    assert down[1]["quantity"] == 5
    assert same[0] == 422
    assert same[1]["error"]["code"] == "adjustment_no_change"
    assert no_comment[0] == 422
    assert no_comment[1]["error"]["code"] == "comment_required"
    [movement] = await _movements(client, admin_headers, item.id)
    assert movement["movement_type"] == "adjustment"
    assert movement["delta"] == -2
    assert movement["quantity_after"] == 5


async def test_transfer_creates_target_item(
    client: AsyncClient,
    admin_headers: dict[str, str],
    stock_refs: StockRefs,
    db_session: AsyncSession,
) -> None:
    item = await make_stock_item(db_session, stock_refs, quantity=5, min_quantity=3)

    status, body = await _operate(
        client,
        admin_headers,
        item.id,
        operation="transfer",
        quantity=2,
        to_location_id=stock_refs.office.id,
    )

    assert status == 200, body
    assert body["quantity"] == 3
    target = await db_session.scalar(
        select(StockItem).where(
            StockItem.location_id == stock_refs.office.id, StockItem.name == item.name
        )
    )
    assert target is not None
    await db_session.refresh(target)
    assert target.quantity == 2
    assert target.min_quantity == 0
    assert target.stock_category_id == item.stock_category_id
    assert target.unit == item.unit
    [out] = await _movements(client, admin_headers, item.id)
    [incoming] = await _movements(client, admin_headers, target.id)
    assert out["movement_type"] == "transfer_out"
    assert out["counterpart_location_name"] == "Офис, каб. 101"
    assert incoming["movement_type"] == "transfer_in"
    assert incoming["counterpart_location_name"] == "Склад"
    assert out["transfer_id"] == incoming["transfer_id"]


async def test_transfer_to_existing_inactive_item_reactivates_it(
    client: AsyncClient,
    admin_headers: dict[str, str],
    stock_refs: StockRefs,
    db_session: AsyncSession,
) -> None:
    item = await make_stock_item(db_session, stock_refs, quantity=5)
    target = await make_stock_item(
        db_session,
        stock_refs,
        name="КАРТРИДЖ HP 85A",
        location=stock_refs.office,
        is_active=False,
    )

    status, _ = await _operate(
        client,
        admin_headers,
        item.id,
        operation="transfer",
        quantity=5,
        to_location_id=stock_refs.office.id,
    )

    assert status == 200
    await db_session.refresh(target)
    assert target.is_active is True
    assert target.quantity == 5
    movement_types = await db_session.scalars(
        select(StockMovement.movement_type).where(StockMovement.stock_item_id == target.id)
    )
    assert list(movement_types) == ["transfer_in"]


@pytest.mark.parametrize(
    ("body", "status", "code"),
    [
        ({"quantity": 1, "to_location_id": None}, 422, "same_location"),
        ({"quantity": 1, "to_location_id": 999999}, 422, "location_invalid"),
        ({"quantity": 9, "to_location_id": "office"}, 409, "insufficient_stock"),
    ],
)
async def test_transfer_validation(
    client: AsyncClient,
    admin_headers: dict[str, str],
    stock_refs: StockRefs,
    db_session: AsyncSession,
    body: dict[str, Any],
    status: int,
    code: str,
) -> None:
    item = await make_stock_item(db_session, stock_refs, quantity=5)
    targets = {None: stock_refs.warehouse.id, "office": stock_refs.office.id}
    to_location = body["to_location_id"]
    body = {**body, "to_location_id": targets.get(to_location, to_location)}

    actual_status, payload = await _operate(
        client, admin_headers, item.id, operation="transfer", **body
    )

    assert actual_status == status
    assert payload["error"]["code"] == code


async def test_operations_forbidden_for_non_admin(
    client: AsyncClient, stock_refs: StockRefs, db_session: AsyncSession
) -> None:
    manager = await make_user(db_session, email="manager@company.ru", role=UserRole.MANAGER)
    item = await make_stock_item(db_session, stock_refs, quantity=5)
    headers = await login(client, manager.email)

    status, _ = await _operate(client, headers, item.id, operation="receipt", quantity=1)
    history = await client.get(f"/api/stock-items/{item.id}/movements", headers=headers)

    assert status == 403
    assert history.status_code == 403
