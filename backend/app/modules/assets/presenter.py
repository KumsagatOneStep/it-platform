"""Сборка ответов API: подставляет названия справочников и ФИО через service других модулей."""

from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.assets.models import Asset, AssetEvent
from app.modules.assets.schemas import AssetEventRead, AssetRead
from app.modules.assets.transitions import Operation, allowed_operations
from app.modules.directories.service import get_reference_names
from app.modules.users_auth.service import CurrentUser, UserRole, get_user_names


def _ids(*values: int | None) -> set[int]:
    return {value for value in values if value is not None}


async def assets_to_read(
    session: AsyncSession, assets: Sequence[Asset], user: CurrentUser
) -> list[AssetRead]:
    types = await get_reference_names(
        session, "asset-types", {asset.asset_type_id for asset in assets}
    )
    locations = await get_reference_names(
        session, "locations", {asset.location_id for asset in assets}
    )
    owners = await get_user_names(session, _ids(*(asset.owner_id for asset in assets)))
    can_operate = user.role == UserRole.ADMIN
    return [
        AssetRead(
            id=asset.id,
            asset_type_id=asset.asset_type_id,
            asset_type_name=types.get(asset.asset_type_id, ""),
            inventory_number=asset.inventory_number,
            serial_number=asset.serial_number,
            model=asset.model,
            status=asset.status,
            location_id=asset.location_id,
            location_name=locations.get(asset.location_id, ""),
            owner_id=asset.owner_id,
            owner_name=owners.get(asset.owner_id) if asset.owner_id is not None else None,
            accepted_at=asset.accepted_at,
            purchased_at=asset.purchased_at,
            warranty_until=asset.warranty_until,
            initial_cost=asset.initial_cost,
            needs_review=asset.needs_review,
            version=asset.version,
            created_at=asset.created_at,
            updated_at=asset.updated_at,
            allowed_operations=allowed_operations(asset.status, asset.owner_id)
            if can_operate
            else [],
        )
        for asset in assets
    ]


async def asset_to_read(session: AsyncSession, asset: Asset, user: CurrentUser) -> AssetRead:
    return (await assets_to_read(session, [asset], user))[0]


async def events_to_read(
    session: AsyncSession, events: Sequence[AssetEvent]
) -> list[AssetEventRead]:
    users = await get_user_names(
        session,
        _ids(
            *(event.from_owner_id for event in events),
            *(event.to_owner_id for event in events),
            *(event.performed_by for event in events),
        ),
    )
    locations = await get_reference_names(
        session,
        "locations",
        _ids(
            *(event.from_location_id for event in events),
            *(event.to_location_id for event in events),
        ),
    )
    reasons = await get_reference_names(
        session, "issue-reasons", _ids(*(event.reason_id for event in events))
    )

    def name(names: dict[int, str], item_id: int | None) -> str | None:
        return names.get(item_id) if item_id is not None else None

    return [
        AssetEventRead(
            id=event.id,
            event_type=event.event_type,
            operation=Operation(event.operation) if event.operation else None,
            from_owner_id=event.from_owner_id,
            from_owner_name=name(users, event.from_owner_id),
            to_owner_id=event.to_owner_id,
            to_owner_name=name(users, event.to_owner_id),
            from_status=event.from_status,
            to_status=event.to_status,
            from_location_id=event.from_location_id,
            from_location_name=name(locations, event.from_location_id),
            to_location_id=event.to_location_id,
            to_location_name=name(locations, event.to_location_id),
            reason_id=event.reason_id,
            reason_name=name(reasons, event.reason_id),
            changes=event.changes,
            comment=event.comment,
            performed_by=event.performed_by,
            performed_by_name=users.get(event.performed_by, ""),
            created_at=event.created_at,
        )
        for event in events
    ]
