from fastapi import FastAPI
from httpx import AsyncClient

from app.core.redis import get_redis


async def test_health_returns_ok(client: AsyncClient) -> None:
    response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


class _BrokenRedis:
    async def ping(self) -> bool:
        raise ConnectionError("redis недоступен")


async def test_ready_returns_ok_when_dependencies_available(client: AsyncClient) -> None:
    response = await client.get("/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "checks": {"database": "ok", "redis": "ok"}}


async def test_ready_returns_503_when_redis_down(app: FastAPI, client: AsyncClient) -> None:
    app.dependency_overrides[get_redis] = lambda: _BrokenRedis()

    response = await client.get("/ready")

    assert response.status_code == 503
    assert response.json()["checks"] == {"database": "ok", "redis": "error"}
