from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.db import SessionDep
from app.core.errors import ForbiddenError, UnauthorizedError
from app.modules.users_auth.models import User, UserRole
from app.modules.users_auth.tokens import decode_access_token

_bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class CurrentUser:
    id: int
    email: str
    full_name: str
    role: UserRole
    department_id: int | None
    must_change_password: bool


async def get_current_user_allow_password_change(
    session: SessionDep,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> CurrentUser:
    if credentials is None:
        raise UnauthorizedError("Требуется вход", code="not_authenticated")
    user = await session.get(User, decode_access_token(credentials.credentials))
    if user is None or not user.is_active:
        raise UnauthorizedError("Требуется вход", code="not_authenticated")
    return CurrentUser(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        department_id=user.department_id,
        must_change_password=user.must_change_password,
    )


PasswordChangeUserDep = Annotated[CurrentUser, Depends(get_current_user_allow_password_change)]


async def get_current_user(user: PasswordChangeUserDep) -> CurrentUser:
    if user.must_change_password:
        raise ForbiddenError("Необходимо сменить пароль", code="password_change_required")
    return user


CurrentUserDep = Annotated[CurrentUser, Depends(get_current_user)]


def require_roles(*roles: UserRole) -> Callable[[CurrentUser], Awaitable[CurrentUser]]:
    allowed = frozenset(roles)

    async def dependency(user: CurrentUserDep) -> CurrentUser:
        if user.role not in allowed:
            raise ForbiddenError("Недостаточно прав", code="insufficient_role")
        return user

    return dependency


AdminDep = Annotated[CurrentUser, Depends(require_roles(UserRole.ADMIN))]
