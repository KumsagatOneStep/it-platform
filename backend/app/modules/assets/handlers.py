from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.events import event_bus
from app.modules.assets.models import Asset, AssetStatus
from app.modules.users_auth.events import Blocker, UserDeactivationRequested

# Статусы, в которых техника числится за владельцем (п. 3.2 ТЗ: деактивация требует передачи).
_OWNED_STATUSES = (AssetStatus.IN_USE, AssetStatus.IN_REPAIR)


@event_bus.subscribe(UserDeactivationRequested)
async def block_deactivation_of_asset_owner(
    session: AsyncSession, event: UserDeactivationRequested
) -> None:
    rows = await session.execute(
        select(Asset.id, Asset.inventory_number, Asset.model)
        .where(Asset.owner_id == event.user_id, Asset.status.in_(_OWNED_STATUSES))
        .order_by(Asset.inventory_number)
    )
    event.blockers.extend(
        Blocker(kind="asset_owner", entity_id=asset_id, title=f"Техника {number} — {model}")
        for asset_id, number, model in rows
    )
