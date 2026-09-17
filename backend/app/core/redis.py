import inspect
from collections.abc import Awaitable
from typing import Annotated, TypeVar, overload

from fastapi import Depends
from redis.asyncio import Redis

from app.core.config import get_settings

T = TypeVar("T")

_client: Redis | None = None


def get_redis() -> Redis:
    global _client
    if _client is None:
        _client = Redis.from_url(get_settings().redis_url, decode_responses=True)
    return _client


@overload
async def resolve(value: Awaitable[T]) -> T: ...
@overload
async def resolve(value: T) -> T: ...
async def resolve(value: Awaitable[T] | T) -> T:
    """Типы redis-py объявляют результат команд как `Awaitable[T] | T`; приводим к T.

    Объявлено через `@overload`, а не единственную сигнатуру с union-параметром:
    с redis-py 8.x методы клиента аннотированы как `Awaitable[T] | T`, и при
    сигнатуре `resolve(value: Awaitable[T] | T) -> T` mypy (strict) выводит для
    вызовов вида `resolve(redis.ping())` тип `Never` вместо `bool`.
    """
    if inspect.isawaitable(value):
        return await value
    return value


RedisDep = Annotated[Redis, Depends(get_redis)]
