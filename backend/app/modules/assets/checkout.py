"""Единая выдача: техника и расходники одному сотруднику одной транзакцией (п. 4.2.1 ТЗ).

Сначала блокируются активы, затем позиции (каждые — в порядке id), и собираются все
проблемы сразу: если хоть одна единица недоступна, ничего не меняется (409).
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError, ValidationFailedError
from app.modules.assets.checks import check_reason, check_recipient
from app.modules.assets.equipment_schemas import (
    CheckoutRequest,
    CheckoutUnavailable,
    UnavailableStockLine,
)
from app.modules.assets.models import Asset, AssetStatus
from app.modules.assets.operations import (
    OperationInput,
    apply_transition,
    lock_assets,
    unavailable_assets,
)
from app.modules.assets.stock_models import StockItem, StockMovementType
from app.modules.assets.stock_operations import lock_stock_items, record_movement
from app.modules.assets.transitions import Operation
from app.modules.users_auth.service import CurrentUser


async def _validate(session: AsyncSession, request: CheckoutRequest) -> None:
    if not request.asset_ids and not request.stock_lines:
        raise ValidationFailedError("Выберите технику или расходники", code="checkout_empty")
    if len(set(request.asset_ids)) != len(request.asset_ids):
        raise ValidationFailedError("Техника указана дважды", code="duplicate_asset")
    item_ids = [line.stock_item_id for line in request.stock_lines]
    if len(set(item_ids)) != len(item_ids):
        raise ValidationFailedError("Позиция указана дважды", code="duplicate_stock_line")
    await check_recipient(session, request.recipient_id)
    if request.reason_id is not None:
        await check_reason(
            session,
            request.reason_id,
            assets=bool(request.asset_ids),
            stock=bool(request.stock_lines),
        )


def _unavailable_stock(
    request: CheckoutRequest, items: dict[int, StockItem]
) -> list[UnavailableStockLine]:
    problems = []
    for line in request.stock_lines:
        item = items.get(line.stock_item_id)
        if item is not None and item.is_active and item.quantity >= line.quantity:
            continue
        problems.append(
            UnavailableStockLine(
                stock_item_id=line.stock_item_id,
                name=item.name if item else None,
                requested=line.quantity,
                available=item.quantity if item else None,
            )
        )
    return problems


async def checkout(
    session: AsyncSession, actor: CurrentUser, request: CheckoutRequest
) -> tuple[list[Asset], list[StockItem]]:
    await _validate(session, request)
    assets = await lock_assets(session, request.asset_ids)
    items = await lock_stock_items(session, [line.stock_item_id for line in request.stock_lines])
    unavailable = CheckoutUnavailable(
        assets=unavailable_assets(assets, request.asset_ids, AssetStatus.IN_STOCK),
        stock=_unavailable_stock(request, items),
    )
    if unavailable.assets or unavailable.stock:
        raise ConflictError(
            "Часть техники или расходников недоступна для выдачи",
            code="checkout_unavailable",
            details=unavailable.model_dump(mode="json"),
        )

    issue = OperationInput(
        Operation.ISSUE,
        owner_id=request.recipient_id,
        reason_id=request.reason_id,
        comment=request.comment,
    )
    for asset in assets.values():
        apply_transition(session, asset, issue, actor.id)
    for line in request.stock_lines:
        record_movement(
            session,
            items[line.stock_item_id],
            movement_type=StockMovementType.ISSUE,
            delta=-line.quantity,
            actor_id=actor.id,
            reason_id=request.reason_id,
            recipient_id=request.recipient_id,
            comment=request.comment,
        )
    await session.flush()
    await session.commit()
    return list(assets.values()), [items[line.stock_item_id] for line in request.stock_lines]
