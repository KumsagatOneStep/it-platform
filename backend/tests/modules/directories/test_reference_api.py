from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import AuditLog
from app.modules.users_auth.models import UserRole
from tests.factories import login, make_user

PAYLOADS: dict[str, dict[str, Any]] = {
    "locations": {"name": "Главный офис, каб. 101", "description": "3 этаж"},
    "asset-types": {"name": "Ноутбук"},
    "stock-categories": {"name": "Картриджи"},
    "issue-reasons": {"name": "Новый сотрудник", "applicability": "both"},
    "ticket-types": {"code": "repair", "name": "На ремонт", "requires_approval": False},
}


@pytest.mark.parametrize("slug", list(PAYLOADS))
async def test_reference_lifecycle(
    slug: str, client: AsyncClient, admin_headers: dict[str, str], db_session: AsyncSession
) -> None:
    employee = await make_user(db_session)
    employee_headers = await login(client, employee.email)

    created = await client.post(
        f"/api/admin/directories/{slug}", headers=admin_headers, json=PAYLOADS[slug]
    )
    assert created.status_code == 201, created.text
    item_id = created.json()["id"]
    assert created.json()["is_active"] is True

    visible = await client.get(f"/api/directories/{slug}", headers=employee_headers)
    assert item_id in [item["id"] for item in visible.json()]

    deactivated = await client.patch(
        f"/api/admin/directories/{slug}/{item_id}", headers=admin_headers, json={"is_active": False}
    )
    assert deactivated.status_code == 200
    assert deactivated.json()["is_active"] is False

    hidden = await client.get(
        f"/api/directories/{slug}", headers=employee_headers, params={"include_inactive": True}
    )
    assert item_id not in [item["id"] for item in hidden.json()]
    for_admin = await client.get(
        f"/api/directories/{slug}", headers=admin_headers, params={"include_inactive": True}
    )
    assert item_id in [item["id"] for item in for_admin.json()]

    audit = await db_session.scalars(
        select(AuditLog.action).where(AuditLog.entity_id == str(item_id))
    )
    assert {"create", "update"} <= set(audit)


@pytest.mark.parametrize("slug", list(PAYLOADS))
async def test_duplicate_returns_409(
    slug: str, client: AsyncClient, admin_headers: dict[str, str]
) -> None:
    first = await client.post(
        f"/api/admin/directories/{slug}", headers=admin_headers, json=PAYLOADS[slug]
    )
    assert first.status_code == 201

    second = await client.post(
        f"/api/admin/directories/{slug}", headers=admin_headers, json=PAYLOADS[slug]
    )

    assert second.status_code == 409
    assert second.json()["error"]["code"] == "already_exists"


async def test_employee_cannot_modify_directories(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    employee = await make_user(db_session)

    response = await client.post(
        "/api/admin/directories/locations",
        headers=await login(client, employee.email),
        json={"name": "Склад"},
    )

    assert response.status_code == 403


async def test_rename_rejects_null_name(client: AsyncClient, admin_headers: dict[str, str]) -> None:
    created = await client.post(
        "/api/admin/directories/asset-types", headers=admin_headers, json={"name": "Монитор"}
    )

    response = await client.patch(
        f"/api/admin/directories/asset-types/{created.json()['id']}",
        headers=admin_headers,
        json={"name": None},
    )

    assert response.status_code == 422


async def test_issue_reason_rejects_unknown_applicability(
    client: AsyncClient, admin_headers: dict[str, str]
) -> None:
    response = await client.post(
        "/api/admin/directories/issue-reasons",
        headers=admin_headers,
        json={"name": "Замена", "applicability": "everything"},
    )

    assert response.status_code == 422


async def test_ticket_type_requires_approval_by_default(
    client: AsyncClient, admin_headers: dict[str, str]
) -> None:
    response = await client.post(
        "/api/admin/directories/ticket-types",
        headers=admin_headers,
        json={"code": "equipment", "name": "На выдачу техники"},
    )

    assert response.status_code == 201
    assert response.json()["requires_approval"] is True
    assert response.json()["default_assignee_id"] is None


async def test_ticket_type_default_assignee_must_be_manager_or_admin(
    client: AsyncClient, admin_headers: dict[str, str], db_session: AsyncSession
) -> None:
    employee = await make_user(db_session, role=UserRole.EMPLOYEE)
    manager = await make_user(db_session, role=UserRole.MANAGER)

    rejected = await client.post(
        "/api/admin/directories/ticket-types",
        headers=admin_headers,
        json={"code": "supplies", "name": "На расходники", "default_assignee_id": employee.id},
    )
    accepted = await client.post(
        "/api/admin/directories/ticket-types",
        headers=admin_headers,
        json={"code": "supplies", "name": "На расходники", "default_assignee_id": manager.id},
    )

    assert rejected.status_code == 422
    assert rejected.json()["error"]["code"] == "invalid_default_assignee"
    assert accepted.status_code == 201
    assert accepted.json()["default_assignee_id"] == manager.id


# --- Дополнительные тесты: нормализация названия (см. review round 1 задачи 10) ---


@pytest.mark.parametrize("slug", list(PAYLOADS))
async def test_whitespace_only_name_rejected_on_create_and_update(
    slug: str, client: AsyncClient, admin_headers: dict[str, str]
) -> None:
    created = await client.post(
        f"/api/admin/directories/{slug}", headers=admin_headers, json=PAYLOADS[slug]
    )
    assert created.status_code == 201, created.text

    blank_payload = {**PAYLOADS[slug], "name": "   "}
    if slug == "ticket-types":
        blank_payload["code"] = "blank-name-check"
    create_response = await client.post(
        f"/api/admin/directories/{slug}", headers=admin_headers, json=blank_payload
    )
    update_response = await client.patch(
        f"/api/admin/directories/{slug}/{created.json()['id']}",
        headers=admin_headers,
        json={"name": "   "},
    )

    assert create_response.status_code == 422, create_response.text
    assert create_response.json()["error"]["code"] == "name_blank"
    assert update_response.status_code == 422, update_response.text
    assert update_response.json()["error"]["code"] == "name_blank"


@pytest.mark.parametrize("slug", list(PAYLOADS))
async def test_update_with_trailing_space_duplicate_name_returns_409(
    slug: str, client: AsyncClient, admin_headers: dict[str, str]
) -> None:
    first = await client.post(
        f"/api/admin/directories/{slug}", headers=admin_headers, json=PAYLOADS[slug]
    )
    assert first.status_code == 201, first.text

    second_payload = {**PAYLOADS[slug], "name": PAYLOADS[slug]["name"] + " второй"}
    if slug == "ticket-types":
        second_payload["code"] = "repair-second"
    second = await client.post(
        f"/api/admin/directories/{slug}", headers=admin_headers, json=second_payload
    )
    assert second.status_code == 201, second.text

    response = await client.patch(
        f"/api/admin/directories/{slug}/{second.json()['id']}",
        headers=admin_headers,
        json={"name": PAYLOADS[slug]["name"] + " "},
    )

    assert response.status_code == 409, response.text
    assert response.json()["error"]["code"] == "already_exists"
