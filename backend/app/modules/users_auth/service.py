"""Публичный интерфейс модуля users_auth. Другие модули импортируют только этот файл и events.py."""

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.users_auth.deps import (
    AdminDep,
    CurrentUser,
    CurrentUserDep,
    PasswordChangeUserDep,
    require_roles,
)
from app.modules.users_auth.models import User, UserRole
from app.modules.users_auth.users import create_first_admin

__all__ = [
    "AdminDep",
    "CurrentUser",
    "CurrentUserDep",
    "PasswordChangeUserDep",
    "UserInfo",
    "UserRole",
    "create_first_admin",
    "get_user_info",
    "get_user_names",
    "list_department_user_ids",
    "require_roles",
]


@dataclass(frozen=True)
class UserInfo:
    id: int
    email: str
    full_name: str
    role: UserRole
    department_id: int | None
    is_active: bool


async def get_user_info(session: AsyncSession, user_id: int) -> UserInfo | None:
    user = await session.get(User, user_id)
    if user is None:
        return None
    return UserInfo(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        department_id=user.department_id,
        is_active=user.is_active,
    )


async def get_user_names(session: AsyncSession, user_ids: set[int]) -> dict[int, str]:
    """ФИО пользователей по id (для подписей в чужих модулях)."""
    if not user_ids:
        return {}
    rows = await session.execute(select(User.id, User.full_name).where(User.id.in_(user_ids)))
    return {user_id: full_name for user_id, full_name in rows.tuples()}


async def list_department_user_ids(session: AsyncSession, department_id: int) -> list[int]:
    """Все пользователи отдела, включая деактивированных (их техника тоже числится за отделом)."""
    rows = await session.scalars(select(User.id).where(User.department_id == department_id))
    return list(rows)
