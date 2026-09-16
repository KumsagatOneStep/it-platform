from dataclasses import dataclass
from typing import cast

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.events import DomainEvent, EventBus

SESSION = cast(AsyncSession, object())


@dataclass(frozen=True)
class _Ping(DomainEvent):
    value: int


@dataclass(frozen=True)
class _Other(DomainEvent):
    pass


async def test_publish_calls_subscribers_in_order() -> None:
    bus = EventBus()
    calls: list[tuple[str, int]] = []

    @bus.subscribe(_Ping)
    async def first(session: AsyncSession, event: _Ping) -> None:
        calls.append(("first", event.value))

    @bus.subscribe(_Ping)
    async def second(session: AsyncSession, event: _Ping) -> None:
        calls.append(("second", event.value))

    await bus.publish(SESSION, _Ping(1))

    assert calls == [("first", 1), ("second", 1)]


async def test_publish_only_matching_event_type() -> None:
    bus = EventBus()
    calls: list[str] = []

    @bus.subscribe(_Other)
    async def handler(session: AsyncSession, event: _Other) -> None:
        calls.append("other")

    await bus.publish(SESSION, _Ping(1))

    assert calls == []


async def test_subscribing_same_handler_twice_registers_once() -> None:
    bus = EventBus()
    calls: list[int] = []

    async def handler(session: AsyncSession, event: _Ping) -> None:
        calls.append(event.value)

    bus.subscribe(_Ping)(handler)
    bus.subscribe(_Ping)(handler)
    await bus.publish(SESSION, _Ping(5))

    assert calls == [5]


async def test_unsubscribe_removes_handler() -> None:
    bus = EventBus()
    calls: list[int] = []

    async def handler(session: AsyncSession, event: _Ping) -> None:
        calls.append(event.value)

    bus.subscribe(_Ping)(handler)
    bus.unsubscribe(_Ping, handler)
    await bus.publish(SESSION, _Ping(5))

    assert calls == []


async def test_handler_exception_propagates() -> None:
    bus = EventBus()

    @bus.subscribe(_Ping)
    async def failing(session: AsyncSession, event: _Ping) -> None:
        raise RuntimeError("обработчик упал")

    with pytest.raises(RuntimeError, match="обработчик упал"):
        await bus.publish(SESSION, _Ping(1))
