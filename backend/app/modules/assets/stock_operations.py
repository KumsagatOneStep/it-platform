"""Операции с остатками расходников: приход, списание, корректировка, перемещение.

Остаток меняется только здесь и только вместе с записью StockMovement (п. 3.2 ТЗ).
Строки позиций блокируются SELECT … FOR UPDATE (несколько — в порядке id, чтобы встречные
операции не заблокировали друг друга); остаток проверяется уже под блокировкой.
"""

import uuid
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import diff_values, record_audit
from app.core.errors import ConflictError, ValidationFailedError
from app.core.timezone import company_today
from app.modules.assets.checks import check_location, check_reason
from app.modules.assets.stock_models import StockItem, StockMovement, StockMovementType
from app.modules.assets.stock_registry import ENTITY_TYPE, get_stock_item, item_snapshot
from app.modules.assets.stock_schemas import (
    StockAdjustmentOperation,
    StockOperationRequest,
    StockReceiptOperation,
    StockTransferOperation,
    StockWriteOffOperation,
)
from app.modules.users_auth.service import CurrentUser


def require_active(item: StockItem) -> None:
    if not item.is_active:
        raise ConflictError(
            "Позиция деактивирована", code="stock_item_inactive", details={"stock_item_id": item.id}
        )


def require_available(item: StockItem, quantity: int) -> None:
    if item.quantity < quantity:
        raise ConflictError(
            "Недостаточно остатка",
            code="insufficient_stock",
            details={"stock_item_id": item.id, "requested": quantity, "available": item.quantity},
        )


def record_movement(
    session: AsyncSession,
    item: StockItem,
    *,
    movement_type: StockMovementType,
    delta: int,
    actor_id: int,
    document_date: date | None = None,
    transfer_id: uuid.UUID | None = None,
    reason_id: int | None = None,
    recipient_id: int | None = None,
    comment: str | None = None,
) -> None:
    """Меняет остаток заблокированной позиции и пишет движение и аудит в той же транзакции."""
    before = item.quantity
    item.quantity += delta
    item.version += 1
    session.add(
        StockMovement(
            stock_item_id=item.id,
            movement_type=movement_type,
            delta=delta,
            quantity_after=item.quantity,
            document_date=document_date,
            transfer_id=transfer_id,
            reason_id=reason_id,
            recipient_id=recipient_id,
            comment=comment,
            performed_by=actor_id,
        )
    )
    record_audit(
        session,
        entity_type=ENTITY_TYPE,
        entity_id=item.id,
        user_id=actor_id,
        action=movement_type.value,
        diff={"quantity": [before, item.quantity]},
    )


async def lock_stock_items(session: AsyncSession, item_ids: list[int]) -> dict[int, StockItem]:
    """Блокирует позиции в порядке id; отсутствующих в ответе нет.

    populate_existing: позиция могла быть прочитана в этой сессии до блокировки —
    без него ORM вернёт объект из identity map с устаревшим остатком.
    """
    rows = await session.scalars(
        select(StockItem)
        .where(StockItem.id.in_(sorted(set(item_ids))))
        .order_by(StockItem.id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    return {item.id: item for item in rows}


async def _receipt(
    session: AsyncSession, actor_id: int, item_id: int, request: StockReceiptOperation
) -> StockItem:
    today = company_today()
    document_date = request.document_date or today
    if document_date > today:
        raise ValidationFailedError(
            "Дата документа не может быть в будущем", code="document_date_in_future"
        )
    item = await get_stock_item(session, item_id, for_update=True)
    require_active(item)
    record_movement(
        session,
        item,
        movement_type=StockMovementType.RECEIPT,
        delta=request.quantity,
        actor_id=actor_id,
        document_date=document_date,
        comment=request.comment,
    )
    return item


async def _write_off(
    session: AsyncSession, actor_id: int, item_id: int, request: StockWriteOffOperation
) -> StockItem:
    if request.reason_id is None:
        raise ValidationFailedError("Укажите причину списания", code="reason_required")
    await check_reason(session, request.reason_id, assets=False, stock=True)
    item = await get_stock_item(session, item_id, for_update=True)
    require_active(item)
    require_available(item, request.quantity)
    record_movement(
        session,
        item,
        movement_type=StockMovementType.WRITE_OFF,
        delta=-request.quantity,
        actor_id=actor_id,
        reason_id=request.reason_id,
        comment=request.comment,
    )
    return item


async def _adjustment(
    session: AsyncSession, actor_id: int, item_id: int, request: StockAdjustmentOperation
) -> StockItem:
    if request.comment is None:
        raise ValidationFailedError("Укажите комментарий к корректировке", code="comment_required")
    item = await get_stock_item(session, item_id, for_update=True)
    require_active(item)
    delta = request.actual_quantity - item.quantity
    if delta == 0:
        raise ValidationFailedError(
            "Фактический остаток совпадает с учётным", code="adjustment_no_change"
        )
    record_movement(
        session,
        item,
        movement_type=StockMovementType.ADJUSTMENT,
        delta=delta,
        actor_id=actor_id,
        comment=request.comment,
    )
    return item


async def _find_or_create_target(
    session: AsyncSession, actor_id: int, source: StockItem, location_id: int
) -> int:
    """id позиции с тем же наименованием на складе-получателе; нет — создаётся (min = 0)."""
    stmt = select(StockItem.id).where(
        func.lower(StockItem.name) == source.name.lower(), StockItem.location_id == location_id
    )
    existing = await session.scalar(stmt)
    if existing is not None:
        return existing
    target = StockItem(
        name=source.name,
        stock_category_id=source.stock_category_id,
        unit=source.unit,
        location_id=location_id,
        quantity=0,
        min_quantity=0,
        is_active=True,
        version=1,
    )
    try:
        async with session.begin_nested():
            session.add(target)
    except IntegrityError:
        # Параллельное перемещение уже создало позицию — берём её.
        created = await session.scalar(stmt)
        if created is None:
            raise
        return created
    record_audit(
        session,
        entity_type=ENTITY_TYPE,
        entity_id=target.id,
        user_id=actor_id,
        action="created",
        diff=diff_values({}, item_snapshot(target)),
    )
    return target.id


async def _transfer(
    session: AsyncSession, actor_id: int, item_id: int, request: StockTransferOperation
) -> StockItem:
    source = await get_stock_item(session, item_id)
    if request.to_location_id == source.location_id:
        raise ValidationFailedError(
            "Склад-получатель совпадает с текущим складом позиции", code="same_location"
        )
    await check_location(session, request.to_location_id)
    target_id = await _find_or_create_target(session, actor_id, source, request.to_location_id)
    locked = await lock_stock_items(session, [source.id, target_id])
    source, target = locked[source.id], locked[target_id]
    require_active(source)
    require_available(source, request.quantity)
    if target.unit != source.unit:
        # Иначе количество в одних единицах тихо прибавится к остатку в других.
        raise ConflictError(
            "На складе-получателе позиция учитывается в других единицах",
            code="stock_unit_mismatch",
            details={"source_unit": source.unit, "target_unit": target.unit},
        )
    if not target.is_active:
        target.is_active = True
        target.version += 1
        record_audit(
            session,
            entity_type=ENTITY_TYPE,
            entity_id=target.id,
            user_id=actor_id,
            action="edited",
            diff={"is_active": [False, True]},
        )
    transfer_id = uuid.uuid4()
    for item, movement_type, delta in (
        (source, StockMovementType.TRANSFER_OUT, -request.quantity),
        (target, StockMovementType.TRANSFER_IN, request.quantity),
    ):
        record_movement(
            session,
            item,
            movement_type=movement_type,
            delta=delta,
            actor_id=actor_id,
            transfer_id=transfer_id,
            comment=request.comment,
        )
    return source


async def apply_stock_operation(
    session: AsyncSession, actor: CurrentUser, item_id: int, request: StockOperationRequest
) -> StockItem:
    match request:
        case StockReceiptOperation():
            item = await _receipt(session, actor.id, item_id, request)
        case StockWriteOffOperation():
            item = await _write_off(session, actor.id, item_id, request)
        case StockAdjustmentOperation():
            item = await _adjustment(session, actor.id, item_id, request)
        case StockTransferOperation():
            item = await _transfer(session, actor.id, item_id, request)
    await session.flush()
    await session.commit()
    return item
