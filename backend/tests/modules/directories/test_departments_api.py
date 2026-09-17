from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.events import event_bus
from app.modules.directories.events import DepartmentHeadChanged
from app.modules.users_auth.models import UserRole
from tests.factories import login, make_user


async def _create_department(
    client: AsyncClient, headers: dict[str, str], name: str, head_id: int | None = None
) -> dict[str, object]:
    response = await client.post(
        "/api/admin/departments", headers=headers, json={"name": name, "head_id": head_id}
    )
    assert response.status_code == 201, response.text
    return dict(response.json())


async def test_admin_creates_department_and_employee_lists_it(
    client: AsyncClient, admin_headers: dict[str, str], db_session: AsyncSession
) -> None:
    head = await make_user(db_session, role=UserRole.MANAGER)
    employee = await make_user(db_session)

    created = await _create_department(client, admin_headers, "Бухгалтерия", head.id)
    listed = await client.get("/api/departments", headers=await login(client, employee.email))

    assert created["head_id"] == head.id
    assert listed.status_code == 200
    assert {"id": created["id"], "name": "Бухгалтерия", "head_id": head.id} in listed.json()


async def test_employee_cannot_create_department(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    employee = await make_user(db_session)

    response = await client.post(
        "/api/admin/departments",
        headers=await login(client, employee.email),
        json={"name": "Склад"},
    )

    assert response.status_code == 403


async def test_duplicate_department_name_returns_409(
    client: AsyncClient, admin_headers: dict[str, str]
) -> None:
    await _create_department(client, admin_headers, "Склад")

    response = await client.post(
        "/api/admin/departments", headers=admin_headers, json={"name": "Склад"}
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "department_name_taken"


async def test_head_must_be_active_manager_or_admin(
    client: AsyncClient, admin_headers: dict[str, str], db_session: AsyncSession
) -> None:
    employee = await make_user(db_session, role=UserRole.EMPLOYEE)

    wrong_role = await client.post(
        "/api/admin/departments",
        headers=admin_headers,
        json={"name": "Отдел продаж", "head_id": employee.id},
    )
    missing = await client.post(
        "/api/admin/departments",
        headers=admin_headers,
        json={"name": "Отдел продаж", "head_id": 999999},
    )

    assert wrong_role.status_code == 422
    assert wrong_role.json()["error"]["code"] == "head_invalid_role"
    assert missing.status_code == 422
    assert missing.json()["error"]["code"] == "head_not_found"


async def test_update_with_trailing_space_duplicate_name_returns_409(
    client: AsyncClient, admin_headers: dict[str, str]
) -> None:
    await _create_department(client, admin_headers, "Финансы")
    other = await _create_department(client, admin_headers, "Кадры")

    response = await client.patch(
        f"/api/admin/departments/{other['id']}",
        headers=admin_headers,
        json={"name": "Финансы "},
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "department_name_taken"


async def test_whitespace_only_name_rejected_on_create_and_update(
    client: AsyncClient, admin_headers: dict[str, str]
) -> None:
    department = await _create_department(client, admin_headers, "Реклама")

    create_response = await client.post(
        "/api/admin/departments", headers=admin_headers, json={"name": "   "}
    )
    update_response = await client.patch(
        f"/api/admin/departments/{department['id']}",
        headers=admin_headers,
        json={"name": "   "},
    )

    assert create_response.status_code == 422
    assert create_response.json()["error"]["code"] == "department_name_blank"
    assert update_response.status_code == 422
    assert update_response.json()["error"]["code"] == "department_name_blank"


async def test_head_change_publishes_event(
    client: AsyncClient, admin_headers: dict[str, str], db_session: AsyncSession
) -> None:
    old_head = await make_user(db_session, role=UserRole.MANAGER)
    new_head = await make_user(db_session, role=UserRole.MANAGER)
    department = await _create_department(client, admin_headers, "Логистика", old_head.id)
    received: list[DepartmentHeadChanged] = []

    async def capture(session: AsyncSession, event: DepartmentHeadChanged) -> None:
        received.append(event)

    event_bus.subscribe(DepartmentHeadChanged)(capture)
    try:
        response = await client.patch(
            f"/api/admin/departments/{department['id']}",
            headers=admin_headers,
            json={"head_id": new_head.id},
        )
        unchanged = await client.patch(
            f"/api/admin/departments/{department['id']}",
            headers=admin_headers,
            json={"name": "Логистика и склад"},
        )
    finally:
        event_bus.unsubscribe(DepartmentHeadChanged, capture)

    assert response.status_code == 200
    assert unchanged.status_code == 200
    assert received == [
        DepartmentHeadChanged(
            department_id=int(str(department["id"])),
            old_head_id=old_head.id,
            new_head_id=new_head.id,
        )
    ]


async def test_department_head_cannot_be_deactivated(
    client: AsyncClient, admin_headers: dict[str, str], db_session: AsyncSession
) -> None:
    head = await make_user(db_session, role=UserRole.MANAGER)
    department = await _create_department(client, admin_headers, "Юристы", head.id)

    response = await client.post(f"/api/admin/users/{head.id}/deactivate", headers=admin_headers)

    assert response.status_code == 409
    assert response.json()["error"]["details"] == [
        {
            "kind": "department_head",
            "entity_id": department["id"],
            "title": "Руководитель отдела «Юристы»",
        }
    ]


async def test_user_with_unknown_department_rejected(
    client: AsyncClient, admin_headers: dict[str, str]
) -> None:
    response = await client.post(
        "/api/admin/users",
        headers=admin_headers,
        json={
            "email": "new@company.ru",
            "full_name": "Новый Сотрудник",
            "role": "employee",
            "department_id": 999999,
        },
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "department_not_found"


async def test_department_head_role_cannot_be_downgraded(
    client: AsyncClient, admin_headers: dict[str, str], db_session: AsyncSession
) -> None:
    head = await make_user(db_session, role=UserRole.MANAGER)
    department = await _create_department(client, admin_headers, "Снабжение", head.id)

    response = await client.patch(
        f"/api/admin/users/{head.id}", headers=admin_headers, json={"role": "employee"}
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "role_change_blocked"
    assert response.json()["error"]["details"] == [
        {
            "kind": "department_head",
            "entity_id": department["id"],
            "title": "Руководитель отдела «Снабжение»",
        }
    ]
    assert head.role is UserRole.MANAGER


async def test_department_head_can_be_promoted_to_admin(
    client: AsyncClient, admin_headers: dict[str, str], db_session: AsyncSession
) -> None:
    head = await make_user(db_session, role=UserRole.MANAGER)
    await _create_department(client, admin_headers, "Финансы", head.id)

    response = await client.patch(
        f"/api/admin/users/{head.id}", headers=admin_headers, json={"role": "admin"}
    )

    assert response.status_code == 200
    assert response.json()["role"] == "admin"
