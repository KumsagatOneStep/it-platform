from typing import Annotated

from fastapi import APIRouter, Cookie, Request, Response

from app.core.config import get_settings
from app.core.db import SessionDep
from app.core.net import client_ip
from app.core.redis import RedisDep
from app.modules.users_auth import auth
from app.modules.users_auth.deps import PasswordChangeUserDep
from app.modules.users_auth.schemas import (
    AccessTokenResponse,
    ChangePasswordRequest,
    LoginRequest,
    MeRead,
)
from app.modules.users_auth.throttle import LoginThrottle

REFRESH_COOKIE_NAME = "refresh_token"
REFRESH_COOKIE_PATH = "/api/auth"

RefreshCookie = Annotated[str | None, Cookie()]

auth_router = APIRouter(prefix="/auth", tags=["auth"])


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
