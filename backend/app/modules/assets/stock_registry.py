"""Позиции расходников: список, карточка, создание и правка (остаток меняют только движения)."""

import uuid
from dataclasses import dataclass
from typing import Any, NoReturn

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import diff_values, record_audit
from app.core.db import constraint_name
from app.core.errors import ConflictError, NotFoundError
from app.core.text import normalize_text_field
from app.modules.assets.checks import check_location, check_stock_category
from app.modules.assets.history import changed_fields
from app.modules.assets.stock_models import StockItem, StockMovement, StockMovementType

ENTITY_TYPE = "stock_item"


@dataclass(frozen=True)
class StockItemFilters:
    category_id: int | None = None
    location_id: int | None = None
    q: str | None = None
    low_stock: bool = False
    in_stock: bool = False
    """Только позиции с остатком > 0 (выбор для выдачи)."""
    include_inactive: bool = False


def is_low(item: StockItem) -> bool:
    return item.min_quantity > 0 and item.quantity <= item.min_quantity


def raise_stock_integrity_error(exc: IntegrityError) -> NoReturn:
    if constraint_name(exc) == "uq_stock_items_name_location":
        raise ConflictError(
            "На этом складе уже есть позиция с таким наименованием",
            code="stock_item_name_taken",
        ) from exc
    raise exc


def _normalize(values: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(values)
    if isinstance(normalized.get("name"), str):
        normalized["name"] = normalize_text_field(
            normalized["name"], code="name_blank", message="Наименование не может быть пустым"
        )
    if isinstance(normalized.get("unit"), str):
        normalized["unit"] = normalize_text_field(
            normalized["unit"], code="unit_blank", message="Единица измерения не может быть пустой"
        )
    return normalized


def item_snapshot(item: StockItem) -> dict[str, Any]:
    """Поля позиции для аудита создания."""
    return {
        "name": item.name,
        "stock_category_id": item.stock_category_id,
        "unit": item.unit,
        "location_id": item.location_id,
        "min_quantity": item.min_quantity,
    }


async def get_stock_item(
    session: AsyncSession, item_id: int, *, for_update: bool = False
) -> StockItem:
    stmt = select(StockItem).where(StockItem.id == item_id)
    if for_update:
        # populate_existing: перечитать остаток под блокировкой, даже если объект уже в сессии.
        stmt = stmt.with_for_update().execution_options(populate_existing=True)
    item = await session.scalar(stmt)
    if item is None:
        raise NotFoundError("Позиция не найдена", code="stock_item_not_found")
    return item


async def list_stock_items(
    session: AsyncSession, filters: StockItemFilters, *, limit: int, offset: int
) -> tuple[list[StockItem], int]:
    stmt = select(StockItem)
    if not filters.include_inactive:
        stmt = stmt.where(StockItem.is_active.is_(True))
    if filters.category_id is not None:
        stmt = stmt.where(StockItem.stock_category_id == filters.category_id)
    if filters.location_id is not None:
        stmt = stmt.where(StockItem.location_id == filters.location_id)
    if filters.low_stock:
        stmt = stmt.where(StockItem.min_quantity > 0, StockItem.quantity <= StockItem.min_quantity)
    if filters.in_stock:
        stmt = stmt.where(StockItem.quantity > 0)
    if filters.q and filters.q.strip():
        stmt = stmt.where(StockItem.name.ilike(f"%{filters.q.strip()}%"))
    total = await session.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = await session.scalars(
        stmt.order_by(func.lower(StockItem.name), StockItem.location_id, StockItem.id)
        .limit(limit)
        .offset(offset)
    )
    return list(rows), total


async def create_stock_item(
    session: AsyncSession, *, actor_id: int, data: dict[str, Any]
) -> StockItem:
    data = _normalize(data)
    await check_stock_category(session, data["stock_category_id"])
    await check_location(session, data["location_id"])
    item = StockItem(**data, quantity=0, is_active=True, version=1)
    try:
        async with session.begin_nested():
            session.add(item)
    except IntegrityError as exc:
        raise_stock_integrity_error(exc)
    record_audit(
        session,
        entity_type=ENTITY_TYPE,
        entity_id=item.id,
        user_id=actor_id,
        action="created",
        diff=diff_values({}, item_snapshot(item)),
    )
    await session.commit()
    return item


async def update_stock_item(
    session: AsyncSession,
    *,
    actor_id: int,
    item_id: int,
    version: int,
    updates: dict[str, Any],
) -> StockItem:
    item = await get_stock_item(session, item_id, for_update=True)
    if item.version != version:
        raise ConflictError(
            "Данные изменил другой пользователь",
            code="version_conflict",
            details={"version": item.version},
        )
    updates = _normalize(updates)
    changes = changed_fields({key: getattr(item, key) for key in updates}, updates)
    if not changes:
        return item
    if "stock_category_id" in changes:
        await check_stock_category(session, updates["stock_category_id"])
    if changes.get("is_active") == [True, False] and item.quantity > 0:
        raise ConflictError(
            "Деактивировать можно только позицию с нулевым остатком",
            code="stock_not_empty",
            details={"quantity": item.quantity},
        )
    try:
        async with session.begin_nested():
            for key in changes:
                setattr(item, key, updates[key])
            item.version += 1
    except IntegrityError as exc:
        raise_stock_integrity_error(exc)
    record_audit(
        session,
        entity_type=ENTITY_TYPE,
        entity_id=item.id,
        user_id=actor_id,
        action="edited",
        diff=changes,
    )
    await session.commit()
    return item


async def list_movements(
    session: AsyncSession, item_id: int, *, limit: int, offset: int
) -> tuple[list[StockMovement], int]:
    await get_stock_item(session, item_id)
    condition = StockMovement.stock_item_id == item_id
    total = (
        await session.scalar(select(func.count()).select_from(StockMovement).where(condition)) or 0
    )
    rows = await session.scalars(
        select(StockMovement)
        .where(condition)
        .order_by(StockMovement.id.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(rows), total


async def transfer_locations(
    session: AsyncSession, transfer_ids: set[uuid.UUID]
) -> dict[tuple[uuid.UUID, StockMovementType], int]:
    """Склад каждой половины перемещения: (transfer_id, тип движения) → location_id."""
    if not transfer_ids:
        return {}
    rows = await session.execute(
        select(StockMovement.transfer_id, StockMovement.movement_type, StockItem.location_id)
        .join(StockItem, StockItem.id == StockMovement.stock_item_id)
        .where(StockMovement.transfer_id.in_(transfer_ids))
    )
    return {
        (transfer_id, movement_type): location_id
        for transfer_id, movement_type, location_id in rows.tuples()
        if transfer_id is not None
    }
