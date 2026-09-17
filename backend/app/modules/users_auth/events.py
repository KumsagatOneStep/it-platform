from dataclasses import dataclass, field

from app.core.events import DomainEvent


@dataclass(frozen=True)
class DeactivationBlocker:
    kind: str
    entity_id: int
    title: str


@dataclass(frozen=True)
class UserDeactivationRequested(DomainEvent):
    """Публикуется перед деактивацией. Подписчики добавляют блокеры в `blockers`."""

    user_id: int
    blockers: list[DeactivationBlocker] = field(default_factory=list)
