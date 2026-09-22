"""Ответы API расходников: названия справочников и ФИО через service других модулей."""

from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.assets.stock_models import StockItem
from app.modules.assets.stock_registry import is_low
from app.modules.assets.stock_schemas import StockItemRead
from app.modules.directories.service import get_reference_names


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
