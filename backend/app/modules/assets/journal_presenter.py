"""Строки журнала для API: ФИО, склады и причины через service других модулей."""

from collections.abc import Sequence

from sqlalchemy.engine import RowMapping
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.assets.equipment_schemas import JournalEntryRead
from app.modules.assets.journal import JournalKind
from app.modules.assets.models import AssetEventType, AssetStatus
from app.modules.assets.stock_models import StockMovementType
from app.modules.assets.transitions import Operation
from app.modules.directories.service import get_reference_names
from app.modules.users_auth.service import get_user_names


def _ids(rows: Sequence[RowMapping], *columns: str) -> set[int]:
    return {row[column] for row in rows for column in columns if row[column] is not None}


async def journal_to_read(
    session: AsyncSession, rows: Sequence[RowMapping]
) -> list[JournalEntryRead]:
    users = await get_user_names(
        session, _ids(rows, "from_owner_id", "to_owner_id", "performed_by")
    )
    locations = await get_reference_names(
        session, "locations", _ids(rows, "from_location_id", "to_location_id")
    )
    reasons = await get_reference_names(session, "issue-reasons", _ids(rows, "reason_id"))

    def name(names: dict[int, str], item_id: int | None) -> str | None:
        return names.get(item_id) if item_id is not None else None

    def status(value: str | None) -> AssetStatus | None:
        return AssetStatus(value) if value is not None else None

    entries = []
    for row in rows:
        is_asset = row["kind"] == JournalKind.ASSET
        entries.append(
            JournalEntryRead(
                kind=JournalKind(row["kind"]),
                id=row["id"],
                created_at=row["created_at"],
                asset_event_type=AssetEventType(row["event_type"]) if is_asset else None,
                asset_operation=Operation(row["asset_operation"])
                if row["asset_operation"]
                else None,
                movement_type=None if is_asset else StockMovementType(row["event_type"]),
                object_id=row["object_id"],
                object_label=row["object_label"],
                delta=row["delta"],
                quantity_after=row["quantity_after"],
                unit=row["unit"],
                document_date=row["document_date"],
                from_owner_id=row["from_owner_id"],
                from_owner_name=name(users, row["from_owner_id"]),
                to_owner_id=row["to_owner_id"],
                to_owner_name=name(users, row["to_owner_id"]),
                from_status=status(row["from_status"]),
                to_status=status(row["to_status"]),
                from_location_id=row["from_location_id"],
                from_location_name=name(locations, row["from_location_id"]),
                to_location_id=row["to_location_id"],
                to_location_name=name(locations, row["to_location_id"]),
                reason_id=row["reason_id"],
                reason_name=name(reasons, row["reason_id"]),
                comment=row["comment"],
                performed_by=row["performed_by"],
                performed_by_name=users.get(row["performed_by"], ""),
            )
        )
    return entries
