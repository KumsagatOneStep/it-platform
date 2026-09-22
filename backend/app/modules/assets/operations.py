"""Операции над активами по таблице переходов: одиночные и массовый возврат.

Массовая выдача — в составе единой выдачи (checkout.py).

Строки активов блокируются SELECT … FOR UPDATE (массово — в порядке id, чтобы не было
взаимных блокировок); статус проверяется уже под блокировкой, поэтому параллельная
выдача того же актива получает 409 (п. 3.2 ТЗ).
"""

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError, ValidationFailedError
from app.modules.assets.access import get_visible_asset
from app.modules.assets.checks import check_location, check_reason, check_recipient
from app.modules.assets.history import Placement, record_event
from app.modules.assets.models import Asset, AssetStatus
from app.modules.assets.schemas import (
    AssetOperationRequest,
    IssueOperation,
    MoveOperation,
    ReturnOperation,
    UnavailableAsset,
    WriteOffOperation,
)
from app.modules.assets.transitions import TRANSITIONS, Operation, OwnerRule, is_allowed
from app.modules.users_auth.service import CurrentUser


@dataclass(frozen=True)
class OperationInput:
    """Поля операции после разбора запроса; None — не задано."""

    operation: Operation
    owner_id: int | None = None
    location_id: int | None = None
    reason_id: int | None = None
    comment: str | None = None


def _to_input(request: AssetOperationRequest) -> OperationInput:
    operation = Operation(request.operation)
    match request:
        case IssueOperation():
            return OperationInput(
                operation,
                owner_id=request.owner_id,
                reason_id=request.reason_id,
                comment=request.comment,
            )
        case ReturnOperation() | MoveOperation():
            return OperationInput(
                operation, location_id=request.location_id, comment=request.comment
            )
        case WriteOffOperation():
            return OperationInput(operation, reason_id=request.reason_id, comment=request.comment)
        case _:
            return OperationInput(operation, comment=request.comment)


async def _validate(session: AsyncSession, data: OperationInput) -> None:
    if data.operation == Operation.WRITE_OFF and data.reason_id is None:
        raise ValidationFailedError("Укажите причину списания", code="reason_required")
    if data.owner_id is not None:
        await check_recipient(session, data.owner_id)
    if data.reason_id is not None:
        await check_reason(session, data.reason_id)
    if data.location_id is not None:
        await check_location(session, data.location_id)


def apply_transition(
    session: AsyncSession, asset: Asset, data: OperationInput, actor_id: int
) -> None:
    transition = TRANSITIONS[data.operation]
    before = Placement.of(asset)
    if transition.to_status is not None:
        asset.status = transition.to_status
    if transition.owner == OwnerRule.SET:
        asset.owner_id = data.owner_id
    elif transition.owner == OwnerRule.CLEAR:
        asset.owner_id = None
    if data.location_id is not None:
        asset.location_id = data.location_id
    asset.version += 1
    record_event(
        session,
        asset,
        event_type=transition.event_type,
        actor_id=actor_id,
        before=before,
        operation=data.operation.value,
        reason_id=data.reason_id,
        comment=data.comment,
    )


async def apply_operation(
    session: AsyncSession, actor: CurrentUser, asset_id: int, request: AssetOperationRequest
) -> Asset:
    data = _to_input(request)
    await _validate(session, data)
    asset = await get_visible_asset(session, actor, asset_id, for_update=True)
    if not is_allowed(data.operation, asset.status, asset.owner_id):
        raise ConflictError(
            "Операция недоступна в текущем статусе техники",
            code="operation_not_allowed",
            details={"status": asset.status.value},
        )
    apply_transition(session, asset, data, actor.id)
    await session.flush()
    await session.commit()
    return asset


async def lock_assets(session: AsyncSession, asset_ids: list[int]) -> dict[int, Asset]:
    """Блокирует активы в порядке id (без взаимных блокировок); отсутствующих в ответе нет."""
    # Без фильтра видимости: массовые операции доступны только Admin;
    # добавить visibility_filter, если это когда-нибудь откроют другим ролям.
    # populate_existing: перечитать статус под блокировкой, даже если актив уже в сессии.
    rows = await session.scalars(
        select(Asset)
        .where(Asset.id.in_(set(asset_ids)))
        .order_by(Asset.id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    return {asset.id: asset for asset in rows}


def unavailable_assets(
    found: dict[int, Asset], asset_ids: list[int], required_status: AssetStatus
) -> list[UnavailableAsset]:
    """Активы из asset_ids (в их порядке), которые не найдены или не в нужном статусе."""
    return [
        UnavailableAsset(
            asset_id=asset_id,
            inventory_number=found[asset_id].inventory_number if asset_id in found else None,
            status=found[asset_id].status if asset_id in found else None,
        )
        for asset_id in asset_ids
        if asset_id not in found or found[asset_id].status != required_status
    ]


async def return_assets(
    session: AsyncSession,
    actor: CurrentUser,
    *,
    asset_ids: list[int],
    location_id: int | None,
    comment: str | None,
) -> list[Asset]:
    data = OperationInput(Operation.RETURN, location_id=location_id, comment=comment)
    await _validate(session, data)
    unique_ids = sorted(set(asset_ids))
    found = await lock_assets(session, unique_ids)
    unavailable = unavailable_assets(found, unique_ids, AssetStatus.IN_USE)
    if unavailable:
        raise ConflictError(
            "Часть техники недоступна для операции",
            code="assets_unavailable",
            details=[item.model_dump(mode="json") for item in unavailable],
        )
    assets = list(found.values())
    for asset in assets:
        apply_transition(session, asset, data, actor.id)
    await session.flush()
    await session.commit()
    return assets
