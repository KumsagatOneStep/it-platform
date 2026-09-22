"""Область видимости реестра (п. 2.3 ТЗ): Employee — своя техника, Manager — отдела, Admin — всё."""

from sqlalchemy import ColumnElement, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.modules.assets.models import Asset
from app.modules.users_auth.service import CurrentUser, UserRole, list_department_user_ids


async def visibility_filter(session: AsyncSession, user: CurrentUser) -> ColumnElement[bool] | None:
    """Условие на видимые пользователю активы; None — ограничений нет."""
    if user.role == UserRole.ADMIN:
        return None
    if user.role == UserRole.MANAGER and user.department_id is not None:
        member_ids = await list_department_user_ids(session, user.department_id)
        return Asset.owner_id.in_(member_ids)
    return Asset.owner_id == user.id


async def get_visible_asset(
    session: AsyncSession, user: CurrentUser, asset_id: int, *, for_update: bool = False
) -> Asset:
    """Актив в области видимости пользователя; иначе 404, чтобы не раскрывать его существование."""
    stmt = select(Asset).where(Asset.id == asset_id)
    condition = await visibility_filter(session, user)
    if condition is not None:
        stmt = stmt.where(condition)
    if for_update:
        stmt = stmt.with_for_update()
    asset = await session.scalar(stmt)
    if asset is None:
        raise NotFoundError("Техника не найдена", code="asset_not_found")
    return asset
