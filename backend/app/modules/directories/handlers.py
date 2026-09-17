from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.events import event_bus
from app.modules.directories.models import Department
from app.modules.users_auth.events import DeactivationBlocker, UserDeactivationRequested


@event_bus.subscribe(UserDeactivationRequested)
async def block_deactivation_of_department_head(
    session: AsyncSession, event: UserDeactivationRequested
) -> None:
    rows = await session.execute(
        select(Department.id, Department.name)
        .where(Department.head_id == event.user_id)
        .order_by(Department.id)
    )
    for department_id, name in rows:
        event.blockers.append(
            DeactivationBlocker(
                kind="department_head",
                entity_id=department_id,
                title=f"Руководитель отдела «{name}»",
            )
        )
