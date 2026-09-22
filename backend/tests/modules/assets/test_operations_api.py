from typing import Any

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import AuditLog
from app.modules.assets.models import AssetStatus
from app.modules.users_auth.models import UserRole
from tests.factories import login, make_user
from tests.modules.assets.conftest import Refs, make_asset


async def _operate(client: AsyncClient, headers: dict[str, str], asset_id: int, **body: Any) -> Any:
    return await client.post(f"/api/assets/{asset_id}/operations", headers=headers, json=body)


def _error_code(response: Any) -> str:
    code: str = response.json()["error"]["code"]
    return code


async def test_full_lifecycle_updates_owner_and_history(
    client: AsyncClient, admin_headers: dict[str, str], refs: Refs, db_session: AsyncSession
) -> None:
    employee = await make_user(db_session, full_name="Петров Пётр")
    asset = await make_asset(db_session, refs, inventory_number="INV-1")

    issued = await _operate(
        client,
        admin_headers,
        asset.id,
        operation="issue",
        owner_id=employee.id,
        reason_id=refs.new_employee.id,
        comment="Выдан",
    )
    assert issued.status_code == 200, issued.text
    assert issued.json()["status"] == "in_use"
    assert issued.json()["owner_name"] == "Петров Пётр"
    assert issued.json()["version"] == 2

    repaired = await _operate(client, admin_headers, asset.id, operation="to_repair")
    assert repaired.json()["status"] == "in_repair"
    assert repaired.json()["owner_id"] == employee.id
    assert "repair_to_owner" in repaired.json()["allowed_operations"]

    back = await _operate(client, admin_headers, asset.id, operation="repair_to_owner")
    assert back.json()["status"] == "in_use"
    assert back.json()["owner_id"] == employee.id

    returned = await _operate(
        client, admin_headers, asset.id, operation="return", location_id=refs.office.id
    )
    assert returned.json()["status"] == "in_stock"
    assert returned.json()["owner_id"] is None
    assert returned.json()["location_name"] == "Офис, каб. 101"

    written_off = await _operate(
        client, admin_headers, asset.id, operation="write_off", reason_id=refs.broken.id
    )
    assert written_off.json()["status"] == "written_off"
    assert written_off.json()["allowed_operations"] == []

    events = (await client.get(f"/api/assets/{asset.id}/events", headers=admin_headers)).json()[
        "items"
    ]
    assert [event["operation"] for event in events] == [
        "write_off",
        "return",
        "repair_to_owner",
        "to_repair",
        "issue",
    ]
    issue_event = events[-1]
    assert issue_event["event_type"] == "issued"
    assert issue_event["from_status"] == "in_stock"
    assert issue_event["to_status"] == "in_use"
    assert issue_event["to_owner_name"] == "Петров Пётр"
    assert issue_event["reason_name"] == "Новый сотрудник"
    assert issue_event["comment"] == "Выдан"
    return_event = events[1]
    assert return_event["event_type"] == "returned"
    assert return_event["from_owner_name"] == "Петров Пётр"
    assert return_event["to_owner_id"] is None
    assert return_event["from_location_name"] == "Склад"
    assert return_event["to_location_name"] == "Офис, каб. 101"
    audit = await db_session.scalars(
        select(AuditLog.action)
        .where(AuditLog.entity_type == "asset", AuditLog.entity_id == str(asset.id))
        .order_by(AuditLog.id)
    )
    assert list(audit) == ["issue", "to_repair", "repair_to_owner", "return", "write_off"]


async def test_move_changes_only_location(
    client: AsyncClient, admin_headers: dict[str, str], refs: Refs, db_session: AsyncSession
) -> None:
    owner = await make_user(db_session)
    asset = await make_asset(
        db_session, refs, inventory_number="INV-1", status=AssetStatus.IN_USE, owner_id=owner.id
    )

    moved = await _operate(
        client, admin_headers, asset.id, operation="move", location_id=refs.office.id
    )

    assert moved.status_code == 200, moved.text
    assert moved.json()["status"] == "in_use"
    assert moved.json()["owner_id"] == owner.id
    assert moved.json()["location_id"] == refs.office.id


async def test_operation_not_allowed_from_current_status(
    client: AsyncClient, admin_headers: dict[str, str], refs: Refs, db_session: AsyncSession
) -> None:
    asset = await make_asset(db_session, refs, inventory_number="INV-1")

    response = await _operate(client, admin_headers, asset.id, operation="return")

    assert response.status_code == 409
    assert _error_code(response) == "operation_not_allowed"
    assert response.json()["error"]["details"] == {"status": "in_stock"}


async def test_operation_validation_errors(
    client: AsyncClient, admin_headers: dict[str, str], refs: Refs, db_session: AsyncSession
) -> None:
    inactive = await make_user(db_session, is_active=False)
    asset = await make_asset(db_session, refs, inventory_number="INV-1")

    no_reason = await _operate(client, admin_headers, asset.id, operation="write_off")
    stock_reason = await _operate(
        client, admin_headers, asset.id, operation="write_off", reason_id=refs.stock_only.id
    )
    inactive_owner = await _operate(
        client, admin_headers, asset.id, operation="issue", owner_id=inactive.id
    )
    move_without_location = await _operate(client, admin_headers, asset.id, operation="move")
    unknown = await _operate(client, admin_headers, asset.id, operation="teleport")

    assert _error_code(no_reason) == "reason_required"
    assert _error_code(stock_reason) == "reason_invalid"
    assert _error_code(inactive_owner) == "recipient_invalid"
    assert move_without_location.status_code == 422
    assert unknown.status_code == 422


async def test_operations_require_admin(
    client: AsyncClient, refs: Refs, db_session: AsyncSession
) -> None:
    manager = await make_user(db_session, role=UserRole.MANAGER)
    asset = await make_asset(db_session, refs, inventory_number="INV-1")
    headers = await login(client, manager.email)

    single = await _operate(client, headers, asset.id, operation="reserve")
    bulk = await client.post("/api/assets/return", headers=headers, json={"asset_ids": [asset.id]})

    assert single.status_code == 403
    assert bulk.status_code == 403


async def test_bulk_return(
    client: AsyncClient, admin_headers: dict[str, str], refs: Refs, db_session: AsyncSession
) -> None:
    employee = await make_user(db_session)
    first = await make_asset(
        db_session, refs, inventory_number="INV-1", status=AssetStatus.IN_USE, owner_id=employee.id
    )
    second = await make_asset(
        db_session, refs, inventory_number="INV-2", status=AssetStatus.IN_USE, owner_id=employee.id
    )

    returned = await client.post(
        "/api/assets/return",
        headers=admin_headers,
        json={"asset_ids": [second.id, first.id, first.id], "location_id": refs.office.id},
    )

    assert returned.status_code == 200, returned.text
    assert [item["inventory_number"] for item in returned.json()] == ["INV-1", "INV-2"]
    assert {item["status"] for item in returned.json()} == {"in_stock"}
    assert {item["owner_id"] for item in returned.json()} == {None}
    assert {item["location_id"] for item in returned.json()} == {refs.office.id}


async def test_bulk_return_is_all_or_nothing(
    client: AsyncClient, admin_headers: dict[str, str], refs: Refs, db_session: AsyncSession
) -> None:
    employee = await make_user(db_session)
    in_use = await make_asset(
        db_session, refs, inventory_number="INV-1", status=AssetStatus.IN_USE, owner_id=employee.id
    )
    free = await make_asset(db_session, refs, inventory_number="INV-2")

    response = await client.post(
        "/api/assets/return",
        headers=admin_headers,
        json={"asset_ids": [in_use.id, free.id, 999999]},
    )

    assert response.status_code == 409
    assert _error_code(response) == "assets_unavailable"
    assert response.json()["error"]["details"] == [
        {"asset_id": free.id, "inventory_number": "INV-2", "status": "in_stock"},
        {"asset_id": 999999, "inventory_number": None, "status": None},
    ]
    await db_session.refresh(in_use)
    assert in_use.status == AssetStatus.IN_USE


async def test_bulk_issue_endpoint_removed(
    client: AsyncClient, admin_headers: dict[str, str]
) -> None:
    """Выдача нескольких единиц — только через POST /api/equipment/checkout."""
    response = await client.post(
        "/api/assets/issue", headers=admin_headers, json={"owner_id": 1, "asset_ids": [1]}
    )

    assert response.status_code == 405
