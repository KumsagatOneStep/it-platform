"""Реестр техники: список, карточка, история, создание и правка."""

from dataclasses import dataclass
from typing import Any, NoReturn

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import constraint_name
from app.core.errors import ConflictError
from app.core.text import normalize_text_field
from app.modules.assets.access import get_visible_asset, visibility_filter
from app.modules.assets.checks import check_asset_type, check_location
from app.modules.assets.history import Placement, changed_fields, record_event
from app.modules.assets.models import Asset, AssetEvent, AssetEventType, AssetStatus
from app.modules.users_auth.service import CurrentUser


@dataclass(frozen=True)
class AssetFilters:
    statuses: list[AssetStatus] | None = None
    asset_type_id: int | None = None
    owner_id: int | None = None
    location_id: int | None = None
    needs_review: bool | None = None
    q: str | None = None


def raise_asset_integrity_error(exc: IntegrityError) -> NoReturn:
    name = constraint_name(exc)
    if name == "uq_assets_inventory_number":
        raise ConflictError(
            "Техника с таким инвентарным номером уже есть", code="inventory_number_taken"
        ) from exc
    if name == "uq_assets_serial_number":
        raise ConflictError(
            "Техника с таким серийным номером уже есть", code="serial_number_taken"
        ) from exc
    raise exc


def _normalize(values: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(values)
    if isinstance(normalized.get("inventory_number"), str):
        normalized["inventory_number"] = normalize_text_field(
            normalized["inventory_number"],
            code="inventory_number_blank",
            message="Инвентарный номер не может быть пустым",
        )
    if isinstance(normalized.get("model"), str):
        normalized["model"] = normalize_text_field(
            normalized["model"], code="model_blank", message="Модель не может быть пустой"
        )
    return normalized


async def list_assets(
    session: AsyncSession, user: CurrentUser, filters: AssetFilters, *, limit: int, offset: int
) -> tuple[list[Asset], int]:
    stmt = select(Asset)
    condition = await visibility_filter(session, user)
    if condition is not None:
        stmt = stmt.where(condition)
    if filters.statuses:
        stmt = stmt.where(Asset.status.in_(filters.statuses))
    else:
        stmt = stmt.where(Asset.status != AssetStatus.WRITTEN_OFF)
    if filters.asset_type_id is not None:
        stmt = stmt.where(Asset.asset_type_id == filters.asset_type_id)
    if filters.owner_id is not None:
        stmt = stmt.where(Asset.owner_id == filters.owner_id)
    if filters.location_id is not None:
        stmt = stmt.where(Asset.location_id == filters.location_id)
    if filters.needs_review is not None:
        stmt = stmt.where(Asset.needs_review.is_(filters.needs_review))
    if filters.q and filters.q.strip():
        pattern = f"%{filters.q.strip()}%"
        stmt = stmt.where(
            or_(
                Asset.inventory_number.ilike(pattern),
                Asset.serial_number.ilike(pattern),
                Asset.model.ilike(pattern),
            )
        )
    total = await session.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = await session.scalars(
        stmt.order_by(Asset.inventory_number, Asset.id).limit(limit).offset(offset)
    )
    return list(rows), total


async def list_events(
    session: AsyncSession, user: CurrentUser, asset_id: int, *, limit: int, offset: int
) -> tuple[list[AssetEvent], int]:
    await get_visible_asset(session, user, asset_id)
    total = (
        await session.scalar(
            select(func.count()).select_from(AssetEvent).where(AssetEvent.asset_id == asset_id)
        )
        or 0
    )
    rows = await session.scalars(
        select(AssetEvent)
        .where(AssetEvent.asset_id == asset_id)
        .order_by(AssetEvent.id.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(rows), total


async def create_asset(session: AsyncSession, *, actor_id: int, data: dict[str, Any]) -> Asset:
    data = _normalize(data)
    await check_asset_type(session, data["asset_type_id"])
    await check_location(session, data["location_id"])
    asset = Asset(**data, status=AssetStatus.IN_STOCK, owner_id=None, version=1)
    try:
        async with session.begin_nested():
            session.add(asset)
    except IntegrityError as exc:
        raise_asset_integrity_error(exc)
    record_event(
        session,
        asset,
        event_type=AssetEventType.CREATED,
        actor_id=actor_id,
        before=None,
    )
    await session.commit()
    return asset


async def update_asset(
    session: AsyncSession,
    actor: CurrentUser,
    *,
    asset_id: int,
    version: int,
    updates: dict[str, Any],
) -> Asset:
    asset = await get_visible_asset(session, actor, asset_id, for_update=True)
    if asset.status == AssetStatus.WRITTEN_OFF:
        raise ConflictError("Списанную технику нельзя редактировать", code="asset_written_off")
    if asset.version != version:
        raise ConflictError(
            "Данные изменил другой пользователь",
            code="version_conflict",
            details={"version": asset.version},
        )
    updates = _normalize(updates)
    changes = changed_fields({key: getattr(asset, key) for key in updates}, updates)
    if not changes:
        return asset
    if "asset_type_id" in changes:
        await check_asset_type(session, updates["asset_type_id"])
    try:
        async with session.begin_nested():
            for key in changes:
                setattr(asset, key, updates[key])
            asset.version += 1
    except IntegrityError as exc:
        raise_asset_integrity_error(exc)
    record_event(
        session,
        asset,
        event_type=AssetEventType.EDITED,
        actor_id=actor.id,
        before=Placement.of(asset),
        changes=changes,
    )
    await session.commit()
    return asset
