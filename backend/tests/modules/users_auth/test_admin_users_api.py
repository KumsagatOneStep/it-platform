from httpx import AsyncClient
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import AuditLog
from app.core.events import event_bus
from app.modules.users_auth.events import (
    Blocker,
    UserDeactivationRequested,
    UserRoleChangeRequested,
)
from app.modules.users_auth.models import User, UserRole
from app.modules.users_auth.throttle import LoginThrottle
from tests.factories import DEFAULT_PASSWORD, login, make_user


async def test_admin_endpoints_require_admin(client: AsyncClient, db_session: AsyncSession) -> None:
    manager = await make_user(db_session, role=UserRole.MANAGER)

    anonymous = await client.get("/api/admin/users")
    as_manager = await client.get("/api/admin/users", headers=await login(client, manager.email))

    assert anonymous.status_code == 401
    assert as_manager.status_code == 403


async def test_create_user_returns_temporary_password(
    client: AsyncClient, admin_headers: dict[str, str], db_session: AsyncSession
) -> None:
    response = await client.post(
        "/api/admin/users",
        headers=admin_headers,
        json={"email": "Petrov@company.ru", "full_name": "Петров Пётр", "role": "employee"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["user"]["email"] == "petrov@company.ru"
    assert body["user"]["must_change_password"] is True
    login_response = await client.post(
        "/api/auth/login",
        json={"email": "petrov@company.ru", "password": body["temporary_password"]},
    )
    assert login_response.json()["must_change_password"] is True
    audit = await db_session.scalar(
        select(AuditLog).where(
            AuditLog.entity_type == "user", AuditLog.entity_id == str(body["user"]["id"])
        )
    )
    assert audit is not None and audit.action == "create"


async def test_create_user_with_taken_email_returns_409(
    client: AsyncClient, admin_headers: dict[str, str], db_session: AsyncSession
) -> None:
    await make_user(db_session, email="petrov@company.ru")

    response = await client.post(
        "/api/admin/users",
        headers=admin_headers,
        json={"email": "petrov@company.ru", "full_name": "Петров Пётр", "role": "employee"},
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "email_taken"


async def test_list_users_filters_and_paginates(
    client: AsyncClient, admin_headers: dict[str, str], db_session: AsyncSession
) -> None:
    await make_user(db_session, full_name="Сидоров Семён", role=UserRole.MANAGER)
    await make_user(db_session, full_name="Сидорова Анна", role=UserRole.EMPLOYEE)
    await make_user(db_session, full_name="Кузнецов Олег", role=UserRole.EMPLOYEE)

    by_name = await client.get(
        "/api/admin/users", headers=admin_headers, params={"q": "сидор", "limit": 1}
    )
    by_role = await client.get(
        "/api/admin/users", headers=admin_headers, params={"role": "manager"}
    )

    assert by_name.json()["total"] == 2
    assert len(by_name.json()["items"]) == 1
    assert [u["full_name"] for u in by_role.json()["items"]] == ["Сидоров Семён"]


async def test_update_user_changes_fields_and_writes_audit(
    client: AsyncClient, admin_headers: dict[str, str], db_session: AsyncSession
) -> None:
    user = await make_user(db_session, full_name="Старое Имя")

    response = await client.patch(
        f"/api/admin/users/{user.id}",
        headers=admin_headers,
        json={"full_name": "Новое Имя", "role": "manager"},
    )

    assert response.status_code == 200
    assert response.json()["full_name"] == "Новое Имя"
    assert response.json()["role"] == "manager"
    audit = await db_session.scalar(
        select(AuditLog).where(AuditLog.entity_id == str(user.id), AuditLog.action == "update")
    )
    assert audit is not None
    assert audit.diff["full_name"] == ["Старое Имя", "Новое Имя"]


async def test_update_rejects_null_for_required_field(
    client: AsyncClient, admin_headers: dict[str, str], db_session: AsyncSession
) -> None:
    user = await make_user(db_session)

    response = await client.patch(
        f"/api/admin/users/{user.id}", headers=admin_headers, json={"full_name": None}
    )

    assert response.status_code == 422


async def test_last_admin_cannot_be_demoted(
    client: AsyncClient, admin_user: User, admin_headers: dict[str, str]
) -> None:
    response = await client.patch(
        f"/api/admin/users/{admin_user.id}", headers=admin_headers, json={"role": "manager"}
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "last_admin"


async def test_deactivate_revokes_sessions_and_blocks_login(
    client: AsyncClient, admin_headers: dict[str, str], db_session: AsyncSession
) -> None:
    user = await make_user(db_session)
    user_login = await client.post(
        "/api/auth/login", json={"email": user.email, "password": DEFAULT_PASSWORD}
    )
    user_refresh = user_login.cookies["refresh_token"]

    response = await client.post(f"/api/admin/users/{user.id}/deactivate", headers=admin_headers)

    assert response.status_code == 200
    assert response.json()["is_active"] is False
    client.cookies.clear()
    refresh = await client.post(
        "/api/auth/refresh", headers={"Cookie": f"refresh_token={user_refresh}"}
    )
    assert refresh.status_code == 401
    relogin = await client.post(
        "/api/auth/login", json={"email": user.email, "password": DEFAULT_PASSWORD}
    )
    assert relogin.status_code == 401


async def test_cannot_deactivate_self(
    client: AsyncClient, admin_user: User, admin_headers: dict[str, str]
) -> None:
    response = await client.post(
        f"/api/admin/users/{admin_user.id}/deactivate", headers=admin_headers
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "cannot_deactivate_self"


async def test_deactivation_blocked_by_subscriber(
    client: AsyncClient, admin_headers: dict[str, str], db_session: AsyncSession
) -> None:
    user = await make_user(db_session)

    async def blocker(session: AsyncSession, event: UserDeactivationRequested) -> None:
        event.blockers.append(Blocker(kind="test", entity_id=1, title="Тестовый блок"))

    event_bus.subscribe(UserDeactivationRequested)(blocker)
    try:
        response = await client.post(
            f"/api/admin/users/{user.id}/deactivate", headers=admin_headers
        )
    finally:
        event_bus.unsubscribe(UserDeactivationRequested, blocker)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "deactivation_blocked"
    assert response.json()["error"]["details"] == [
        {"kind": "test", "entity_id": 1, "title": "Тестовый блок"}
    ]
    assert user.is_active


async def test_activate_user(
    client: AsyncClient, admin_headers: dict[str, str], db_session: AsyncSession
) -> None:
    user = await make_user(db_session, is_active=False)

    response = await client.post(f"/api/admin/users/{user.id}/activate", headers=admin_headers)

    assert response.status_code == 200
    assert response.json()["is_active"] is True


async def test_temporary_password_replaces_old_one(
    client: AsyncClient, admin_headers: dict[str, str], db_session: AsyncSession
) -> None:
    user = await make_user(db_session)

    response = await client.post(
        f"/api/admin/users/{user.id}/temporary-password", headers=admin_headers
    )

    assert response.status_code == 200
    temporary = response.json()["temporary_password"]
    old = await client.post(
        "/api/auth/login", json={"email": user.email, "password": DEFAULT_PASSWORD}
    )
    new = await client.post("/api/auth/login", json={"email": user.email, "password": temporary})
    assert old.status_code == 401
    assert new.status_code == 200
    assert new.json()["must_change_password"] is True


async def test_unlock_login(
    client: AsyncClient,
    admin_headers: dict[str, str],
    db_session: AsyncSession,
    redis_client: Redis,
) -> None:
    user = await make_user(db_session)
    throttle = LoginThrottle(redis_client)
    for _ in range(5):
        await throttle.register_failure(user.email, "203.0.113.5")

    response = await client.post(f"/api/admin/users/{user.id}/unlock-login", headers=admin_headers)

    assert response.status_code == 204
    assert not await throttle.is_locked(user.email, "203.0.113.5")


async def test_user_lookup_returns_only_active_matches(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    employee = await make_user(db_session, full_name="Смирнов Алексей")
    await make_user(db_session, full_name="Смирнова Ольга", is_active=False)
    await make_user(db_session, full_name="Попов Игорь")

    response = await client.get(
        "/api/users", params={"q": "смирнов"}, headers=await login(client, employee.email)
    )

    assert response.status_code == 200
    assert [u["full_name"] for u in response.json()] == ["Смирнов Алексей"]


async def test_whitespace_full_name_rejected_on_create_and_update(
    client: AsyncClient, admin_headers: dict[str, str], db_session: AsyncSession
) -> None:
    user = await make_user(db_session, full_name="Старое Имя")

    created = await client.post(
        "/api/admin/users",
        headers=admin_headers,
        json={"email": "blank@company.ru", "full_name": "   ", "role": "employee"},
    )
    updated = await client.patch(
        f"/api/admin/users/{user.id}", headers=admin_headers, json={"full_name": "   "}
    )

    assert created.status_code == 422
    assert created.json()["error"]["code"] == "full_name_blank"
    assert created.json()["error"]["message"] == "ФИО не может быть пустым"
    assert updated.status_code == 422
    assert updated.json()["error"]["code"] == "full_name_blank"
    assert user.full_name == "Старое Имя"


async def test_update_strips_full_name(
    client: AsyncClient, admin_headers: dict[str, str], db_session: AsyncSession
) -> None:
    user = await make_user(db_session)

    response = await client.patch(
        f"/api/admin/users/{user.id}", headers=admin_headers, json={"full_name": "  Новое Имя "}
    )

    assert response.status_code == 200
    assert response.json()["full_name"] == "Новое Имя"


async def test_role_change_publishes_event_and_respects_blockers(
    client: AsyncClient, admin_headers: dict[str, str], db_session: AsyncSession
) -> None:
    user = await make_user(db_session, role=UserRole.MANAGER)
    events: list[UserRoleChangeRequested] = []

    async def blocker(session: AsyncSession, event: UserRoleChangeRequested) -> None:
        events.append(event)
        event.blockers.append(Blocker(kind="test", entity_id=1, title="Тестовый блок"))

    event_bus.subscribe(UserRoleChangeRequested)(blocker)
    try:
        same_role = await client.patch(
            f"/api/admin/users/{user.id}", headers=admin_headers, json={"role": "manager"}
        )
        blocked = await client.patch(
            f"/api/admin/users/{user.id}", headers=admin_headers, json={"role": "employee"}
        )
    finally:
        event_bus.unsubscribe(UserRoleChangeRequested, blocker)

    assert same_role.status_code == 200
    assert blocked.status_code == 409
    assert blocked.json()["error"]["code"] == "role_change_blocked"
    assert blocked.json()["error"]["details"] == [
        {"kind": "test", "entity_id": 1, "title": "Тестовый блок"}
    ]
    assert [(e.user_id, e.old_role, e.new_role) for e in events] == [
        (user.id, UserRole.MANAGER, UserRole.EMPLOYEE)
    ]
    assert user.role is UserRole.MANAGER
