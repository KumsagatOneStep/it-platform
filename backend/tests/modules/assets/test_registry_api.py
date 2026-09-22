from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import AuditLog
from app.modules.assets.models import AssetStatus
from app.modules.directories.models import Department
from app.modules.users_auth.models import User, UserRole
from tests.factories import login, make_user
from tests.modules.assets.conftest import Refs, asset_payload, create_via_api, make_asset


async def test_admin_creates_asset_in_stock_with_created_event(
    client: AsyncClient,
    admin_headers: dict[str, str],
    admin_user: User,
    refs: Refs,
    db_session: AsyncSession,
) -> None:
    created = await create_via_api(
        client, admin_headers, refs, inventory_number="  INV-001 ", serial_number=" "
    )

    assert created["inventory_number"] == "INV-001"
    assert created["serial_number"] is None
    assert created["status"] == "in_stock"
    assert created["owner_id"] is None
    assert created["asset_type_name"] == "Ноутбук"
    assert created["location_name"] == "Склад"
    assert created["initial_cost"] == "95000.00"
    assert created["version"] == 1
    assert "issue" in created["allowed_operations"]

    events = await client.get(f"/api/assets/{created['id']}/events", headers=admin_headers)
    assert events.status_code == 200
    [event] = events.json()["items"]
    assert event["event_type"] == "created"
    assert event["to_status"] == "in_stock"
    assert event["to_location_name"] == "Склад"
    assert event["performed_by_name"] == admin_user.full_name
    audit = await db_session.scalars(
        select(AuditLog.action).where(
            AuditLog.entity_type == "asset", AuditLog.entity_id == str(created["id"])
        )
    )
    assert list(audit) == ["created"]


async def test_duplicate_numbers_return_409(
    client: AsyncClient, admin_headers: dict[str, str], refs: Refs
) -> None:
    await create_via_api(client, admin_headers, refs)

    same_inventory = await client.post(
        "/api/assets",
        headers=admin_headers,
        json=asset_payload(refs, serial_number="SN-OTHER"),
    )
    same_serial = await client.post(
        "/api/assets",
        headers=admin_headers,
        json=asset_payload(refs, inventory_number="INV-OTHER"),
    )
    no_serial = await client.post(
        "/api/assets",
        headers=admin_headers,
        json=asset_payload(refs, inventory_number="INV-002", serial_number=None),
    )
    no_serial_again = await client.post(
        "/api/assets",
        headers=admin_headers,
        json=asset_payload(refs, inventory_number="INV-003", serial_number=None),
    )

    assert same_inventory.status_code == 409
    assert same_inventory.json()["error"]["code"] == "inventory_number_taken"
    assert same_serial.status_code == 409
    assert same_serial.json()["error"]["code"] == "serial_number_taken"
    assert no_serial.status_code == 201
    assert no_serial_again.status_code == 201


async def test_create_rejects_inactive_references_and_blank_fields(
    client: AsyncClient, admin_headers: dict[str, str], refs: Refs, db_session: AsyncSession
) -> None:
    refs.office.is_active = False
    await db_session.flush()

    inactive_location = await client.post(
        "/api/assets", headers=admin_headers, json=asset_payload(refs, location_id=refs.office.id)
    )
    missing_type = await client.post(
        "/api/assets", headers=admin_headers, json=asset_payload(refs, asset_type_id=999999)
    )
    blank_model = await client.post(
        "/api/assets", headers=admin_headers, json=asset_payload(refs, model="   ")
    )

    assert inactive_location.status_code == 422
    assert inactive_location.json()["error"]["code"] == "location_invalid"
    assert missing_type.json()["error"]["code"] == "asset_type_invalid"
    assert blank_model.json()["error"]["code"] == "model_blank"


async def test_non_admin_cannot_create(
    client: AsyncClient, refs: Refs, db_session: AsyncSession
) -> None:
    manager = await make_user(db_session, role=UserRole.MANAGER)
    headers = await login(client, manager.email)

    response = await client.post("/api/assets", headers=headers, json=asset_payload(refs))

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "insufficient_role"


async def test_list_filters_search_and_hides_written_off_by_default(
    client: AsyncClient, admin_headers: dict[str, str], refs: Refs, db_session: AsyncSession
) -> None:
    owner = await make_user(db_session)
    await make_asset(db_session, refs, inventory_number="INV-1", model="Dell Latitude")
    await make_asset(
        db_session, refs, inventory_number="INV-2", status=AssetStatus.IN_USE, owner_id=owner.id
    )
    await make_asset(db_session, refs, inventory_number="INV-3", status=AssetStatus.WRITTEN_OFF)

    async def numbers(**params: str | int | bool | list[str]) -> list[str]:
        response = await client.get("/api/assets", headers=admin_headers, params=params)
        assert response.status_code == 200, response.text
        return [item["inventory_number"] for item in response.json()["items"]]

    assert await numbers() == ["INV-1", "INV-2"]
    assert await numbers(status=["written_off", "in_use"]) == ["INV-2", "INV-3"]
    assert await numbers(owner_id=owner.id) == ["INV-2"]
    assert await numbers(q="latitude") == ["INV-1"]
    assert await numbers(location_id=refs.office.id) == []
    assert await numbers(needs_review=True) == []


async def test_visibility_by_role(
    client: AsyncClient, admin_headers: dict[str, str], refs: Refs, db_session: AsyncSession
) -> None:
    department = Department(name="Бухгалтерия")
    other_department = Department(name="Склад")
    db_session.add_all([department, other_department])
    await db_session.flush()
    manager = await make_user(db_session, role=UserRole.MANAGER, department_id=department.id)
    colleague = await make_user(db_session, department_id=department.id)
    stranger = await make_user(db_session, department_id=other_department.id)
    own = await make_asset(
        db_session, refs, inventory_number="INV-C", status=AssetStatus.IN_USE, owner_id=colleague.id
    )
    foreign = await make_asset(
        db_session, refs, inventory_number="INV-S", status=AssetStatus.IN_USE, owner_id=stranger.id
    )
    await make_asset(db_session, refs, inventory_number="INV-W")

    async def visible(user: User) -> list[str]:
        headers = await login(client, user.email)
        response = await client.get("/api/assets", headers=headers)
        return [item["inventory_number"] for item in response.json()["items"]]

    assert await visible(colleague) == ["INV-C"]
    assert await visible(manager) == ["INV-C"]
    admin_view = await client.get("/api/assets", headers=admin_headers)
    assert admin_view.json()["total"] == 3

    colleague_headers = await login(client, colleague.email)
    own_card = await client.get(f"/api/assets/{own.id}", headers=colleague_headers)
    foreign_card = await client.get(f"/api/assets/{foreign.id}", headers=colleague_headers)
    foreign_events = await client.get(f"/api/assets/{foreign.id}/events", headers=colleague_headers)
    assert own_card.status_code == 200
    assert own_card.json()["allowed_operations"] == []
    assert own_card.json()["owner_name"] == colleague.full_name
    assert foreign_card.status_code == 404
    assert foreign_card.json()["error"]["code"] == "asset_not_found"
    assert foreign_events.status_code == 404


async def test_edit_records_changes_and_checks_version(
    client: AsyncClient, admin_headers: dict[str, str], refs: Refs, db_session: AsyncSession
) -> None:
    created = await create_via_api(client, admin_headers, refs)
    url = f"/api/assets/{created['id']}"

    edited = await client.patch(
        url,
        headers=admin_headers,
        json={"version": 1, "model": "Lenovo ThinkPad T14 Gen 5", "initial_cost": "95000"},
    )
    stale = await client.patch(url, headers=admin_headers, json={"version": 1, "model": "X"})

    assert edited.status_code == 200, edited.text
    assert edited.json()["model"] == "Lenovo ThinkPad T14 Gen 5"
    assert edited.json()["version"] == 2
    assert stale.status_code == 409
    assert stale.json()["error"]["code"] == "version_conflict"

    events = (await client.get(f"{url}/events", headers=admin_headers)).json()["items"]
    assert events[0]["event_type"] == "edited"
    assert events[0]["changes"] == {"model": ["Lenovo ThinkPad T14", "Lenovo ThinkPad T14 Gen 5"]}
    assert events[0]["to_status"] is None
    assert events[0]["to_location_id"] is None


async def test_edit_without_changes_keeps_version(
    client: AsyncClient, admin_headers: dict[str, str], refs: Refs
) -> None:
    created = await create_via_api(client, admin_headers, refs)

    response = await client.patch(
        f"/api/assets/{created['id']}",
        headers=admin_headers,
        json={"version": 1, "model": "Lenovo ThinkPad T14"},
    )

    assert response.json()["version"] == 1


async def test_edit_rejects_null_for_required_field_and_duplicate_number(
    client: AsyncClient, admin_headers: dict[str, str], refs: Refs
) -> None:
    first = await create_via_api(client, admin_headers, refs)
    await create_via_api(
        client, admin_headers, refs, inventory_number="INV-002", serial_number=None
    )

    null_model = await client.patch(
        f"/api/assets/{first['id']}", headers=admin_headers, json={"version": 1, "model": None}
    )
    duplicate = await client.patch(
        f"/api/assets/{first['id']}",
        headers=admin_headers,
        json={"version": 1, "inventory_number": "INV-002"},
    )

    assert null_model.status_code == 422
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "inventory_number_taken"


async def test_written_off_asset_cannot_be_edited(
    client: AsyncClient, admin_headers: dict[str, str], refs: Refs, db_session: AsyncSession
) -> None:
    asset = await make_asset(
        db_session, refs, inventory_number="INV-X", status=AssetStatus.WRITTEN_OFF
    )

    response = await client.patch(
        f"/api/assets/{asset.id}", headers=admin_headers, json={"version": 1, "model": "X"}
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "asset_written_off"
