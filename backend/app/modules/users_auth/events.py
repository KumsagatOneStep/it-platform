from dataclasses import dataclass, field

from app.core.events import DomainEvent
from app.modules.users_auth.models import UserRole


@dataclass(frozen=True)
class Blocker:
    """Причина, по которой операцию над пользователем нельзя выполнить."""

    kind: str
    entity_id: int
    title: str


@dataclass(frozen=True)
class UserDeactivationRequested(DomainEvent):
    """Публикуется перед деактивацией. Подписчики добавляют блокеры в `blockers`."""

    user_id: int
    blockers: list[Blocker] = field(default_factory=list)


@dataclass(frozen=True)
class UserRoleChangeRequested(DomainEvent):
    """Публикуется перед сменой роли. Подписчики добавляют блокеры в `blockers`."""

    user_id: int
    old_role: UserRole
    new_role: UserRole
    blockers: list[Blocker] = field(default_factory=list)
