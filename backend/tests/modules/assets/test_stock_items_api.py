"""Позиции расходников: создание, список, карточка, правка (п. 3 и 5 спецификации 2b)."""

from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import AuditLog
from app.modules.users_auth.models import UserRole
from tests.factories import login, make_user
from tests.modules.assets.conftest import StockRefs, make_stock_item, stock_item_payload


async def _create(
    client: AsyncClient, headers: dict[str, str], stock_refs: StockRefs, **overrides: object
) -> dict[str, Any]:
    response = await client.post(
        "/api/stock-items", headers=headers, json=stock_item_payload(stock_refs, **overrides)
    )
    assert response.status_code == 201, response.text
    body: dict[str, Any] = response.json()
    return body


async def test_admin_creates_item_with_zero_quantity(
    client: AsyncClient,
    admin_headers: dict[str, str],
    stock_refs: StockRefs,
    db_session: AsyncSession,
) -> None:
    created = await _create(client, admin_headers, stock_refs, name="  Картридж HP 85A ")

    assert created["name"] == "Картридж HP 85A"
    assert created["quantity"] == 0
    assert created["min_quantity"] == 2
    assert created["category_name"] == "Картриджи"
    assert created["location_name"] == "Склад"
    assert created["unit"] == "шт"
    assert created["is_active"] is True
    assert created["is_low"] is True
    assert created["version"] == 1
    audit = await db_session.scalars(
        select(AuditLog.action).where(
            AuditLog.entity_type == "stock_item", AuditLog.entity_id == str(created["id"])
        )
    )
    assert list(audit) == ["created"]


async def test_name_unique_per_location_ignoring_case(
    client: AsyncClient, admin_headers: dict[str, str], stock_refs: StockRefs
) -> None:
    await _create(client, admin_headers, stock_refs)

    same = await client.post(
        "/api/stock-items",
        headers=admin_headers,
        json=stock_item_payload(stock_refs, name="картридж hp 85a"),
    )
    other_location = await client.post(
        "/api/stock-items",
        headers=admin_headers,
        json=stock_item_payload(stock_refs, location_id=stock_refs.office.id),
    )

    assert same.status_code == 409
    assert same.json()["error"]["code"] == "stock_item_name_taken"
    assert other_location.status_code == 201


@pytest.mark.parametrize(
    ("overrides", "code"),
    [
        ({"name": "   "}, "name_blank"),
        ({"unit": " "}, "unit_blank"),
        ({"stock_category_id": 999999}, "category_invalid"),
        ({"location_id": 999999}, "location_invalid"),
    ],
)
async def test_create_validation(
    client: AsyncClient,
    admin_headers: dict[str, str],
    stock_refs: StockRefs,
    overrides: dict[str, object],
    code: str,
) -> None:
    response = await client.post(
        "/api/stock-items", headers=admin_headers, json=stock_item_payload(stock_refs, **overrides)
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == code


async def test_inactive_category_rejected(
    client: AsyncClient,
    admin_headers: dict[str, str],
    stock_refs: StockRefs,
    db_session: AsyncSession,
) -> None:
    stock_refs.paper.is_active = False
    await db_session.flush()

    response = await client.post(
        "/api/stock-items",
        headers=admin_headers,
        json=stock_item_payload(stock_refs, stock_category_id=stock_refs.paper.id),
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "category_invalid"


async def test_list_filters(
    client: AsyncClient,
    admin_headers: dict[str, str],
    stock_refs: StockRefs,
    db_session: AsyncSession,
) -> None:
    low = await make_stock_item(
        db_session, stock_refs, name="Картридж HP 85A", quantity=1, min_quantity=2
    )
    ok = await make_stock_item(
        db_session,
        stock_refs,
        name="Бумага A4",
        quantity=50,
        min_quantity=10,
        category=stock_refs.paper,
    )
    no_min = await make_stock_item(
        db_session, stock_refs, name="Картридж HP 85A", location=stock_refs.office
    )
    inactive = await make_stock_item(db_session, stock_refs, name="Старый тонер", is_active=False)

    async def ids(**params: str | int | bool) -> list[int]:
        response = await client.get("/api/stock-items", headers=admin_headers, params=params)
        assert response.status_code == 200, response.text
        return [item["id"] for item in response.json()["items"]]

    # Наименование без учёта регистра, затем склад (офис в refs создан раньше склада).
    assert await ids() == [ok.id, no_min.id, low.id]
    assert await ids(category_id=stock_refs.paper.id) == [ok.id]
    assert await ids(location_id=stock_refs.office.id) == [no_min.id]
    assert await ids(q="hp") == [no_min.id, low.id]
    assert await ids(low_stock=True) == [low.id]
    assert inactive.id in await ids(include_inactive=True)


async def test_get_item_and_404(
    client: AsyncClient,
    admin_headers: dict[str, str],
    stock_refs: StockRefs,
    db_session: AsyncSession,
) -> None:
    item = await make_stock_item(db_session, stock_refs, quantity=3)

    found = await client.get(f"/api/stock-items/{item.id}", headers=admin_headers)
    missing = await client.get("/api/stock-items/999999", headers=admin_headers)

    assert found.status_code == 200
    assert found.json()["quantity"] == 3
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "stock_item_not_found"


async def test_update_changes_fields_and_version(
    client: AsyncClient,
    admin_headers: dict[str, str],
    stock_refs: StockRefs,
    db_session: AsyncSession,
) -> None:
    created = await _create(client, admin_headers, stock_refs)

    response = await client.patch(
        f"/api/stock-items/{created['id']}",
        headers=admin_headers,
        json={"version": 1, "name": "Картридж HP 85A (оригинал)", "min_quantity": 5},
    )
    unchanged = await client.patch(
        f"/api/stock-items/{created['id']}",
        headers=admin_headers,
        json={"version": 2, "min_quantity": 5},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["name"] == "Картридж HP 85A (оригинал)"
    assert body["min_quantity"] == 5
    assert body["version"] == 2
    assert unchanged.json()["version"] == 2
    diff = await db_session.scalar(
        select(AuditLog.diff).where(
            AuditLog.entity_type == "stock_item",
            AuditLog.entity_id == str(created["id"]),
            AuditLog.action == "edited",
        )
    )
    assert diff == {
        "name": ["Картридж HP 85A", "Картридж HP 85A (оригинал)"],
        "min_quantity": [2, 5],
    }


async def test_update_version_conflict(
    client: AsyncClient, admin_headers: dict[str, str], stock_refs: StockRefs
) -> None:
    created = await _create(client, admin_headers, stock_refs)

    response = await client.patch(
        f"/api/stock-items/{created['id']}",
        headers=admin_headers,
        json={"version": 7, "unit": "уп"},
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "version_conflict"


async def test_update_name_conflict_and_blank(
    client: AsyncClient, admin_headers: dict[str, str], stock_refs: StockRefs
) -> None:
    await _create(client, admin_headers, stock_refs, name="Бумага A4")
    created = await _create(client, admin_headers, stock_refs)

    taken = await client.patch(
        f"/api/stock-items/{created['id']}",
        headers=admin_headers,
        json={"version": 1, "name": "БУМАГА a4"},
    )
    blank = await client.patch(
        f"/api/stock-items/{created['id']}", headers=admin_headers, json={"version": 1, "name": " "}
    )

    assert taken.status_code == 409
    assert taken.json()["error"]["code"] == "stock_item_name_taken"
    assert blank.status_code == 422
    assert blank.json()["error"]["code"] == "name_blank"


async def test_deactivate_only_when_empty(
    client: AsyncClient,
    admin_headers: dict[str, str],
    stock_refs: StockRefs,
    db_session: AsyncSession,
) -> None:
    full = await make_stock_item(db_session, stock_refs, quantity=3)
    empty = await make_stock_item(db_session, stock_refs, name="Бумага A4")

    rejected = await client.patch(
        f"/api/stock-items/{full.id}",
        headers=admin_headers,
        json={"version": 1, "is_active": False},
    )
    accepted = await client.patch(
        f"/api/stock-items/{empty.id}",
        headers=admin_headers,
        json={"version": 1, "is_active": False},
    )

    assert rejected.status_code == 409
    assert rejected.json()["error"]["code"] == "stock_not_empty"
    assert rejected.json()["error"]["details"] == {"quantity": 3}
    assert accepted.status_code == 200
    assert accepted.json()["is_active"] is False


@pytest.mark.parametrize("role", [UserRole.EMPLOYEE, UserRole.MANAGER])
async def test_non_admin_forbidden(
    client: AsyncClient,
    stock_refs: StockRefs,
    db_session: AsyncSession,
    role: UserRole,
) -> None:
    user = await make_user(db_session, email=f"{role.value}@company.ru", role=role)
    item = await make_stock_item(db_session, stock_refs)
    headers = await login(client, user.email)

    responses = [
        await client.get("/api/stock-items", headers=headers),
        await client.get(f"/api/stock-items/{item.id}", headers=headers),
        await client.post("/api/stock-items", headers=headers, json=stock_item_payload(stock_refs)),
        await client.patch(
            f"/api/stock-items/{item.id}", headers=headers, json={"version": 1, "unit": "уп"}
        ),
    ]

    assert [response.status_code for response in responses] == [403, 403, 403, 403]
    assert responses[0].json()["error"]["code"] == "insufficient_role"
