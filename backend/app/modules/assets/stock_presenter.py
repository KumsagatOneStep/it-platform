"""Ответы API расходников: названия справочников и ФИО через service других модулей."""

from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.assets.stock_models import StockItem, StockMovement, StockMovementType
from app.modules.assets.stock_registry import is_low, transfer_locations
from app.modules.assets.stock_schemas import StockItemRead, StockMovementRead
from app.modules.directories.service import get_reference_names
from app.modules.users_auth.service import get_user_names

_COUNTERPART = {
    StockMovementType.TRANSFER_OUT: StockMovementType.TRANSFER_IN,
    StockMovementType.TRANSFER_IN: StockMovementType.TRANSFER_OUT,
}


async def stock_items_to_read(
    session: AsyncSession, items: Sequence[StockItem]
) -> list[StockItemRead]:
    categories = await get_reference_names(
        session, "stock-categories", {item.stock_category_id for item in items}
    )
    locations = await get_reference_names(
        session, "locations", {item.location_id for item in items}
    )
    return [
        StockItemRead(
            id=item.id,
            name=item.name,
            stock_category_id=item.stock_category_id,
            category_name=categories.get(item.stock_category_id, ""),
            unit=item.unit,
            location_id=item.location_id,
            location_name=locations.get(item.location_id, ""),
            quantity=item.quantity,
            min_quantity=item.min_quantity,
            is_low=is_low(item),
            is_active=item.is_active,
            version=item.version,
            created_at=item.created_at,
            updated_at=item.updated_at,
        )
        for item in items
    ]


async def stock_item_to_read(session: AsyncSession, item: StockItem) -> StockItemRead:
    return (await stock_items_to_read(session, [item]))[0]


def _ids(*values: int | None) -> set[int]:
    return {value for value in values if value is not None}


async def movements_to_read(
    session: AsyncSession, movements: Sequence[StockMovement]
) -> list[StockMovementRead]:
    pairs = await transfer_locations(
        session, {m.transfer_id for m in movements if m.transfer_id is not None}
    )

    def counterpart(movement: StockMovement) -> int | None:
        if movement.transfer_id is None:
            return None
        return pairs.get((movement.transfer_id, _COUNTERPART[movement.movement_type]))

    counterparts = {movement.id: counterpart(movement) for movement in movements}
    users = await get_user_names(
        session,
        _ids(*(m.recipient_id for m in movements), *(m.performed_by for m in movements)),
    )
    locations = await get_reference_names(session, "locations", _ids(*counterparts.values()))
    reasons = await get_reference_names(
        session, "issue-reasons", _ids(*(m.reason_id for m in movements))
    )

    def name(names: dict[int, str], item_id: int | None) -> str | None:
        return names.get(item_id) if item_id is not None else None

    return [
        StockMovementRead(
            id=movement.id,
            stock_item_id=movement.stock_item_id,
            movement_type=movement.movement_type,
            delta=movement.delta,
            quantity_after=movement.quantity_after,
            document_date=movement.document_date,
            transfer_id=movement.transfer_id,
            counterpart_location_id=counterparts[movement.id],
            counterpart_location_name=name(locations, counterparts[movement.id]),
            reason_id=movement.reason_id,
            reason_name=name(reasons, movement.reason_id),
            recipient_id=movement.recipient_id,
            recipient_name=name(users, movement.recipient_id),
            comment=movement.comment,
            performed_by=movement.performed_by,
            performed_by_name=users.get(movement.performed_by, ""),
            created_at=movement.created_at,
        )
        for movement in movements
    ]
