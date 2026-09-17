from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.events import event_bus
from app.modules.directories.models import Department, TicketType
from app.modules.users_auth.events import (
    Blocker,
    UserDeactivationRequested,
    UserRoleChangeRequested,
)
from app.modules.users_auth.service import UserRole

# Роли, которым разрешено руководить отделом и быть исполнителем по умолчанию.
_RESPONSIBLE_ROLES = frozenset({UserRole.MANAGER, UserRole.ADMIN})


async def _department_head_blockers(session: AsyncSession, user_id: int) -> list[Blocker]:
    rows = await session.execute(
        select(Department.id, Department.name)
        .where(Department.head_id == user_id)
        .order_by(Department.id)
    )
    return [
        Blocker(
            kind="department_head",
            entity_id=department_id,
            title=f"Руководитель отдела «{name}»",
        )
        for department_id, name in rows
    ]


async def _default_assignee_blockers(session: AsyncSession, user_id: int) -> list[Blocker]:
    rows = await session.execute(
        select(TicketType.id, TicketType.name)
        .where(TicketType.default_assignee_id == user_id)
        .order_by(TicketType.id)
    )
    return [
        Blocker(
            kind="ticket_type_default_assignee",
            entity_id=ticket_type_id,
            title=f"Исполнитель по умолчанию для типа заявок «{name}»",
        )
        for ticket_type_id, name in rows
    ]


@event_bus.subscribe(UserDeactivationRequested)
async def block_deactivation_of_department_head(
    session: AsyncSession, event: UserDeactivationRequested
) -> None:
    event.blockers.extend(await _department_head_blockers(session, event.user_id))


@event_bus.subscribe(UserRoleChangeRequested)
async def block_role_change_of_responsible_user(
    session: AsyncSession, event: UserRoleChangeRequested
) -> None:
    if event.new_role in _RESPONSIBLE_ROLES:
        return
    event.blockers.extend(await _department_head_blockers(session, event.user_id))
    event.blockers.extend(await _default_assignee_blockers(session, event.user_id))
