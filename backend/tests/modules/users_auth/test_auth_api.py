from datetime import UTC, datetime, timedelta

from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.users_auth.deps import AdminDep, CurrentUserDep
from app.modules.users_auth.models import RefreshToken, UserRole
from tests.factories import DEFAULT_PASSWORD, login, make_user


def _add_probe_routes(app: FastAPI) -> None:
    async def protected(user: CurrentUserDep) -> dict[str, int]:
        return {"id": user.id}

    async def admin_only(user: AdminDep) -> dict[str, int]:
        return {"id": user.id}

    app.add_api_route("/_probe/protected", protected, methods=["GET"])
    app.add_api_route("/_probe/admin", admin_only, methods=["GET"])


async def test_login_returns_access_token_and_sets_refresh_cookie(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    user = await make_user(db_session, email="ivanov@company.ru")

    response = await client.post(
        "/api/auth/login", json={"email": "IVANOV@company.ru", "password": DEFAULT_PASSWORD}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["must_change_password"] is False
    assert body["access_token"]
    set_cookie = response.headers["set-cookie"].lower()
    assert "refresh_token=" in set_cookie
    assert "httponly" in set_cookie
    assert "samesite=strict" in set_cookie
    assert "path=/api/auth" in set_cookie
    me = await client.get(
        "/api/auth/me", headers={"Authorization": f"Bearer {body['access_token']}"}
    )
    assert me.json()["id"] == user.id


async def test_login_with_wrong_password_returns_401(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    await make_user(db_session, email="ivanov@company.ru")

    response = await client.post(
        "/api/auth/login", json={"email": "ivanov@company.ru", "password": "wrong-password"}
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_credentials"


async def test_login_unknown_email_and_inactive_user_look_the_same(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    await make_user(db_session, email="fired@company.ru", is_active=False)

    unknown = await client.post(
        "/api/auth/login", json={"email": "nobody@company.ru", "password": DEFAULT_PASSWORD}
    )
    inactive = await client.post(
        "/api/auth/login", json={"email": "fired@company.ru", "password": DEFAULT_PASSWORD}
    )

    assert unknown.status_code == inactive.status_code == 401
    assert unknown.json() == inactive.json()


async def test_me_requires_valid_token(client: AsyncClient) -> None:
    missing = await client.get("/api/auth/me")
    garbage = await client.get("/api/auth/me", headers={"Authorization": "Bearer garbage"})

    assert missing.status_code == 401
    assert garbage.status_code == 401


async def test_refresh_rotates_token_and_detects_reuse(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    user = await make_user(db_session)
    login_response = await client.post(
        "/api/auth/login", json={"email": user.email, "password": DEFAULT_PASSWORD}
    )
    old_refresh = login_response.cookies["refresh_token"]

    rotated = await client.post("/api/auth/refresh")
    assert rotated.status_code == 200
    new_refresh = rotated.cookies["refresh_token"]
    assert new_refresh != old_refresh

    client.cookies.clear()
    reused = await client.post(
        "/api/auth/refresh", headers={"Cookie": f"refresh_token={old_refresh}"}
    )
    assert reused.status_code == 401

    after_reuse = await client.post(
        "/api/auth/refresh", headers={"Cookie": f"refresh_token={new_refresh}"}
    )
    assert after_reuse.status_code == 401


async def test_refresh_without_cookie_returns_401(client: AsyncClient) -> None:
    response = await client.post("/api/auth/refresh")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_refresh_token"


async def test_expired_refresh_token_rejected(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    user = await make_user(db_session)
    await login(client, user.email)
    await db_session.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user.id)
        .values(expires_at=datetime.now(UTC) - timedelta(seconds=1))
    )

    response = await client.post("/api/auth/refresh")

    assert response.status_code == 401


async def test_logout_revokes_refresh_token(client: AsyncClient, db_session: AsyncSession) -> None:
    user = await make_user(db_session)
    login_response = await client.post(
        "/api/auth/login", json={"email": user.email, "password": DEFAULT_PASSWORD}
    )
    refresh = login_response.cookies["refresh_token"]

    logout = await client.post("/api/auth/logout")
    assert logout.status_code == 204

    client.cookies.clear()
    response = await client.post(
        "/api/auth/refresh", headers={"Cookie": f"refresh_token={refresh}"}
    )
    assert response.status_code == 401


async def test_must_change_password_blocks_other_endpoints_until_changed(
    app: FastAPI, client: AsyncClient, db_session: AsyncSession
) -> None:
    _add_probe_routes(app)
    user = await make_user(db_session, must_change_password=True)
    login_response = await client.post(
        "/api/auth/login", json={"email": user.email, "password": DEFAULT_PASSWORD}
    )
    assert login_response.json()["must_change_password"] is True
    headers = {"Authorization": f"Bearer {login_response.json()['access_token']}"}

    blocked = await client.get("/_probe/protected", headers=headers)
    assert blocked.status_code == 403
    assert blocked.json()["error"]["code"] == "password_change_required"
    assert (await client.get("/api/auth/me", headers=headers)).status_code == 200

    changed = await client.post(
        "/api/auth/change-password",
        headers=headers,
        json={"current_password": DEFAULT_PASSWORD, "new_password": "Brand-New-Pass-2"},
    )
    assert changed.status_code == 200
    assert changed.json()["must_change_password"] is False

    new_headers = {"Authorization": f"Bearer {changed.json()['access_token']}"}
    assert (await client.get("/_probe/protected", headers=new_headers)).status_code == 200
    assert (await login(client, user.email, "Brand-New-Pass-2"))["Authorization"]


async def test_change_password_revokes_other_sessions(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    user = await make_user(db_session)
    first = await client.post(
        "/api/auth/login", json={"email": user.email, "password": DEFAULT_PASSWORD}
    )
    other_session_refresh = first.cookies["refresh_token"]
    headers = {"Authorization": f"Bearer {first.json()['access_token']}"}

    changed = await client.post(
        "/api/auth/change-password",
        headers=headers,
        json={"current_password": DEFAULT_PASSWORD, "new_password": "Brand-New-Pass-2"},
    )
    assert changed.status_code == 200

    client.cookies.clear()
    response = await client.post(
        "/api/auth/refresh", headers={"Cookie": f"refresh_token={other_session_refresh}"}
    )
    assert response.status_code == 401


async def test_change_password_with_wrong_current_password(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    user = await make_user(db_session)
    headers = await login(client, user.email)

    response = await client.post(
        "/api/auth/change-password",
        headers=headers,
        json={"current_password": "wrong-password", "new_password": "Brand-New-Pass-2"},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_current_password"


async def test_require_roles(app: FastAPI, client: AsyncClient, db_session: AsyncSession) -> None:
    _add_probe_routes(app)
    employee = await make_user(db_session, role=UserRole.EMPLOYEE)
    admin = await make_user(db_session, role=UserRole.ADMIN)

    employee_response = await client.get(
        "/_probe/admin", headers=await login(client, employee.email)
    )
    admin_response = await client.get("/_probe/admin", headers=await login(client, admin.email))

    assert employee_response.status_code == 403
    assert employee_response.json()["error"]["code"] == "insufficient_role"
    assert admin_response.status_code == 200


async def test_deactivated_user_access_token_stops_working(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    user = await make_user(db_session)
    headers = await login(client, user.email)
    user.is_active = False
    await db_session.flush()

    response = await client.get("/api/auth/me", headers=headers)

    assert response.status_code == 401
