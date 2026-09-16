from collections import defaultdict
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, TypeVar

from sqlalchemy.ext.asyncio import AsyncSession


@dataclass(frozen=True)
class DomainEvent:
    """Базовый класс доменного события."""


E = TypeVar("E", bound=DomainEvent)
Handler = Callable[[AsyncSession, E], Awaitable[None]]
_AnyHandler = Callable[[AsyncSession, Any], Awaitable[None]]


class EventBus:
    """Синхронная внутрипроцессная шина: обработчики выполняются в текущей транзакции."""

    def __init__(self) -> None:
        self._handlers: dict[type[DomainEvent], list[_AnyHandler]] = defaultdict(list)

    def subscribe(self, event_type: type[E]) -> Callable[[Handler[E]], Handler[E]]:
        def decorator(handler: Handler[E]) -> Handler[E]:
            handlers = self._handlers[event_type]
            if handler not in handlers:
                handlers.append(handler)
            return handler

        return decorator

    def unsubscribe(self, event_type: type[E], handler: Handler[E]) -> None:
        handlers = self._handlers.get(event_type, [])
        if handler in handlers:
            handlers.remove(handler)

    async def publish(self, session: AsyncSession, event: DomainEvent) -> None:
        for handler in list(self._handlers.get(type(event), [])):
            await handler(session, event)


event_bus = EventBus()
