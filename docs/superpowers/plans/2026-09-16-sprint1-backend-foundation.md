# Спринт 1 — фундамент backend: план реализации

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Рабочий скелет модульного монолита: FastAPI-приложение с PostgreSQL/Redis в Docker Compose, миграциями Alembic, проверкой границ модулей, JWT-аутентификацией (п. 2.4 ТЗ), управлением пользователями, отделами и справочниками, CI.

**Architecture:** Один backend-проект `backend/app` с пакетами `core/` (инфраструктура) и `modules/<имя>/` (бизнес-модули). Другие модули обращаются к модулю только через его `service.py` (и `events.py` для доменных событий); это проверяет import-linter. Обратные связи между модулями — через синхронные доменные события `core/events.py`. Все таблицы спринта — в схеме `common`.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2.0 (async, asyncpg), Alembic, Pydantic v2 / pydantic-settings, argon2-cffi, PyJWT, redis-py (asyncio), pytest + pytest-asyncio + httpx, ruff, mypy (strict), import-linter, uv, Docker Compose (PostgreSQL 17, Redis 7), GitHub Actions.

**Spec:** `docs/spec/TZ_IT_platforma_v1.2.md` (разделы 1.3, 2.1–2.4, 3.1–3.2, 4.7, 7.2–7.6, 9).

**Вне этого плана** (отдельные планы/спринты):
- Фронтенд-скелет, генерация TS-типов из `backend/openapi.json`, базовые UI-компоненты — план 2 спринта 1.
- Staging-окружение и CD — требуют сервера; проверка доступа к Telegram API с VPS — там же.
- Сброс пароля через Telegram (спринт 4), `AlertRecipient` и отправка системных алертов (спринт 5). В этом плане подозрение на перебор пишется в журнал событием `auth.login_bruteforce_suspected`; подключение к алертам — в спринте 5.
- Переназначение согласующего при смене руководителя (п. 2.3) — обработчик появится с модулем `tickets`; здесь публикуется событие `DepartmentHeadChanged`.

## Global Constraints

- Python `>=3.12,<3.13`; менеджер зависимостей — uv; все команды backend выполняются из каталога `backend/`.
- Структура: `app/core/`, `app/modules/{users_auth,directories}/`. Схемы PostgreSQL: `common`, `equipment`, `tickets`, `kanban`, `notifications`, `reporting`.
- «Модули обращаются друг к другу только через сервисный слой (`service.py`), прямой импорт моделей другого модуля запрещён» — проверяется `lint-imports`, нарушение ломает CI. `app.core` не импортирует `app.modules`. Циклические зависимости между модулями запрещены.
- Пароли — Argon2id. Access-токен JWT — 15 минут, заголовок `Authorization`. Refresh-токен — 14 дней, cookie `HttpOnly`, `Secure`, `SameSite=Strict`, `Path=/api/auth`, ротация при каждом использовании, в БД хранится хэш.
- Деактивация пользователя или смена пароля отзывает все его refresh-токены.
- Перебор: 5 неудачных попыток за 15 минут на пару «учётная запись + IP» → блокировка пары на 15 минут; 20 попыток за 15 минут с IP → блокировка IP на 15 минут; более 50 попыток за час на учётную запись → сигнал (без блокировки); IP из `X-Forwarded-For` — только от доверенного прокси; Admin снимает блокировку вручную.
- Первый Admin создаётся CLI-командой.
- Все даты — `timestamptz` в UTC; часовой пояс компании — настройка `COMPANY_TIMEZONE`.
- Элементы справочников не удаляются, а деактивируются (`is_active = false`).
- Фронтенд и API на одном домене; CORS в staging/production отключён.
- Логи — JSON с `request_id`; эндпоинты `/health` и `/ready` (БД и Redis).
- Каждая миграция имеет рабочий `downgrade` (проверяется тестом).
- Тексты ошибок для пользователя — на русском; формат ошибки API: `{"error": {"code", "message", "details"}}`.
- Файлы с FastAPI-роутерами не используют `from __future__ import annotations`.
- Сообщения коммитов заканчиваются строкой `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>` (в шагах ниже опущено для краткости).
- Перед каждым коммитом: `uv run ruff format . && uv run ruff check --fix .`

## Структура файлов

```
it-platform/
├── compose.yaml                      # postgres, redis, backend (локально)
├── Makefile                          # up / test / lint / openapi
├── README.md
├── .github/workflows/ci.yml
├── deploy/postgres/init/01-create-test-db.sql
└── backend/
    ├── pyproject.toml                # зависимости, ruff, mypy, pytest, import-linter
    ├── .python-version  .env.example  Dockerfile  .dockerignore
    ├── alembic.ini
    ├── openapi.json                  # экспорт схемы, проверяется тестом
    ├── migrations/env.py, script.py.mako, versions/000{1..4}_*.py
    ├── app/
    │   ├── main.py                   # create_app()
    │   ├── cli.py                    # python -m app.cli create-admin
    │   ├── wiring.py                 # импорт модулей-обработчиков событий
    │   ├── model_registry.py         # импорт всех моделей для Alembic
    │   ├── scripts/export_openapi.py
    │   ├── core/
    │   │   ├── config.py  db.py  redis.py  health.py
    │   │   ├── logging.py  middleware.py  errors.py
    │   │   ├── events.py  audit.py  net.py  schemas.py
    │   └── modules/
    │       ├── users_auth/
    │       │   ├── models.py  schemas.py  passwords.py  tokens.py
    │       │   ├── throttle.py  auth.py  users.py  deps.py  events.py
    │       │   ├── router.py
    │       │   └── service.py        # публичный фасад модуля
    │       └── directories/
    │           ├── models.py  schemas.py  departments.py
    │           ├── reference.py  references.py  reference_router.py
    │           ├── events.py  handlers.py  router.py
    │           └── service.py        # публичный фасад модуля
    └── tests/
        ├── conftest.py  db_utils.py  factories.py
        ├── test_health.py  test_migrations.py  test_openapi.py
        ├── core/ test_config.py test_errors.py test_logging.py test_events.py test_audit.py test_net.py
        └── modules/users_auth/..., modules/directories/...
```

---

### Task 1: Каркас backend-проекта и `/health`

**Files:**
- Create: `.gitignore`, `backend/.python-version`, `backend/pyproject.toml`
- Create: `backend/app/__init__.py`, `backend/app/core/__init__.py`, `backend/app/modules/__init__.py`
- Create: `backend/app/core/config.py`, `backend/app/core/health.py`, `backend/app/main.py`
- Test: `backend/tests/__init__.py`, `backend/tests/core/__init__.py`, `backend/tests/conftest.py`, `backend/tests/test_health.py`, `backend/tests/core/test_config.py`

**Interfaces:**
- Produces: `app.core.config.Settings`, `get_settings() -> Settings` (поля: `app_env`, `database_url`, `redis_url`, `jwt_secret`, `access_token_ttl_minutes`, `refresh_token_ttl_days`, `cookie_secure`, `trusted_proxies`, `cors_origins`, `company_timezone`); `app.main.create_app() -> FastAPI`; фикстура `client`.

- [ ] **Step 1: Создать файлы проекта**

`.gitignore` (в корне репозитория):
```gitignore
.venv/
__pycache__/
*.pyc
.pytest_cache/
.mypy_cache/
.ruff_cache/
.env
node_modules/
dist/
```

`backend/.python-version`:
```
3.12
```

`backend/pyproject.toml`:
```toml
[project]
name = "it-platform-backend"
version = "0.1.0"
requires-python = ">=3.12,<3.13"
dependencies = [
    "fastapi>=0.115",
    "uvicorn[standard]>=0.32",
    "sqlalchemy[asyncio]>=2.0.36",
    "asyncpg>=0.30",
    "alembic>=1.14",
    "pydantic>=2.9",
    "pydantic-settings>=2.6",
    "email-validator>=2.2",
    "argon2-cffi>=23.1",
    "pyjwt>=2.10",
    "redis>=5.2",
]

[dependency-groups]
dev = [
    "pytest>=8.3",
    "pytest-asyncio>=0.24",
    "httpx>=0.28",
    "ruff>=0.8",
    "mypy>=1.13",
    "import-linter>=2.1",
]

[tool.uv]
package = false

[tool.pytest.ini_options]
asyncio_mode = "auto"
asyncio_default_fixture_loop_scope = "function"
pythonpath = ["."]
testpaths = ["tests"]

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "W", "I", "B", "UP", "SIM", "ASYNC", "RUF"]
# RUF001-003: кириллица в строках и комментариях; UP046/047: оставляем Generic[T] ради совместимости с pydantic
ignore = ["RUF001", "RUF002", "RUF003", "UP046", "UP047"]

[tool.ruff.lint.isort]
known-first-party = ["app", "tests"]

[tool.mypy]
python_version = "3.12"
strict = true
plugins = ["pydantic.mypy"]

[[tool.mypy.overrides]]
module = ["tests.*"]
disallow_untyped_defs = false
disallow_incomplete_defs = false
```

Пустые `__init__.py`: `backend/app/__init__.py`, `backend/app/core/__init__.py`, `backend/app/modules/__init__.py`, `backend/tests/__init__.py`, `backend/tests/core/__init__.py`.

- [ ] **Step 2: Установить Python и зависимости**

Run: `cd backend && uv python install 3.12 && uv sync`
Expected: создан `.venv`, `uv.lock`, без ошибок.

- [ ] **Step 3: Написать падающие тесты**

`backend/tests/conftest.py`:
```python
import os

os.environ["APP_ENV"] = "test"

from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import create_app


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=create_app())
    async with AsyncClient(transport=transport, base_url="http://testserver") as http_client:
        yield http_client
```

`backend/tests/test_health.py`:
```python
from httpx import AsyncClient


async def test_health_returns_ok(client: AsyncClient) -> None:
    response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

`backend/tests/core/test_config.py`:
```python
import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_production_rejects_default_jwt_secret() -> None:
    with pytest.raises(ValidationError):
        Settings(app_env="production")


def test_production_rejects_short_jwt_secret() -> None:
    with pytest.raises(ValidationError):
        Settings(app_env="production", jwt_secret="short")


def test_production_accepts_strong_secret() -> None:
    settings = Settings(app_env="production", jwt_secret="x" * 40)

    assert settings.jwt_secret == "x" * 40


def test_production_rejects_cors_origins() -> None:
    with pytest.raises(ValidationError):
        Settings(app_env="production", jwt_secret="x" * 40, cors_origins=["https://a.ru"])


def test_invalid_timezone_rejected() -> None:
    with pytest.raises(ValidationError):
        Settings(company_timezone="Mars/Olympus")


def test_defaults_match_spec() -> None:
    settings = Settings()

    assert settings.access_token_ttl_minutes == 15
    assert settings.refresh_token_ttl_days == 14
    assert settings.company_timezone == "Europe/Moscow"
```

- [ ] **Step 4: Убедиться, что тесты падают**

Run: `uv run pytest -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.main'`.

- [ ] **Step 5: Реализовать**

`backend/app/core/config.py`:
```python
from functools import lru_cache
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

LOCAL_JWT_SECRET = "local-development-secret-do-not-use-in-production"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: Literal["local", "test", "staging", "production"] = "local"
    database_url: str = "postgresql+asyncpg://app:app@localhost:5432/it_platform"
    redis_url: str = "redis://localhost:6379/0"
    jwt_secret: str = LOCAL_JWT_SECRET
    access_token_ttl_minutes: int = 15
    refresh_token_ttl_days: int = 14
    cookie_secure: bool = True
    trusted_proxies: list[str] = Field(default_factory=lambda: ["127.0.0.1/32", "::1/128"])
    cors_origins: list[str] = Field(default_factory=list)
    company_timezone: str = "Europe/Moscow"

    @model_validator(mode="after")
    def _validate(self) -> "Settings":
        try:
            ZoneInfo(self.company_timezone)
        except ZoneInfoNotFoundError as exc:
            raise ValueError(f"Неизвестный часовой пояс: {self.company_timezone}") from exc
        if self.app_env in ("staging", "production"):
            if self.jwt_secret == LOCAL_JWT_SECRET or len(self.jwt_secret) < 32:
                raise ValueError("JWT_SECRET должен быть случайной строкой длиной от 32 символов")
            if self.cors_origins:
                raise ValueError("CORS_ORIGINS должен быть пустым: фронтенд и API на одном домене")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

`backend/app/core/health.py`:
```python
from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
```

`backend/app/main.py`:
```python
from fastapi import FastAPI

from app.core.health import router as health_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="IT-платформа",
        version="0.1.0",
        openapi_url="/api/openapi.json",
        docs_url="/api/docs",
        redoc_url=None,
    )
    app.include_router(health_router)
    return app


app = create_app()
```

- [ ] **Step 6: Прогнать тесты и проверки**

Run: `uv run pytest -q && uv run ruff check . && uv run mypy app tests`
Expected: 7 passed; ruff и mypy без ошибок.

- [ ] **Step 7: Commit**

```bash
git add .gitignore backend
git commit -m "chore: скелет backend-проекта, настройки и /health"
```

---

### Task 2: Docker Compose, подключение к БД и Redis, `/ready`

**Files:**
- Create: `compose.yaml`, `deploy/postgres/init/01-create-test-db.sql`, `backend/.env.example`
- Create: `backend/app/core/db.py`, `backend/app/core/redis.py`
- Modify: `backend/app/core/health.py`
- Modify: `backend/tests/conftest.py` (полная замена)
- Test: `backend/tests/test_health.py`

**Interfaces:**
- Consumes: `get_settings()` (Task 1).
- Produces: `app.core.db.get_session`, `SessionDep = Annotated[AsyncSession, Depends(get_session)]`, `SessionFactory`, `SCHEMAS`; `app.core.redis.get_redis() -> Redis`, `RedisDep`, `async resolve(value: Awaitable[T] | T) -> T`; фикстуры `db_session`, `redis_client`, `app`, `client`.

- [ ] **Step 1: Compose и тестовая БД**

`compose.yaml`:
```yaml
name: it-platform

services:
  postgres:
    image: postgres:17
    environment:
      POSTGRES_USER: app
      POSTGRES_PASSWORD: app
      POSTGRES_DB: it_platform
    ports:
      - "127.0.0.1:5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
      - ./deploy/postgres/init:/docker-entrypoint-initdb.d:ro
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U app -d it_platform"]
      interval: 5s
      retries: 10

  redis:
    image: redis:7
    ports:
      - "127.0.0.1:6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      retries: 10

volumes:
  pgdata:
```

`deploy/postgres/init/01-create-test-db.sql`:
```sql
CREATE DATABASE it_platform_test OWNER app;
```

`backend/.env.example`:
```dotenv
APP_ENV=local
DATABASE_URL=postgresql+asyncpg://app:app@localhost:5432/it_platform
REDIS_URL=redis://localhost:6379/0
JWT_SECRET=local-development-secret-do-not-use-in-production
COOKIE_SECURE=false
COMPANY_TIMEZONE=Europe/Moscow
```

Run: `docker compose up -d postgres redis && docker compose ps`
Expected: оба сервиса `healthy`.

- [ ] **Step 2: Написать падающие тесты**

`backend/tests/conftest.py` (полная замена):
```python
import os

os.environ["APP_ENV"] = "test"
os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+asyncpg://app:app@localhost:5432/it_platform_test"
)
os.environ["REDIS_URL"] = os.environ.get("TEST_REDIS_URL", "redis://localhost:6379/15")
os.environ["COOKIE_SECURE"] = "false"

from collections.abc import AsyncIterator

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import get_settings
from app.core.db import get_session
from app.core.redis import get_redis, resolve
from app.main import create_app


@pytest.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    """Сессия внутри внешней транзакции, которая откатывается после теста."""
    engine = create_async_engine(get_settings().database_url, poolclass=NullPool)
    async with engine.connect() as connection:
        transaction = await connection.begin()
        session = AsyncSession(
            bind=connection,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint",
        )
        try:
            yield session
        finally:
            await session.close()
            await transaction.rollback()
    await engine.dispose()


@pytest.fixture
async def redis_client() -> AsyncIterator[Redis]:
    client = Redis.from_url(get_settings().redis_url, decode_responses=True)
    await resolve(client.flushdb())
    try:
        yield client
    finally:
        await resolve(client.flushdb())
        await client.aclose()


@pytest.fixture
def app(db_session: AsyncSession, redis_client: Redis) -> FastAPI:
    application = create_app()

    async def _session_override() -> AsyncIterator[AsyncSession]:
        yield db_session

    application.dependency_overrides[get_session] = _session_override
    application.dependency_overrides[get_redis] = lambda: redis_client
    return application


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as http_client:
        yield http_client
```

Добавить в `backend/tests/test_health.py`:
```python
from fastapi import FastAPI

from app.core.redis import get_redis


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
```
(Импорты `FastAPI` и `get_redis` поместить в начало файла.)

- [ ] **Step 3: Убедиться, что тесты падают**

Run: `uv run pytest -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.core.db'`.

- [ ] **Step 4: Реализовать**

`backend/app/core/db.py`:
```python
from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings

SCHEMAS = ("common", "equipment", "tickets", "kanban", "notifications", "reporting")

engine = create_async_engine(get_settings().database_url, pool_pre_ping=True)
SessionFactory = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with SessionFactory() as session:
        yield session


SessionDep = Annotated[AsyncSession, Depends(get_session)]
```

`backend/app/core/redis.py`:
```python
import inspect
from collections.abc import Awaitable
from typing import Annotated, TypeVar, cast

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


async def resolve(value: Awaitable[T] | T) -> T:
    """Типы redis-py объявляют результат команд как `Awaitable[T] | T`; приводим к T."""
    if inspect.isawaitable(value):
        return cast(T, await value)
    return cast(T, value)


RedisDep = Annotated[Redis, Depends(get_redis)]
```

`backend/app/core/health.py` (полная замена):
```python
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
```

- [ ] **Step 5: Прогнать тесты**

Run: `uv run pytest -q && uv run mypy app tests`
Expected: 9 passed; mypy без ошибок.

- [ ] **Step 6: Commit**

```bash
git add compose.yaml deploy backend
git commit -m "feat: Docker Compose, сессии БД и Redis, /ready"
```

---

### Task 3: Alembic, схемы БД, журнал аудита, import-linter

**Files:**
- Modify: `backend/app/core/db.py` (добавить `Base`, `NAMING_CONVENTION`, `constraint_name`)
- Create: `backend/app/core/audit.py`, `backend/app/model_registry.py`
- Create: `backend/alembic.ini`, `backend/migrations/env.py`, `backend/migrations/script.py.mako`, `backend/migrations/versions/0001_schemas_and_audit_log.py`
- Modify: `backend/pyproject.toml` (секция import-linter)
- Create: `backend/tests/db_utils.py`
- Modify: `backend/tests/conftest.py` (фикстура миграций)
- Test: `backend/tests/test_migrations.py`, `backend/tests/core/test_audit.py`

**Interfaces:**
- Consumes: `SCHEMAS`, `get_settings()`.
- Produces: `app.core.db.Base`; `constraint_name(exc: IntegrityError) -> str | None`; `app.core.audit.AuditLog`; `record_audit(session, *, entity_type: str, entity_id: int | str, user_id: int | None, action: str, diff: dict[str, Any]) -> None`; `diff_values(before: Mapping[str, Any], after: Mapping[str, Any]) -> dict[str, list[Any]]`; `tests.db_utils.alembic_config() -> Config`.

- [ ] **Step 1: Настроить Alembic**

`backend/alembic.ini`:
```ini
[alembic]
script_location = %(here)s/migrations
prepend_sys_path = .
file_template = %%(rev)s_%%(slug)s

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARNING
handlers = console

[logger_sqlalchemy]
level = WARNING
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
```

`backend/migrations/script.py.mako`:
```mako
"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
${imports if imports else ""}

revision: str = ${repr(up_revision)}
down_revision: str | None = ${repr(down_revision)}
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    ${downgrades if downgrades else "pass"}
```

`backend/migrations/env.py`:
```python
import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

import app.model_registry  # noqa: F401  регистрирует модели в Base.metadata
from app.core.config import get_settings
from app.core.db import SCHEMAS, Base

config = context.config
if config.config_file_name is not None and not config.attributes.get("skip_logging"):
    fileConfig(config.config_file_name, disable_existing_loggers=False)
config.set_main_option("sqlalchemy.url", get_settings().database_url)

target_metadata = Base.metadata


def include_name(name: str | None, type_: str, parent_names: object) -> bool:
    if type_ == "schema":
        return name in SCHEMAS
    return True


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        include_schemas=True,
        include_name=include_name,
        version_table_schema="public",
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    raise RuntimeError("Offline-режим миграций не поддерживается")

asyncio.run(run_async_migrations())
```

- [ ] **Step 2: Написать падающие тесты**

`backend/tests/db_utils.py`:
```python
from pathlib import Path

from alembic.config import Config

BACKEND_DIR = Path(__file__).resolve().parents[1]


def alembic_config() -> Config:
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.attributes["skip_logging"] = True
    return config
```

Добавить в `backend/tests/conftest.py` (импорт `from alembic import command` и `from tests.db_utils import alembic_config` — в блок импортов):
```python
@pytest.fixture(scope="session", autouse=True)
def _migrated_database() -> None:
    config = alembic_config()
    command.downgrade(config, "base")
    command.upgrade(config, "head")
```

`backend/tests/test_migrations.py`:
```python
from alembic import command
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import SCHEMAS
from tests.db_utils import alembic_config


def test_migrations_downgrade_to_base_and_upgrade_again() -> None:
    config = alembic_config()

    command.downgrade(config, "base")
    command.upgrade(config, "head")


async def test_all_schemas_exist(db_session: AsyncSession) -> None:
    rows = await db_session.execute(text("SELECT schema_name FROM information_schema.schemata"))

    assert set(SCHEMAS) <= {row[0] for row in rows}
```

`backend/tests/core/test_audit.py`:
```python
from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import AuditLog, diff_values, record_audit


class _Color(StrEnum):
    RED = "red"
    BLUE = "blue"


def test_diff_values_returns_only_changed_fields() -> None:
    before = {"name": "Старое", "color": _Color.RED, "count": 1}
    after = {"name": "Новое", "color": _Color.BLUE, "count": 1}

    assert diff_values(before, after) == {"name": ["Старое", "Новое"], "color": ["red", "blue"]}


def test_diff_values_serializes_datetimes() -> None:
    moment = datetime(2026, 9, 16, 12, 0, tzinfo=UTC)

    assert diff_values({}, {"at": moment}) == {"at": [None, "2026-09-16T12:00:00+00:00"]}


async def test_record_audit_persists_entry(db_session: AsyncSession) -> None:
    record_audit(
        db_session,
        entity_type="test_entity",
        entity_id=42,
        user_id=None,
        action="create",
        diff={"name": [None, "Тест"]},
    )
    await db_session.flush()

    row = (
        await db_session.scalars(select(AuditLog).where(AuditLog.entity_type == "test_entity"))
    ).one()
    assert row.entity_id == "42"
    assert row.action == "create"
    assert row.diff == {"name": [None, "Тест"]}
    assert row.created_at is not None
```

- [ ] **Step 3: Убедиться, что тесты падают**

Run: `uv run pytest -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.model_registry'` при подготовке миграций.

- [ ] **Step 4: Реализовать**

Добавить в `backend/app/core/db.py` (импорты `from sqlalchemy import MetaData`, `from sqlalchemy.exc import IntegrityError`, `from sqlalchemy.orm import DeclarativeBase`):
```python
NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_N_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


def constraint_name(exc: IntegrityError) -> str | None:
    """Имя нарушенного ограничения из исключения asyncpg."""
    cause = getattr(exc.orig, "__cause__", None)
    name = getattr(cause, "constraint_name", None)
    return name if isinstance(name, str) else None
```

`backend/app/core/audit.py`:
```python
from collections.abc import Mapping
from datetime import date, datetime
from enum import Enum
from typing import Any

from sqlalchemy import BigInteger, DateTime, Index, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class AuditLog(Base):
    __tablename__ = "audit_log"
    __table_args__ = (
        Index("ix_audit_log_entity", "entity_type", "entity_id"),
        {"schema": "common"},
    )
    __mapper_args__ = {"eager_defaults": True}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(64))
    entity_id: Mapped[str] = mapped_column(String(64))
    user_id: Mapped[int | None] = mapped_column(Integer)
    action: Mapped[str] = mapped_column(String(32))
    diff: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


def _json_safe(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, datetime | date):
        return value.isoformat()
    return value


def diff_values(before: Mapping[str, Any], after: Mapping[str, Any]) -> dict[str, list[Any]]:
    return {
        key: [_json_safe(before.get(key)), _json_safe(value)]
        for key, value in after.items()
        if before.get(key) != value
    }


def record_audit(
    session: AsyncSession,
    *,
    entity_type: str,
    entity_id: int | str,
    user_id: int | None,
    action: str,
    diff: dict[str, Any],
) -> None:
    session.add(
        AuditLog(
            entity_type=entity_type,
            entity_id=str(entity_id),
            user_id=user_id,
            action=action,
            diff=diff,
        )
    )
```

`backend/app/model_registry.py`:
```python
"""Импорт всех ORM-моделей для Alembic. Код приложения этот файл не импортирует."""

from app.core import audit  # noqa: F401
```

`backend/migrations/versions/0001_schemas_and_audit_log.py`:
```python
"""Схемы БД и журнал аудита

Revision ID: 0001
Revises:
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMAS = ("common", "equipment", "tickets", "kanban", "notifications", "reporting")


def upgrade() -> None:
    for schema in SCHEMAS:
        op.execute(f'CREATE SCHEMA IF NOT EXISTS "{schema}"')
    op.create_table(
        "audit_log",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("entity_type", sa.String(64), nullable=False),
        sa.Column("entity_id", sa.String(64), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("action", sa.String(32), nullable=False),
        sa.Column(
            "diff", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        schema="common",
    )
    op.create_index(
        "ix_audit_log_entity", "audit_log", ["entity_type", "entity_id"], schema="common"
    )


def downgrade() -> None:
    op.drop_index("ix_audit_log_entity", table_name="audit_log", schema="common")
    op.drop_table("audit_log", schema="common")
    for schema in reversed(SCHEMAS):
        op.execute(f'DROP SCHEMA IF EXISTS "{schema}"')
```

Добавить в конец `backend/pyproject.toml`:
```toml
[tool.importlinter]
root_packages = ["app"]

[[tool.importlinter.contracts]]
name = "core не зависит от бизнес-модулей"
type = "forbidden"
source_modules = ["app.core"]
forbidden_modules = ["app.modules"]
```

- [ ] **Step 5: Прогнать тесты и проверку границ**

Run: `uv run pytest -q && uv run lint-imports && uv run mypy app tests`
Expected: все тесты проходят; `Contracts: 1 kept, 0 broken.`

- [ ] **Step 6: Проверить, что контракт действительно ловит нарушение**

Создать временно `backend/app/core/_violation.py` с содержимым `import app.modules  # noqa: F401`.
Run: `uv run lint-imports`
Expected: `Contracts: 0 kept, 1 broken.` Затем удалить `backend/app/core/_violation.py` и повторить — `1 kept`.

- [ ] **Step 7: Commit**

```bash
git add backend
git commit -m "feat: Alembic, схемы PostgreSQL, журнал аудита, import-linter"
```

---

### Task 4: Ошибки API, JSON-логи, `request_id`

**Files:**
- Create: `backend/app/core/errors.py`, `backend/app/core/logging.py`, `backend/app/core/middleware.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/core/test_errors.py`, `backend/tests/core/test_logging.py`

**Interfaces:**
- Produces: `AppError(message, *, code=None, details=None)` и подклассы `NotFoundError` (404), `ConflictError` (409), `ForbiddenError` (403), `UnauthorizedError` (401), `ValidationFailedError` (422), `TooManyRequestsError` (429); `register_error_handlers(app)`; `request_id_var: ContextVar[str]`; `JsonFormatter`; `configure_logging(level="INFO")`; `RequestIdMiddleware`.

- [ ] **Step 1: Написать падающие тесты**

`backend/tests/core/test_errors.py`:
```python
from fastapi import FastAPI
from httpx import AsyncClient

from app.core.errors import ConflictError, UnauthorizedError


async def test_app_error_rendered_as_json(app: FastAPI, client: AsyncClient) -> None:
    async def conflict() -> None:
        raise ConflictError("Уже существует", code="already_exists", details={"field": "name"})

    app.add_api_route("/_probe/conflict", conflict, methods=["GET"])

    response = await client.get("/_probe/conflict")

    assert response.status_code == 409
    assert response.json() == {
        "error": {
            "code": "already_exists",
            "message": "Уже существует",
            "details": {"field": "name"},
        }
    }


async def test_unauthorized_sets_www_authenticate(app: FastAPI, client: AsyncClient) -> None:
    async def unauthorized() -> None:
        raise UnauthorizedError("Требуется вход")

    app.add_api_route("/_probe/unauthorized", unauthorized, methods=["GET"])

    response = await client.get("/_probe/unauthorized")

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
    assert response.json()["error"]["code"] == "unauthorized"
```

`backend/tests/core/test_logging.py`:
```python
import json
import logging

from httpx import AsyncClient

from app.core.logging import JsonFormatter, request_id_var


def test_json_formatter_includes_request_id_and_extra() -> None:
    record = logging.LogRecord("app.test", logging.INFO, __file__, 1, "событие", None, None)
    record.user_id = 7
    token = request_id_var.set("abc123")
    try:
        payload = json.loads(JsonFormatter().format(record))
    finally:
        request_id_var.reset(token)

    assert payload["message"] == "событие"
    assert payload["level"] == "INFO"
    assert payload["logger"] == "app.test"
    assert payload["request_id"] == "abc123"
    assert payload["user_id"] == 7


async def test_request_id_generated_when_missing(client: AsyncClient) -> None:
    response = await client.get("/health")

    assert len(response.headers["x-request-id"]) == 32


async def test_valid_incoming_request_id_is_echoed(client: AsyncClient) -> None:
    response = await client.get("/health", headers={"X-Request-ID": "req-1.A_b"})

    assert response.headers["x-request-id"] == "req-1.A_b"


async def test_invalid_incoming_request_id_is_replaced(client: AsyncClient) -> None:
    response = await client.get("/health", headers={"X-Request-ID": "bad id\nwith newline"})

    assert response.headers["x-request-id"] != "bad id\nwith newline"
    assert len(response.headers["x-request-id"]) == 32
```

- [ ] **Step 2: Убедиться, что тесты падают**

Run: `uv run pytest tests/core/test_errors.py tests/core/test_logging.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.core.errors'`.

- [ ] **Step 3: Реализовать**

`backend/app/core/errors.py`:
```python
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class AppError(Exception):
    status_code: int = 400
    code: str = "bad_request"

    def __init__(self, message: str, *, code: str | None = None, details: Any = None) -> None:
        super().__init__(message)
        self.message = message
        if code is not None:
            self.code = code
        self.details = details


class UnauthorizedError(AppError):
    status_code = 401
    code = "unauthorized"


class ForbiddenError(AppError):
    status_code = 403
    code = "forbidden"


class NotFoundError(AppError):
    status_code = 404
    code = "not_found"


class ConflictError(AppError):
    status_code = 409
    code = "conflict"


class ValidationFailedError(AppError):
    status_code = 422
    code = "validation_failed"


class TooManyRequestsError(AppError):
    status_code = 429
    code = "too_many_requests"


async def app_error_handler(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, AppError)
    headers = {"WWW-Authenticate": "Bearer"} if isinstance(exc, UnauthorizedError) else None
    return JSONResponse(
        {"error": {"code": exc.code, "message": exc.message, "details": exc.details}},
        status_code=exc.status_code,
        headers=headers,
    )


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, app_error_handler)
```

`backend/app/core/logging.py`:
```python
import json
import logging
from contextvars import ContextVar
from datetime import UTC, datetime

request_id_var: ContextVar[str] = ContextVar("request_id", default="-")

_STANDARD_ATTRS = set(vars(logging.LogRecord("", 0, "", 0, "", None, None))) | {
    "message",
    "asctime",
    "taskName",
}


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "ts": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": request_id_var.get(),
        }
        for key, value in vars(record).items():
            if key not in _STANDARD_ATTRS and not key.startswith("_"):
                payload[key] = value
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str)


def configure_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)
```

`backend/app/core/middleware.py`:
```python
import re
from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.core.logging import request_id_var

_VALID_REQUEST_ID = re.compile(r"^[A-Za-z0-9._-]{1,128}$")


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        incoming = request.headers.get("x-request-id", "")
        request_id = incoming if _VALID_REQUEST_ID.fullmatch(incoming) else uuid4().hex
        token = request_id_var.set(request_id)
        try:
            response = await call_next(request)
        finally:
            request_id_var.reset(token)
        response.headers["X-Request-ID"] = request_id
        return response
```

`backend/app/main.py` (полная замена):
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.errors import register_error_handlers
from app.core.health import router as health_router
from app.core.logging import configure_logging
from app.core.middleware import RequestIdMiddleware


def create_app() -> FastAPI:
    settings = get_settings()
    if settings.app_env != "test":
        configure_logging()
    app = FastAPI(
        title="IT-платформа",
        version="0.1.0",
        openapi_url="/api/openapi.json",
        docs_url="/api/docs",
        redoc_url=None,
    )
    app.add_middleware(RequestIdMiddleware)
    if settings.cors_origins:
        # Только local: в staging/production Settings запрещает CORS_ORIGINS (п. 7.3)
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    register_error_handlers(app)
    app.include_router(health_router)
    return app


app = create_app()
```

- [ ] **Step 4: Прогнать тесты**

Run: `uv run pytest -q && uv run mypy app tests && uv run lint-imports`
Expected: всё проходит.

- [ ] **Step 5: Commit**

```bash
git add backend
git commit -m "feat: единый формат ошибок API, JSON-логи и request_id"
```

---

### Task 5: Доменные события

**Files:**
- Create: `backend/app/core/events.py`, `backend/app/wiring.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/core/test_events.py`

**Interfaces:**
- Produces: `DomainEvent` (базовый frozen dataclass); `EventBus` с методами `subscribe(event_type) -> decorator`, `unsubscribe(event_type, handler) -> None`, `async publish(session, event) -> None`; глобальный `event_bus`; `app.wiring.HANDLER_MODULES: tuple[str, ...]`, `register_event_handlers() -> None`.
- Правило: обработчики выполняются синхронно, в порядке подписки, в текущей транзакции; исключение обработчика пробрасывается и откатывает операцию.

- [ ] **Step 1: Написать падающие тесты**

`backend/tests/core/test_events.py`:
```python
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
```

- [ ] **Step 2: Убедиться, что тесты падают**

Run: `uv run pytest tests/core/test_events.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.core.events'`.

- [ ] **Step 3: Реализовать**

`backend/app/core/events.py`:
```python
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
```

`backend/app/wiring.py`:
```python
import importlib

# Модули, которые при импорте подписывают обработчики на event_bus.
HANDLER_MODULES: tuple[str, ...] = ()


def register_event_handlers() -> None:
    for module_name in HANDLER_MODULES:
        importlib.import_module(module_name)
```

В `backend/app/main.py`: добавить `from app.wiring import register_event_handlers` и первой строкой тела `create_app()` вызвать `register_event_handlers()`.

- [ ] **Step 4: Прогнать тесты**

Run: `uv run pytest -q && uv run mypy app tests`
Expected: всё проходит.

- [ ] **Step 5: Commit**

```bash
git add backend
git commit -m "feat: шина доменных событий"
```

---

### Task 6: Пользователи — модели, пароли, CLI первого администратора

**Files:**
- Create: `backend/app/modules/users_auth/__init__.py`, `models.py`, `passwords.py`, `users.py`, `service.py`
- Create: `backend/app/cli.py`
- Create: `backend/migrations/versions/0002_users_and_refresh_tokens.py`
- Modify: `backend/app/core/audit.py` (FK `user_id`), `backend/app/model_registry.py`, `backend/pyproject.toml` (контракт модуля)
- Create: `backend/tests/factories.py`
- Test: `backend/tests/modules/__init__.py`, `backend/tests/modules/users_auth/__init__.py`, `test_passwords.py`, `test_first_admin.py`, `test_cli.py`

**Interfaces:**
- Consumes: `Base`, `constraint_name`, `record_audit`, `ConflictError`, `ValidationFailedError`.
- Produces:
  - `models.UserRole(StrEnum)`: `EMPLOYEE="employee"`, `MANAGER="manager"`, `ADMIN="admin"`; `models.User` (`id, full_name, email, password_hash, role, department_id, is_active, must_change_password, created_at`); `models.RefreshToken` (`id, user_id, token_hash, expires_at, created_at, revoked_at`).
  - `passwords.hash_password(password: str) -> str`, `verify_password(password_hash: str, password: str) -> bool`, `dummy_verify(password: str) -> None`, `validate_password_strength(password: str) -> None`, `generate_temporary_password() -> str`, `PASSWORD_MIN_LENGTH = 10`.
  - `users.normalize_email(email: str) -> str`; `async get_user_by_email(session, email) -> User | None`; `async create_user(session, *, email, full_name, role, department_id, password, must_change_password) -> User` (flush без commit; `email_taken` → 409, `department_not_found` → 422); `async create_first_admin(session, *, email, full_name, password) -> User` (с commit).
  - `service.py` (фасад): реэкспорт `UserRole`, `create_first_admin`.
  - `tests.factories.DEFAULT_PASSWORD`, `async make_user(session, **overrides) -> User`.

- [ ] **Step 1: Написать падающие тесты**

`backend/tests/factories.py`:
```python
import itertools
from functools import cache

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.users_auth.models import User, UserRole
from app.modules.users_auth.passwords import hash_password

DEFAULT_PASSWORD = "Pa55word-Test"

_counter = itertools.count(1)


@cache
def _default_password_hash() -> str:
    return hash_password(DEFAULT_PASSWORD)


async def make_user(
    session: AsyncSession,
    *,
    email: str | None = None,
    full_name: str = "Иванов Иван Иванович",
    role: UserRole = UserRole.EMPLOYEE,
    department_id: int | None = None,
    password: str = DEFAULT_PASSWORD,
    must_change_password: bool = False,
    is_active: bool = True,
) -> User:
    password_hash = (
        _default_password_hash() if password == DEFAULT_PASSWORD else hash_password(password)
    )
    user = User(
        email=email or f"user{next(_counter)}@company.ru",
        full_name=full_name,
        password_hash=password_hash,
        role=role,
        department_id=department_id,
        must_change_password=must_change_password,
        is_active=is_active,
    )
    session.add(user)
    await session.flush()
    return user
```

Пустые `backend/tests/modules/__init__.py` и `backend/tests/modules/users_auth/__init__.py`.

`backend/tests/modules/users_auth/test_passwords.py`:
```python
import pytest

from app.core.errors import ValidationFailedError
from app.modules.users_auth.passwords import (
    PASSWORD_MIN_LENGTH,
    generate_temporary_password,
    hash_password,
    validate_password_strength,
    verify_password,
)


def test_hash_is_argon2id_and_verifies() -> None:
    password_hash = hash_password("Correct-Horse-1")

    assert password_hash.startswith("$argon2id$")
    assert verify_password(password_hash, "Correct-Horse-1")
    assert not verify_password(password_hash, "wrong-password")


def test_verify_returns_false_for_garbage_hash() -> None:
    assert not verify_password("not-a-hash", "whatever")


def test_short_password_rejected() -> None:
    with pytest.raises(ValidationFailedError) as exc_info:
        validate_password_strength("x" * (PASSWORD_MIN_LENGTH - 1))

    assert exc_info.value.code == "weak_password"


def test_temporary_password_is_long_enough_and_random() -> None:
    first, second = generate_temporary_password(), generate_temporary_password()

    assert len(first) >= PASSWORD_MIN_LENGTH
    assert first != second
```

`backend/tests/modules/users_auth/test_first_admin.py`:
```python
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import AuditLog
from app.core.errors import ConflictError, ValidationFailedError
from app.modules.users_auth.models import UserRole
from app.modules.users_auth.passwords import verify_password
from app.modules.users_auth.service import create_first_admin


async def test_creates_active_admin_with_normalized_email(db_session: AsyncSession) -> None:
    user = await create_first_admin(
        db_session, email="  Admin@Company.RU ", full_name="Администратор", password="Strong-Pass-1"
    )

    assert user.email == "admin@company.ru"
    assert user.role is UserRole.ADMIN
    assert user.is_active
    assert not user.must_change_password
    assert verify_password(user.password_hash, "Strong-Pass-1")
    audit = (
        await db_session.scalars(select(AuditLog).where(AuditLog.entity_id == str(user.id)))
    ).one()
    assert audit.entity_type == "user"
    assert audit.action == "create"


async def test_duplicate_email_rejected(db_session: AsyncSession) -> None:
    await create_first_admin(
        db_session, email="admin@company.ru", full_name="Первый", password="Strong-Pass-1"
    )

    with pytest.raises(ConflictError) as exc_info:
        await create_first_admin(
            db_session, email="ADMIN@company.ru", full_name="Второй", password="Strong-Pass-1"
        )

    assert exc_info.value.code == "email_taken"


async def test_weak_password_rejected(db_session: AsyncSession) -> None:
    with pytest.raises(ValidationFailedError):
        await create_first_admin(
            db_session, email="admin@company.ru", full_name="Администратор", password="short"
        )
```

`backend/tests/modules/users_auth/test_cli.py`:
```python
import pytest

from app import cli


def test_create_admin_rejects_mismatched_passwords(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    answers = iter(["First-Password-1", "Second-Password-2"])
    monkeypatch.setattr(cli.getpass, "getpass", lambda prompt="": next(answers))

    exit_code = cli.main(["create-admin", "--email", "a@company.ru", "--full-name", "Админ"])

    assert exit_code == 1
    assert "не совпадают" in capsys.readouterr().err
```

- [ ] **Step 2: Убедиться, что тесты падают**

Run: `uv run pytest tests/modules -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.modules.users_auth'`.

- [ ] **Step 3: Модели и миграция**

`backend/app/modules/users_auth/__init__.py` — пустой.

`backend/app/modules/users_auth/models.py`:
```python
from datetime import datetime
from enum import StrEnum

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, String, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class UserRole(StrEnum):
    EMPLOYEE = "employee"
    MANAGER = "manager"
    ADMIN = "admin"


class User(Base):
    __tablename__ = "users"
    __table_args__ = {"schema": "common"}
    __mapper_args__ = {"eager_defaults": True}

    id: Mapped[int] = mapped_column(primary_key=True)
    full_name: Mapped[str] = mapped_column(String(255))
    email: Mapped[str] = mapped_column(String(320), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(
        SAEnum(
            UserRole,
            native_enum=False,
            length=16,
            values_callable=lambda enum: [member.value for member in enum],
        )
    )
    department_id: Mapped[int | None] = mapped_column()
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    __table_args__ = {"schema": "common"}
    __mapper_args__ = {"eager_defaults": True}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("common.users.id", ondelete="CASCADE"), index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
```

В `backend/app/core/audit.py` заменить объявление `user_id`:
```python
    user_id: Mapped[int | None] = mapped_column(ForeignKey("common.users.id"))
```
(добавить `ForeignKey` в импорт из `sqlalchemy`, убрать неиспользуемый `Integer`).

`backend/app/model_registry.py` — добавить строку:
```python
from app.modules.users_auth import models as users_auth_models  # noqa: F401
```

`backend/migrations/versions/0002_users_and_refresh_tokens.py`:
```python
"""Пользователи и refresh-токены

Revision ID: 0002
Revises: 0001
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", sa.String(16), nullable=False),
        sa.Column("department_id", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "must_change_password", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("email", name="uq_users_email"),
        sa.CheckConstraint("role IN ('employee', 'manager', 'admin')", name="ck_users_role"),
        schema="common",
    )
    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["common.users.id"],
            name="fk_refresh_tokens_user_id_users",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("token_hash", name="uq_refresh_tokens_token_hash"),
        schema="common",
    )
    op.create_index(
        "ix_refresh_tokens_user_id", "refresh_tokens", ["user_id"], schema="common"
    )
    op.create_foreign_key(
        "fk_audit_log_user_id_users",
        "audit_log",
        "users",
        ["user_id"],
        ["id"],
        source_schema="common",
        referent_schema="common",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_audit_log_user_id_users", "audit_log", schema="common", type_="foreignkey"
    )
    op.drop_index("ix_refresh_tokens_user_id", table_name="refresh_tokens", schema="common")
    op.drop_table("refresh_tokens", schema="common")
    op.drop_table("users", schema="common")
```

- [ ] **Step 4: Пароли, сервис, фасад, CLI**

`backend/app/modules/users_auth/passwords.py`:
```python
import secrets
from functools import cache

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from app.core.errors import ValidationFailedError

PASSWORD_MIN_LENGTH = 10

_hasher = PasswordHasher()  # Argon2id с параметрами по умолчанию (RFC 9106)


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


@cache
def _dummy_hash() -> str:
    return hash_password(secrets.token_urlsafe(16))


def dummy_verify(password: str) -> None:
    """Выравнивает время ответа, когда пользователь не найден."""
    verify_password(_dummy_hash(), password)


def validate_password_strength(password: str) -> None:
    if len(password) < PASSWORD_MIN_LENGTH:
        raise ValidationFailedError(
            f"Пароль должен содержать не менее {PASSWORD_MIN_LENGTH} символов",
            code="weak_password",
        )


def generate_temporary_password() -> str:
    return secrets.token_urlsafe(12)
```

`backend/app/modules/users_auth/users.py`:
```python
from typing import NoReturn

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import record_audit
from app.core.db import constraint_name
from app.core.errors import ConflictError, ValidationFailedError
from app.modules.users_auth.models import User, UserRole
from app.modules.users_auth.passwords import hash_password, validate_password_strength


def normalize_email(email: str) -> str:
    return email.strip().lower()


def raise_user_integrity_error(exc: IntegrityError) -> NoReturn:
    name = constraint_name(exc)
    if name == "uq_users_email":
        raise ConflictError(
            "Пользователь с таким email уже существует", code="email_taken"
        ) from exc
    if name == "fk_users_department_id_departments":
        raise ValidationFailedError("Отдел не найден", code="department_not_found") from exc
    raise exc


async def get_user_by_email(session: AsyncSession, email: str) -> User | None:
    return await session.scalar(select(User).where(User.email == normalize_email(email)))


async def create_user(
    session: AsyncSession,
    *,
    email: str,
    full_name: str,
    role: UserRole,
    department_id: int | None,
    password: str,
    must_change_password: bool,
) -> User:
    user = User(
        email=normalize_email(email),
        full_name=full_name.strip(),
        password_hash=hash_password(password),
        role=role,
        department_id=department_id,
        must_change_password=must_change_password,
    )
    try:
        async with session.begin_nested():
            session.add(user)
    except IntegrityError as exc:
        raise_user_integrity_error(exc)
    return user


async def create_first_admin(
    session: AsyncSession, *, email: str, full_name: str, password: str
) -> User:
    validate_password_strength(password)
    user = await create_user(
        session,
        email=email,
        full_name=full_name,
        role=UserRole.ADMIN,
        department_id=None,
        password=password,
        must_change_password=False,
    )
    record_audit(
        session,
        entity_type="user",
        entity_id=user.id,
        user_id=None,
        action="create",
        diff={"email": [None, user.email], "role": [None, user.role.value]},
    )
    await session.commit()
    return user
```

`backend/app/modules/users_auth/service.py`:
```python
"""Публичный интерфейс модуля users_auth. Другие модули импортируют только этот файл и events.py."""

from app.modules.users_auth.models import UserRole
from app.modules.users_auth.users import create_first_admin

__all__ = ["UserRole", "create_first_admin"]
```

`backend/app/cli.py`:
```python
import argparse
import asyncio
import getpass
import sys
from collections.abc import Sequence

from app.core.db import SessionFactory
from app.core.errors import AppError
from app.modules.users_auth.service import create_first_admin


async def _create_admin(email: str, full_name: str, password: str) -> int:
    async with SessionFactory() as session:
        user = await create_first_admin(
            session, email=email, full_name=full_name, password=password
        )
        return user.id


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    commands = parser.add_subparsers(dest="command", required=True)
    create_admin = commands.add_parser("create-admin", help="Создать администратора")
    create_admin.add_argument("--email", required=True)
    create_admin.add_argument("--full-name", required=True)
    args = parser.parse_args(argv)

    password = getpass.getpass("Пароль: ")
    if password != getpass.getpass("Повторите пароль: "):
        print("Ошибка: пароли не совпадают", file=sys.stderr)
        return 1
    try:
        user_id = asyncio.run(_create_admin(args.email, args.full_name, password))
    except AppError as exc:
        print(f"Ошибка: {exc.message}", file=sys.stderr)
        return 1
    print(f"Создан администратор id={user_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

Добавить в `backend/pyproject.toml` контракт модуля:
```toml
[[tool.importlinter.contracts]]
name = "Другие модули используют users_auth только через service и events"
type = "forbidden"
source_modules = ["app.modules.directories"]
forbidden_modules = [
    "app.modules.users_auth.models",
    "app.modules.users_auth.schemas",
    "app.modules.users_auth.passwords",
    "app.modules.users_auth.tokens",
    "app.modules.users_auth.throttle",
    "app.modules.users_auth.auth",
    "app.modules.users_auth.users",
    "app.modules.users_auth.deps",
    "app.modules.users_auth.router",
]
allow_indirect_imports = true
```
Модуля `directories` ещё нет, поэтому до Task 10 контракт закомментировать строкой `# (включается в Task 10)`: import-linter падает, если исходного модуля не существует. В Task 10 раскомментировать. Отсутствующие пока файлы из `forbidden_modules` (`schemas`, `tokens`, `throttle`, `auth`, `deps`, `router`) появятся в Tasks 7–9.

- [ ] **Step 5: Прогнать тесты и проверки**

Run: `uv run pytest -q && uv run mypy app tests && uv run lint-imports`
Expected: всё проходит, включая `test_migrations_downgrade_to_base_and_upgrade_again`.

- [ ] **Step 6: Проверить CLI вручную на локальной БД**

Run: `uv run alembic upgrade head && uv run python -m app.cli create-admin --email admin@company.ru --full-name "Администратор"` (ввести пароль дважды)
Expected: `Создан администратор id=1`.

- [ ] **Step 7: Commit**

```bash
git add backend
git commit -m "feat: модель пользователей, хэширование Argon2id, CLI создания администратора"
```

---

### Task 7: Аутентификация — вход, refresh с ротацией, выход, смена пароля, проверка ролей

**Files:**
- Create: `backend/app/modules/users_auth/tokens.py`, `auth.py`, `deps.py`, `schemas.py`, `router.py`
- Modify: `backend/app/modules/users_auth/service.py`, `backend/app/main.py`, `backend/tests/conftest.py`
- Test: `backend/tests/modules/users_auth/test_tokens.py`, `test_auth_api.py`

**Interfaces:**
- Consumes: `User`, `RefreshToken`, `UserRole`, `passwords.*`, `users.get_user_by_email`, `users.normalize_email`, ошибки из `app.core.errors`, `SessionDep`, `record_audit`.
- Produces:
  - `tokens.create_access_token(user_id: int, *, now: datetime | None = None) -> str`; `tokens.decode_access_token(token: str) -> int` (id пользователя, иначе `UnauthorizedError(code="invalid_token")`); `tokens.new_refresh_token() -> tuple[str, str]` (сырой токен, sha256-хэш); `tokens.hash_refresh_token(raw: str) -> str`.
  - `auth.TokenPair(access_token, refresh_token, must_change_password)`; `async auth.authenticate(session, email, password) -> User | None`; `async auth.issue_tokens(session, user) -> TokenPair` (commit); `async auth.login(session, *, email, password) -> TokenPair`; `async auth.rotate_refresh_token(session, raw: str | None) -> TokenPair`; `async auth.logout(session, raw: str | None) -> None`; `async auth.revoke_all_refresh_tokens(session, user_id) -> None` (без commit); `async auth.change_password(session, *, user_id, current_password, new_password) -> TokenPair`.
  - `deps.CurrentUser` (frozen dataclass: `id, email, full_name, role, department_id, must_change_password`); `CurrentUserDep`; `PasswordChangeUserDep`; `require_roles(*roles) -> dependency`; `AdminDep`.
  - Эндпоинты: `POST /api/auth/login`, `POST /api/auth/refresh`, `POST /api/auth/logout` (204), `GET /api/auth/me`, `POST /api/auth/change-password`.
  - Тестовые фикстуры: `admin_user`, `admin_headers`; хелпер `tests.factories.login(client, email, password=DEFAULT_PASSWORD) -> dict[str, str]`.

- [ ] **Step 1: Написать падающие тесты токенов**

`backend/tests/modules/users_auth/test_tokens.py`:
```python
from datetime import UTC, datetime, timedelta

import jwt
import pytest

from app.core.config import get_settings
from app.core.errors import UnauthorizedError
from app.modules.users_auth.tokens import (
    create_access_token,
    decode_access_token,
    hash_refresh_token,
    new_refresh_token,
)


def test_access_token_roundtrip() -> None:
    assert decode_access_token(create_access_token(42)) == 42


def test_access_token_expires_after_15_minutes() -> None:
    issued = datetime.now(UTC) - timedelta(minutes=16)

    with pytest.raises(UnauthorizedError):
        decode_access_token(create_access_token(42, now=issued))


def test_tampered_token_rejected() -> None:
    token = create_access_token(42)

    with pytest.raises(UnauthorizedError):
        decode_access_token(token[:-2] + ("aa" if token[-2:] != "aa" else "bb"))


def test_token_of_other_type_rejected() -> None:
    token = jwt.encode(
        {"sub": "42", "type": "refresh", "exp": datetime.now(UTC) + timedelta(minutes=5)},
        get_settings().jwt_secret,
        algorithm="HS256",
    )

    with pytest.raises(UnauthorizedError):
        decode_access_token(token)


def test_refresh_token_hash_is_sha256_of_raw() -> None:
    raw, token_hash = new_refresh_token()

    assert len(raw) >= 40
    assert token_hash == hash_refresh_token(raw)
    assert len(token_hash) == 64
```

- [ ] **Step 2: Убедиться, что тесты падают**

Run: `uv run pytest tests/modules/users_auth/test_tokens.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.modules.users_auth.tokens'`.

- [ ] **Step 3: Реализовать токены**

`backend/app/modules/users_auth/tokens.py`:
```python
import hashlib
import secrets
from datetime import UTC, datetime, timedelta

import jwt

from app.core.config import get_settings
from app.core.errors import UnauthorizedError

ALGORITHM = "HS256"


def create_access_token(user_id: int, *, now: datetime | None = None) -> str:
    settings = get_settings()
    issued_at = now or datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "type": "access",
        "iat": int(issued_at.timestamp()),
        "exp": int((issued_at + timedelta(minutes=settings.access_token_ttl_minutes)).timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)


def decode_access_token(token: str) -> int:
    invalid = UnauthorizedError("Сессия недействительна, войдите снова", code="invalid_token")
    try:
        payload = jwt.decode(
            token,
            get_settings().jwt_secret,
            algorithms=[ALGORITHM],
            options={"require": ["sub", "exp", "type"]},
        )
    except jwt.PyJWTError as exc:
        raise invalid from exc
    if payload.get("type") != "access":
        raise invalid
    try:
        return int(payload["sub"])
    except (TypeError, ValueError) as exc:
        raise invalid from exc


def hash_refresh_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def new_refresh_token() -> tuple[str, str]:
    raw = secrets.token_urlsafe(32)
    return raw, hash_refresh_token(raw)
```

Run: `uv run pytest tests/modules/users_auth/test_tokens.py -q`
Expected: 5 passed.

- [ ] **Step 4: Написать падающие API-тесты**

Добавить в `backend/tests/factories.py`:
```python
from httpx import AsyncClient


async def login(
    client: AsyncClient, email: str, password: str = DEFAULT_PASSWORD
) -> dict[str, str]:
    response = await client.post("/api/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}
```
(импорт `AsyncClient` — в блок импортов файла.)

Добавить в `backend/tests/conftest.py` (импорты — в блок импортов):
```python
from app.modules.users_auth.models import User, UserRole
from tests.factories import login, make_user


@pytest.fixture
async def admin_user(db_session: AsyncSession) -> User:
    return await make_user(
        db_session, email="admin@company.ru", full_name="Админов Админ", role=UserRole.ADMIN
    )


@pytest.fixture
async def admin_headers(client: AsyncClient, admin_user: User) -> dict[str, str]:
    return await login(client, admin_user.email)
```

`backend/tests/modules/users_auth/test_auth_api.py`:
```python
from datetime import UTC, datetime, timedelta

from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.users_auth.deps import AdminDep, CurrentUserDep
from app.modules.users_auth.models import RefreshToken, UserRole
from tests.factories import DEFAULT_PASSWORD, login, make_user


def _add_probe_routes(app: FastAPI) -> None:
    async def protected(user: CurrentUserDep) -> dict[str, int]:
        return {"id": user.id}

    async def admin_only(user: AdminDep) -> dict[str, int]:
        return {"id": user.id}

    app.add_api_route("/_probe/protected", protected, methods=["GET"])
    app.add_api_route("/_probe/admin", admin_only, methods=["GET"])


async def test_login_returns_access_token_and_sets_refresh_cookie(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    user = await make_user(db_session, email="ivanov@company.ru")

    response = await client.post(
        "/api/auth/login", json={"email": "IVANOV@company.ru", "password": DEFAULT_PASSWORD}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["must_change_password"] is False
    assert body["access_token"]
    set_cookie = response.headers["set-cookie"].lower()
    assert "refresh_token=" in set_cookie
    assert "httponly" in set_cookie
    assert "samesite=strict" in set_cookie
    assert "path=/api/auth" in set_cookie
    me = await client.get(
        "/api/auth/me", headers={"Authorization": f"Bearer {body['access_token']}"}
    )
    assert me.json()["id"] == user.id


async def test_login_with_wrong_password_returns_401(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    await make_user(db_session, email="ivanov@company.ru")

    response = await client.post(
        "/api/auth/login", json={"email": "ivanov@company.ru", "password": "wrong-password"}
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_credentials"


async def test_login_unknown_email_and_inactive_user_look_the_same(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    await make_user(db_session, email="fired@company.ru", is_active=False)

    unknown = await client.post(
        "/api/auth/login", json={"email": "nobody@company.ru", "password": DEFAULT_PASSWORD}
    )
    inactive = await client.post(
        "/api/auth/login", json={"email": "fired@company.ru", "password": DEFAULT_PASSWORD}
    )

    assert unknown.status_code == inactive.status_code == 401
    assert unknown.json() == inactive.json()


async def test_me_requires_valid_token(client: AsyncClient) -> None:
    missing = await client.get("/api/auth/me")
    garbage = await client.get("/api/auth/me", headers={"Authorization": "Bearer garbage"})

    assert missing.status_code == 401
    assert garbage.status_code == 401


async def test_refresh_rotates_token_and_detects_reuse(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    user = await make_user(db_session)
    login_response = await client.post(
        "/api/auth/login", json={"email": user.email, "password": DEFAULT_PASSWORD}
    )
    old_refresh = login_response.cookies["refresh_token"]

    rotated = await client.post("/api/auth/refresh")
    assert rotated.status_code == 200
    new_refresh = rotated.cookies["refresh_token"]
    assert new_refresh != old_refresh

    client.cookies.clear()
    reused = await client.post(
        "/api/auth/refresh", headers={"Cookie": f"refresh_token={old_refresh}"}
    )
    assert reused.status_code == 401

    after_reuse = await client.post(
        "/api/auth/refresh", headers={"Cookie": f"refresh_token={new_refresh}"}
    )
    assert after_reuse.status_code == 401


async def test_refresh_without_cookie_returns_401(client: AsyncClient) -> None:
    response = await client.post("/api/auth/refresh")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_refresh_token"


async def test_expired_refresh_token_rejected(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    user = await make_user(db_session)
    await login(client, user.email)
    await db_session.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user.id)
        .values(expires_at=datetime.now(UTC) - timedelta(seconds=1))
    )

    response = await client.post("/api/auth/refresh")

    assert response.status_code == 401


async def test_logout_revokes_refresh_token(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    user = await make_user(db_session)
    login_response = await client.post(
        "/api/auth/login", json={"email": user.email, "password": DEFAULT_PASSWORD}
    )
    refresh = login_response.cookies["refresh_token"]

    logout = await client.post("/api/auth/logout")
    assert logout.status_code == 204

    client.cookies.clear()
    response = await client.post(
        "/api/auth/refresh", headers={"Cookie": f"refresh_token={refresh}"}
    )
    assert response.status_code == 401


async def test_must_change_password_blocks_other_endpoints_until_changed(
    app: FastAPI, client: AsyncClient, db_session: AsyncSession
) -> None:
    _add_probe_routes(app)
    user = await make_user(db_session, must_change_password=True)
    login_response = await client.post(
        "/api/auth/login", json={"email": user.email, "password": DEFAULT_PASSWORD}
    )
    assert login_response.json()["must_change_password"] is True
    headers = {"Authorization": f"Bearer {login_response.json()['access_token']}"}

    blocked = await client.get("/_probe/protected", headers=headers)
    assert blocked.status_code == 403
    assert blocked.json()["error"]["code"] == "password_change_required"
    assert (await client.get("/api/auth/me", headers=headers)).status_code == 200

    changed = await client.post(
        "/api/auth/change-password",
        headers=headers,
        json={"current_password": DEFAULT_PASSWORD, "new_password": "Brand-New-Pass-2"},
    )
    assert changed.status_code == 200
    assert changed.json()["must_change_password"] is False

    new_headers = {"Authorization": f"Bearer {changed.json()['access_token']}"}
    assert (await client.get("/_probe/protected", headers=new_headers)).status_code == 200
    assert (await login(client, user.email, "Brand-New-Pass-2"))["Authorization"]


async def test_change_password_revokes_other_sessions(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    user = await make_user(db_session)
    first = await client.post(
        "/api/auth/login", json={"email": user.email, "password": DEFAULT_PASSWORD}
    )
    other_session_refresh = first.cookies["refresh_token"]
    headers = {"Authorization": f"Bearer {first.json()['access_token']}"}

    changed = await client.post(
        "/api/auth/change-password",
        headers=headers,
        json={"current_password": DEFAULT_PASSWORD, "new_password": "Brand-New-Pass-2"},
    )
    assert changed.status_code == 200

    client.cookies.clear()
    response = await client.post(
        "/api/auth/refresh", headers={"Cookie": f"refresh_token={other_session_refresh}"}
    )
    assert response.status_code == 401


async def test_change_password_with_wrong_current_password(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    user = await make_user(db_session)
    headers = await login(client, user.email)

    response = await client.post(
        "/api/auth/change-password",
        headers=headers,
        json={"current_password": "wrong-password", "new_password": "Brand-New-Pass-2"},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_current_password"


async def test_require_roles(app: FastAPI, client: AsyncClient, db_session: AsyncSession) -> None:
    _add_probe_routes(app)
    employee = await make_user(db_session, role=UserRole.EMPLOYEE)
    admin = await make_user(db_session, role=UserRole.ADMIN)

    employee_response = await client.get("/_probe/admin", headers=await login(client, employee.email))
    admin_response = await client.get("/_probe/admin", headers=await login(client, admin.email))

    assert employee_response.status_code == 403
    assert employee_response.json()["error"]["code"] == "insufficient_role"
    assert admin_response.status_code == 200


async def test_deactivated_user_access_token_stops_working(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    user = await make_user(db_session)
    headers = await login(client, user.email)
    user.is_active = False
    await db_session.flush()

    response = await client.get("/api/auth/me", headers=headers)

    assert response.status_code == 401
```

- [ ] **Step 5: Убедиться, что тесты падают**

Run: `uv run pytest tests/modules/users_auth/test_auth_api.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.modules.users_auth.deps'`.

- [ ] **Step 6: Реализовать логику аутентификации**

`backend/app/modules/users_auth/auth.py`:
```python
import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import record_audit
from app.core.config import get_settings
from app.core.errors import UnauthorizedError, ValidationFailedError
from app.modules.users_auth.models import RefreshToken, User
from app.modules.users_auth.passwords import (
    dummy_verify,
    hash_password,
    validate_password_strength,
    verify_password,
)
from app.modules.users_auth.tokens import (
    create_access_token,
    hash_refresh_token,
    new_refresh_token,
)
from app.modules.users_auth.users import get_user_by_email

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TokenPair:
    access_token: str
    refresh_token: str
    must_change_password: bool


def _now() -> datetime:
    return datetime.now(UTC)


def _invalid_refresh() -> UnauthorizedError:
    return UnauthorizedError("Сессия истекла, войдите снова", code="invalid_refresh_token")


async def authenticate(session: AsyncSession, email: str, password: str) -> User | None:
    user = await get_user_by_email(session, email)
    if user is None:
        dummy_verify(password)
        return None
    if not verify_password(user.password_hash, password) or not user.is_active:
        return None
    return user


async def issue_tokens(session: AsyncSession, user: User) -> TokenPair:
    raw, token_hash = new_refresh_token()
    session.add(
        RefreshToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=_now() + timedelta(days=get_settings().refresh_token_ttl_days),
        )
    )
    await session.commit()
    return TokenPair(
        access_token=create_access_token(user.id),
        refresh_token=raw,
        must_change_password=user.must_change_password,
    )


async def login(session: AsyncSession, *, email: str, password: str) -> TokenPair:
    user = await authenticate(session, email, password)
    if user is None:
        raise UnauthorizedError("Неверный email или пароль", code="invalid_credentials")
    return await issue_tokens(session, user)


async def revoke_all_refresh_tokens(session: AsyncSession, user_id: int) -> None:
    await session.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=_now())
    )


async def rotate_refresh_token(session: AsyncSession, raw: str | None) -> TokenPair:
    if not raw:
        raise _invalid_refresh()
    token = await session.scalar(
        select(RefreshToken)
        .where(RefreshToken.token_hash == hash_refresh_token(raw))
        .with_for_update()
    )
    if token is None:
        raise _invalid_refresh()
    now = _now()
    if token.revoked_at is not None:
        # Повторное использование отозванного токена — вероятная кража: отзываем все сессии.
        await revoke_all_refresh_tokens(session, token.user_id)
        await session.commit()
        logger.warning("auth.refresh_token_reuse", extra={"user_id": token.user_id})
        raise _invalid_refresh()
    if token.expires_at <= now:
        raise _invalid_refresh()
    user = await session.get(User, token.user_id)
    if user is None or not user.is_active:
        raise _invalid_refresh()
    token.revoked_at = now
    return await issue_tokens(session, user)


async def logout(session: AsyncSession, raw: str | None) -> None:
    if not raw:
        return
    await session.execute(
        update(RefreshToken)
        .where(
            RefreshToken.token_hash == hash_refresh_token(raw),
            RefreshToken.revoked_at.is_(None),
        )
        .values(revoked_at=_now())
    )
    await session.commit()


async def change_password(
    session: AsyncSession, *, user_id: int, current_password: str, new_password: str
) -> TokenPair:
    user = await session.get(User, user_id)
    if user is None or not user.is_active:
        raise UnauthorizedError("Требуется вход", code="not_authenticated")
    if not verify_password(user.password_hash, current_password):
        raise ValidationFailedError(
            "Текущий пароль указан неверно", code="invalid_current_password"
        )
    validate_password_strength(new_password)
    if verify_password(user.password_hash, new_password):
        raise ValidationFailedError(
            "Новый пароль должен отличаться от текущего", code="password_reused"
        )
    user.password_hash = hash_password(new_password)
    user.must_change_password = False
    await revoke_all_refresh_tokens(session, user.id)
    record_audit(
        session,
        entity_type="user",
        entity_id=user.id,
        user_id=user.id,
        action="change_password",
        diff={},
    )
    return await issue_tokens(session, user)
```

`backend/app/modules/users_auth/deps.py`:
```python
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.db import SessionDep
from app.core.errors import ForbiddenError, UnauthorizedError
from app.modules.users_auth.models import User, UserRole
from app.modules.users_auth.tokens import decode_access_token

_bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class CurrentUser:
    id: int
    email: str
    full_name: str
    role: UserRole
    department_id: int | None
    must_change_password: bool


async def get_current_user_allow_password_change(
    session: SessionDep,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> CurrentUser:
    if credentials is None:
        raise UnauthorizedError("Требуется вход", code="not_authenticated")
    user = await session.get(User, decode_access_token(credentials.credentials))
    if user is None or not user.is_active:
        raise UnauthorizedError("Требуется вход", code="not_authenticated")
    return CurrentUser(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        department_id=user.department_id,
        must_change_password=user.must_change_password,
    )


PasswordChangeUserDep = Annotated[CurrentUser, Depends(get_current_user_allow_password_change)]


async def get_current_user(user: PasswordChangeUserDep) -> CurrentUser:
    if user.must_change_password:
        raise ForbiddenError("Необходимо сменить пароль", code="password_change_required")
    return user


CurrentUserDep = Annotated[CurrentUser, Depends(get_current_user)]


def require_roles(*roles: UserRole) -> Callable[[CurrentUser], Awaitable[CurrentUser]]:
    allowed = frozenset(roles)

    async def dependency(user: CurrentUserDep) -> CurrentUser:
        if user.role not in allowed:
            raise ForbiddenError("Недостаточно прав", code="insufficient_role")
        return user

    return dependency


AdminDep = Annotated[CurrentUser, Depends(require_roles(UserRole.ADMIN))]
```

`backend/app/modules/users_auth/schemas.py`:
```python
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.modules.users_auth.models import UserRole


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1, max_length=256)


class AccessTokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    must_change_password: bool


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=256)
    new_password: str = Field(min_length=1, max_length=256)


class MeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    full_name: str
    role: UserRole
    department_id: int | None
    must_change_password: bool


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    full_name: str
    role: UserRole
    department_id: int | None
    is_active: bool
    must_change_password: bool
    created_at: datetime
```

`backend/app/modules/users_auth/router.py`:
```python
from typing import Annotated

from fastapi import APIRouter, Cookie, Response

from app.core.config import get_settings
from app.core.db import SessionDep
from app.modules.users_auth import auth
from app.modules.users_auth.deps import PasswordChangeUserDep
from app.modules.users_auth.schemas import (
    AccessTokenResponse,
    ChangePasswordRequest,
    LoginRequest,
    MeRead,
)

REFRESH_COOKIE_NAME = "refresh_token"
REFRESH_COOKIE_PATH = "/api/auth"

RefreshCookie = Annotated[str | None, Cookie()]

auth_router = APIRouter(prefix="/auth", tags=["auth"])


def _token_response(response: Response, pair: auth.TokenPair) -> AccessTokenResponse:
    settings = get_settings()
    response.set_cookie(
        REFRESH_COOKIE_NAME,
        pair.refresh_token,
        max_age=settings.refresh_token_ttl_days * 24 * 60 * 60,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="strict",
        path=REFRESH_COOKIE_PATH,
    )
    return AccessTokenResponse(
        access_token=pair.access_token, must_change_password=pair.must_change_password
    )


@auth_router.post("/login", response_model=AccessTokenResponse)
async def login(
    body: LoginRequest, response: Response, session: SessionDep
) -> AccessTokenResponse:
    pair = await auth.login(session, email=body.email, password=body.password)
    return _token_response(response, pair)


@auth_router.post("/refresh", response_model=AccessTokenResponse)
async def refresh(
    response: Response, session: SessionDep, refresh_token: RefreshCookie = None
) -> AccessTokenResponse:
    pair = await auth.rotate_refresh_token(session, refresh_token)
    return _token_response(response, pair)


@auth_router.post("/logout", status_code=204)
async def logout(session: SessionDep, refresh_token: RefreshCookie = None) -> Response:
    await auth.logout(session, refresh_token)
    response = Response(status_code=204)
    response.delete_cookie(
        REFRESH_COOKIE_NAME,
        path=REFRESH_COOKIE_PATH,
        secure=get_settings().cookie_secure,
        httponly=True,
        samesite="strict",
    )
    return response


@auth_router.get("/me", response_model=MeRead)
async def me(user: PasswordChangeUserDep) -> MeRead:
    return MeRead.model_validate(user)


@auth_router.post("/change-password", response_model=AccessTokenResponse)
async def change_password(
    body: ChangePasswordRequest,
    response: Response,
    session: SessionDep,
    user: PasswordChangeUserDep,
) -> AccessTokenResponse:
    pair = await auth.change_password(
        session,
        user_id=user.id,
        current_password=body.current_password,
        new_password=body.new_password,
    )
    return _token_response(response, pair)
```

`backend/app/modules/users_auth/service.py` (полная замена):
```python
"""Публичный интерфейс модуля users_auth. Другие модули импортируют только этот файл и events.py."""

from app.modules.users_auth.deps import (
    AdminDep,
    CurrentUser,
    CurrentUserDep,
    PasswordChangeUserDep,
    require_roles,
)
from app.modules.users_auth.models import UserRole
from app.modules.users_auth.users import create_first_admin

__all__ = [
    "AdminDep",
    "CurrentUser",
    "CurrentUserDep",
    "PasswordChangeUserDep",
    "UserRole",
    "create_first_admin",
    "require_roles",
]
```

В `backend/app/main.py`: импортировать `from app.modules.users_auth.router import auth_router` и после `include_router(health_router)` добавить `app.include_router(auth_router, prefix="/api")`.

- [ ] **Step 7: Прогнать тесты и проверки**

Run: `uv run pytest -q && uv run mypy app tests && uv run lint-imports`
Expected: всё проходит.

- [ ] **Step 8: Commit**

```bash
git add backend
git commit -m "feat: JWT-аутентификация с ротацией refresh-токенов и сменой пароля"
```

---

### Task 8: Защита от перебора паролей и определение IP клиента

**Files:**
- Create: `backend/app/core/net.py`, `backend/app/modules/users_auth/throttle.py`
- Modify: `backend/app/modules/users_auth/auth.py` (функция `login`), `backend/app/modules/users_auth/router.py` (эндпоинт `login`)
- Test: `backend/tests/core/test_net.py`, `backend/tests/modules/users_auth/test_throttle.py`, дополнить `test_auth_api.py`

**Interfaces:**
- Consumes: `Settings.trusted_proxies`, `RedisDep`, `resolve`, `TooManyRequestsError`, `normalize_email`.
- Produces:
  - `app.core.net.client_ip(request: Request, trusted_proxies: Collection[str]) -> str`.
  - `throttle.ThrottleLimits` (frozen dataclass: `account_ip_attempts=5`, `ip_attempts=20`, `window_seconds=900`, `lock_seconds=900`, `account_alert_attempts=50`, `account_alert_window_seconds=3600`).
  - `throttle.LoginThrottle(redis, limits=None)`: `async is_locked(email, ip) -> bool`, `async register_failure(email, ip) -> None`, `async register_success(email, ip) -> None`, `async unlock_account(email) -> int` (число удалённых ключей).
  - `auth.login(session, throttle, *, email, password, ip) -> TokenPair` — новая сигнатура; при блокировке `TooManyRequestsError(code="login_locked")`.

- [ ] **Step 1: Написать падающие тесты**

`backend/tests/core/test_net.py`:
```python
from starlette.requests import Request

from app.core.net import client_ip

TRUSTED = ["127.0.0.1/32", "172.16.0.0/12"]


def _request(peer: str, forwarded: str | None = None) -> Request:
    headers = [(b"x-forwarded-for", forwarded.encode())] if forwarded else []
    return Request({"type": "http", "client": (peer, 5000), "headers": headers})


def test_untrusted_peer_ignores_forwarded_header() -> None:
    assert client_ip(_request("198.51.100.7", "203.0.113.1"), TRUSTED) == "198.51.100.7"


def test_trusted_peer_uses_forwarded_header() -> None:
    assert client_ip(_request("172.18.0.5", "203.0.113.1"), TRUSTED) == "203.0.113.1"


def test_rightmost_untrusted_address_wins_over_spoofed_prefix() -> None:
    request = _request("172.18.0.5", "10.9.9.9, 203.0.113.1, 172.18.0.2")

    assert client_ip(request, TRUSTED) == "203.0.113.1"


def test_trusted_peer_without_header_returns_peer() -> None:
    assert client_ip(_request("127.0.0.1"), TRUSTED) == "127.0.0.1"


def test_garbage_in_forwarded_header_is_not_trusted() -> None:
    assert client_ip(_request("127.0.0.1", "not-an-ip"), TRUSTED) == "not-an-ip"
```

`backend/tests/modules/users_auth/test_throttle.py`:
```python
import logging

import pytest
from redis.asyncio import Redis

from app.core.redis import resolve
from app.modules.users_auth.throttle import LoginThrottle, ThrottleLimits

EMAIL = "ivanov@company.ru"


async def test_account_ip_pair_locked_after_5_failures(redis_client: Redis) -> None:
    throttle = LoginThrottle(redis_client)

    for _ in range(4):
        await throttle.register_failure(EMAIL, "10.0.0.1")
    assert not await throttle.is_locked(EMAIL, "10.0.0.1")

    await throttle.register_failure(EMAIL, "10.0.0.1")

    assert await throttle.is_locked(EMAIL, "10.0.0.1")
    assert not await throttle.is_locked(EMAIL, "10.0.0.2")
    ttl = await resolve(redis_client.ttl(f"login:lock:acct_ip:{EMAIL}:10.0.0.1"))
    assert 0 < ttl <= 900


async def test_ip_locked_after_20_failures_across_accounts(redis_client: Redis) -> None:
    throttle = LoginThrottle(redis_client)

    for index in range(20):
        await throttle.register_failure(f"user{index}@company.ru", "10.0.0.9")

    assert await throttle.is_locked("someone-else@company.ru", "10.0.0.9")


async def test_success_resets_pair_counter(redis_client: Redis) -> None:
    throttle = LoginThrottle(redis_client)

    for _ in range(4):
        await throttle.register_failure(EMAIL, "10.0.0.1")
    await throttle.register_success(EMAIL, "10.0.0.1")
    for _ in range(4):
        await throttle.register_failure(EMAIL, "10.0.0.1")

    assert not await throttle.is_locked(EMAIL, "10.0.0.1")


async def test_bruteforce_alert_logged_once_without_locking(
    redis_client: Redis, caplog: pytest.LogCaptureFixture
) -> None:
    limits = ThrottleLimits(account_alert_attempts=3, account_ip_attempts=100, ip_attempts=100)
    throttle = LoginThrottle(redis_client, limits)

    with caplog.at_level(logging.WARNING, logger="app.modules.users_auth.throttle"):
        for index in range(5):
            await throttle.register_failure(EMAIL, f"10.0.1.{index}")

    alerts = [r for r in caplog.records if r.getMessage() == "auth.login_bruteforce_suspected"]
    assert len(alerts) == 1
    assert not await throttle.is_locked(EMAIL, "10.0.2.1")


async def test_unlock_account_removes_locks_and_counters(redis_client: Redis) -> None:
    throttle = LoginThrottle(redis_client)
    for _ in range(5):
        await throttle.register_failure(EMAIL, "10.0.0.1")

    removed = await throttle.unlock_account(EMAIL)

    assert removed >= 1
    assert not await throttle.is_locked(EMAIL, "10.0.0.1")
```

Добавить в `backend/tests/modules/users_auth/test_auth_api.py`:
```python
async def test_login_locked_for_pair_after_5_failures_but_not_from_other_ip(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    user = await make_user(db_session)
    attacker = {"X-Forwarded-For": "203.0.113.5"}
    for _ in range(5):
        failed = await client.post(
            "/api/auth/login",
            json={"email": user.email, "password": "wrong-password"},
            headers=attacker,
        )
        assert failed.status_code == 401

    locked = await client.post(
        "/api/auth/login",
        json={"email": user.email, "password": DEFAULT_PASSWORD},
        headers=attacker,
    )
    from_office = await client.post(
        "/api/auth/login",
        json={"email": user.email, "password": DEFAULT_PASSWORD},
        headers={"X-Forwarded-For": "203.0.113.6"},
    )

    assert locked.status_code == 429
    assert locked.json()["error"]["code"] == "login_locked"
    assert from_office.status_code == 200
```

- [ ] **Step 2: Убедиться, что тесты падают**

Run: `uv run pytest tests/core/test_net.py tests/modules/users_auth/test_throttle.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.core.net'`.

- [ ] **Step 3: Реализовать**

`backend/app/core/net.py`:
```python
import ipaddress
from collections.abc import Collection

from starlette.requests import Request


def _is_trusted(address: str, trusted_proxies: Collection[str]) -> bool:
    try:
        ip = ipaddress.ip_address(address)
    except ValueError:
        return False
    return any(ip in ipaddress.ip_network(network, strict=False) for network in trusted_proxies)


def client_ip(request: Request, trusted_proxies: Collection[str]) -> str:
    """IP клиента. X-Forwarded-For учитывается только от доверенного прокси."""
    peer = request.client.host if request.client else "unknown"
    if not _is_trusted(peer, trusted_proxies):
        return peer
    forwarded = request.headers.get("x-forwarded-for", "")
    hops = [hop.strip() for hop in forwarded.split(",") if hop.strip()]
    for hop in reversed(hops):
        if not _is_trusted(hop, trusted_proxies):
            return hop
    return peer
```

`backend/app/modules/users_auth/throttle.py`:
```python
import logging
import re
from dataclasses import dataclass

from redis.asyncio import Redis

from app.core.redis import resolve

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ThrottleLimits:
    account_ip_attempts: int = 5
    ip_attempts: int = 20
    window_seconds: int = 15 * 60
    lock_seconds: int = 15 * 60
    account_alert_attempts: int = 50
    account_alert_window_seconds: int = 60 * 60


def _glob_escape(value: str) -> str:
    return re.sub(r"([*?\[\]\\])", r"\\\1", value)


class LoginThrottle:
    """Счётчики неудачных входов в Redis (п. 2.4 ТЗ)."""

    def __init__(self, redis: Redis, limits: ThrottleLimits | None = None) -> None:
        self._redis = redis
        self._limits = limits or ThrottleLimits()

    async def is_locked(self, email: str, ip: str) -> bool:
        count = await resolve(
            self._redis.exists(f"login:lock:acct_ip:{email}:{ip}", f"login:lock:ip:{ip}")
        )
        return bool(count)

    async def register_failure(self, email: str, ip: str) -> None:
        limits = self._limits

        pair_key = f"login:fail:acct_ip:{email}:{ip}"
        if await self._increment(pair_key, limits.window_seconds) >= limits.account_ip_attempts:
            await self._lock(f"login:lock:acct_ip:{email}:{ip}", pair_key)

        ip_key = f"login:fail:ip:{ip}"
        if await self._increment(ip_key, limits.window_seconds) >= limits.ip_attempts:
            await self._lock(f"login:lock:ip:{ip}", ip_key)

        account_failures = await self._increment(
            f"login:fail:acct:{email}", limits.account_alert_window_seconds
        )
        if account_failures >= limits.account_alert_attempts:
            first_alert = await resolve(
                self._redis.set(
                    f"login:alerted:acct:{email}",
                    "1",
                    ex=limits.account_alert_window_seconds,
                    nx=True,
                )
            )
            if first_alert:
                logger.warning(
                    "auth.login_bruteforce_suspected",
                    extra={"email": email, "failed_attempts": account_failures},
                )

    async def register_success(self, email: str, ip: str) -> None:
        await resolve(self._redis.delete(f"login:fail:acct_ip:{email}:{ip}"))

    async def unlock_account(self, email: str) -> int:
        pattern = f"login:*:acct_ip:{_glob_escape(email)}:*"
        keys = [key async for key in self._redis.scan_iter(match=pattern)]
        if not keys:
            return 0
        return int(await resolve(self._redis.delete(*keys)))

    async def _increment(self, key: str, ttl_seconds: int) -> int:
        count = int(await resolve(self._redis.incr(key)))
        if count == 1:
            await resolve(self._redis.expire(key, ttl_seconds))
        return count

    async def _lock(self, lock_key: str, counter_key: str) -> None:
        await resolve(self._redis.set(lock_key, "1", ex=self._limits.lock_seconds))
        await resolve(self._redis.delete(counter_key))
```

В `backend/app/modules/users_auth/auth.py` заменить функцию `login` (добавить импорты `from app.core.errors import TooManyRequestsError`, `from app.modules.users_auth.throttle import LoginThrottle`, `from app.modules.users_auth.users import normalize_email`):
```python
async def login(
    session: AsyncSession, throttle: LoginThrottle, *, email: str, password: str, ip: str
) -> TokenPair:
    normalized = normalize_email(email)
    if await throttle.is_locked(normalized, ip):
        raise TooManyRequestsError(
            "Слишком много неудачных попыток входа. Повторите через 15 минут",
            code="login_locked",
        )
    user = await authenticate(session, normalized, password)
    if user is None:
        await throttle.register_failure(normalized, ip)
        raise UnauthorizedError("Неверный email или пароль", code="invalid_credentials")
    await throttle.register_success(normalized, ip)
    return await issue_tokens(session, user)
```

В `backend/app/modules/users_auth/router.py` заменить эндпоинт `login` (импорты: `Request` из `fastapi`, `from app.core.net import client_ip`, `from app.core.redis import RedisDep`, `from app.modules.users_auth.throttle import LoginThrottle`):
```python
@auth_router.post("/login", response_model=AccessTokenResponse)
async def login(
    body: LoginRequest,
    request: Request,
    response: Response,
    session: SessionDep,
    redis: RedisDep,
) -> AccessTokenResponse:
    pair = await auth.login(
        session,
        LoginThrottle(redis),
        email=body.email,
        password=body.password,
        ip=client_ip(request, get_settings().trusted_proxies),
    )
    return _token_response(response, pair)
```

- [ ] **Step 4: Прогнать тесты и проверки**

Run: `uv run pytest -q && uv run mypy app tests && uv run lint-imports`
Expected: всё проходит.

- [ ] **Step 5: Commit**

```bash
git add backend
git commit -m "feat: защита от перебора паролей по паре учётная запись+IP и по IP"
```

---

### Task 9: Администрирование пользователей

**Files:**
- Create: `backend/app/core/schemas.py`, `backend/app/modules/users_auth/events.py`
- Modify: `backend/app/modules/users_auth/users.py`, `schemas.py`, `router.py`, `service.py`, `backend/app/main.py`
- Test: `backend/tests/modules/users_auth/test_admin_users_api.py`

**Interfaces:**
- Consumes: `event_bus`, `record_audit`, `diff_values`, `revoke_all_refresh_tokens`, `LoginThrottle`, `AdminDep`, `CurrentUserDep`.
- Produces:
  - `app.core.schemas`: `Page[T]` (`items, total, limit, offset`); `Pagination(limit, offset)`; `PaginationDep` (`limit` 1..200, по умолчанию 50; `offset` ≥ 0); `PartialUpdate` — базовая модель PATCH-запросов с `non_nullable: ClassVar[frozenset[str]]`.
  - `events.DeactivationBlocker(kind: str, entity_id: int, title: str)`; `events.UserDeactivationRequested(user_id: int, blockers: list[DeactivationBlocker])` — подписчики других модулей добавляют блокеры; если список не пуст, деактивация → 409 `deactivation_blocked`, `details` — список блокеров.
  - `users.py`: `list_users`, `search_active_users`, `get_user_or_404`, `admin_create_user -> tuple[User, str]`, `update_user`, `deactivate_user`, `activate_user`, `issue_temporary_password -> str`.
  - `service.UserInfo(id, email, full_name, role, department_id, is_active)`; `async service.get_user_info(session, user_id) -> UserInfo | None`.
  - Эндпоинты `/api/admin/users`: `GET` (фильтры `q`, `role`, `department_id`, `is_active`, пагинация), `POST` (201, возвращает временный пароль), `GET /{id}`, `PATCH /{id}`, `POST /{id}/deactivate`, `POST /{id}/activate`, `POST /{id}/temporary-password`, `POST /{id}/unlock-login` (204). `GET /api/users?q=` — автокомплит активных пользователей для любого вошедшего.
  - Правила: нельзя деактивировать себя (`cannot_deactivate_self`); нельзя оставить систему без активного Admin (`last_admin`).

- [ ] **Step 1: Написать падающие тесты**

`backend/tests/modules/users_auth/test_admin_users_api.py`:
```python
from httpx import AsyncClient
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import AuditLog
from app.core.events import event_bus
from app.modules.users_auth.events import DeactivationBlocker, UserDeactivationRequested
from app.modules.users_auth.models import User, UserRole
from app.modules.users_auth.throttle import LoginThrottle
from tests.factories import DEFAULT_PASSWORD, login, make_user


async def test_admin_endpoints_require_admin(client: AsyncClient, db_session: AsyncSession) -> None:
    manager = await make_user(db_session, role=UserRole.MANAGER)

    anonymous = await client.get("/api/admin/users")
    as_manager = await client.get("/api/admin/users", headers=await login(client, manager.email))

    assert anonymous.status_code == 401
    assert as_manager.status_code == 403


async def test_create_user_returns_temporary_password(
    client: AsyncClient, admin_headers: dict[str, str], db_session: AsyncSession
) -> None:
    response = await client.post(
        "/api/admin/users",
        headers=admin_headers,
        json={"email": "Petrov@company.ru", "full_name": "Петров Пётр", "role": "employee"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["user"]["email"] == "petrov@company.ru"
    assert body["user"]["must_change_password"] is True
    login_response = await client.post(
        "/api/auth/login",
        json={"email": "petrov@company.ru", "password": body["temporary_password"]},
    )
    assert login_response.json()["must_change_password"] is True
    audit = await db_session.scalar(
        select(AuditLog).where(
            AuditLog.entity_type == "user", AuditLog.entity_id == str(body["user"]["id"])
        )
    )
    assert audit is not None and audit.action == "create"


async def test_create_user_with_taken_email_returns_409(
    client: AsyncClient, admin_headers: dict[str, str], db_session: AsyncSession
) -> None:
    await make_user(db_session, email="petrov@company.ru")

    response = await client.post(
        "/api/admin/users",
        headers=admin_headers,
        json={"email": "petrov@company.ru", "full_name": "Петров Пётр", "role": "employee"},
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "email_taken"


async def test_list_users_filters_and_paginates(
    client: AsyncClient, admin_headers: dict[str, str], db_session: AsyncSession
) -> None:
    await make_user(db_session, full_name="Сидоров Семён", role=UserRole.MANAGER)
    await make_user(db_session, full_name="Сидорова Анна", role=UserRole.EMPLOYEE)
    await make_user(db_session, full_name="Кузнецов Олег", role=UserRole.EMPLOYEE)

    by_name = await client.get(
        "/api/admin/users", headers=admin_headers, params={"q": "сидор", "limit": 1}
    )
    by_role = await client.get(
        "/api/admin/users", headers=admin_headers, params={"role": "manager"}
    )

    assert by_name.json()["total"] == 2
    assert len(by_name.json()["items"]) == 1
    assert [u["full_name"] for u in by_role.json()["items"]] == ["Сидоров Семён"]


async def test_update_user_changes_fields_and_writes_audit(
    client: AsyncClient, admin_headers: dict[str, str], db_session: AsyncSession
) -> None:
    user = await make_user(db_session, full_name="Старое Имя")

    response = await client.patch(
        f"/api/admin/users/{user.id}",
        headers=admin_headers,
        json={"full_name": "Новое Имя", "role": "manager"},
    )

    assert response.status_code == 200
    assert response.json()["full_name"] == "Новое Имя"
    assert response.json()["role"] == "manager"
    audit = await db_session.scalar(
        select(AuditLog).where(AuditLog.entity_id == str(user.id), AuditLog.action == "update")
    )
    assert audit is not None
    assert audit.diff["full_name"] == ["Старое Имя", "Новое Имя"]


async def test_update_rejects_null_for_required_field(
    client: AsyncClient, admin_headers: dict[str, str], db_session: AsyncSession
) -> None:
    user = await make_user(db_session)

    response = await client.patch(
        f"/api/admin/users/{user.id}", headers=admin_headers, json={"full_name": None}
    )

    assert response.status_code == 422


async def test_last_admin_cannot_be_demoted(
    client: AsyncClient, admin_user: User, admin_headers: dict[str, str]
) -> None:
    response = await client.patch(
        f"/api/admin/users/{admin_user.id}", headers=admin_headers, json={"role": "manager"}
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "last_admin"


async def test_deactivate_revokes_sessions_and_blocks_login(
    client: AsyncClient, admin_headers: dict[str, str], db_session: AsyncSession
) -> None:
    user = await make_user(db_session)
    user_login = await client.post(
        "/api/auth/login", json={"email": user.email, "password": DEFAULT_PASSWORD}
    )
    user_refresh = user_login.cookies["refresh_token"]

    response = await client.post(f"/api/admin/users/{user.id}/deactivate", headers=admin_headers)

    assert response.status_code == 200
    assert response.json()["is_active"] is False
    client.cookies.clear()
    refresh = await client.post(
        "/api/auth/refresh", headers={"Cookie": f"refresh_token={user_refresh}"}
    )
    assert refresh.status_code == 401
    relogin = await client.post(
        "/api/auth/login", json={"email": user.email, "password": DEFAULT_PASSWORD}
    )
    assert relogin.status_code == 401


async def test_cannot_deactivate_self(
    client: AsyncClient, admin_user: User, admin_headers: dict[str, str]
) -> None:
    response = await client.post(
        f"/api/admin/users/{admin_user.id}/deactivate", headers=admin_headers
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "cannot_deactivate_self"


async def test_deactivation_blocked_by_subscriber(
    client: AsyncClient, admin_headers: dict[str, str], db_session: AsyncSession
) -> None:
    user = await make_user(db_session)

    async def blocker(session: AsyncSession, event: UserDeactivationRequested) -> None:
        event.blockers.append(DeactivationBlocker(kind="test", entity_id=1, title="Тестовый блок"))

    event_bus.subscribe(UserDeactivationRequested)(blocker)
    try:
        response = await client.post(
            f"/api/admin/users/{user.id}/deactivate", headers=admin_headers
        )
    finally:
        event_bus.unsubscribe(UserDeactivationRequested, blocker)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "deactivation_blocked"
    assert response.json()["error"]["details"] == [
        {"kind": "test", "entity_id": 1, "title": "Тестовый блок"}
    ]
    assert user.is_active


async def test_activate_user(
    client: AsyncClient, admin_headers: dict[str, str], db_session: AsyncSession
) -> None:
    user = await make_user(db_session, is_active=False)

    response = await client.post(f"/api/admin/users/{user.id}/activate", headers=admin_headers)

    assert response.status_code == 200
    assert response.json()["is_active"] is True


async def test_temporary_password_replaces_old_one(
    client: AsyncClient, admin_headers: dict[str, str], db_session: AsyncSession
) -> None:
    user = await make_user(db_session)

    response = await client.post(
        f"/api/admin/users/{user.id}/temporary-password", headers=admin_headers
    )

    assert response.status_code == 200
    temporary = response.json()["temporary_password"]
    old = await client.post(
        "/api/auth/login", json={"email": user.email, "password": DEFAULT_PASSWORD}
    )
    new = await client.post("/api/auth/login", json={"email": user.email, "password": temporary})
    assert old.status_code == 401
    assert new.status_code == 200
    assert new.json()["must_change_password"] is True


async def test_unlock_login(
    client: AsyncClient,
    admin_headers: dict[str, str],
    db_session: AsyncSession,
    redis_client: Redis,
) -> None:
    user = await make_user(db_session)
    throttle = LoginThrottle(redis_client)
    for _ in range(5):
        await throttle.register_failure(user.email, "203.0.113.5")

    response = await client.post(
        f"/api/admin/users/{user.id}/unlock-login", headers=admin_headers
    )

    assert response.status_code == 204
    assert not await throttle.is_locked(user.email, "203.0.113.5")


async def test_user_lookup_returns_only_active_matches(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    employee = await make_user(db_session, full_name="Смирнов Алексей")
    await make_user(db_session, full_name="Смирнова Ольга", is_active=False)
    await make_user(db_session, full_name="Попов Игорь")

    response = await client.get(
        "/api/users", params={"q": "смирнов"}, headers=await login(client, employee.email)
    )

    assert response.status_code == 200
    assert [u["full_name"] for u in response.json()] == ["Смирнов Алексей"]
```

- [ ] **Step 2: Убедиться, что тесты падают**

Run: `uv run pytest tests/modules/users_auth/test_admin_users_api.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.modules.users_auth.events'`.

- [ ] **Step 3: Общие схемы и событие**

`backend/app/core/schemas.py`:
```python
from dataclasses import dataclass
from typing import Annotated, ClassVar, Generic, Self, TypeVar

from fastapi import Depends, Query
from pydantic import BaseModel, model_validator

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    limit: int
    offset: int


@dataclass(frozen=True)
class Pagination:
    limit: int
    offset: int


def get_pagination(
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> Pagination:
    return Pagination(limit=limit, offset=offset)


PaginationDep = Annotated[Pagination, Depends(get_pagination)]


class PartialUpdate(BaseModel):
    """Тело PATCH-запроса: переданы только изменяемые поля; для полей из non_nullable null запрещён."""

    non_nullable: ClassVar[frozenset[str]] = frozenset()

    @model_validator(mode="after")
    def _reject_nulls(self) -> Self:
        for field in self.model_fields_set & self.non_nullable:
            if getattr(self, field) is None:
                raise ValueError(f"Поле {field} не может быть пустым")
        return self
```

`backend/app/modules/users_auth/events.py`:
```python
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
```

- [ ] **Step 4: Логика управления пользователями**

Добавить в `backend/app/modules/users_auth/users.py` (импорты: `from dataclasses import asdict`, `Any` добавить в `from typing import NoReturn`, `from sqlalchemy import func, or_`, `from app.core.audit import diff_values`, `from app.core.events import event_bus`, `from app.core.errors import NotFoundError`, `from app.modules.users_auth.events import UserDeactivationRequested`, `from app.modules.users_auth.passwords import generate_temporary_password`):
```python
async def list_users(
    session: AsyncSession,
    *,
    q: str | None,
    role: UserRole | None,
    department_id: int | None,
    is_active: bool | None,
    limit: int,
    offset: int,
) -> tuple[list[User], int]:
    stmt = select(User)
    if q:
        pattern = f"%{q.strip()}%"
        stmt = stmt.where(or_(User.full_name.ilike(pattern), User.email.ilike(pattern)))
    if role is not None:
        stmt = stmt.where(User.role == role)
    if department_id is not None:
        stmt = stmt.where(User.department_id == department_id)
    if is_active is not None:
        stmt = stmt.where(User.is_active.is_(is_active))
    total = await session.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    items = await session.scalars(stmt.order_by(User.full_name, User.id).limit(limit).offset(offset))
    return list(items), total


async def search_active_users(session: AsyncSession, *, q: str, limit: int) -> list[User]:
    pattern = f"%{q.strip()}%"
    items = await session.scalars(
        select(User)
        .where(User.is_active.is_(True), or_(User.full_name.ilike(pattern), User.email.ilike(pattern)))
        .order_by(User.full_name, User.id)
        .limit(limit)
    )
    return list(items)


async def get_user_or_404(session: AsyncSession, user_id: int) -> User:
    user = await session.get(User, user_id)
    if user is None:
        raise NotFoundError("Пользователь не найден", code="user_not_found")
    return user


async def _ensure_not_last_admin(session: AsyncSession, user_id: int) -> None:
    other_admins = await session.scalar(
        select(func.count())
        .select_from(User)
        .where(User.role == UserRole.ADMIN, User.is_active.is_(True), User.id != user_id)
    )
    if not other_admins:
        raise ConflictError(
            "В системе должен оставаться хотя бы один активный администратор", code="last_admin"
        )


async def admin_create_user(
    session: AsyncSession,
    *,
    actor_id: int,
    email: str,
    full_name: str,
    role: UserRole,
    department_id: int | None,
) -> tuple[User, str]:
    temporary_password = generate_temporary_password()
    user = await create_user(
        session,
        email=email,
        full_name=full_name,
        role=role,
        department_id=department_id,
        password=temporary_password,
        must_change_password=True,
    )
    record_audit(
        session,
        entity_type="user",
        entity_id=user.id,
        user_id=actor_id,
        action="create",
        diff=diff_values(
            {}, {"email": user.email, "full_name": user.full_name, "role": user.role,
                 "department_id": user.department_id}
        ),
    )
    await session.commit()
    return user, temporary_password


async def update_user(
    session: AsyncSession, *, actor_id: int, user_id: int, updates: dict[str, Any]
) -> User:
    user = await get_user_or_404(session, user_id)
    if (
        "role" in updates
        and user.role == UserRole.ADMIN
        and updates["role"] != UserRole.ADMIN
        and user.is_active
    ):
        await _ensure_not_last_admin(session, user.id)
    before = {key: getattr(user, key) for key in updates}
    try:
        async with session.begin_nested():
            for key, value in updates.items():
                setattr(user, key, value)
    except IntegrityError as exc:
        raise_user_integrity_error(exc)
    diff = diff_values(before, updates)
    if diff:
        record_audit(
            session, entity_type="user", entity_id=user.id, user_id=actor_id, action="update",
            diff=diff,
        )
    await session.commit()
    return user


async def deactivate_user(session: AsyncSession, *, actor_id: int, user_id: int) -> User:
    user = await get_user_or_404(session, user_id)
    if user.id == actor_id:
        raise ConflictError(
            "Нельзя деактивировать собственную учётную запись", code="cannot_deactivate_self"
        )
    if not user.is_active:
        return user
    if user.role == UserRole.ADMIN:
        await _ensure_not_last_admin(session, user.id)
    event = UserDeactivationRequested(user_id=user.id)
    await event_bus.publish(session, event)
    if event.blockers:
        raise ConflictError(
            "Перед деактивацией нужно передать ответственность другим сотрудникам",
            code="deactivation_blocked",
            details=[asdict(blocker) for blocker in event.blockers],
        )
    # Импорт внутри функции: auth.py импортирует users.py.
    from app.modules.users_auth.auth import revoke_all_refresh_tokens

    user.is_active = False
    await revoke_all_refresh_tokens(session, user.id)
    record_audit(
        session, entity_type="user", entity_id=user.id, user_id=actor_id, action="deactivate",
        diff={"is_active": [True, False]},
    )
    await session.commit()
    return user


async def activate_user(session: AsyncSession, *, actor_id: int, user_id: int) -> User:
    user = await get_user_or_404(session, user_id)
    if user.is_active:
        return user
    user.is_active = True
    record_audit(
        session, entity_type="user", entity_id=user.id, user_id=actor_id, action="activate",
        diff={"is_active": [False, True]},
    )
    await session.commit()
    return user


async def issue_temporary_password(session: AsyncSession, *, actor_id: int, user_id: int) -> str:
    from app.modules.users_auth.auth import revoke_all_refresh_tokens

    user = await get_user_or_404(session, user_id)
    temporary_password = generate_temporary_password()
    user.password_hash = hash_password(temporary_password)
    user.must_change_password = True
    await revoke_all_refresh_tokens(session, user.id)
    record_audit(
        session, entity_type="user", entity_id=user.id, user_id=actor_id,
        action="temporary_password", diff={},
    )
    await session.commit()
    return temporary_password
```

- [ ] **Step 5: Схемы, роутеры, фасад**

Добавить в `backend/app/modules/users_auth/schemas.py` (импорты `from pydantic import EmailStr`, `from typing import ClassVar`, `from app.core.schemas import PartialUpdate`):
```python
class UserCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=255)
    role: UserRole
    department_id: int | None = None


class UserUpdate(PartialUpdate):
    non_nullable: ClassVar[frozenset[str]] = frozenset({"full_name", "role"})

    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    role: UserRole | None = None
    department_id: int | None = None


class UserCreatedResponse(BaseModel):
    user: UserRead
    temporary_password: str


class TemporaryPasswordResponse(BaseModel):
    temporary_password: str


class UserBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    department_id: int | None
```

Добавить в `backend/app/modules/users_auth/router.py` (импорты: `Query` из `fastapi`; `from app.core.schemas import Page, PaginationDep`; `from app.modules.users_auth import users`; `from app.modules.users_auth.deps import AdminDep, CurrentUserDep`; `from app.modules.users_auth.models import UserRole`; новые схемы):
```python
admin_users_router = APIRouter(prefix="/admin/users", tags=["admin: users"])
users_router = APIRouter(prefix="/users", tags=["users"])


@admin_users_router.get("", response_model=Page[UserRead])
async def list_users(
    session: SessionDep,
    admin: AdminDep,
    pagination: PaginationDep,
    q: Annotated[str | None, Query(max_length=100)] = None,
    role: UserRole | None = None,
    department_id: int | None = None,
    is_active: bool | None = None,
) -> Page[UserRead]:
    items, total = await users.list_users(
        session,
        q=q,
        role=role,
        department_id=department_id,
        is_active=is_active,
        limit=pagination.limit,
        offset=pagination.offset,
    )
    return Page(
        items=[UserRead.model_validate(item) for item in items],
        total=total,
        limit=pagination.limit,
        offset=pagination.offset,
    )


@admin_users_router.post("", response_model=UserCreatedResponse, status_code=201)
async def create_user(
    body: UserCreate, session: SessionDep, admin: AdminDep
) -> UserCreatedResponse:
    user, temporary_password = await users.admin_create_user(
        session,
        actor_id=admin.id,
        email=body.email,
        full_name=body.full_name,
        role=body.role,
        department_id=body.department_id,
    )
    return UserCreatedResponse(
        user=UserRead.model_validate(user), temporary_password=temporary_password
    )


@admin_users_router.get("/{user_id}", response_model=UserRead)
async def get_user(user_id: int, session: SessionDep, admin: AdminDep) -> UserRead:
    return UserRead.model_validate(await users.get_user_or_404(session, user_id))


@admin_users_router.patch("/{user_id}", response_model=UserRead)
async def update_user(
    user_id: int, body: UserUpdate, session: SessionDep, admin: AdminDep
) -> UserRead:
    user = await users.update_user(
        session, actor_id=admin.id, user_id=user_id, updates=body.model_dump(exclude_unset=True)
    )
    return UserRead.model_validate(user)


@admin_users_router.post("/{user_id}/deactivate", response_model=UserRead)
async def deactivate_user(user_id: int, session: SessionDep, admin: AdminDep) -> UserRead:
    user = await users.deactivate_user(session, actor_id=admin.id, user_id=user_id)
    return UserRead.model_validate(user)


@admin_users_router.post("/{user_id}/activate", response_model=UserRead)
async def activate_user(user_id: int, session: SessionDep, admin: AdminDep) -> UserRead:
    user = await users.activate_user(session, actor_id=admin.id, user_id=user_id)
    return UserRead.model_validate(user)


@admin_users_router.post("/{user_id}/temporary-password", response_model=TemporaryPasswordResponse)
async def issue_temporary_password(
    user_id: int, session: SessionDep, admin: AdminDep
) -> TemporaryPasswordResponse:
    password = await users.issue_temporary_password(session, actor_id=admin.id, user_id=user_id)
    return TemporaryPasswordResponse(temporary_password=password)


@admin_users_router.post("/{user_id}/unlock-login", status_code=204)
async def unlock_login(
    user_id: int, session: SessionDep, redis: RedisDep, admin: AdminDep
) -> Response:
    user = await users.get_user_or_404(session, user_id)
    await LoginThrottle(redis).unlock_account(user.email)
    return Response(status_code=204)


@users_router.get("", response_model=list[UserBrief])
async def search_users(
    session: SessionDep,
    user: CurrentUserDep,
    q: Annotated[str, Query(min_length=1, max_length=100)],
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
) -> list[UserBrief]:
    found = await users.search_active_users(session, q=q, limit=limit)
    return [UserBrief.model_validate(item) for item in found]
```

В `backend/app/main.py` импортировать `admin_users_router`, `users_router` и подключить оба с `prefix="/api"`.

Добавить в `backend/app/modules/users_auth/service.py`:
```python
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.users_auth.models import User


@dataclass(frozen=True)
class UserInfo:
    id: int
    email: str
    full_name: str
    role: UserRole
    department_id: int | None
    is_active: bool


async def get_user_info(session: AsyncSession, user_id: int) -> UserInfo | None:
    user = await session.get(User, user_id)
    if user is None:
        return None
    return UserInfo(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        department_id=user.department_id,
        is_active=user.is_active,
    )
```
и дополнить `__all__` значениями `"UserInfo"`, `"get_user_info"`. (Импорты — в общий блок импортов файла.)

- [ ] **Step 6: Прогнать тесты и проверки**

Run: `uv run pytest -q && uv run mypy app tests && uv run lint-imports`
Expected: всё проходит.

- [ ] **Step 7: Commit**

```bash
git add backend
git commit -m "feat: администрирование пользователей, временные пароли, снятие блокировки входа"
```

---

### Task 10: Отделы и руководители

**Files:**
- Create: `backend/app/modules/directories/__init__.py`, `models.py`, `schemas.py`, `departments.py`, `events.py`, `handlers.py`, `router.py`, `service.py`
- Create: `backend/migrations/versions/0003_departments.py`
- Modify: `backend/app/modules/users_auth/models.py` (FK `department_id`), `backend/app/model_registry.py`, `backend/app/wiring.py`, `backend/app/main.py`, `backend/pyproject.toml`
- Test: `backend/tests/modules/directories/__init__.py`, `backend/tests/modules/directories/test_departments_api.py`

**Interfaces:**
- Consumes: `users_auth.service.get_user_info`, `UserRole`, `AdminDep`, `CurrentUserDep`, `users_auth.events.UserDeactivationRequested`, `DeactivationBlocker`, `event_bus`, `PartialUpdate`.
- Produces:
  - `models.Department(id, name, head_id)` в `common.departments`.
  - `events.DepartmentHeadChanged(department_id: int, old_head_id: int | None, new_head_id: int | None)` — модуль `tickets` подпишется, чтобы переназначать согласующего (п. 2.3).
  - Обработчик: руководитель отдела не может быть деактивирован (блокер `kind="department_head"`).
  - `service.DepartmentInfo(id, name, head_id)`; `async service.get_department(session, department_id) -> DepartmentInfo | None`.
  - Эндпоинты: `GET /api/departments` (любой вошедший), `POST /api/admin/departments` (201), `PATCH /api/admin/departments/{id}`.
  - Правила: название уникально (`department_name_taken`, 409); руководитель — активный пользователь с ролью Manager или Admin (`head_not_found` / `head_invalid_role`, 422). Отделы не удаляются.
  - Зависимость только в одну сторону: `directories` → `users_auth`.

- [ ] **Step 1: Написать падающие тесты**

Пустой `backend/tests/modules/directories/__init__.py`.

`backend/tests/modules/directories/test_departments_api.py`:
```python
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.events import event_bus
from app.modules.directories.events import DepartmentHeadChanged
from app.modules.users_auth.models import UserRole
from tests.factories import login, make_user


async def _create_department(
    client: AsyncClient, headers: dict[str, str], name: str, head_id: int | None = None
) -> dict[str, object]:
    response = await client.post(
        "/api/admin/departments", headers=headers, json={"name": name, "head_id": head_id}
    )
    assert response.status_code == 201, response.text
    return dict(response.json())


async def test_admin_creates_department_and_employee_lists_it(
    client: AsyncClient, admin_headers: dict[str, str], db_session: AsyncSession
) -> None:
    head = await make_user(db_session, role=UserRole.MANAGER)
    employee = await make_user(db_session)

    created = await _create_department(client, admin_headers, "Бухгалтерия", head.id)
    listed = await client.get("/api/departments", headers=await login(client, employee.email))

    assert created["head_id"] == head.id
    assert listed.status_code == 200
    assert {"id": created["id"], "name": "Бухгалтерия", "head_id": head.id} in listed.json()


async def test_employee_cannot_create_department(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    employee = await make_user(db_session)

    response = await client.post(
        "/api/admin/departments",
        headers=await login(client, employee.email),
        json={"name": "Склад"},
    )

    assert response.status_code == 403


async def test_duplicate_department_name_returns_409(
    client: AsyncClient, admin_headers: dict[str, str]
) -> None:
    await _create_department(client, admin_headers, "Склад")

    response = await client.post(
        "/api/admin/departments", headers=admin_headers, json={"name": "Склад"}
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "department_name_taken"


async def test_head_must_be_active_manager_or_admin(
    client: AsyncClient, admin_headers: dict[str, str], db_session: AsyncSession
) -> None:
    employee = await make_user(db_session, role=UserRole.EMPLOYEE)

    wrong_role = await client.post(
        "/api/admin/departments",
        headers=admin_headers,
        json={"name": "Отдел продаж", "head_id": employee.id},
    )
    missing = await client.post(
        "/api/admin/departments",
        headers=admin_headers,
        json={"name": "Отдел продаж", "head_id": 999999},
    )

    assert wrong_role.status_code == 422
    assert wrong_role.json()["error"]["code"] == "head_invalid_role"
    assert missing.status_code == 422
    assert missing.json()["error"]["code"] == "head_not_found"


async def test_head_change_publishes_event(
    client: AsyncClient, admin_headers: dict[str, str], db_session: AsyncSession
) -> None:
    old_head = await make_user(db_session, role=UserRole.MANAGER)
    new_head = await make_user(db_session, role=UserRole.MANAGER)
    department = await _create_department(client, admin_headers, "Логистика", old_head.id)
    received: list[DepartmentHeadChanged] = []

    async def capture(session: AsyncSession, event: DepartmentHeadChanged) -> None:
        received.append(event)

    event_bus.subscribe(DepartmentHeadChanged)(capture)
    try:
        response = await client.patch(
            f"/api/admin/departments/{department['id']}",
            headers=admin_headers,
            json={"head_id": new_head.id},
        )
        unchanged = await client.patch(
            f"/api/admin/departments/{department['id']}",
            headers=admin_headers,
            json={"name": "Логистика и склад"},
        )
    finally:
        event_bus.unsubscribe(DepartmentHeadChanged, capture)

    assert response.status_code == 200
    assert unchanged.status_code == 200
    assert received == [
        DepartmentHeadChanged(
            department_id=int(str(department["id"])),
            old_head_id=old_head.id,
            new_head_id=new_head.id,
        )
    ]


async def test_department_head_cannot_be_deactivated(
    client: AsyncClient, admin_headers: dict[str, str], db_session: AsyncSession
) -> None:
    head = await make_user(db_session, role=UserRole.MANAGER)
    department = await _create_department(client, admin_headers, "Юристы", head.id)

    response = await client.post(f"/api/admin/users/{head.id}/deactivate", headers=admin_headers)

    assert response.status_code == 409
    assert response.json()["error"]["details"] == [
        {
            "kind": "department_head",
            "entity_id": department["id"],
            "title": "Руководитель отдела «Юристы»",
        }
    ]


async def test_user_with_unknown_department_rejected(
    client: AsyncClient, admin_headers: dict[str, str]
) -> None:
    response = await client.post(
        "/api/admin/users",
        headers=admin_headers,
        json={
            "email": "new@company.ru",
            "full_name": "Новый Сотрудник",
            "role": "employee",
            "department_id": 999999,
        },
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "department_not_found"
```

- [ ] **Step 2: Убедиться, что тесты падают**

Run: `uv run pytest tests/modules/directories -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.modules.directories'`.

- [ ] **Step 3: Модель и миграция**

`backend/app/modules/directories/__init__.py` — пустой.

`backend/app/modules/directories/models.py`:
```python
from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Department(Base):
    __tablename__ = "departments"
    __table_args__ = {"schema": "common"}

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True)
    head_id: Mapped[int | None] = mapped_column(ForeignKey("common.users.id"))
```

В `backend/app/modules/users_auth/models.py` заменить объявление `department_id` (добавить `ForeignKey` уже импортирован):
```python
    department_id: Mapped[int | None] = mapped_column(ForeignKey("common.departments.id"))
```

`backend/app/model_registry.py` — добавить:
```python
from app.modules.directories import models as directories_models  # noqa: F401
```

`backend/migrations/versions/0003_departments.py`:
```python
"""Отделы

Revision ID: 0003
Revises: 0002
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "departments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("head_id", sa.Integer(), nullable=True),
        sa.UniqueConstraint("name", name="uq_departments_name"),
        sa.ForeignKeyConstraint(
            ["head_id"], ["common.users.id"], name="fk_departments_head_id_users"
        ),
        schema="common",
    )
    op.create_foreign_key(
        "fk_users_department_id_departments",
        "users",
        "departments",
        ["department_id"],
        ["id"],
        source_schema="common",
        referent_schema="common",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_users_department_id_departments", "users", schema="common", type_="foreignkey"
    )
    op.drop_table("departments", schema="common")
```

- [ ] **Step 4: Логика, события, обработчик, роутер, фасад**

`backend/app/modules/directories/events.py`:
```python
from dataclasses import dataclass

from app.core.events import DomainEvent


@dataclass(frozen=True)
class DepartmentHeadChanged(DomainEvent):
    department_id: int
    old_head_id: int | None
    new_head_id: int | None
```

`backend/app/modules/directories/departments.py`:
```python
from typing import Any, NoReturn

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import diff_values, record_audit
from app.core.db import constraint_name
from app.core.errors import ConflictError, NotFoundError, ValidationFailedError
from app.core.events import event_bus
from app.modules.directories.events import DepartmentHeadChanged
from app.modules.directories.models import Department
from app.modules.users_auth.service import UserRole, get_user_info

_HEAD_ROLES = frozenset({UserRole.MANAGER, UserRole.ADMIN})


def _raise_integrity_error(exc: IntegrityError) -> NoReturn:
    if constraint_name(exc) == "uq_departments_name":
        raise ConflictError(
            "Отдел с таким названием уже существует", code="department_name_taken"
        ) from exc
    raise exc


async def _validate_head(session: AsyncSession, user_id: int) -> None:
    info = await get_user_info(session, user_id)
    if info is None or not info.is_active:
        raise ValidationFailedError(
            "Руководитель не найден или деактивирован", code="head_not_found"
        )
    if info.role not in _HEAD_ROLES:
        raise ValidationFailedError(
            "Руководителем отдела может быть только Manager или Admin", code="head_invalid_role"
        )


async def list_departments(session: AsyncSession) -> list[Department]:
    return list(await session.scalars(select(Department).order_by(Department.name)))


async def create_department(
    session: AsyncSession, *, actor_id: int, name: str, head_id: int | None
) -> Department:
    if head_id is not None:
        await _validate_head(session, head_id)
    department = Department(name=name.strip(), head_id=head_id)
    try:
        async with session.begin_nested():
            session.add(department)
    except IntegrityError as exc:
        _raise_integrity_error(exc)
    record_audit(
        session,
        entity_type="department",
        entity_id=department.id,
        user_id=actor_id,
        action="create",
        diff=diff_values({}, {"name": department.name, "head_id": head_id}),
    )
    await session.commit()
    return department


async def update_department(
    session: AsyncSession, *, actor_id: int, department_id: int, updates: dict[str, Any]
) -> Department:
    department = await session.get(Department, department_id)
    if department is None:
        raise NotFoundError("Отдел не найден", code="department_not_found")
    if updates.get("head_id") is not None:
        await _validate_head(session, updates["head_id"])
    before = {key: getattr(department, key) for key in updates}
    try:
        async with session.begin_nested():
            for key, value in updates.items():
                setattr(department, key, value)
    except IntegrityError as exc:
        _raise_integrity_error(exc)
    if "head_id" in updates and before["head_id"] != department.head_id:
        await event_bus.publish(
            session,
            DepartmentHeadChanged(
                department_id=department.id,
                old_head_id=before["head_id"],
                new_head_id=department.head_id,
            ),
        )
    diff = diff_values(before, updates)
    if diff:
        record_audit(
            session,
            entity_type="department",
            entity_id=department.id,
            user_id=actor_id,
            action="update",
            diff=diff,
        )
    await session.commit()
    return department
```

`backend/app/modules/directories/handlers.py`:
```python
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
```

`backend/app/modules/directories/schemas.py`:
```python
from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field

from app.core.schemas import PartialUpdate


class DepartmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    head_id: int | None


class DepartmentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    head_id: int | None = None


class DepartmentUpdate(PartialUpdate):
    non_nullable: ClassVar[frozenset[str]] = frozenset({"name"})

    name: str | None = Field(default=None, min_length=1, max_length=255)
    head_id: int | None = None
```

`backend/app/modules/directories/router.py`:
```python
from fastapi import APIRouter

from app.core.db import SessionDep
from app.modules.directories import departments
from app.modules.directories.schemas import DepartmentCreate, DepartmentRead, DepartmentUpdate
from app.modules.users_auth.service import AdminDep, CurrentUserDep

departments_router = APIRouter(prefix="/departments", tags=["departments"])
admin_departments_router = APIRouter(prefix="/admin/departments", tags=["admin: departments"])


@departments_router.get("", response_model=list[DepartmentRead])
async def list_departments(session: SessionDep, user: CurrentUserDep) -> list[DepartmentRead]:
    items = await departments.list_departments(session)
    return [DepartmentRead.model_validate(item) for item in items]


@admin_departments_router.post("", response_model=DepartmentRead, status_code=201)
async def create_department(
    body: DepartmentCreate, session: SessionDep, admin: AdminDep
) -> DepartmentRead:
    department = await departments.create_department(
        session, actor_id=admin.id, name=body.name, head_id=body.head_id
    )
    return DepartmentRead.model_validate(department)


@admin_departments_router.patch("/{department_id}", response_model=DepartmentRead)
async def update_department(
    department_id: int, body: DepartmentUpdate, session: SessionDep, admin: AdminDep
) -> DepartmentRead:
    department = await departments.update_department(
        session,
        actor_id=admin.id,
        department_id=department_id,
        updates=body.model_dump(exclude_unset=True),
    )
    return DepartmentRead.model_validate(department)


routers = [departments_router, admin_departments_router]
```

`backend/app/modules/directories/service.py`:
```python
"""Публичный интерфейс модуля directories. Другие модули импортируют только этот файл и events.py."""

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.directories.models import Department


@dataclass(frozen=True)
class DepartmentInfo:
    id: int
    name: str
    head_id: int | None


async def get_department(session: AsyncSession, department_id: int) -> DepartmentInfo | None:
    department = await session.get(Department, department_id)
    if department is None:
        return None
    return DepartmentInfo(id=department.id, name=department.name, head_id=department.head_id)


__all__ = ["DepartmentInfo", "get_department"]
```

`backend/app/wiring.py` — заменить кортеж:
```python
HANDLER_MODULES: tuple[str, ...] = ("app.modules.directories.handlers",)
```

`backend/app/main.py` — импортировать `from app.modules.directories.router import routers as directories_routers` и после подключения роутеров `users_auth` добавить:
```python
    for router in directories_routers:
        app.include_router(router, prefix="/api")
```

В `backend/pyproject.toml`: раскомментировать контракт `users_auth` из Task 6 и добавить:
```toml
[[tool.importlinter.contracts]]
name = "users_auth не зависит от directories (связь только через события)"
type = "forbidden"
source_modules = ["app.modules.users_auth"]
forbidden_modules = ["app.modules.directories"]

[[tool.importlinter.contracts]]
name = "Другие модули используют directories только через service и events"
type = "forbidden"
source_modules = ["app.modules.users_auth"]
forbidden_modules = [
    "app.modules.directories.models",
    "app.modules.directories.schemas",
    "app.modules.directories.departments",
    "app.modules.directories.handlers",
    "app.modules.directories.router",
]
allow_indirect_imports = true
```
Модули `reference`, `references`, `reference_router` добавляются в `forbidden_modules` в Task 11, когда появятся (import-linter не принимает несуществующие модули). При добавлении новых модулей (`assets`, `tickets`, …) их имена дописываются в `source_modules` обоих контрактов «только через service и events».

- [ ] **Step 5: Прогнать тесты и проверки**

Run: `uv run pytest -q && uv run mypy app tests && uv run lint-imports`
Expected: всё проходит; `Contracts: 4 kept, 0 broken.`

- [ ] **Step 6: Commit**

```bash
git add backend
git commit -m "feat: отделы, руководители и событие смены руководителя"
```

---

### Task 11: Справочники — локации, типы техники, категории расходников, причины выдачи, типы заявок

**Files:**
- Modify: `backend/app/modules/directories/models.py`, `schemas.py`, `router.py`
- Create: `backend/app/modules/directories/reference.py`, `references.py`, `reference_router.py`
- Create: `backend/migrations/versions/0004_reference_directories.py`
- Modify: `backend/pyproject.toml` (контракт и mypy-override)
- Test: `backend/tests/modules/directories/test_reference_api.py`

**Interfaces:**
- Consumes: `get_user_info`, `UserRole`, `AdminDep`, `CurrentUserDep`, `record_audit`, `diff_values`, `constraint_name`, `PartialUpdate`.
- Produces:
  - Модели в схеме `common`: `Location(id, name, description, is_active)`, `AssetType(id, name, is_active)`, `StockCategory(id, name, is_active)`, `IssueReason(id, name, applicability, is_active)` с `IssueReasonApplicability(StrEnum)`: `ASSETS="assets"`, `STOCK="stock"`, `BOTH="both"`; `TicketType(id, code, name, requires_approval, default_assignee_id, is_active)`.
  - `reference.ReferenceSpec(slug, model, read_schema, create_schema, update_schema, entity_type, validate=None)`; `async list_items(session, spec, *, include_inactive) -> list[Any]`; `async create_item(session, spec, *, actor_id, data) -> Any`; `async update_item(session, spec, *, actor_id, item_id, updates) -> Any`.
  - `references.REFERENCE_SPECS` — кортеж из пяти спецификаций со слагами `locations`, `asset-types`, `stock-categories`, `issue-reasons`, `ticket-types`.
  - `reference_router.build_reference_routers(spec) -> list[APIRouter]`.
  - Эндпоинты для каждого `<slug>`: `GET /api/directories/<slug>?include_inactive=` (любой вошедший; неактивные видит только Admin), `POST /api/admin/directories/<slug>` (201), `PATCH /api/admin/directories/<slug>/{id}` (включая `is_active`). Удаления нет.
  - Ошибки: дубликат — 409 `already_exists`; исполнитель по умолчанию у типа заявки — активный Manager/Admin, иначе 422 `invalid_default_assignee`.

- [ ] **Step 1: Написать падающие тесты**

`backend/tests/modules/directories/test_reference_api.py`:
```python
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import AuditLog
from app.modules.users_auth.models import UserRole
from tests.factories import login, make_user

PAYLOADS: dict[str, dict[str, Any]] = {
    "locations": {"name": "Главный офис, каб. 101", "description": "3 этаж"},
    "asset-types": {"name": "Ноутбук"},
    "stock-categories": {"name": "Картриджи"},
    "issue-reasons": {"name": "Новый сотрудник", "applicability": "both"},
    "ticket-types": {"code": "repair", "name": "На ремонт", "requires_approval": False},
}


@pytest.mark.parametrize("slug", list(PAYLOADS))
async def test_reference_lifecycle(
    slug: str, client: AsyncClient, admin_headers: dict[str, str], db_session: AsyncSession
) -> None:
    employee = await make_user(db_session)
    employee_headers = await login(client, employee.email)

    created = await client.post(
        f"/api/admin/directories/{slug}", headers=admin_headers, json=PAYLOADS[slug]
    )
    assert created.status_code == 201, created.text
    item_id = created.json()["id"]
    assert created.json()["is_active"] is True

    visible = await client.get(f"/api/directories/{slug}", headers=employee_headers)
    assert item_id in [item["id"] for item in visible.json()]

    deactivated = await client.patch(
        f"/api/admin/directories/{slug}/{item_id}", headers=admin_headers, json={"is_active": False}
    )
    assert deactivated.status_code == 200
    assert deactivated.json()["is_active"] is False

    hidden = await client.get(
        f"/api/directories/{slug}", headers=employee_headers, params={"include_inactive": True}
    )
    assert item_id not in [item["id"] for item in hidden.json()]
    for_admin = await client.get(
        f"/api/directories/{slug}", headers=admin_headers, params={"include_inactive": True}
    )
    assert item_id in [item["id"] for item in for_admin.json()]

    audit = await db_session.scalars(
        select(AuditLog.action).where(AuditLog.entity_id == str(item_id))
    )
    assert {"create", "update"} <= set(audit)


@pytest.mark.parametrize("slug", list(PAYLOADS))
async def test_duplicate_returns_409(
    slug: str, client: AsyncClient, admin_headers: dict[str, str]
) -> None:
    first = await client.post(
        f"/api/admin/directories/{slug}", headers=admin_headers, json=PAYLOADS[slug]
    )
    assert first.status_code == 201

    second = await client.post(
        f"/api/admin/directories/{slug}", headers=admin_headers, json=PAYLOADS[slug]
    )

    assert second.status_code == 409
    assert second.json()["error"]["code"] == "already_exists"


async def test_employee_cannot_modify_directories(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    employee = await make_user(db_session)

    response = await client.post(
        "/api/admin/directories/locations",
        headers=await login(client, employee.email),
        json={"name": "Склад"},
    )

    assert response.status_code == 403


async def test_rename_rejects_null_name(
    client: AsyncClient, admin_headers: dict[str, str]
) -> None:
    created = await client.post(
        "/api/admin/directories/asset-types", headers=admin_headers, json={"name": "Монитор"}
    )

    response = await client.patch(
        f"/api/admin/directories/asset-types/{created.json()['id']}",
        headers=admin_headers,
        json={"name": None},
    )

    assert response.status_code == 422


async def test_issue_reason_rejects_unknown_applicability(
    client: AsyncClient, admin_headers: dict[str, str]
) -> None:
    response = await client.post(
        "/api/admin/directories/issue-reasons",
        headers=admin_headers,
        json={"name": "Замена", "applicability": "everything"},
    )

    assert response.status_code == 422


async def test_ticket_type_requires_approval_by_default(
    client: AsyncClient, admin_headers: dict[str, str]
) -> None:
    response = await client.post(
        "/api/admin/directories/ticket-types",
        headers=admin_headers,
        json={"code": "equipment", "name": "На выдачу техники"},
    )

    assert response.status_code == 201
    assert response.json()["requires_approval"] is True
    assert response.json()["default_assignee_id"] is None


async def test_ticket_type_default_assignee_must_be_manager_or_admin(
    client: AsyncClient, admin_headers: dict[str, str], db_session: AsyncSession
) -> None:
    employee = await make_user(db_session, role=UserRole.EMPLOYEE)
    manager = await make_user(db_session, role=UserRole.MANAGER)

    rejected = await client.post(
        "/api/admin/directories/ticket-types",
        headers=admin_headers,
        json={"code": "supplies", "name": "На расходники", "default_assignee_id": employee.id},
    )
    accepted = await client.post(
        "/api/admin/directories/ticket-types",
        headers=admin_headers,
        json={"code": "supplies", "name": "На расходники", "default_assignee_id": manager.id},
    )

    assert rejected.status_code == 422
    assert rejected.json()["error"]["code"] == "invalid_default_assignee"
    assert accepted.status_code == 201
    assert accepted.json()["default_assignee_id"] == manager.id
```

- [ ] **Step 2: Убедиться, что тесты падают**

Run: `uv run pytest tests/modules/directories/test_reference_api.py -q`
Expected: FAIL — `404 Not Found` на `/api/admin/directories/...` (assert 201).

- [ ] **Step 3: Модели и миграция**

Добавить в `backend/app/modules/directories/models.py` (импорты: `from enum import StrEnum`, `Boolean`, `Text`, `Enum as SAEnum` из `sqlalchemy`):
```python
class Location(Base):
    __tablename__ = "locations"
    __table_args__ = {"schema": "common"}

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True)
    description: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class AssetType(Base):
    __tablename__ = "asset_types"
    __table_args__ = {"schema": "common"}

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class StockCategory(Base):
    __tablename__ = "stock_categories"
    __table_args__ = {"schema": "common"}

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class IssueReasonApplicability(StrEnum):
    ASSETS = "assets"
    STOCK = "stock"
    BOTH = "both"


class IssueReason(Base):
    __tablename__ = "issue_reasons"
    __table_args__ = {"schema": "common"}

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True)
    applicability: Mapped[IssueReasonApplicability] = mapped_column(
        SAEnum(
            IssueReasonApplicability,
            native_enum=False,
            length=16,
            values_callable=lambda enum: [member.value for member in enum],
        )
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class TicketType(Base):
    __tablename__ = "ticket_types"
    __table_args__ = {"schema": "common"}

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(64), unique=True)
    name: Mapped[str] = mapped_column(String(255), unique=True)
    requires_approval: Mapped[bool] = mapped_column(Boolean, default=True)
    default_assignee_id: Mapped[int | None] = mapped_column(ForeignKey("common.users.id"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
```

`backend/migrations/versions/0004_reference_directories.py`:
```python
"""Справочники: локации, типы техники, категории расходников, причины выдачи, типы заявок

Revision ID: 0004
Revises: 0003
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _is_active() -> sa.Column[bool]:
    return sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true())


def upgrade() -> None:
    op.create_table(
        "locations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        _is_active(),
        sa.UniqueConstraint("name", name="uq_locations_name"),
        schema="common",
    )
    for table in ("asset_types", "stock_categories"):
        op.create_table(
            table,
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("name", sa.String(255), nullable=False),
            _is_active(),
            sa.UniqueConstraint("name", name=f"uq_{table}_name"),
            schema="common",
        )
    op.create_table(
        "issue_reasons",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("applicability", sa.String(16), nullable=False),
        _is_active(),
        sa.UniqueConstraint("name", name="uq_issue_reasons_name"),
        sa.CheckConstraint(
            "applicability IN ('assets', 'stock', 'both')", name="ck_issue_reasons_applicability"
        ),
        schema="common",
    )
    op.create_table(
        "ticket_types",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("requires_approval", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("default_assignee_id", sa.Integer(), nullable=True),
        _is_active(),
        sa.UniqueConstraint("code", name="uq_ticket_types_code"),
        sa.UniqueConstraint("name", name="uq_ticket_types_name"),
        sa.ForeignKeyConstraint(
            ["default_assignee_id"],
            ["common.users.id"],
            name="fk_ticket_types_default_assignee_id_users",
        ),
        schema="common",
    )


def downgrade() -> None:
    for table in ("ticket_types", "issue_reasons", "stock_categories", "asset_types", "locations"):
        op.drop_table(table, schema="common")
```

- [ ] **Step 4: Схемы**

Добавить в `backend/app/modules/directories/schemas.py` (импорт `from app.modules.directories.models import IssueReasonApplicability`):
```python
class LocationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    is_active: bool


class LocationCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=2000)


class LocationUpdate(PartialUpdate):
    non_nullable: ClassVar[frozenset[str]] = frozenset({"name", "is_active"})

    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=2000)
    is_active: bool | None = None


class NamedItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    is_active: bool


class AssetTypeRead(NamedItemRead):
    pass


class StockCategoryRead(NamedItemRead):
    pass


class AssetTypeCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class StockCategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class AssetTypeUpdate(PartialUpdate):
    non_nullable: ClassVar[frozenset[str]] = frozenset({"name", "is_active"})

    name: str | None = Field(default=None, min_length=1, max_length=255)
    is_active: bool | None = None


class StockCategoryUpdate(AssetTypeUpdate):
    pass


class IssueReasonRead(NamedItemRead):
    applicability: IssueReasonApplicability


class IssueReasonCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    applicability: IssueReasonApplicability


class IssueReasonUpdate(PartialUpdate):
    non_nullable: ClassVar[frozenset[str]] = frozenset({"name", "applicability", "is_active"})

    name: str | None = Field(default=None, min_length=1, max_length=255)
    applicability: IssueReasonApplicability | None = None
    is_active: bool | None = None


class TicketTypeRead(NamedItemRead):
    code: str
    requires_approval: bool
    default_assignee_id: int | None


class TicketTypeCreate(BaseModel):
    code: str = Field(min_length=1, max_length=64, pattern=r"^[a-z0-9_-]+$")
    name: str = Field(min_length=1, max_length=255)
    requires_approval: bool = True
    default_assignee_id: int | None = None


class TicketTypeUpdate(PartialUpdate):
    non_nullable: ClassVar[frozenset[str]] = frozenset({"name", "requires_approval", "is_active"})

    name: str | None = Field(default=None, min_length=1, max_length=255)
    requires_approval: bool | None = None
    default_assignee_id: int | None = None
    is_active: bool | None = None
```
Код типа заявки после создания не меняется: на него опирается бизнес-логика модуля `tickets`.

- [ ] **Step 5: Универсальная логика и роутеры**

`backend/app/modules/directories/reference.py`:
```python
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, NoReturn

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import diff_values, record_audit
from app.core.db import constraint_name
from app.core.errors import ConflictError, NotFoundError, ValidationFailedError

Validator = Callable[[AsyncSession, dict[str, Any]], Awaitable[None]]


@dataclass(frozen=True)
class ReferenceSpec:
    slug: str
    model: type[Any]
    read_schema: type[BaseModel]
    create_schema: type[BaseModel]
    update_schema: type[BaseModel]
    entity_type: str
    validate: Validator | None = None


def _raise_integrity_error(exc: IntegrityError) -> NoReturn:
    name = constraint_name(exc) or ""
    if name.startswith("uq_"):
        raise ConflictError(
            "Элемент с таким значением уже существует",
            code="already_exists",
            details={"constraint": name},
        ) from exc
    if name.startswith("fk_"):
        raise ValidationFailedError(
            "Связанная запись не найдена", code="reference_not_found"
        ) from exc
    raise exc


async def list_items(
    session: AsyncSession, spec: ReferenceSpec, *, include_inactive: bool
) -> list[Any]:
    stmt = select(spec.model).order_by(spec.model.name, spec.model.id)
    if not include_inactive:
        stmt = stmt.where(spec.model.is_active.is_(True))
    return list(await session.scalars(stmt))


async def create_item(
    session: AsyncSession, spec: ReferenceSpec, *, actor_id: int, data: dict[str, Any]
) -> Any:
    if spec.validate is not None:
        await spec.validate(session, data)
    item = spec.model(**data)
    try:
        async with session.begin_nested():
            session.add(item)
    except IntegrityError as exc:
        _raise_integrity_error(exc)
    record_audit(
        session,
        entity_type=spec.entity_type,
        entity_id=item.id,
        user_id=actor_id,
        action="create",
        diff=diff_values({}, data),
    )
    await session.commit()
    return item


async def update_item(
    session: AsyncSession,
    spec: ReferenceSpec,
    *,
    actor_id: int,
    item_id: int,
    updates: dict[str, Any],
) -> Any:
    item = await session.get(spec.model, item_id)
    if item is None:
        raise NotFoundError("Элемент справочника не найден", code="reference_item_not_found")
    if spec.validate is not None:
        await spec.validate(session, updates)
    before = {key: getattr(item, key) for key in updates}
    try:
        async with session.begin_nested():
            for key, value in updates.items():
                setattr(item, key, value)
    except IntegrityError as exc:
        _raise_integrity_error(exc)
    diff = diff_values(before, updates)
    if diff:
        record_audit(
            session,
            entity_type=spec.entity_type,
            entity_id=item.id,
            user_id=actor_id,
            action="update",
            diff=diff,
        )
    await session.commit()
    return item
```

`backend/app/modules/directories/references.py`:
```python
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ValidationFailedError
from app.modules.directories import schemas
from app.modules.directories.models import (
    AssetType,
    IssueReason,
    Location,
    StockCategory,
    TicketType,
)
from app.modules.directories.reference import ReferenceSpec
from app.modules.users_auth.service import UserRole, get_user_info

_ASSIGNEE_ROLES = frozenset({UserRole.MANAGER, UserRole.ADMIN})


async def validate_ticket_type(session: AsyncSession, data: dict[str, Any]) -> None:
    assignee_id = data.get("default_assignee_id")
    if assignee_id is None:
        return
    info = await get_user_info(session, assignee_id)
    if info is None or not info.is_active or info.role not in _ASSIGNEE_ROLES:
        raise ValidationFailedError(
            "Исполнителем по умолчанию может быть только активный Manager или Admin",
            code="invalid_default_assignee",
        )


REFERENCE_SPECS: tuple[ReferenceSpec, ...] = (
    ReferenceSpec(
        slug="locations",
        model=Location,
        read_schema=schemas.LocationRead,
        create_schema=schemas.LocationCreate,
        update_schema=schemas.LocationUpdate,
        entity_type="location",
    ),
    ReferenceSpec(
        slug="asset-types",
        model=AssetType,
        read_schema=schemas.AssetTypeRead,
        create_schema=schemas.AssetTypeCreate,
        update_schema=schemas.AssetTypeUpdate,
        entity_type="asset_type",
    ),
    ReferenceSpec(
        slug="stock-categories",
        model=StockCategory,
        read_schema=schemas.StockCategoryRead,
        create_schema=schemas.StockCategoryCreate,
        update_schema=schemas.StockCategoryUpdate,
        entity_type="stock_category",
    ),
    ReferenceSpec(
        slug="issue-reasons",
        model=IssueReason,
        read_schema=schemas.IssueReasonRead,
        create_schema=schemas.IssueReasonCreate,
        update_schema=schemas.IssueReasonUpdate,
        entity_type="issue_reason",
    ),
    ReferenceSpec(
        slug="ticket-types",
        model=TicketType,
        read_schema=schemas.TicketTypeRead,
        create_schema=schemas.TicketTypeCreate,
        update_schema=schemas.TicketTypeUpdate,
        entity_type="ticket_type",
        validate=validate_ticket_type,
    ),
)
```

`backend/app/modules/directories/reference_router.py` (без `from __future__ import annotations`: FastAPI читает аннотации, ссылающиеся на локальные переменные):
```python
from typing import Any

from fastapi import APIRouter

from app.core.db import SessionDep
from app.modules.directories import reference
from app.modules.directories.reference import ReferenceSpec
from app.modules.users_auth.service import AdminDep, CurrentUserDep, UserRole


def build_reference_routers(spec: ReferenceSpec) -> list[APIRouter]:
    read_schema = spec.read_schema
    create_schema = spec.create_schema
    update_schema = spec.update_schema
    operation = spec.slug.replace("-", "_")

    public = APIRouter(prefix=f"/directories/{spec.slug}", tags=["directories"])
    admin = APIRouter(prefix=f"/admin/directories/{spec.slug}", tags=["admin: directories"])

    @public.get(
        "",
        response_model=list[read_schema],  # type: ignore[valid-type]
        operation_id=f"list_{operation}",
    )
    async def list_items(
        session: SessionDep, user: CurrentUserDep, include_inactive: bool = False
    ) -> Any:
        return await reference.list_items(
            session, spec, include_inactive=include_inactive and user.role == UserRole.ADMIN
        )

    @admin.post(
        "", response_model=read_schema, status_code=201, operation_id=f"create_{operation}"
    )
    async def create_item(
        body: create_schema,  # type: ignore[valid-type]
        session: SessionDep,
        admin_user: AdminDep,
    ) -> Any:
        return await reference.create_item(
            session, spec, actor_id=admin_user.id, data=body.model_dump()
        )

    @admin.patch("/{item_id}", response_model=read_schema, operation_id=f"update_{operation}")
    async def update_item(
        item_id: int,
        body: update_schema,  # type: ignore[valid-type]
        session: SessionDep,
        admin_user: AdminDep,
    ) -> Any:
        return await reference.update_item(
            session,
            spec,
            actor_id=admin_user.id,
            item_id=item_id,
            updates=body.model_dump(exclude_unset=True),
        )

    return [public, admin]
```

В `backend/app/modules/directories/router.py` заменить последнюю строку:
```python
routers = [departments_router, admin_departments_router]
for _spec in REFERENCE_SPECS:
    routers.extend(build_reference_routers(_spec))
```
(импорты: `from app.modules.directories.reference_router import build_reference_routers`, `from app.modules.directories.references import REFERENCE_SPECS`).

В `backend/pyproject.toml`:
- в контракт «Другие модули используют directories только через service и events» дописать в `forbidden_modules` `"app.modules.directories.reference"`, `"app.modules.directories.references"`, `"app.modules.directories.reference_router"`;
- добавить override для mypy (в зависимости от версии mypy сообщение `valid-type` может не возникать, и тогда игнорирование не должно считаться ошибкой):
```toml
[[tool.mypy.overrides]]
module = ["app.modules.directories.reference_router"]
warn_unused_ignores = false
```

- [ ] **Step 6: Прогнать тесты и проверки**

Run: `uv run pytest -q && uv run mypy app tests && uv run lint-imports`
Expected: всё проходит.

- [ ] **Step 7: Commit**

```bash
git add backend
git commit -m "feat: справочники с деактивацией вместо удаления"
```

---

### Task 12: OpenAPI-схема, Docker-образ, CI, документация

**Files:**
- Create: `backend/app/scripts/__init__.py`, `backend/app/scripts/export_openapi.py`, `backend/openapi.json`
- Create: `backend/Dockerfile`, `backend/.dockerignore`
- Modify: `compose.yaml` (сервис `backend`)
- Create: `.github/workflows/ci.yml`, `Makefile`, `README.md`
- Test: `backend/tests/test_openapi.py`

**Interfaces:**
- Consumes: `create_app()`.
- Produces: `backend/openapi.json` — источник для генерации TS-типов фронтенда (план 2); `python -m app.scripts.export_openapi <path>`; цели `make up | test | lint | openapi`.

- [ ] **Step 1: Написать падающий тест**

`backend/tests/test_openapi.py`:
```python
import json

from app.main import create_app
from app.scripts.export_openapi import render_openapi
from tests.db_utils import BACKEND_DIR


def test_committed_openapi_schema_is_up_to_date() -> None:
    committed = (BACKEND_DIR / "openapi.json").read_text(encoding="utf-8")

    assert committed == render_openapi(create_app()), (
        "openapi.json устарел: выполните `make openapi` и закоммитьте результат"
    )


def test_openapi_contains_core_paths() -> None:
    paths = json.loads(render_openapi(create_app()))["paths"]

    for path in ("/api/auth/login", "/api/admin/users", "/api/departments", "/api/directories/locations"):
        assert path in paths
```

Run: `uv run pytest tests/test_openapi.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.scripts'`.

- [ ] **Step 2: Реализовать экспорт схемы**

Пустой `backend/app/scripts/__init__.py`.

`backend/app/scripts/export_openapi.py`:
```python
import json
import sys
from pathlib import Path

from fastapi import FastAPI

from app.main import create_app


def render_openapi(app: FastAPI) -> str:
    return json.dumps(app.openapi(), ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def main() -> None:
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("openapi.json")
    target.write_text(render_openapi(create_app()), encoding="utf-8")
    print(f"OpenAPI-схема записана в {target}")


if __name__ == "__main__":
    main()
```

Run: `uv run python -m app.scripts.export_openapi openapi.json && uv run pytest tests/test_openapi.py -q`
Expected: 2 passed.

- [ ] **Step 3: Docker-образ и сервис в Compose**

`backend/.dockerignore`:
```
.venv
__pycache__
.pytest_cache
.mypy_cache
.ruff_cache
.env
tests
```

`backend/Dockerfile`:
```dockerfile
FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY . .

RUN useradd --system --uid 10001 app
USER app

EXPOSE 8000

# --no-proxy-headers: IP клиента определяет приложение (app/core/net.py) по TRUSTED_PROXIES
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-proxy-headers"]
```

Добавить в `compose.yaml` в раздел `services`:
```yaml
  backend:
    build: ./backend
    environment:
      APP_ENV: local
      DATABASE_URL: postgresql+asyncpg://app:app@postgres:5432/it_platform
      REDIS_URL: redis://redis:6379/0
      COOKIE_SECURE: "false"
    command: >
      sh -c "alembic upgrade head &&
             uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --no-proxy-headers"
    volumes:
      - ./backend/app:/app/app
      - ./backend/migrations:/app/migrations
    ports:
      - "127.0.0.1:8000:8000"
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
```

Run: `docker compose up -d --build backend && sleep 5 && curl -s localhost:8000/ready`
Expected: `{"status":"ok","checks":{"database":"ok","redis":"ok"}}`.

- [ ] **Step 4: CI**

`.github/workflows/ci.yml`:
```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:

jobs:
  backend:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: backend
    services:
      postgres:
        image: postgres:17
        env:
          POSTGRES_USER: app
          POSTGRES_PASSWORD: app
          POSTGRES_DB: it_platform_test
        ports:
          - 5432:5432
        options: >-
          --health-cmd "pg_isready -U app -d it_platform_test"
          --health-interval 5s --health-retries 10
      redis:
        image: redis:7
        ports:
          - 6379:6379
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 5s --health-retries 10
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
        with:
          enable-cache: true
      - run: uv sync --frozen
      - run: uv run ruff format --check .
      - run: uv run ruff check .
      - run: uv run mypy app tests
      - run: uv run lint-imports
      - run: uv run pytest -q
```

- [ ] **Step 5: Makefile и README**

`Makefile` (отступы в рецептах — символ табуляции):
```make
.PHONY: up down test lint format openapi migrate create-admin

up:
	docker compose up -d postgres redis

down:
	docker compose down

test:
	cd backend && uv run pytest -q

lint:
	cd backend && uv run ruff format --check . && uv run ruff check . && uv run mypy app tests && uv run lint-imports

format:
	cd backend && uv run ruff format . && uv run ruff check --fix .

openapi:
	cd backend && uv run python -m app.scripts.export_openapi openapi.json

migrate:
	cd backend && uv run alembic upgrade head

create-admin:
	cd backend && uv run python -m app.cli create-admin --email "$(EMAIL)" --full-name "$(NAME)"
```

`README.md`:
````markdown
# IT-платформа

Внутренний инструмент IT-отдела: учёт оргтехники, служебные заявки, Kanban. ТЗ — `docs/spec/TZ_IT_platforma_v1.2.md`.

## Требования

- Docker (OrbStack или Docker Desktop)
- [uv](https://docs.astral.sh/uv/)

## Запуск локально

```bash
make up                         # PostgreSQL и Redis
cp backend/.env.example backend/.env
cd backend && uv sync && cd ..
make migrate
make create-admin EMAIL=admin@company.ru NAME="Администратор"
cd backend && uv run uvicorn app.main:app --reload
```

API: http://localhost:8000/api/docs

## Проверки

```bash
make test      # тесты (нужны запущенные postgres и redis)
make lint      # ruff, mypy, границы модулей
make openapi   # после изменения API — обновить backend/openapi.json
```

## Архитектура

Модульный монолит (`backend/app/modules/*`). Модуль используется другими модулями только через `service.py` и `events.py` — это проверяет `lint-imports` в CI. Обратные связи между модулями — через доменные события (`app/core/events.py`).
````

- [ ] **Step 6: Полная проверка**

Run: `make lint && make test`
Expected: все проверки и тесты проходят.

- [ ] **Step 7: Commit**

```bash
git add .github Makefile README.md compose.yaml backend
git commit -m "chore: экспорт OpenAPI, Docker-образ backend, CI, README"
```

---

## Покрытие ТЗ этим планом

| Требование ТЗ | Задача |
|---|---|
| 2.1 Стек backend, Docker Compose | 1, 2, 12 |
| 2.2 Модульный монолит, import-linter, FK между схемами, доменные события | 3, 5, 10, 11 |
| 2.3 Роли, проверка роли на backend | 7, 9 |
| 2.4 Argon2id, access 15 мин, refresh 14 дней с ротацией и отзывом, cookie, защита от перебора, временный пароль, CLI первого Admin | 6, 7, 8, 9 |
| 3.1 `User`, `Department`, `Location`, `AssetType`, `StockCategory`, `IssueReason`, `TicketType`, `AuditLog` | 3, 6, 10, 11 |
| 3.1 Справочники деактивируются, а не удаляются | 11 |
| 3.2 Деактивация пользователя с ответственностью требует передачи (блокеры) | 9, 10 |
| 3.2 `timestamptz`, UTC | 3, 6 |
| 4.7 Пользователи, отделы, справочники, журнал действий (запись) | 3, 9, 10, 11 |
| 7.2 `/health`, `/ready`, JSON-логи с `request_id` | 2, 4 |
| 7.3 Секреты в окружении, CORS отключён вне local, порты БД/Redis только на localhost | 1, 2 |
| 7.4 Локальное окружение, миграции с downgrade, CI | 2, 3, 12 |
| 7.6 Часовой пояс компании — настройка | 1 |
| 9 Линтинг, типизация, границы модулей, тесты прав, OpenAPI | 3, 7, 9, 12 |
