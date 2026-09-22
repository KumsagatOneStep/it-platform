"""Журнал движений: события техники и движения расходников одним запросом UNION ALL.

Обе таблицы принадлежат модулю assets, поэтому межмодульного JOIN нет. Колонки приводятся
к общему виду; фильтры, сортировка и пагинация выполняются в БД.
"""

from dataclasses import dataclass
from datetime import date
from enum import StrEnum

from sqlalchemy import (
    Date,
    Integer,
    Select,
    String,
    and_,
    case,
    cast,
    func,
    literal,
    null,
    or_,
    select,
    union_all,
)
from sqlalchemy.engine import RowMapping
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.core.timezone import company_day_bounds
from app.modules.assets.models import Asset, AssetEvent, AssetEventType
from app.modules.assets.stock_models import StockItem, StockMovement, StockMovementType


class JournalKind(StrEnum):
    ASSET = "asset"
    STOCK = "stock"


class JournalGroup(StrEnum):
    ISSUE = "issue"
    RETURN = "return"
    RECEIPT = "receipt"
    WRITE_OFF = "write_off"
    ADJUSTMENT = "adjustment"
    TRANSFER = "transfer"
    STATUS = "status"
    RECORD = "record"


_E = AssetEventType
_M = StockMovementType

# Группа операций → типы событий техники и типы движений расходников.
GROUPS: dict[JournalGroup, tuple[tuple[AssetEventType, ...], tuple[StockMovementType, ...]]] = {
    JournalGroup.ISSUE: ((_E.ISSUED,), (_M.ISSUE,)),
    JournalGroup.RETURN: ((_E.RETURNED,), ()),
    JournalGroup.RECEIPT: ((), (_M.RECEIPT,)),
    JournalGroup.WRITE_OFF: ((_E.WRITTEN_OFF,), (_M.WRITE_OFF,)),
    JournalGroup.ADJUSTMENT: ((), (_M.ADJUSTMENT,)),
    JournalGroup.TRANSFER: ((_E.MOVED,), (_M.TRANSFER_OUT, _M.TRANSFER_IN)),
    JournalGroup.STATUS: ((_E.STATUS_CHANGED,), ()),
    JournalGroup.RECORD: ((_E.CREATED, _E.EDITED), ()),
}


@dataclass(frozen=True)
class JournalFilters:
    date_from: date | None = None
    date_to: date | None = None
    kind: JournalKind | None = None
    groups: list[JournalGroup] | None = None
    person_id: int | None = None
    performed_by: int | None = None
    location_id: int | None = None


def _asset_rows() -> Select[tuple[object, ...]]:
    return select(
        literal(JournalKind.ASSET.value, String).label("kind"),
        AssetEvent.id.label("id"),
        AssetEvent.created_at.label("created_at"),
        cast(AssetEvent.event_type, String).label("event_type"),
        AssetEvent.operation.label("asset_operation"),
        AssetEvent.asset_id.label("object_id"),
        (Asset.inventory_number + " — " + Asset.model).label("object_label"),
        null().cast(Integer).label("delta"),
        null().cast(Integer).label("quantity_after"),
        null().cast(String).label("unit"),
        null().cast(Date).label("document_date"),
        AssetEvent.from_owner_id.label("from_owner_id"),
        AssetEvent.to_owner_id.label("to_owner_id"),
        cast(AssetEvent.from_status, String).label("from_status"),
        cast(AssetEvent.to_status, String).label("to_status"),
        AssetEvent.from_location_id.label("from_location_id"),
        AssetEvent.to_location_id.label("to_location_id"),
        AssetEvent.reason_id.label("reason_id"),
        AssetEvent.comment.label("comment"),
        AssetEvent.performed_by.label("performed_by"),
    ).join(Asset, Asset.id == AssetEvent.asset_id)


def _stock_rows() -> Select[tuple[object, ...]]:
    other = aliased(StockMovement)
    other_item = aliased(StockItem)
    # Склад второй половины перемещения (у прочих движений — NULL).
    counterpart = (
        select(other_item.location_id)
        .join(other, other.stock_item_id == other_item.id)
        .where(other.transfer_id == StockMovement.transfer_id, other.id != StockMovement.id)
        .limit(1)
        .scalar_subquery()
    )
    return select(
        literal(JournalKind.STOCK.value, String).label("kind"),
        StockMovement.id.label("id"),
        StockMovement.created_at.label("created_at"),
        cast(StockMovement.movement_type, String).label("event_type"),
        null().cast(String).label("asset_operation"),
        StockMovement.stock_item_id.label("object_id"),
        StockItem.name.label("object_label"),
        StockMovement.delta.label("delta"),
        StockMovement.quantity_after.label("quantity_after"),
        StockItem.unit.label("unit"),
        StockMovement.document_date.label("document_date"),
        null().cast(Integer).label("from_owner_id"),
        StockMovement.recipient_id.label("to_owner_id"),
        null().cast(String).label("from_status"),
        null().cast(String).label("to_status"),
        case(
            (StockMovement.movement_type == _M.TRANSFER_IN, counterpart),
            (StockMovement.movement_type == _M.TRANSFER_OUT, StockItem.location_id),
            else_=None,
        ).label("from_location_id"),
        case(
            (StockMovement.movement_type == _M.TRANSFER_OUT, counterpart),
            else_=StockItem.location_id,
        ).label("to_location_id"),
        StockMovement.reason_id.label("reason_id"),
        StockMovement.comment.label("comment"),
        StockMovement.performed_by.label("performed_by"),
    ).join(StockItem, StockItem.id == StockMovement.stock_item_id)


async def list_journal(
    session: AsyncSession, filters: JournalFilters, *, limit: int, offset: int
) -> tuple[list[RowMapping], int]:
    journal = union_all(_asset_rows(), _stock_rows()).subquery("journal")
    c = journal.c
    conditions = []
    start, end = company_day_bounds(filters.date_from, filters.date_to)
    if start is not None:
        conditions.append(c.created_at >= start)
    if end is not None:
        conditions.append(c.created_at < end)
    if filters.kind is not None:
        conditions.append(c.kind == filters.kind.value)
    if filters.groups:
        asset_types = [t.value for g in filters.groups for t in GROUPS[g][0]]
        stock_types = [t.value for g in filters.groups for t in GROUPS[g][1]]
        conditions.append(
            or_(
                and_(c.kind == JournalKind.ASSET.value, c.event_type.in_(asset_types)),
                and_(c.kind == JournalKind.STOCK.value, c.event_type.in_(stock_types)),
            )
        )
    if filters.person_id is not None:
        conditions.append(
            or_(c.from_owner_id == filters.person_id, c.to_owner_id == filters.person_id)
        )
    if filters.performed_by is not None:
        conditions.append(c.performed_by == filters.performed_by)
    if filters.location_id is not None:
        conditions.append(
            or_(
                c.from_location_id == filters.location_id,
                c.to_location_id == filters.location_id,
            )
        )
    stmt = select(journal).where(*conditions)
    total = await session.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = await session.execute(
        stmt.order_by(c.created_at.desc(), c.kind, c.id.desc()).limit(limit).offset(offset)
    )
    return list(rows.mappings()), total
