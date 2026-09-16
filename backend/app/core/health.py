import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.core.db import SessionDep
from app.core.redis import RedisDep, resolve

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready", responses={503: {"description": "Зависимость недоступна"}})
async def ready(session: SessionDep, redis: RedisDep) -> JSONResponse:
    checks: dict[str, str] = {}
    try:
        await session.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception:
        logger.exception("readiness.database_failed")
        checks["database"] = "error"
    try:
        await resolve(redis.ping())
        checks["redis"] = "ok"
    except Exception:
        logger.exception("readiness.redis_failed")
        checks["redis"] = "error"
    ok = all(value == "ok" for value in checks.values())
    return JSONResponse(
        {"status": "ok" if ok else "error", "checks": checks},
        status_code=200 if ok else 503,
    )
