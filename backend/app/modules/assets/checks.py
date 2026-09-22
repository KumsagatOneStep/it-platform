"""Проверки ссылок на справочники и пользователей (ошибки 422 с кодом поля)."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ValidationFailedError
from app.modules.directories.service import get_reference_item
from app.modules.users_auth.service import get_user_info


async def check_asset_type(session: AsyncSession, asset_type_id: int) -> None:
    item = await get_reference_item(session, "asset-types", asset_type_id)
    if item is None or not item.is_active:
        raise ValidationFailedError(
            "Тип техники не найден или деактивирован", code="asset_type_invalid"
        )


async def check_location(session: AsyncSession, location_id: int) -> None:
    item = await get_reference_item(session, "locations", location_id)
    if item is None or not item.is_active:
        raise ValidationFailedError(
            "Локация не найдена или деактивирована", code="location_invalid"
        )


async def check_reason(session: AsyncSession, reason_id: int) -> None:
    item = await get_reference_item(session, "issue-reasons", reason_id)
    if item is None or not item.is_active or item.applicability == "stock":
        raise ValidationFailedError(
            "Причина не найдена, деактивирована или не применяется к технике",
            code="reason_invalid",
        )


async def check_recipient(session: AsyncSession, user_id: int) -> None:
    info = await get_user_info(session, user_id)
    if info is None or not info.is_active:
        raise ValidationFailedError(
            "Получатель не найден или деактивирован", code="recipient_invalid"
        )
