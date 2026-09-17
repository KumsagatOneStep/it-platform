from typing import Annotated

from fastapi import APIRouter, Cookie, Query, Request, Response

from app.core.config import get_settings
from app.core.db import SessionDep
from app.core.net import client_ip
from app.core.redis import RedisDep
from app.core.schemas import Page, PaginationDep
from app.modules.users_auth import auth, users
from app.modules.users_auth.deps import AdminDep, CurrentUserDep, PasswordChangeUserDep
from app.modules.users_auth.models import UserRole
from app.modules.users_auth.schemas import (
    AccessTokenResponse,
    ChangePasswordRequest,
    LoginRequest,
    MeRead,
    TemporaryPasswordResponse,
    UserBrief,
    UserCreate,
    UserCreatedResponse,
    UserRead,
    UserUpdate,
)
from app.modules.users_auth.throttle import LoginThrottle

REFRESH_COOKIE_NAME = "refresh_token"
REFRESH_COOKIE_PATH = "/api/auth"

RefreshCookie = Annotated[str | None, Cookie()]

auth_router = APIRouter(prefix="/auth", tags=["auth"])
admin_users_router = APIRouter(prefix="/admin/users", tags=["admin: users"])
users_router = APIRouter(prefix="/users", tags=["users"])


def _token_response(response: Response, pair: auth.TokenPair) -> AccessTokenResponse:
    settings = get_settings()
    response.set_cookie(
        REFRESH_COOKIE_NAME,
        pair.refresh_token,
        max_age=settings.refresh_token_ttl_days * 24 * 60 * 60,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="strict",
        path=REFRESH_COOKIE_PATH,
    )
    return AccessTokenResponse(
        access_token=pair.access_token, must_change_password=pair.must_change_password
    )


@auth_router.post("/login", response_model=AccessTokenResponse)
async def login(
    body: LoginRequest,
    request: Request,
    response: Response,
    session: SessionDep,
    redis: RedisDep,
) -> AccessTokenResponse:
    pair = await auth.login(
        session,
        LoginThrottle(redis),
        email=body.email,
        password=body.password,
        ip=client_ip(request, get_settings().trusted_proxies),
    )
    return _token_response(response, pair)


@auth_router.post("/refresh", response_model=AccessTokenResponse)
async def refresh(
    response: Response, session: SessionDep, refresh_token: RefreshCookie = None
) -> AccessTokenResponse:
    pair = await auth.rotate_refresh_token(session, refresh_token)
    return _token_response(response, pair)


@auth_router.post("/logout", status_code=204)
async def logout(session: SessionDep, refresh_token: RefreshCookie = None) -> Response:
    await auth.logout(session, refresh_token)
    response = Response(status_code=204)
    response.delete_cookie(
        REFRESH_COOKIE_NAME,
        path=REFRESH_COOKIE_PATH,
        secure=get_settings().cookie_secure,
        httponly=True,
        samesite="strict",
    )
    return response


@auth_router.get("/me", response_model=MeRead)
async def me(user: PasswordChangeUserDep) -> MeRead:
    return MeRead.model_validate(user)


@auth_router.post("/change-password", response_model=AccessTokenResponse)
async def change_password(
    body: ChangePasswordRequest,
    response: Response,
    session: SessionDep,
    user: PasswordChangeUserDep,
) -> AccessTokenResponse:
    pair = await auth.change_password(
        session,
        user_id=user.id,
        current_password=body.current_password,
        new_password=body.new_password,
    )
    return _token_response(response, pair)


@admin_users_router.get("", response_model=Page[UserRead])
async def list_users(
    session: SessionDep,
    admin: AdminDep,
    pagination: PaginationDep,
    q: Annotated[str | None, Query(max_length=100)] = None,
    role: UserRole | None = None,
    department_id: int | None = None,
    is_active: bool | None = None,
) -> Page[UserRead]:
    items, total = await users.list_users(
        session,
        q=q,
        role=role,
        department_id=department_id,
        is_active=is_active,
        limit=pagination.limit,
        offset=pagination.offset,
    )
    return Page(
        items=[UserRead.model_validate(item) for item in items],
        total=total,
        limit=pagination.limit,
        offset=pagination.offset,
    )


@admin_users_router.post("", response_model=UserCreatedResponse, status_code=201)
async def create_user(
    body: UserCreate, session: SessionDep, admin: AdminDep
) -> UserCreatedResponse:
    user, temporary_password = await users.admin_create_user(
        session,
        actor_id=admin.id,
        email=body.email,
        full_name=body.full_name,
        role=body.role,
        department_id=body.department_id,
    )
    return UserCreatedResponse(
        user=UserRead.model_validate(user), temporary_password=temporary_password
    )


@admin_users_router.get("/{user_id}", response_model=UserRead)
async def get_user(user_id: int, session: SessionDep, admin: AdminDep) -> UserRead:
    return UserRead.model_validate(await users.get_user_or_404(session, user_id))


@admin_users_router.patch("/{user_id}", response_model=UserRead)
async def update_user(
    user_id: int, body: UserUpdate, session: SessionDep, admin: AdminDep
) -> UserRead:
    user = await users.update_user(
        session, actor_id=admin.id, user_id=user_id, updates=body.model_dump(exclude_unset=True)
    )
    return UserRead.model_validate(user)


@admin_users_router.post("/{user_id}/deactivate", response_model=UserRead)
async def deactivate_user(user_id: int, session: SessionDep, admin: AdminDep) -> UserRead:
    user = await users.deactivate_user(session, actor_id=admin.id, user_id=user_id)
    return UserRead.model_validate(user)


@admin_users_router.post("/{user_id}/activate", response_model=UserRead)
async def activate_user(user_id: int, session: SessionDep, admin: AdminDep) -> UserRead:
    user = await users.activate_user(session, actor_id=admin.id, user_id=user_id)
    return UserRead.model_validate(user)


@admin_users_router.post("/{user_id}/temporary-password", response_model=TemporaryPasswordResponse)
async def issue_temporary_password(
    user_id: int, session: SessionDep, admin: AdminDep
) -> TemporaryPasswordResponse:
    password = await users.issue_temporary_password(session, actor_id=admin.id, user_id=user_id)
    return TemporaryPasswordResponse(temporary_password=password)


@admin_users_router.post("/{user_id}/unlock-login", status_code=204)
async def unlock_login(
    user_id: int, session: SessionDep, redis: RedisDep, admin: AdminDep
) -> Response:
    await users.unlock_login(session, LoginThrottle(redis), actor_id=admin.id, user_id=user_id)
    return Response(status_code=204)


@users_router.get("", response_model=list[UserBrief])
async def search_users(
    session: SessionDep,
    user: CurrentUserDep,
    q: Annotated[str, Query(min_length=1, max_length=100)],
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
) -> list[UserBrief]:
    found = await users.search_active_users(session, q=q, limit=limit)
    return [UserBrief.model_validate(item) for item in found]
