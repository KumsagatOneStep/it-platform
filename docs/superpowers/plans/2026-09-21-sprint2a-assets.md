# Спринт 2, часть 2a — оргтехника: план реализации

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Модуль «Оргтехника», часть техники: реестр с областью видимости по ролям, карточка с историей, статусы и переходы по п. 4.2.2 ТЗ, одиночные операции и массовые выдача и возврат, блокер деактивации владельца — backend и фронтенд.

**Architecture:** Новый модуль модульного монолита `backend/app/modules/assets` (схема БД `equipment`). Правила переходов — одна таблица `transitions.py`; по ней сервис проверяет операции и отдаёт `allowed_operations`. Другие модули читаются только через `service.py` (новые функции имён и справочников), обратная связь `users_auth → assets` — через событие `UserDeactivationRequested`. Конкурентный доступ — блокировка строк `SELECT … FOR UPDATE`, правка — оптимистическая по `version`. Фронтенд — фича `frontend/src/features/assets` на общих компонентах спринта 1 (DataTable, фильтры в URL, FormDialog, EntityAutocomplete).

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2 (async) + asyncpg, Alembic, pydantic 2, pytest; React 19 + TypeScript 5.9, MUI 9, TanStack Query 5, react-hook-form 7, openapi-fetch, Vitest + Testing Library + MSW.

**Spec:** `docs/superpowers/specs/2026-09-21-sprint2a-assets-design.md`; ТЗ — `docs/spec/TZ_IT_platforma_v1.2.md` (п. 2.2, 2.3, 3.1, 3.2, 4.2).

**Как проверен план.** Весь код плана сначала написан и прогнан целиком, затем задачи применены по порядку к ветке `feature/sprint2a-assets` в отдельном worktree: после каждой задачи выполнены её команды — шаг RED действительно падал, шаги GREEN, `make lint` и `npm run check` проходили (итого backend — 232 теста, фронтенд — 84). Тест гонки проверен на то, что без `FOR UPDATE` он падает. Не проверялось агентом: работа в браузере — пункты 8–13 чек-листа README выполняет пользователь.

## Уточнения к спецификации

Внесены в спецификацию отдельным коммитом (`docs: уточнения спецификации 2a…`) по итогам проверки реализации:

1. **Блокировка строки вместо условного `UPDATE`.** Операция блокирует актив `SELECT … FOR UPDATE` и проверяет статус под блокировкой; гарантия та же (параллельная операция ждёт коммита и получает 409), а код проще — одна ORM-модель вместо ручного `UPDATE … RETURNING`.
2. **Уникальность номеров** — только через уникальный индекс и перехват нарушения, как `email_taken` в спринте 1.
3. **Имена в ответах** (`owner_name`, `location_name`, …) подставляет backend: Employee и Manager не имеют доступа к `/api/admin/users`.
4. **Фильтр статуса на фронтенде — одиночный выбор** («Все, кроме списанных» по умолчанию); API принимает несколько статусов.
5. **Фильтр владельца и «Требует проверки» — только Admin** (варианты владельцев берутся из `/api/admin/users`).
6. **Конфликт версий при правке** — форма закрывается с предупреждением, карточка перезагружается (без отдельной кнопки «Обновить»).
7. **Инвентарный номер в реестре — ссылка на карточку**; общий `DataTable` не меняется.

## Global Constraints

- Ветка `feature/sprint2a-assets` (от `feature/sprint1-frontend`); команды — из корня репозитория, если не сказано иное.
- Модули обращаются друг к другу только через `service.py` и `events.py`; `users_auth` и `directories` не импортируют `assets` — проверяет `make lint` (import-linter). Межсхемные JOIN в бизнес-логике запрещены, внешние ключи между схемами разрешены.
- Формат ошибок API — `{"error": {"code", "message", "details"}}`; коды ошибок — ровно из п. 5 спецификации: `asset_not_found`, `operation_not_allowed`, `assets_unavailable`, `version_conflict`, `asset_written_off`, `inventory_number_taken`, `serial_number_taken`, `inventory_number_blank`, `model_blank`, `recipient_invalid`, `reason_invalid`, `reason_required`, `location_invalid`, `asset_type_invalid`; роли — существующий `insufficient_role`.
- Операции, создание и правка — только Admin; Employee видит технику, где он владелец, Manager — технику сотрудников своего отдела (включая деактивированных), Admin — всё; актив вне области — 404.
- Каждое изменение актива пишет `AssetEvent` и `AuditLog` в той же транзакции.
- После изменения API — `make gen-api` (обновляет `backend/openapi.json` и `frontend/src/api/schema.d.ts`), оба файла коммитятся вместе с кодом: CI проверяет их актуальность (`test_openapi.py`, `npm run check:api`).
- Интерфейс на русском; статусы — «На складе», «Резерв», «В работе», «В ремонте», «Списана»; тексты ошибок для пользователя — из `message` backend.
- Фронтенд: фича импортирует другие фичи только через `index.ts`, не импортирует `layout/` и `app/` (ESLint); типы API — только из `schema.d.ts`.
- TDD: тест пишется и падает до кода. Перед коммитом backend — `make lint` и тесты задачи; фронтенд — `npm run format && npm run check`.
- Сообщения коммитов заканчиваются строкой `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>` (в шагах опущено для краткости).

## Структура файлов

```
backend/app/modules/assets/
├── models.py        Asset, AssetEvent, AssetStatus, AssetEventType
├── transitions.py   таблица переходов, allowed_operations
├── schemas.py       запросы и ответы API, схемы операций
├── access.py        область видимости по ролям, get_visible_asset
├── checks.py        проверки справочников и получателя (422)
├── history.py       запись AssetEvent + AuditLog, Placement, changed_fields
├── presenter.py     ответы API с именами через service других модулей
├── registry.py      список, создание, правка, история
├── operations.py    одиночные и массовые операции
├── handlers.py      блокер деактивации владельца
└── router.py        /api/assets…
backend/migrations/versions/0005_assets.py
backend/tests/modules/assets/  conftest, test_models, test_transitions, test_registry_api,
                               test_operations_api, test_concurrency, test_deactivation_blocker
backend/tests/modules/test_cross_module_services.py

frontend/src/features/assets/
├── labels.ts                подписи статусов, операций, строки истории
├── api.ts                   запросы и мутации TanStack Query
├── AssetStatusChip.tsx
├── AssetsPage.tsx           реестр
├── AssetFormDialog.tsx      создание и правка
├── AssetPage.tsx            карточка: информация, история, действия
├── AssetHistory.tsx
├── AssetOperationDialog.tsx поля по операции
├── AssetMultiPicker.tsx     выбор нескольких активов «На складе»
├── IssuePage.tsx            выдать / принять
├── testing.ts               MSW-заглушки справочников для тестов
└── index.ts
frontend/src/shared/lookups/directories.ts   локации, типы техники, причины выдачи
```

---

### Task 1: Модели и миграция `equipment.assets`, `equipment.asset_events`

**Files:**
- Create: `backend/app/modules/assets/__init__.py` (пустой)
- Create: `backend/app/modules/assets/models.py`
- Create: `backend/migrations/versions/0005_assets.py`
- Modify: `backend/app/model_registry.py`
- Create: `backend/tests/modules/assets/__init__.py` (пустой)
- Test: `backend/tests/modules/assets/test_models.py`

**Interfaces:**
- Produces: `AssetStatus` (`in_stock`, `reserved`, `in_use`, `in_repair`, `written_off`), `AssetEventType` (`created`, `issued`, `returned`, `status_changed`, `moved`, `edited`, `written_off`), ORM-модели `Asset` и `AssetEvent` в `app.modules.assets.models` — поля ровно как в п. 2.1–2.2 спецификации.
- Ограничения БД: `ck_assets_in_use_has_owner`, `ck_assets_stock_has_no_owner`, `ck_assets_initial_cost`, `uq_assets_inventory_number`, частичный уникальный индекс `uq_assets_serial_number` (имена используются в Task 4 для кодов ошибок).

- [ ] **Step 1: Написать падающий тест ограничений БД**

Создать `backend/tests/modules/assets/__init__.py`:

```python

```

Создать `backend/tests/modules/assets/test_models.py`:

```python
"""Ограничения БД страхуют правила владельца независимо от кода (п. 2.1 спецификации)."""

from datetime import date

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.assets.models import Asset, AssetStatus
from app.modules.directories.models import AssetType, Location
from tests.factories import make_user


async def _refs(session: AsyncSession) -> tuple[int, int]:
    asset_type = AssetType(name="Монитор")
    location = Location(name="Склад")
    session.add_all([asset_type, location])
    await session.flush()
    return asset_type.id, location.id


def _asset(type_id: int, location_id: int, **overrides: object) -> Asset:
    values: dict[str, object] = {
        "asset_type_id": type_id,
        "inventory_number": "INV-1",
        "model": "Dell P2422H",
        "status": AssetStatus.IN_STOCK,
        "location_id": location_id,
        "accepted_at": date(2026, 1, 1),
        "needs_review": False,
        "version": 1,
    }
    values.update(overrides)
    return Asset(**values)


@pytest.mark.parametrize(
    ("status", "with_owner"),
    [
        (AssetStatus.IN_USE, False),
        (AssetStatus.IN_STOCK, True),
        (AssetStatus.RESERVED, True),
        (AssetStatus.WRITTEN_OFF, True),
    ],
)
async def test_owner_rules_enforced_by_database(
    db_session: AsyncSession, status: AssetStatus, with_owner: bool
) -> None:
    type_id, location_id = await _refs(db_session)
    owner = await make_user(db_session)

    with pytest.raises(IntegrityError):
        async with db_session.begin_nested():
            db_session.add(
                _asset(
                    type_id, location_id, status=status, owner_id=owner.id if with_owner else None
                )
            )


async def test_in_repair_allows_owner_or_none(db_session: AsyncSession) -> None:
    type_id, location_id = await _refs(db_session)
    owner = await make_user(db_session)

    db_session.add_all(
        [
            _asset(type_id, location_id, status=AssetStatus.IN_REPAIR, owner_id=owner.id),
            _asset(type_id, location_id, inventory_number="INV-2", status=AssetStatus.IN_REPAIR),
        ]
    )
    await db_session.flush()


async def test_negative_cost_rejected(db_session: AsyncSession) -> None:
    type_id, location_id = await _refs(db_session)

    with pytest.raises(IntegrityError):
        async with db_session.begin_nested():
            db_session.add(_asset(type_id, location_id, initial_cost=-1))
```

- [ ] **Step 2: Убедиться, что тест падает**

Run: `cd backend && uv run pytest -q tests/modules/assets/test_models.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.modules.assets'`

- [ ] **Step 3: Модели**

Создать `backend/app/modules/assets/__init__.py`:

```python

```

Создать `backend/app/modules/assets/models.py` — статусы и типы событий хранятся строками (`native_enum=False`), как роли в спринте 1; допустимые значения проверяет CHECK из миграции:

```python
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class AssetStatus(StrEnum):
    IN_STOCK = "in_stock"
    RESERVED = "reserved"
    IN_USE = "in_use"
    IN_REPAIR = "in_repair"
    WRITTEN_OFF = "written_off"


class AssetEventType(StrEnum):
    CREATED = "created"
    ISSUED = "issued"
    RETURNED = "returned"
    STATUS_CHANGED = "status_changed"
    MOVED = "moved"
    EDITED = "edited"
    WRITTEN_OFF = "written_off"


def _enum_column(enum: type[StrEnum]) -> SAEnum:
    return SAEnum(
        enum,
        native_enum=False,
        create_constraint=False,
        length=16,
        values_callable=lambda members: [member.value for member in members],
    )


class Asset(Base):
    __tablename__ = "assets"
    __table_args__ = (
        CheckConstraint("status <> 'in_use' OR owner_id IS NOT NULL", name="in_use_has_owner"),
        CheckConstraint(
            "status NOT IN ('in_stock', 'reserved', 'written_off') OR owner_id IS NULL",
            name="stock_has_no_owner",
        ),
        CheckConstraint("initial_cost IS NULL OR initial_cost >= 0", name="initial_cost"),
        Index(
            "uq_assets_serial_number",
            "serial_number",
            unique=True,
            postgresql_where="serial_number IS NOT NULL",
        ),
        {"schema": "equipment"},
    )
    __mapper_args__ = {"eager_defaults": True}  # noqa: RUF012

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    asset_type_id: Mapped[int] = mapped_column(ForeignKey("common.asset_types.id"), index=True)
    inventory_number: Mapped[str] = mapped_column(String(64), unique=True)
    serial_number: Mapped[str | None] = mapped_column(String(128))
    model: Mapped[str] = mapped_column(String(200))
    status: Mapped[AssetStatus] = mapped_column(_enum_column(AssetStatus), index=True)
    location_id: Mapped[int] = mapped_column(ForeignKey("common.locations.id"), index=True)
    owner_id: Mapped[int | None] = mapped_column(ForeignKey("common.users.id"), index=True)
    accepted_at: Mapped[date] = mapped_column(Date)
    purchased_at: Mapped[date | None] = mapped_column(Date)
    warranty_until: Mapped[date | None] = mapped_column(Date)
    initial_cost: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    needs_review: Mapped[bool] = mapped_column(Boolean, default=False)
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class AssetEvent(Base):
    __tablename__ = "asset_events"
    __table_args__ = (
        Index("ix_asset_events_asset_id_id", "asset_id", "id"),
        {"schema": "equipment"},
    )
    __mapper_args__ = {"eager_defaults": True}  # noqa: RUF012

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("equipment.assets.id"))
    event_type: Mapped[AssetEventType] = mapped_column(_enum_column(AssetEventType))
    operation: Mapped[str | None] = mapped_column(String(32))
    from_owner_id: Mapped[int | None] = mapped_column(ForeignKey("common.users.id"))
    to_owner_id: Mapped[int | None] = mapped_column(ForeignKey("common.users.id"))
    from_status: Mapped[AssetStatus | None] = mapped_column(_enum_column(AssetStatus))
    to_status: Mapped[AssetStatus | None] = mapped_column(_enum_column(AssetStatus))
    from_location_id: Mapped[int | None] = mapped_column(ForeignKey("common.locations.id"))
    to_location_id: Mapped[int | None] = mapped_column(ForeignKey("common.locations.id"))
    reason_id: Mapped[int | None] = mapped_column(ForeignKey("common.issue_reasons.id"))
    changes: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    comment: Mapped[str | None] = mapped_column(Text)
    performed_by: Mapped[int] = mapped_column(ForeignKey("common.users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
```

В `backend/app/model_registry.py` заменить:

```python
from app.core import audit  # noqa: F401
```

на:

```python
from app.core import audit  # noqa: F401
from app.modules.assets import models as assets_models  # noqa: F401
```

- [ ] **Step 4: Миграция**

Создать `backend/migrations/versions/0005_assets.py`:

```python
"""Оргтехника: активы и история активов

Revision ID: 0005
Revises: 0004
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_STATUSES = "'in_stock', 'reserved', 'in_use', 'in_repair', 'written_off'"
_EVENT_TYPES = "'created', 'issued', 'returned', 'status_changed', 'moved', 'edited', 'written_off'"


def upgrade() -> None:
    op.create_table(
        "assets",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("asset_type_id", sa.Integer(), nullable=False),
        sa.Column("inventory_number", sa.String(64), nullable=False),
        sa.Column("serial_number", sa.String(128), nullable=True),
        sa.Column("model", sa.String(200), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("location_id", sa.Integer(), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=True),
        sa.Column("accepted_at", sa.Date(), nullable=False),
        sa.Column("purchased_at", sa.Date(), nullable=True),
        sa.Column("warranty_until", sa.Date(), nullable=True),
        sa.Column("initial_cost", sa.Numeric(12, 2), nullable=True),
        sa.Column("needs_review", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint("inventory_number", name="uq_assets_inventory_number"),
        sa.CheckConstraint(f"status IN ({_STATUSES})", name="ck_assets_status"),
        sa.CheckConstraint(
            "status <> 'in_use' OR owner_id IS NOT NULL", name="ck_assets_in_use_has_owner"
        ),
        sa.CheckConstraint(
            "status NOT IN ('in_stock', 'reserved', 'written_off') OR owner_id IS NULL",
            name="ck_assets_stock_has_no_owner",
        ),
        sa.CheckConstraint(
            "initial_cost IS NULL OR initial_cost >= 0", name="ck_assets_initial_cost"
        ),
        sa.ForeignKeyConstraint(
            ["asset_type_id"], ["common.asset_types.id"], name="fk_assets_asset_type_id_asset_types"
        ),
        sa.ForeignKeyConstraint(
            ["location_id"], ["common.locations.id"], name="fk_assets_location_id_locations"
        ),
        sa.ForeignKeyConstraint(["owner_id"], ["common.users.id"], name="fk_assets_owner_id_users"),
        schema="equipment",
    )
    for column in ("asset_type_id", "status", "location_id", "owner_id"):
        op.create_index(f"ix_assets_{column}", "assets", [column], schema="equipment")
    op.create_index(
        "uq_assets_serial_number",
        "assets",
        ["serial_number"],
        unique=True,
        schema="equipment",
        postgresql_where=sa.text("serial_number IS NOT NULL"),
    )

    op.create_table(
        "asset_events",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("asset_id", sa.BigInteger(), nullable=False),
        sa.Column("event_type", sa.String(16), nullable=False),
        sa.Column("operation", sa.String(32), nullable=True),
        sa.Column("from_owner_id", sa.Integer(), nullable=True),
        sa.Column("to_owner_id", sa.Integer(), nullable=True),
        sa.Column("from_status", sa.String(16), nullable=True),
        sa.Column("to_status", sa.String(16), nullable=True),
        sa.Column("from_location_id", sa.Integer(), nullable=True),
        sa.Column("to_location_id", sa.Integer(), nullable=True),
        sa.Column("reason_id", sa.Integer(), nullable=True),
        sa.Column("changes", postgresql.JSONB(), nullable=True),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("performed_by", sa.Integer(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint(f"event_type IN ({_EVENT_TYPES})", name="ck_asset_events_event_type"),
        sa.ForeignKeyConstraint(
            ["asset_id"], ["equipment.assets.id"], name="fk_asset_events_asset_id_assets"
        ),
        sa.ForeignKeyConstraint(
            ["from_owner_id"], ["common.users.id"], name="fk_asset_events_from_owner_id_users"
        ),
        sa.ForeignKeyConstraint(
            ["to_owner_id"], ["common.users.id"], name="fk_asset_events_to_owner_id_users"
        ),
        sa.ForeignKeyConstraint(
            ["from_location_id"],
            ["common.locations.id"],
            name="fk_asset_events_from_location_id_locations",
        ),
        sa.ForeignKeyConstraint(
            ["to_location_id"],
            ["common.locations.id"],
            name="fk_asset_events_to_location_id_locations",
        ),
        sa.ForeignKeyConstraint(
            ["reason_id"],
            ["common.issue_reasons.id"],
            name="fk_asset_events_reason_id_issue_reasons",
        ),
        sa.ForeignKeyConstraint(
            ["performed_by"], ["common.users.id"], name="fk_asset_events_performed_by_users"
        ),
        schema="equipment",
    )
    op.create_index(
        "ix_asset_events_asset_id_id", "asset_events", ["asset_id", "id"], schema="equipment"
    )


def downgrade() -> None:
    op.drop_table("asset_events", schema="equipment")
    op.drop_table("assets", schema="equipment")
```

- [ ] **Step 5: Тесты проходят, миграция откатывается и накатывается**

Run: `cd backend && uv run pytest -q tests/modules/assets/test_models.py tests/test_migrations.py`
Expected: PASS (8 тестов)

Run: `make lint`
Expected: ruff, mypy и import-linter без ошибок (`Contracts: N kept, 0 broken.`)

- [ ] **Step 6: Коммит**

```bash
git add backend && git commit -m "feat(assets): модели и миграция техники и истории"
```

### Task 2: Таблица переходов статусов

Единственный источник правил п. 4.2.2 ТЗ: по ней backend проверяет операции (Task 5) и отдаёт `allowed_operations` (Task 4). Тест выписывает ожидания из ТЗ независимо от реализации.

**Files:**
- Create: `backend/app/modules/assets/transitions.py`
- Test: `backend/tests/modules/assets/test_transitions.py`

**Interfaces:**
- Consumes: `AssetStatus`, `AssetEventType` (Task 1).
- Produces: `Operation` (StrEnum: `issue`, `return`, `reserve`, `unreserve`, `to_repair`, `repair_to_owner`, `repair_to_stock`, `write_off`, `move`), `OwnerRule` (`set`/`keep`/`clear`), `Transition(from_statuses, to_status, owner, event_type, requires_owner)`, `TRANSITIONS: dict[Operation, Transition]`, `is_allowed(operation, status, owner_id) -> bool`, `allowed_operations(status, owner_id) -> list[Operation]` (в порядке объявления `Operation`).

- [ ] **Step 1: Написать падающий тест**

Создать `backend/tests/modules/assets/test_transitions.py`:

```python
"""Таблица переходов против п. 4.2.2 ТЗ: все пары «статус × операция»."""

import pytest

from app.modules.assets.models import AssetStatus as S
from app.modules.assets.transitions import TRANSITIONS, Operation, OwnerRule, allowed_operations

# Ожидания выписаны из ТЗ независимо от реализации.
EXPECTED_FROM: dict[Operation, set[S]] = {
    Operation.ISSUE: {S.IN_STOCK, S.RESERVED},
    Operation.RETURN: {S.IN_USE},
    Operation.RESERVE: {S.IN_STOCK},
    Operation.UNRESERVE: {S.RESERVED},
    Operation.TO_REPAIR: {S.IN_STOCK, S.IN_USE, S.RESERVED},
    Operation.REPAIR_TO_OWNER: {S.IN_REPAIR},
    Operation.REPAIR_TO_STOCK: {S.IN_REPAIR},
    Operation.WRITE_OFF: {S.IN_STOCK, S.IN_REPAIR},
    Operation.MOVE: {S.IN_STOCK, S.RESERVED, S.IN_USE, S.IN_REPAIR},
}
EXPECTED_TO: dict[Operation, S | None] = {
    Operation.ISSUE: S.IN_USE,
    Operation.RETURN: S.IN_STOCK,
    Operation.RESERVE: S.RESERVED,
    Operation.UNRESERVE: S.IN_STOCK,
    Operation.TO_REPAIR: S.IN_REPAIR,
    Operation.REPAIR_TO_OWNER: S.IN_USE,
    Operation.REPAIR_TO_STOCK: S.IN_STOCK,
    Operation.WRITE_OFF: S.WRITTEN_OFF,
    Operation.MOVE: None,
}
EXPECTED_OWNER: dict[Operation, OwnerRule] = {
    Operation.ISSUE: OwnerRule.SET,
    Operation.RETURN: OwnerRule.CLEAR,
    Operation.RESERVE: OwnerRule.KEEP,
    Operation.UNRESERVE: OwnerRule.KEEP,
    Operation.TO_REPAIR: OwnerRule.KEEP,
    Operation.REPAIR_TO_OWNER: OwnerRule.KEEP,
    Operation.REPAIR_TO_STOCK: OwnerRule.CLEAR,
    Operation.WRITE_OFF: OwnerRule.CLEAR,
    Operation.MOVE: OwnerRule.KEEP,
}


@pytest.mark.parametrize("status", list(S))
@pytest.mark.parametrize("operation", list(Operation))
def test_operation_allowed_only_from_statuses_in_spec(operation: Operation, status: S) -> None:
    owner_id = 7 if status in {S.IN_USE, S.IN_REPAIR} else None

    allowed = operation in allowed_operations(status, owner_id)

    assert allowed == (status in EXPECTED_FROM[operation])


@pytest.mark.parametrize("operation", list(Operation))
def test_target_status_and_owner_rule(operation: Operation) -> None:
    assert TRANSITIONS[operation].to_status == EXPECTED_TO[operation]
    assert TRANSITIONS[operation].owner == EXPECTED_OWNER[operation]


def test_repair_to_owner_requires_owner() -> None:
    assert Operation.REPAIR_TO_OWNER in allowed_operations(S.IN_REPAIR, owner_id=7)
    assert Operation.REPAIR_TO_OWNER not in allowed_operations(S.IN_REPAIR, owner_id=None)


def test_written_off_is_final() -> None:
    assert allowed_operations(S.WRITTEN_OFF, owner_id=None) == []
```

- [ ] **Step 2: Убедиться, что тест падает**

Run: `cd backend && uv run pytest -q tests/modules/assets/test_transitions.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.modules.assets.transitions'`

- [ ] **Step 3: Реализация**

Создать `backend/app/modules/assets/transitions.py`:

```python
"""Таблица переходов статусов актива (п. 4.2.2 ТЗ) — единственный источник правил."""

from dataclasses import dataclass
from enum import StrEnum

from app.modules.assets.models import AssetEventType, AssetStatus


class Operation(StrEnum):
    ISSUE = "issue"
    RETURN = "return"
    RESERVE = "reserve"
    UNRESERVE = "unreserve"
    TO_REPAIR = "to_repair"
    REPAIR_TO_OWNER = "repair_to_owner"
    REPAIR_TO_STOCK = "repair_to_stock"
    WRITE_OFF = "write_off"
    MOVE = "move"


class OwnerRule(StrEnum):
    SET = "set"
    """Владелец берётся из запроса (обязателен)."""
    KEEP = "keep"
    CLEAR = "clear"


@dataclass(frozen=True)
class Transition:
    from_statuses: frozenset[AssetStatus]
    to_status: AssetStatus | None
    """None — статус не меняется (перемещение)."""
    owner: OwnerRule
    event_type: AssetEventType
    requires_owner: bool = False
    """Операция допустима, только если у актива есть владелец."""


_S = AssetStatus
_NOT_WRITTEN_OFF = frozenset(set(AssetStatus) - {AssetStatus.WRITTEN_OFF})

TRANSITIONS: dict[Operation, Transition] = {
    Operation.ISSUE: Transition(
        frozenset({_S.IN_STOCK, _S.RESERVED}), _S.IN_USE, OwnerRule.SET, AssetEventType.ISSUED
    ),
    Operation.RETURN: Transition(
        frozenset({_S.IN_USE}), _S.IN_STOCK, OwnerRule.CLEAR, AssetEventType.RETURNED
    ),
    Operation.RESERVE: Transition(
        frozenset({_S.IN_STOCK}), _S.RESERVED, OwnerRule.KEEP, AssetEventType.STATUS_CHANGED
    ),
    Operation.UNRESERVE: Transition(
        frozenset({_S.RESERVED}), _S.IN_STOCK, OwnerRule.KEEP, AssetEventType.STATUS_CHANGED
    ),
    Operation.TO_REPAIR: Transition(
        frozenset({_S.IN_STOCK, _S.IN_USE, _S.RESERVED}),
        _S.IN_REPAIR,
        OwnerRule.KEEP,
        AssetEventType.STATUS_CHANGED,
    ),
    Operation.REPAIR_TO_OWNER: Transition(
        frozenset({_S.IN_REPAIR}),
        _S.IN_USE,
        OwnerRule.KEEP,
        AssetEventType.STATUS_CHANGED,
        requires_owner=True,
    ),
    Operation.REPAIR_TO_STOCK: Transition(
        frozenset({_S.IN_REPAIR}), _S.IN_STOCK, OwnerRule.CLEAR, AssetEventType.RETURNED
    ),
    Operation.WRITE_OFF: Transition(
        frozenset({_S.IN_STOCK, _S.IN_REPAIR}),
        _S.WRITTEN_OFF,
        OwnerRule.CLEAR,
        AssetEventType.WRITTEN_OFF,
    ),
    Operation.MOVE: Transition(_NOT_WRITTEN_OFF, None, OwnerRule.KEEP, AssetEventType.MOVED),
}


def is_allowed(operation: Operation, status: AssetStatus, owner_id: int | None) -> bool:
    transition = TRANSITIONS[operation]
    if status not in transition.from_statuses:
        return False
    return not (transition.requires_owner and owner_id is None)


def allowed_operations(status: AssetStatus, owner_id: int | None) -> list[Operation]:
    """Операции, допустимые для актива в текущем состоянии, в порядке объявления."""
    return [operation for operation in Operation if is_allowed(operation, status, owner_id)]
```

- [ ] **Step 4: Тесты проходят**

Run: `cd backend && uv run pytest -q tests/modules/assets/test_transitions.py`
Expected: PASS (56 тестов)

Run: `make lint`
Expected: ruff, mypy и import-linter без ошибок (`Contracts: N kept, 0 broken.`)

- [ ] **Step 5: Коммит**

```bash
git add backend && git commit -m "feat(assets): таблица переходов статусов по п. 4.2.2 ТЗ"
```

### Task 3: Публичные функции `users_auth.service` и `directories.service`, контракты import-linter

Модулю `assets` нужны имена пользователей и справочников, состав отдела и проверка элемента справочника. По п. 2.2 ТЗ другие модули читаются только через `service.py`; import-linter закрепляет это для `assets` и запрещает обратную зависимость.

**Files:**
- Modify: `backend/app/modules/users_auth/service.py`
- Modify (переписать целиком): `backend/app/modules/directories/service.py`
- Modify: `backend/pyproject.toml` (секция `tool.importlinter`)
- Test: `backend/tests/modules/test_cross_module_services.py`

**Interfaces:**
- Produces (`app.modules.users_auth.service`): `get_user_names(session, user_ids: set[int]) -> dict[int, str]`, `list_department_user_ids(session, department_id: int) -> list[int]` (включая деактивированных).
- Produces (`app.modules.directories.service`): `ReferenceKind = Literal["locations", "asset-types", "issue-reasons"]`, `ReferenceItemInfo(id, name, is_active, applicability: str | None)`, `get_reference_item(session, kind, item_id) -> ReferenceItemInfo | None`, `get_reference_names(session, kind, item_ids: set[int]) -> dict[int, str]`. `get_department`/`DepartmentInfo` сохраняются без изменений.

- [ ] **Step 1: Написать падающий тест**

Создать `backend/tests/modules/test_cross_module_services.py`:

```python
"""Публичные функции service.py, которыми пользуются другие модули."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.directories.models import (
    Department,
    IssueReason,
    IssueReasonApplicability,
    Location,
)
from app.modules.directories.service import get_reference_item, get_reference_names
from app.modules.users_auth.service import get_user_names, list_department_user_ids
from tests.factories import make_user


async def test_get_user_names(db_session: AsyncSession) -> None:
    first = await make_user(db_session, full_name="Петров Пётр")
    second = await make_user(db_session, full_name="Сидорова Анна")

    names = await get_user_names(db_session, {first.id, second.id, 999999})

    assert names == {first.id: "Петров Пётр", second.id: "Сидорова Анна"}
    assert await get_user_names(db_session, set()) == {}


async def test_list_department_user_ids_includes_inactive(db_session: AsyncSession) -> None:
    department = Department(name="Бухгалтерия")
    db_session.add(department)
    await db_session.flush()
    active = await make_user(db_session, department_id=department.id)
    inactive = await make_user(db_session, department_id=department.id, is_active=False)
    await make_user(db_session)

    ids = await list_department_user_ids(db_session, department.id)

    assert sorted(ids) == sorted([active.id, inactive.id])


async def test_get_reference_item(db_session: AsyncSession) -> None:
    reason = IssueReason(name="Заправка", applicability=IssueReasonApplicability.STOCK)
    location = Location(name="Склад", is_active=False)
    db_session.add_all([reason, location])
    await db_session.flush()

    reason_info = await get_reference_item(db_session, "issue-reasons", reason.id)
    location_info = await get_reference_item(db_session, "locations", location.id)

    assert reason_info is not None
    assert reason_info.applicability == "stock"
    assert reason_info.is_active is True
    assert location_info is not None
    assert location_info.is_active is False
    assert location_info.applicability is None
    assert await get_reference_item(db_session, "asset-types", 999999) is None


async def test_get_reference_names(db_session: AsyncSession) -> None:
    location = Location(name="Склад")
    db_session.add(location)
    await db_session.flush()

    assert await get_reference_names(db_session, "locations", {location.id}) == {
        location.id: "Склад"
    }
```

- [ ] **Step 2: Убедиться, что тест падает**

Run: `cd backend && uv run pytest -q tests/modules/test_cross_module_services.py`
Expected: FAIL — `ImportError: cannot import name 'get_reference_item'`

- [ ] **Step 3: Функции `users_auth.service`**

В `backend/app/modules/users_auth/service.py` заменить:

```python
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession
```

на:

```python
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
```

В `backend/app/modules/users_auth/service.py` заменить:

```python
    "get_user_info",
```

на:

```python
    "get_user_info",
    "get_user_names",
    "list_department_user_ids",
```

Дописать в конец `backend/app/modules/users_auth/service.py`:

```python


async def get_user_names(session: AsyncSession, user_ids: set[int]) -> dict[int, str]:
    """ФИО пользователей по id (для подписей в чужих модулях)."""
    if not user_ids:
        return {}
    rows = await session.execute(select(User.id, User.full_name).where(User.id.in_(user_ids)))
    return {user_id: full_name for user_id, full_name in rows.tuples()}


async def list_department_user_ids(session: AsyncSession, department_id: int) -> list[int]:
    """Все пользователи отдела, включая деактивированных (их техника тоже числится за отделом)."""
    rows = await session.scalars(select(User.id).where(User.department_id == department_id))
    return list(rows)
```

- [ ] **Step 4: `directories.service` целиком**

Создать `backend/app/modules/directories/service.py`:

```python
"""Публичный интерфейс модуля directories.

Другие модули импортируют только этот файл и events.py.
"""

from dataclasses import dataclass
from typing import Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.directories.models import AssetType, Department, IssueReason, Location

ReferenceKind = Literal["locations", "asset-types", "issue-reasons"]

_ReferenceModel = Location | AssetType | IssueReason

_REFERENCE_MODELS: dict[ReferenceKind, type[_ReferenceModel]] = {
    "locations": Location,
    "asset-types": AssetType,
    "issue-reasons": IssueReason,
}


@dataclass(frozen=True)
class DepartmentInfo:
    id: int
    name: str
    head_id: int | None


@dataclass(frozen=True)
class ReferenceItemInfo:
    id: int
    name: str
    is_active: bool
    applicability: str | None
    """Только для причин выдачи: assets / stock / both."""


async def get_department(session: AsyncSession, department_id: int) -> DepartmentInfo | None:
    department = await session.get(Department, department_id)
    if department is None:
        return None
    return DepartmentInfo(id=department.id, name=department.name, head_id=department.head_id)


async def get_reference_item(
    session: AsyncSession, kind: ReferenceKind, item_id: int
) -> ReferenceItemInfo | None:
    item: _ReferenceModel | None = await session.get(_REFERENCE_MODELS[kind], item_id)
    if item is None:
        return None
    applicability = item.applicability.value if isinstance(item, IssueReason) else None
    return ReferenceItemInfo(
        id=item.id, name=item.name, is_active=item.is_active, applicability=applicability
    )


async def get_reference_names(
    session: AsyncSession, kind: ReferenceKind, item_ids: set[int]
) -> dict[int, str]:
    if not item_ids:
        return {}
    model = _REFERENCE_MODELS[kind]
    rows = await session.execute(select(model.id, model.name).where(model.id.in_(item_ids)))
    return {item_id: name for item_id, name in rows.tuples()}


__all__ = [
    "DepartmentInfo",
    "ReferenceItemInfo",
    "ReferenceKind",
    "get_department",
    "get_reference_item",
    "get_reference_names",
]
```

- [ ] **Step 5: Контракты import-linter**

В `backend/pyproject.toml` заменить:

```toml
name = "Другие модули используют users_auth только через service и events"
type = "forbidden"
source_modules = ["app.modules.directories"]
```

на:

```toml
name = "Другие модули используют users_auth только через service и events"
type = "forbidden"
source_modules = ["app.modules.directories", "app.modules.assets"]
```

В `backend/pyproject.toml` заменить:

```toml
name = "Другие модули используют directories только через service и events"
type = "forbidden"
source_modules = ["app.modules.users_auth"]
```

на:

```toml
name = "Другие модули используют directories только через service и events"
type = "forbidden"
source_modules = ["app.modules.users_auth", "app.modules.assets"]
```

Дописать в конец `backend/pyproject.toml`:

```toml

[[tool.importlinter.contracts]]
name = "users_auth и directories не зависят от assets (связь только через события)"
type = "forbidden"
source_modules = ["app.modules.users_auth", "app.modules.directories"]
forbidden_modules = ["app.modules.assets"]
```

- [ ] **Step 6: Тесты и контракты проходят**

Run: `cd backend && uv run pytest -q tests/modules/test_cross_module_services.py`
Expected: PASS (4 теста)

Run: `make lint`
Expected: `Contracts: 5 kept, 0 broken.`

- [ ] **Step 7: Коммит**

```bash
git add backend && git commit -m "feat: service-функции имён и справочников для модуля assets, контракты import-linter"
```

### Task 4: Реестр: создание, список, карточка, история, правка

Основа модуля: область видимости (п. 2.3 ТЗ), проверки справочников, запись истории (`AssetEvent` + `AuditLog`), сборка ответов с именами и эндпоинты реестра. Схемы операций (`IssueOperation` и др.) создаются здесь же, чтобы `schemas.py` писался один раз; используются они в Task 5.

Поведение, на которое опираются следующие задачи:
- `history.record_event(...)` пишет в событие только изменившиеся пары «было/стало»; `before=None` — создание.
- Правка без фактических изменений не меняет `version` и не пишет событие; `Decimal("95000") == Decimal("95000.00")` — не изменение.
- Уникальность номеров ловится по имени нарушенного индекса (`constraint_name`), как `email_taken` в спринте 1.

**Files:**
- Create: `backend/app/modules/assets/schemas.py`, `access.py`, `checks.py`, `history.py`, `presenter.py`, `registry.py`, `router.py`
- Modify: `backend/app/main.py`
- Modify: `backend/openapi.json`, `frontend/src/api/schema.d.ts` (генерируются)
- Test: `backend/tests/modules/assets/conftest.py`, `backend/tests/modules/assets/test_registry_api.py`

**Interfaces:**
- Consumes: модели (Task 1), `allowed_operations`, `Operation` (Task 2), service-функции (Task 3).
- Produces:
  - `access.visibility_filter(session, user) -> ColumnElement[bool] | None`, `access.get_visible_asset(session, user, asset_id, *, for_update=False) -> Asset` (404 `asset_not_found`).
  - `checks.check_asset_type / check_location / check_reason / check_recipient(session, id)` → 422 `asset_type_invalid` / `location_invalid` / `reason_invalid` / `recipient_invalid`.
  - `history.Placement(status, owner_id, location_id)` с `Placement.of(asset)`, `history.record_event(session, asset, *, event_type, actor_id, before, operation=None, reason_id=None, changes=None, comment=None)`, `history.changed_fields(before, after)`.
  - `presenter.assets_to_read(session, assets, user)`, `presenter.asset_to_read(session, asset, user)`, `presenter.events_to_read(session, events)`.
  - `schemas`: `AssetCreate`, `AssetUpdate`, `AssetRead`, `AssetEventRead`, `IssueOperation`, `ReturnOperation`, `StatusOperation`, `WriteOffOperation`, `MoveOperation`, `AssetOperationRequest`, `AssetIssueRequest`, `AssetReturnRequest`, `UnavailableAsset`.
  - `router.router` (prefix `/assets`): `GET ""`, `POST ""`, `GET /{asset_id}`, `PATCH /{asset_id}`, `GET /{asset_id}/events`.
  - Тестовые помощники `tests/modules/assets/conftest.py`: фикстура `refs` (`Refs`: `laptop`, `office`, `warehouse`, `new_employee`, `broken`, `stock_only`), `make_asset(session, refs, *, inventory_number, status=IN_STOCK, owner_id=None, serial_number=None, model=...)`, `asset_payload(refs, **overrides)`, `create_via_api(client, headers, refs, **overrides)`.

- [ ] **Step 1: Написать тестовые помощники и падающие тесты**

Создать `backend/tests/modules/assets/conftest.py`:

```python
from dataclasses import dataclass
from datetime import date
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.assets.models import Asset, AssetStatus
from app.modules.directories.models import (
    AssetType,
    IssueReason,
    IssueReasonApplicability,
    Location,
)


@dataclass(frozen=True)
class Refs:
    laptop: AssetType
    office: Location
    warehouse: Location
    new_employee: IssueReason
    broken: IssueReason
    stock_only: IssueReason


@pytest.fixture
async def refs(db_session: AsyncSession) -> Refs:
    laptop = AssetType(name="Ноутбук")
    office = Location(name="Офис, каб. 101")
    warehouse = Location(name="Склад")
    new_employee = IssueReason(name="Новый сотрудник", applicability=IssueReasonApplicability.BOTH)
    broken = IssueReason(name="Неисправность", applicability=IssueReasonApplicability.ASSETS)
    stock_only = IssueReason(name="Заправка", applicability=IssueReasonApplicability.STOCK)
    db_session.add_all([laptop, office, warehouse, new_employee, broken, stock_only])
    await db_session.flush()
    return Refs(laptop, office, warehouse, new_employee, broken, stock_only)


async def make_asset(
    session: AsyncSession,
    refs: Refs,
    *,
    inventory_number: str,
    status: AssetStatus = AssetStatus.IN_STOCK,
    owner_id: int | None = None,
    serial_number: str | None = None,
    model: str = "Lenovo ThinkPad T14",
) -> Asset:
    asset = Asset(
        asset_type_id=refs.laptop.id,
        inventory_number=inventory_number,
        serial_number=serial_number,
        model=model,
        status=status,
        location_id=refs.warehouse.id,
        owner_id=owner_id,
        accepted_at=date(2026, 1, 15),
        needs_review=False,
        version=1,
    )
    session.add(asset)
    await session.flush()
    return asset


def asset_payload(refs: Refs, **overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "asset_type_id": refs.laptop.id,
        "inventory_number": "INV-001",
        "serial_number": "SN-001",
        "model": "Lenovo ThinkPad T14",
        "location_id": refs.warehouse.id,
        "accepted_at": "2026-01-15",
        "warranty_until": "2028-01-15",
        "initial_cost": "95000.00",
    }
    payload.update(overrides)
    return payload


async def create_via_api(
    client: AsyncClient, headers: dict[str, str], refs: Refs, **overrides: object
) -> dict[str, Any]:
    response = await client.post(
        "/api/assets", headers=headers, json=asset_payload(refs, **overrides)
    )
    assert response.status_code == 201, response.text
    body: dict[str, Any] = response.json()
    return body
```

Создать `backend/tests/modules/assets/test_registry_api.py`:

```python
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import AuditLog
from app.modules.assets.models import AssetStatus
from app.modules.directories.models import Department
from app.modules.users_auth.models import User, UserRole
from tests.factories import login, make_user
from tests.modules.assets.conftest import Refs, asset_payload, create_via_api, make_asset


async def test_admin_creates_asset_in_stock_with_created_event(
    client: AsyncClient,
    admin_headers: dict[str, str],
    admin_user: User,
    refs: Refs,
    db_session: AsyncSession,
) -> None:
    created = await create_via_api(
        client, admin_headers, refs, inventory_number="  INV-001 ", serial_number=" "
    )

    assert created["inventory_number"] == "INV-001"
    assert created["serial_number"] is None
    assert created["status"] == "in_stock"
    assert created["owner_id"] is None
    assert created["asset_type_name"] == "Ноутбук"
    assert created["location_name"] == "Склад"
    assert created["initial_cost"] == "95000.00"
    assert created["version"] == 1
    assert "issue" in created["allowed_operations"]

    events = await client.get(f"/api/assets/{created['id']}/events", headers=admin_headers)
    assert events.status_code == 200
    [event] = events.json()["items"]
    assert event["event_type"] == "created"
    assert event["to_status"] == "in_stock"
    assert event["to_location_name"] == "Склад"
    assert event["performed_by_name"] == admin_user.full_name
    audit = await db_session.scalars(
        select(AuditLog.action).where(
            AuditLog.entity_type == "asset", AuditLog.entity_id == str(created["id"])
        )
    )
    assert list(audit) == ["created"]


async def test_duplicate_numbers_return_409(
    client: AsyncClient, admin_headers: dict[str, str], refs: Refs
) -> None:
    await create_via_api(client, admin_headers, refs)

    same_inventory = await client.post(
        "/api/assets",
        headers=admin_headers,
        json=asset_payload(refs, serial_number="SN-OTHER"),
    )
    same_serial = await client.post(
        "/api/assets",
        headers=admin_headers,
        json=asset_payload(refs, inventory_number="INV-OTHER"),
    )
    no_serial = await client.post(
        "/api/assets",
        headers=admin_headers,
        json=asset_payload(refs, inventory_number="INV-002", serial_number=None),
    )
    no_serial_again = await client.post(
        "/api/assets",
        headers=admin_headers,
        json=asset_payload(refs, inventory_number="INV-003", serial_number=None),
    )

    assert same_inventory.status_code == 409
    assert same_inventory.json()["error"]["code"] == "inventory_number_taken"
    assert same_serial.status_code == 409
    assert same_serial.json()["error"]["code"] == "serial_number_taken"
    assert no_serial.status_code == 201
    assert no_serial_again.status_code == 201


async def test_create_rejects_inactive_references_and_blank_fields(
    client: AsyncClient, admin_headers: dict[str, str], refs: Refs, db_session: AsyncSession
) -> None:
    refs.office.is_active = False
    await db_session.flush()

    inactive_location = await client.post(
        "/api/assets", headers=admin_headers, json=asset_payload(refs, location_id=refs.office.id)
    )
    missing_type = await client.post(
        "/api/assets", headers=admin_headers, json=asset_payload(refs, asset_type_id=999999)
    )
    blank_model = await client.post(
        "/api/assets", headers=admin_headers, json=asset_payload(refs, model="   ")
    )

    assert inactive_location.status_code == 422
    assert inactive_location.json()["error"]["code"] == "location_invalid"
    assert missing_type.json()["error"]["code"] == "asset_type_invalid"
    assert blank_model.json()["error"]["code"] == "model_blank"


async def test_non_admin_cannot_create(
    client: AsyncClient, refs: Refs, db_session: AsyncSession
) -> None:
    manager = await make_user(db_session, role=UserRole.MANAGER)
    headers = await login(client, manager.email)

    response = await client.post("/api/assets", headers=headers, json=asset_payload(refs))

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "insufficient_role"


async def test_list_filters_search_and_hides_written_off_by_default(
    client: AsyncClient, admin_headers: dict[str, str], refs: Refs, db_session: AsyncSession
) -> None:
    owner = await make_user(db_session)
    await make_asset(db_session, refs, inventory_number="INV-1", model="Dell Latitude")
    await make_asset(
        db_session, refs, inventory_number="INV-2", status=AssetStatus.IN_USE, owner_id=owner.id
    )
    await make_asset(db_session, refs, inventory_number="INV-3", status=AssetStatus.WRITTEN_OFF)

    async def numbers(**params: str | int | bool | list[str]) -> list[str]:
        response = await client.get("/api/assets", headers=admin_headers, params=params)
        assert response.status_code == 200, response.text
        return [item["inventory_number"] for item in response.json()["items"]]

    assert await numbers() == ["INV-1", "INV-2"]
    assert await numbers(status=["written_off", "in_use"]) == ["INV-2", "INV-3"]
    assert await numbers(owner_id=owner.id) == ["INV-2"]
    assert await numbers(q="latitude") == ["INV-1"]
    assert await numbers(location_id=refs.office.id) == []
    assert await numbers(needs_review=True) == []


async def test_visibility_by_role(
    client: AsyncClient, admin_headers: dict[str, str], refs: Refs, db_session: AsyncSession
) -> None:
    department = Department(name="Бухгалтерия")
    other_department = Department(name="Склад")
    db_session.add_all([department, other_department])
    await db_session.flush()
    manager = await make_user(db_session, role=UserRole.MANAGER, department_id=department.id)
    colleague = await make_user(db_session, department_id=department.id)
    stranger = await make_user(db_session, department_id=other_department.id)
    own = await make_asset(
        db_session, refs, inventory_number="INV-C", status=AssetStatus.IN_USE, owner_id=colleague.id
    )
    foreign = await make_asset(
        db_session, refs, inventory_number="INV-S", status=AssetStatus.IN_USE, owner_id=stranger.id
    )
    await make_asset(db_session, refs, inventory_number="INV-W")

    async def visible(user: User) -> list[str]:
        headers = await login(client, user.email)
        response = await client.get("/api/assets", headers=headers)
        return [item["inventory_number"] for item in response.json()["items"]]

    assert await visible(colleague) == ["INV-C"]
    assert await visible(manager) == ["INV-C"]
    admin_view = await client.get("/api/assets", headers=admin_headers)
    assert admin_view.json()["total"] == 3

    colleague_headers = await login(client, colleague.email)
    own_card = await client.get(f"/api/assets/{own.id}", headers=colleague_headers)
    foreign_card = await client.get(f"/api/assets/{foreign.id}", headers=colleague_headers)
    foreign_events = await client.get(f"/api/assets/{foreign.id}/events", headers=colleague_headers)
    assert own_card.status_code == 200
    assert own_card.json()["allowed_operations"] == []
    assert own_card.json()["owner_name"] == colleague.full_name
    assert foreign_card.status_code == 404
    assert foreign_card.json()["error"]["code"] == "asset_not_found"
    assert foreign_events.status_code == 404


async def test_edit_records_changes_and_checks_version(
    client: AsyncClient, admin_headers: dict[str, str], refs: Refs, db_session: AsyncSession
) -> None:
    created = await create_via_api(client, admin_headers, refs)
    url = f"/api/assets/{created['id']}"

    edited = await client.patch(
        url,
        headers=admin_headers,
        json={"version": 1, "model": "Lenovo ThinkPad T14 Gen 5", "initial_cost": "95000"},
    )
    stale = await client.patch(url, headers=admin_headers, json={"version": 1, "model": "X"})

    assert edited.status_code == 200, edited.text
    assert edited.json()["model"] == "Lenovo ThinkPad T14 Gen 5"
    assert edited.json()["version"] == 2
    assert stale.status_code == 409
    assert stale.json()["error"]["code"] == "version_conflict"

    events = (await client.get(f"{url}/events", headers=admin_headers)).json()["items"]
    assert events[0]["event_type"] == "edited"
    assert events[0]["changes"] == {"model": ["Lenovo ThinkPad T14", "Lenovo ThinkPad T14 Gen 5"]}
    assert events[0]["to_status"] is None
    assert events[0]["to_location_id"] is None


async def test_edit_without_changes_keeps_version(
    client: AsyncClient, admin_headers: dict[str, str], refs: Refs
) -> None:
    created = await create_via_api(client, admin_headers, refs)

    response = await client.patch(
        f"/api/assets/{created['id']}",
        headers=admin_headers,
        json={"version": 1, "model": "Lenovo ThinkPad T14"},
    )

    assert response.json()["version"] == 1


async def test_edit_rejects_null_for_required_field_and_duplicate_number(
    client: AsyncClient, admin_headers: dict[str, str], refs: Refs
) -> None:
    first = await create_via_api(client, admin_headers, refs)
    await create_via_api(
        client, admin_headers, refs, inventory_number="INV-002", serial_number=None
    )

    null_model = await client.patch(
        f"/api/assets/{first['id']}", headers=admin_headers, json={"version": 1, "model": None}
    )
    duplicate = await client.patch(
        f"/api/assets/{first['id']}",
        headers=admin_headers,
        json={"version": 1, "inventory_number": "INV-002"},
    )

    assert null_model.status_code == 422
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "inventory_number_taken"


async def test_written_off_asset_cannot_be_edited(
    client: AsyncClient, admin_headers: dict[str, str], refs: Refs, db_session: AsyncSession
) -> None:
    asset = await make_asset(
        db_session, refs, inventory_number="INV-X", status=AssetStatus.WRITTEN_OFF
    )

    response = await client.patch(
        f"/api/assets/{asset.id}", headers=admin_headers, json={"version": 1, "model": "X"}
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "asset_written_off"
```

- [ ] **Step 2: Убедиться, что тесты падают**

Run: `cd backend && uv run pytest -q tests/modules/assets/test_registry_api.py`
Expected: FAIL — запросы к `/api/assets` возвращают 404 (роутера ещё нет)

- [ ] **Step 3: Схемы**

Создать `backend/app/modules/assets/schemas.py`:

```python
from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Any, ClassVar, Literal

from pydantic import AfterValidator, BaseModel, Field

from app.core.schemas import PartialUpdate
from app.modules.assets.models import AssetEventType, AssetStatus
from app.modules.assets.transitions import Operation


def _blank_to_none(value: str | None) -> str | None:
    if value is None:
        return None
    return value.strip() or None


Comment = Annotated[str | None, Field(max_length=1000), AfterValidator(_blank_to_none)]
SerialNumber = Annotated[str | None, Field(max_length=128), AfterValidator(_blank_to_none)]
InventoryNumber = Annotated[str, Field(min_length=1, max_length=64)]
Model = Annotated[str, Field(min_length=1, max_length=200)]
Cost = Annotated[Decimal, Field(ge=0, max_digits=12, decimal_places=2)]
AssetIds = Annotated[list[int], Field(min_length=1, max_length=50)]


class AssetCreate(BaseModel):
    asset_type_id: int
    inventory_number: InventoryNumber
    serial_number: SerialNumber = None
    model: Model
    location_id: int
    accepted_at: date
    purchased_at: date | None = None
    warranty_until: date | None = None
    initial_cost: Cost | None = None
    needs_review: bool = False


class AssetUpdate(PartialUpdate):
    non_nullable: ClassVar[frozenset[str]] = frozenset(
        {"asset_type_id", "inventory_number", "model", "accepted_at", "needs_review"}
    )

    version: int
    asset_type_id: int | None = None
    inventory_number: InventoryNumber | None = None
    serial_number: SerialNumber = None
    model: Model | None = None
    accepted_at: date | None = None
    purchased_at: date | None = None
    warranty_until: date | None = None
    initial_cost: Cost | None = None
    needs_review: bool | None = None


class AssetRead(BaseModel):
    id: int
    asset_type_id: int
    asset_type_name: str
    inventory_number: str
    serial_number: str | None
    model: str
    status: AssetStatus
    location_id: int
    location_name: str
    owner_id: int | None
    owner_name: str | None
    accepted_at: date
    purchased_at: date | None
    warranty_until: date | None
    initial_cost: Decimal | None
    needs_review: bool
    version: int
    created_at: datetime
    updated_at: datetime
    allowed_operations: list[Operation]


class AssetEventRead(BaseModel):
    id: int
    event_type: AssetEventType
    operation: Operation | None
    from_owner_id: int | None
    from_owner_name: str | None
    to_owner_id: int | None
    to_owner_name: str | None
    from_status: AssetStatus | None
    to_status: AssetStatus | None
    from_location_id: int | None
    from_location_name: str | None
    to_location_id: int | None
    to_location_name: str | None
    reason_id: int | None
    reason_name: str | None
    changes: dict[str, Any] | None
    comment: str | None
    performed_by: int
    performed_by_name: str
    created_at: datetime


class IssueOperation(BaseModel):
    operation: Literal[Operation.ISSUE]
    owner_id: int
    reason_id: int | None = None
    comment: Comment = None


class ReturnOperation(BaseModel):
    """Возврат на склад: из работы или из ремонта."""

    operation: Literal[Operation.RETURN, Operation.REPAIR_TO_STOCK]
    location_id: int | None = None
    comment: Comment = None


class StatusOperation(BaseModel):
    """Операции без дополнительных полей."""

    operation: Literal[
        Operation.RESERVE, Operation.UNRESERVE, Operation.TO_REPAIR, Operation.REPAIR_TO_OWNER
    ]
    comment: Comment = None


class WriteOffOperation(BaseModel):
    operation: Literal[Operation.WRITE_OFF]
    reason_id: int | None = None
    """Обязательна; проверяется сервисом, чтобы вернуть код reason_required."""
    comment: Comment = None


class MoveOperation(BaseModel):
    operation: Literal[Operation.MOVE]
    location_id: int
    comment: Comment = None


AssetOperationRequest = Annotated[
    IssueOperation | ReturnOperation | StatusOperation | WriteOffOperation | MoveOperation,
    Field(discriminator="operation"),
]


class AssetIssueRequest(BaseModel):
    owner_id: int
    asset_ids: AssetIds
    reason_id: int | None = None
    comment: Comment = None


class AssetReturnRequest(BaseModel):
    asset_ids: AssetIds
    location_id: int | None = None
    comment: Comment = None


class UnavailableAsset(BaseModel):
    """Элемент details ошибки assets_unavailable."""

    asset_id: int
    inventory_number: str | None
    status: AssetStatus | None
```

- [ ] **Step 4: Область видимости, проверки, история**

Создать `backend/app/modules/assets/access.py`:

```python
"""Область видимости реестра (п. 2.3 ТЗ): Employee — своя техника, Manager — отдела, Admin — всё."""

from sqlalchemy import ColumnElement, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.modules.assets.models import Asset
from app.modules.users_auth.service import CurrentUser, UserRole, list_department_user_ids


async def visibility_filter(session: AsyncSession, user: CurrentUser) -> ColumnElement[bool] | None:
    """Условие на видимые пользователю активы; None — ограничений нет."""
    if user.role == UserRole.ADMIN:
        return None
    if user.role == UserRole.MANAGER and user.department_id is not None:
        member_ids = await list_department_user_ids(session, user.department_id)
        return Asset.owner_id.in_(member_ids)
    return Asset.owner_id == user.id


async def get_visible_asset(
    session: AsyncSession, user: CurrentUser, asset_id: int, *, for_update: bool = False
) -> Asset:
    """Актив в области видимости пользователя; иначе 404, чтобы не раскрывать его существование."""
    stmt = select(Asset).where(Asset.id == asset_id)
    condition = await visibility_filter(session, user)
    if condition is not None:
        stmt = stmt.where(condition)
    if for_update:
        stmt = stmt.with_for_update()
    asset = await session.scalar(stmt)
    if asset is None:
        raise NotFoundError("Техника не найдена", code="asset_not_found")
    return asset
```

Создать `backend/app/modules/assets/checks.py`:

```python
"""Проверки ссылок на справочники и пользователей (ошибки 422 с кодом поля)."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ValidationFailedError
from app.modules.directories.service import get_reference_item
from app.modules.users_auth.service import get_user_info


async def check_asset_type(session: AsyncSession, asset_type_id: int) -> None:
    item = await get_reference_item(session, "asset-types", asset_type_id)
    if item is None or not item.is_active:
        raise ValidationFailedError(
            "Тип техники не найден или деактивирован", code="asset_type_invalid"
        )


async def check_location(session: AsyncSession, location_id: int) -> None:
    item = await get_reference_item(session, "locations", location_id)
    if item is None or not item.is_active:
        raise ValidationFailedError(
            "Локация не найдена или деактивирована", code="location_invalid"
        )


async def check_reason(session: AsyncSession, reason_id: int) -> None:
    item = await get_reference_item(session, "issue-reasons", reason_id)
    if item is None or not item.is_active or item.applicability == "stock":
        raise ValidationFailedError(
            "Причина не найдена, деактивирована или не применяется к технике",
            code="reason_invalid",
        )


async def check_recipient(session: AsyncSession, user_id: int) -> None:
    info = await get_user_info(session, user_id)
    if info is None or not info.is_active:
        raise ValidationFailedError(
            "Получатель не найден или деактивирован", code="recipient_invalid"
        )
```

Создать `backend/app/modules/assets/history.py`:

```python
"""Запись истории актива: AssetEvent и общий AuditLog."""

from dataclasses import asdict, dataclass
from decimal import Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import diff_values, record_audit
from app.modules.assets.models import Asset, AssetEvent, AssetEventType, AssetStatus

ENTITY_TYPE = "asset"


@dataclass(frozen=True)
class Placement:
    """Статус, владелец и локация актива — то, что меняют операции."""

    status: AssetStatus
    owner_id: int | None
    location_id: int

    @classmethod
    def of(cls, asset: Asset) -> "Placement":
        return cls(status=asset.status, owner_id=asset.owner_id, location_id=asset.location_id)


def jsonable(values: dict[str, Any]) -> dict[str, Any]:
    """Decimal → str: diff_values и JSONB не умеют Decimal."""
    return {
        key: str(value) if isinstance(value, Decimal) else value for key, value in values.items()
    }


def changed_fields(before: dict[str, Any], after: dict[str, Any]) -> dict[str, list[Any]]:
    """Изменившиеся поля в виде {поле: [было, стало]}; сравнение по исходным значениям
    (Decimal("1000") == Decimal("1000.00")), в ответ — JSON-совместимые."""
    keys = [key for key, value in after.items() if before.get(key) != value]
    return diff_values(
        jsonable({key: before.get(key) for key in keys}),
        jsonable({key: after[key] for key in keys}),
    )


def record_event(
    session: AsyncSession,
    asset: Asset,
    *,
    event_type: AssetEventType,
    actor_id: int,
    before: Placement | None,
    operation: str | None = None,
    reason_id: int | None = None,
    changes: dict[str, list[Any]] | None = None,
    comment: str | None = None,
) -> None:
    """Пишет событие и аудит. В событии заполняются только изменившиеся пары «было/стало».

    before=None — создание: «было» пусто, «стало» — текущие статус, владелец и локация.
    """
    after = Placement.of(asset)
    event = AssetEvent(
        asset_id=asset.id,
        event_type=event_type,
        operation=operation,
        reason_id=reason_id,
        changes=changes,
        comment=comment,
        performed_by=actor_id,
    )
    if before is None or before.status != after.status:
        event.from_status = before.status if before else None
        event.to_status = after.status
    if (before.owner_id if before else None) != after.owner_id:
        event.from_owner_id = before.owner_id if before else None
        event.to_owner_id = after.owner_id
    if before is None or before.location_id != after.location_id:
        event.from_location_id = before.location_id if before else None
        event.to_location_id = after.location_id
    session.add(event)

    if changes is not None:
        audit_diff = changes
    else:
        audit_diff = diff_values(asdict(before) if before else {}, asdict(after))
    record_audit(
        session,
        entity_type=ENTITY_TYPE,
        entity_id=asset.id,
        user_id=actor_id,
        action=operation or event_type.value,
        diff=audit_diff,
    )
```

- [ ] **Step 5: Сборка ответов и реестр**

Создать `backend/app/modules/assets/presenter.py`:

```python
"""Сборка ответов API: подставляет названия справочников и ФИО через service других модулей."""

from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.assets.models import Asset, AssetEvent
from app.modules.assets.schemas import AssetEventRead, AssetRead
from app.modules.assets.transitions import Operation, allowed_operations
from app.modules.directories.service import get_reference_names
from app.modules.users_auth.service import CurrentUser, UserRole, get_user_names


def _ids(*values: int | None) -> set[int]:
    return {value for value in values if value is not None}


async def assets_to_read(
    session: AsyncSession, assets: Sequence[Asset], user: CurrentUser
) -> list[AssetRead]:
    types = await get_reference_names(
        session, "asset-types", {asset.asset_type_id for asset in assets}
    )
    locations = await get_reference_names(
        session, "locations", {asset.location_id for asset in assets}
    )
    owners = await get_user_names(session, _ids(*(asset.owner_id for asset in assets)))
    can_operate = user.role == UserRole.ADMIN
    return [
        AssetRead(
            id=asset.id,
            asset_type_id=asset.asset_type_id,
            asset_type_name=types.get(asset.asset_type_id, ""),
            inventory_number=asset.inventory_number,
            serial_number=asset.serial_number,
            model=asset.model,
            status=asset.status,
            location_id=asset.location_id,
            location_name=locations.get(asset.location_id, ""),
            owner_id=asset.owner_id,
            owner_name=owners.get(asset.owner_id) if asset.owner_id is not None else None,
            accepted_at=asset.accepted_at,
            purchased_at=asset.purchased_at,
            warranty_until=asset.warranty_until,
            initial_cost=asset.initial_cost,
            needs_review=asset.needs_review,
            version=asset.version,
            created_at=asset.created_at,
            updated_at=asset.updated_at,
            allowed_operations=allowed_operations(asset.status, asset.owner_id)
            if can_operate
            else [],
        )
        for asset in assets
    ]


async def asset_to_read(session: AsyncSession, asset: Asset, user: CurrentUser) -> AssetRead:
    return (await assets_to_read(session, [asset], user))[0]


async def events_to_read(
    session: AsyncSession, events: Sequence[AssetEvent]
) -> list[AssetEventRead]:
    users = await get_user_names(
        session,
        _ids(
            *(event.from_owner_id for event in events),
            *(event.to_owner_id for event in events),
            *(event.performed_by for event in events),
        ),
    )
    locations = await get_reference_names(
        session,
        "locations",
        _ids(
            *(event.from_location_id for event in events),
            *(event.to_location_id for event in events),
        ),
    )
    reasons = await get_reference_names(
        session, "issue-reasons", _ids(*(event.reason_id for event in events))
    )

    def name(names: dict[int, str], item_id: int | None) -> str | None:
        return names.get(item_id) if item_id is not None else None

    return [
        AssetEventRead(
            id=event.id,
            event_type=event.event_type,
            operation=Operation(event.operation) if event.operation else None,
            from_owner_id=event.from_owner_id,
            from_owner_name=name(users, event.from_owner_id),
            to_owner_id=event.to_owner_id,
            to_owner_name=name(users, event.to_owner_id),
            from_status=event.from_status,
            to_status=event.to_status,
            from_location_id=event.from_location_id,
            from_location_name=name(locations, event.from_location_id),
            to_location_id=event.to_location_id,
            to_location_name=name(locations, event.to_location_id),
            reason_id=event.reason_id,
            reason_name=name(reasons, event.reason_id),
            changes=event.changes,
            comment=event.comment,
            performed_by=event.performed_by,
            performed_by_name=users.get(event.performed_by, ""),
            created_at=event.created_at,
        )
        for event in events
    ]
```

Создать `backend/app/modules/assets/registry.py`:

```python
"""Реестр техники: список, карточка, история, создание и правка."""

from dataclasses import dataclass
from typing import Any, NoReturn

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import constraint_name
from app.core.errors import ConflictError
from app.core.text import normalize_text_field
from app.modules.assets.access import get_visible_asset, visibility_filter
from app.modules.assets.checks import check_asset_type, check_location
from app.modules.assets.history import Placement, changed_fields, record_event
from app.modules.assets.models import Asset, AssetEvent, AssetEventType, AssetStatus
from app.modules.users_auth.service import CurrentUser


@dataclass(frozen=True)
class AssetFilters:
    statuses: list[AssetStatus] | None = None
    asset_type_id: int | None = None
    owner_id: int | None = None
    location_id: int | None = None
    needs_review: bool | None = None
    q: str | None = None


def raise_asset_integrity_error(exc: IntegrityError) -> NoReturn:
    name = constraint_name(exc)
    if name == "uq_assets_inventory_number":
        raise ConflictError(
            "Техника с таким инвентарным номером уже есть", code="inventory_number_taken"
        ) from exc
    if name == "uq_assets_serial_number":
        raise ConflictError(
            "Техника с таким серийным номером уже есть", code="serial_number_taken"
        ) from exc
    raise exc


def _normalize(values: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(values)
    if isinstance(normalized.get("inventory_number"), str):
        normalized["inventory_number"] = normalize_text_field(
            normalized["inventory_number"],
            code="inventory_number_blank",
            message="Инвентарный номер не может быть пустым",
        )
    if isinstance(normalized.get("model"), str):
        normalized["model"] = normalize_text_field(
            normalized["model"], code="model_blank", message="Модель не может быть пустой"
        )
    return normalized


async def list_assets(
    session: AsyncSession, user: CurrentUser, filters: AssetFilters, *, limit: int, offset: int
) -> tuple[list[Asset], int]:
    stmt = select(Asset)
    condition = await visibility_filter(session, user)
    if condition is not None:
        stmt = stmt.where(condition)
    if filters.statuses:
        stmt = stmt.where(Asset.status.in_(filters.statuses))
    else:
        stmt = stmt.where(Asset.status != AssetStatus.WRITTEN_OFF)
    if filters.asset_type_id is not None:
        stmt = stmt.where(Asset.asset_type_id == filters.asset_type_id)
    if filters.owner_id is not None:
        stmt = stmt.where(Asset.owner_id == filters.owner_id)
    if filters.location_id is not None:
        stmt = stmt.where(Asset.location_id == filters.location_id)
    if filters.needs_review is not None:
        stmt = stmt.where(Asset.needs_review.is_(filters.needs_review))
    if filters.q and filters.q.strip():
        pattern = f"%{filters.q.strip()}%"
        stmt = stmt.where(
            or_(
                Asset.inventory_number.ilike(pattern),
                Asset.serial_number.ilike(pattern),
                Asset.model.ilike(pattern),
            )
        )
    total = await session.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = await session.scalars(
        stmt.order_by(Asset.inventory_number, Asset.id).limit(limit).offset(offset)
    )
    return list(rows), total


async def list_events(
    session: AsyncSession, user: CurrentUser, asset_id: int, *, limit: int, offset: int
) -> tuple[list[AssetEvent], int]:
    await get_visible_asset(session, user, asset_id)
    total = (
        await session.scalar(
            select(func.count()).select_from(AssetEvent).where(AssetEvent.asset_id == asset_id)
        )
        or 0
    )
    rows = await session.scalars(
        select(AssetEvent)
        .where(AssetEvent.asset_id == asset_id)
        .order_by(AssetEvent.id.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(rows), total


async def create_asset(session: AsyncSession, *, actor_id: int, data: dict[str, Any]) -> Asset:
    data = _normalize(data)
    await check_asset_type(session, data["asset_type_id"])
    await check_location(session, data["location_id"])
    asset = Asset(**data, status=AssetStatus.IN_STOCK, owner_id=None, version=1)
    try:
        async with session.begin_nested():
            session.add(asset)
    except IntegrityError as exc:
        raise_asset_integrity_error(exc)
    record_event(
        session,
        asset,
        event_type=AssetEventType.CREATED,
        actor_id=actor_id,
        before=None,
    )
    await session.commit()
    return asset


async def update_asset(
    session: AsyncSession,
    actor: CurrentUser,
    *,
    asset_id: int,
    version: int,
    updates: dict[str, Any],
) -> Asset:
    asset = await get_visible_asset(session, actor, asset_id, for_update=True)
    if asset.status == AssetStatus.WRITTEN_OFF:
        raise ConflictError("Списанную технику нельзя редактировать", code="asset_written_off")
    if asset.version != version:
        raise ConflictError(
            "Данные изменил другой пользователь",
            code="version_conflict",
            details={"version": asset.version},
        )
    updates = _normalize(updates)
    changes = changed_fields({key: getattr(asset, key) for key in updates}, updates)
    if not changes:
        return asset
    if "asset_type_id" in changes:
        await check_asset_type(session, updates["asset_type_id"])
    try:
        async with session.begin_nested():
            for key in changes:
                setattr(asset, key, updates[key])
            asset.version += 1
    except IntegrityError as exc:
        raise_asset_integrity_error(exc)
    record_event(
        session,
        asset,
        event_type=AssetEventType.EDITED,
        actor_id=actor.id,
        before=Placement.of(asset),
        changes=changes,
    )
    await session.commit()
    return asset
```

- [ ] **Step 6: Роутер и подключение**

Создать `backend/app/modules/assets/router.py` — операции добавятся в Task 5:

```python
from typing import Annotated

from fastapi import APIRouter, Query

from app.core.db import SessionDep
from app.core.schemas import Page, PaginationDep
from app.modules.assets import registry
from app.modules.assets.access import get_visible_asset
from app.modules.assets.models import AssetStatus
from app.modules.assets.presenter import asset_to_read, assets_to_read, events_to_read
from app.modules.assets.schemas import (
    AssetCreate,
    AssetEventRead,
    AssetRead,
    AssetUpdate,
)
from app.modules.users_auth.service import AdminDep, CurrentUserDep

router = APIRouter(prefix="/assets", tags=["assets"])


@router.get("", response_model=Page[AssetRead])
async def list_assets(
    session: SessionDep,
    user: CurrentUserDep,
    pagination: PaginationDep,
    status: Annotated[list[AssetStatus] | None, Query()] = None,
    asset_type_id: int | None = None,
    owner_id: int | None = None,
    location_id: int | None = None,
    needs_review: bool | None = None,
    q: Annotated[str | None, Query(max_length=100)] = None,
) -> Page[AssetRead]:
    filters = registry.AssetFilters(
        statuses=status,
        asset_type_id=asset_type_id,
        owner_id=owner_id,
        location_id=location_id,
        needs_review=needs_review,
        q=q,
    )
    items, total = await registry.list_assets(
        session, user, filters, limit=pagination.limit, offset=pagination.offset
    )
    return Page(
        items=await assets_to_read(session, items, user),
        total=total,
        limit=pagination.limit,
        offset=pagination.offset,
    )


@router.post("", response_model=AssetRead, status_code=201)
async def create_asset(body: AssetCreate, session: SessionDep, admin: AdminDep) -> AssetRead:
    asset = await registry.create_asset(session, actor_id=admin.id, data=body.model_dump())
    return await asset_to_read(session, asset, admin)


@router.get("/{asset_id}", response_model=AssetRead)
async def get_asset(asset_id: int, session: SessionDep, user: CurrentUserDep) -> AssetRead:
    asset = await get_visible_asset(session, user, asset_id)
    return await asset_to_read(session, asset, user)


@router.patch("/{asset_id}", response_model=AssetRead)
async def update_asset(
    asset_id: int, body: AssetUpdate, session: SessionDep, admin: AdminDep
) -> AssetRead:
    updates = body.model_dump(exclude_unset=True, exclude={"version"})
    asset = await registry.update_asset(
        session, admin, asset_id=asset_id, version=body.version, updates=updates
    )
    return await asset_to_read(session, asset, admin)


@router.get("/{asset_id}/events", response_model=Page[AssetEventRead])
async def list_asset_events(
    asset_id: int, session: SessionDep, user: CurrentUserDep, pagination: PaginationDep
) -> Page[AssetEventRead]:
    events, total = await registry.list_events(
        session, user, asset_id, limit=pagination.limit, offset=pagination.offset
    )
    return Page(
        items=await events_to_read(session, events),
        total=total,
        limit=pagination.limit,
        offset=pagination.offset,
    )
```

В `backend/app/main.py` заменить:

```python
from app.core.middleware import RequestIdMiddleware
```

на:

```python
from app.core.middleware import RequestIdMiddleware
from app.modules.assets.router import router as assets_router
```

В `backend/app/main.py` заменить:

```python
    for router in (auth_router, admin_users_router, users_router, *directories_routers):
```

на:

```python
    for router in (
        auth_router,
        admin_users_router,
        users_router,
        *directories_routers,
        assets_router,
    ):
```

- [ ] **Step 7: Тесты проходят; OpenAPI и типы фронтенда обновлены**

Run: `cd backend && uv run pytest -q tests/modules/assets`
Expected: PASS

Run: `make gen-api`
Expected: `openapi.json` и `frontend/src/api/schema.d.ts` перезаписаны

Run: `make test`
Expected: PASS, включая `test_committed_openapi_schema_is_up_to_date`

Run: `make lint`
Expected: ruff, mypy и import-linter без ошибок (`Contracts: N kept, 0 broken.`)

- [ ] **Step 8: Коммит**

```bash
git add backend frontend/src/api/schema.d.ts && git commit -m "feat(assets): реестр техники — создание, список, карточка, история, правка"
```

### Task 5: Операции: одиночные, массовые выдача и возврат, гонка

Строка актива блокируется `SELECT … FOR UPDATE`, статус проверяется под блокировкой; массовые операции блокируют строки в порядке `id` и работают по принципу «всё или ничего». Тест гонки работает на реальных коммитах в двух соединениях (обычная фикстура откатывает транзакцию и параллельности не даёт) и сам убирает за собой данные. Проверено: если убрать `for_update=True`, тест гонки стабильно падает.

**Files:**
- Create: `backend/app/modules/assets/operations.py`
- Modify: `backend/app/modules/assets/router.py`
- Modify: `backend/openapi.json`, `frontend/src/api/schema.d.ts` (генерируются)
- Test: `backend/tests/modules/assets/test_operations_api.py`, `backend/tests/modules/assets/test_concurrency.py`

**Interfaces:**
- Consumes: `TRANSITIONS`, `is_allowed`, `OwnerRule` (Task 2); `get_visible_asset`, `check_*`, `Placement`, `record_event`, схемы операций, `assets_to_read` (Task 4).
- Produces: `operations.apply_operation(session, actor, asset_id, request) -> Asset` (409 `operation_not_allowed`, `details: {"status": ...}`; 422 `reason_required`), `operations.issue_assets(session, actor, *, owner_id, asset_ids, reason_id, comment) -> list[Asset]`, `operations.return_assets(session, actor, *, asset_ids, location_id, comment) -> list[Asset]` (409 `assets_unavailable`, `details` — список `UnavailableAsset`, по возрастанию `asset_id`). Эндпоинты `POST /api/assets/{asset_id}/operations`, `POST /api/assets/issue`, `POST /api/assets/return` — только Admin, ответ — `AssetRead` / `list[AssetRead]` по возрастанию `id`.

- [ ] **Step 1: Написать падающие тесты**

Создать `backend/tests/modules/assets/test_operations_api.py`:

```python
from typing import Any

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import AuditLog
from app.modules.assets.models import AssetStatus
from app.modules.users_auth.models import UserRole
from tests.factories import login, make_user
from tests.modules.assets.conftest import Refs, make_asset


async def _operate(client: AsyncClient, headers: dict[str, str], asset_id: int, **body: Any) -> Any:
    return await client.post(f"/api/assets/{asset_id}/operations", headers=headers, json=body)


def _error_code(response: Any) -> str:
    code: str = response.json()["error"]["code"]
    return code


async def test_full_lifecycle_updates_owner_and_history(
    client: AsyncClient, admin_headers: dict[str, str], refs: Refs, db_session: AsyncSession
) -> None:
    employee = await make_user(db_session, full_name="Петров Пётр")
    asset = await make_asset(db_session, refs, inventory_number="INV-1")

    issued = await _operate(
        client,
        admin_headers,
        asset.id,
        operation="issue",
        owner_id=employee.id,
        reason_id=refs.new_employee.id,
        comment="Выдан",
    )
    assert issued.status_code == 200, issued.text
    assert issued.json()["status"] == "in_use"
    assert issued.json()["owner_name"] == "Петров Пётр"
    assert issued.json()["version"] == 2

    repaired = await _operate(client, admin_headers, asset.id, operation="to_repair")
    assert repaired.json()["status"] == "in_repair"
    assert repaired.json()["owner_id"] == employee.id
    assert "repair_to_owner" in repaired.json()["allowed_operations"]

    back = await _operate(client, admin_headers, asset.id, operation="repair_to_owner")
    assert back.json()["status"] == "in_use"
    assert back.json()["owner_id"] == employee.id

    returned = await _operate(
        client, admin_headers, asset.id, operation="return", location_id=refs.office.id
    )
    assert returned.json()["status"] == "in_stock"
    assert returned.json()["owner_id"] is None
    assert returned.json()["location_name"] == "Офис, каб. 101"

    written_off = await _operate(
        client, admin_headers, asset.id, operation="write_off", reason_id=refs.broken.id
    )
    assert written_off.json()["status"] == "written_off"
    assert written_off.json()["allowed_operations"] == []

    events = (await client.get(f"/api/assets/{asset.id}/events", headers=admin_headers)).json()[
        "items"
    ]
    assert [event["operation"] for event in events] == [
        "write_off",
        "return",
        "repair_to_owner",
        "to_repair",
        "issue",
    ]
    issue_event = events[-1]
    assert issue_event["event_type"] == "issued"
    assert issue_event["from_status"] == "in_stock"
    assert issue_event["to_status"] == "in_use"
    assert issue_event["to_owner_name"] == "Петров Пётр"
    assert issue_event["reason_name"] == "Новый сотрудник"
    assert issue_event["comment"] == "Выдан"
    return_event = events[1]
    assert return_event["event_type"] == "returned"
    assert return_event["from_owner_name"] == "Петров Пётр"
    assert return_event["to_owner_id"] is None
    assert return_event["from_location_name"] == "Склад"
    assert return_event["to_location_name"] == "Офис, каб. 101"
    audit = await db_session.scalars(
        select(AuditLog.action)
        .where(AuditLog.entity_type == "asset", AuditLog.entity_id == str(asset.id))
        .order_by(AuditLog.id)
    )
    assert list(audit) == ["issue", "to_repair", "repair_to_owner", "return", "write_off"]


async def test_move_changes_only_location(
    client: AsyncClient, admin_headers: dict[str, str], refs: Refs, db_session: AsyncSession
) -> None:
    owner = await make_user(db_session)
    asset = await make_asset(
        db_session, refs, inventory_number="INV-1", status=AssetStatus.IN_USE, owner_id=owner.id
    )

    moved = await _operate(
        client, admin_headers, asset.id, operation="move", location_id=refs.office.id
    )

    assert moved.status_code == 200, moved.text
    assert moved.json()["status"] == "in_use"
    assert moved.json()["owner_id"] == owner.id
    assert moved.json()["location_id"] == refs.office.id


async def test_operation_not_allowed_from_current_status(
    client: AsyncClient, admin_headers: dict[str, str], refs: Refs, db_session: AsyncSession
) -> None:
    asset = await make_asset(db_session, refs, inventory_number="INV-1")

    response = await _operate(client, admin_headers, asset.id, operation="return")

    assert response.status_code == 409
    assert _error_code(response) == "operation_not_allowed"
    assert response.json()["error"]["details"] == {"status": "in_stock"}


async def test_operation_validation_errors(
    client: AsyncClient, admin_headers: dict[str, str], refs: Refs, db_session: AsyncSession
) -> None:
    inactive = await make_user(db_session, is_active=False)
    asset = await make_asset(db_session, refs, inventory_number="INV-1")

    no_reason = await _operate(client, admin_headers, asset.id, operation="write_off")
    stock_reason = await _operate(
        client, admin_headers, asset.id, operation="write_off", reason_id=refs.stock_only.id
    )
    inactive_owner = await _operate(
        client, admin_headers, asset.id, operation="issue", owner_id=inactive.id
    )
    move_without_location = await _operate(client, admin_headers, asset.id, operation="move")
    unknown = await _operate(client, admin_headers, asset.id, operation="teleport")

    assert _error_code(no_reason) == "reason_required"
    assert _error_code(stock_reason) == "reason_invalid"
    assert _error_code(inactive_owner) == "recipient_invalid"
    assert move_without_location.status_code == 422
    assert unknown.status_code == 422


async def test_operations_require_admin(
    client: AsyncClient, refs: Refs, db_session: AsyncSession
) -> None:
    manager = await make_user(db_session, role=UserRole.MANAGER)
    asset = await make_asset(db_session, refs, inventory_number="INV-1")
    headers = await login(client, manager.email)

    single = await _operate(client, headers, asset.id, operation="reserve")
    bulk = await client.post(
        "/api/assets/issue", headers=headers, json={"owner_id": manager.id, "asset_ids": [asset.id]}
    )

    assert single.status_code == 403
    assert bulk.status_code == 403


async def test_bulk_issue_and_return(
    client: AsyncClient, admin_headers: dict[str, str], refs: Refs, db_session: AsyncSession
) -> None:
    employee = await make_user(db_session)
    first = await make_asset(db_session, refs, inventory_number="INV-1")
    second = await make_asset(db_session, refs, inventory_number="INV-2")

    issued = await client.post(
        "/api/assets/issue",
        headers=admin_headers,
        json={
            "owner_id": employee.id,
            "asset_ids": [second.id, first.id, first.id],
            "reason_id": refs.new_employee.id,
        },
    )
    assert issued.status_code == 200, issued.text
    assert [item["inventory_number"] for item in issued.json()] == ["INV-1", "INV-2"]
    assert {item["owner_id"] for item in issued.json()} == {employee.id}

    returned = await client.post(
        "/api/assets/return",
        headers=admin_headers,
        json={"asset_ids": [first.id, second.id], "location_id": refs.office.id},
    )
    assert returned.status_code == 200, returned.text
    assert {item["status"] for item in returned.json()} == {"in_stock"}
    assert {item["location_id"] for item in returned.json()} == {refs.office.id}


async def test_bulk_issue_is_all_or_nothing(
    client: AsyncClient, admin_headers: dict[str, str], refs: Refs, db_session: AsyncSession
) -> None:
    employee = await make_user(db_session)
    free = await make_asset(db_session, refs, inventory_number="INV-1")
    taken = await make_asset(
        db_session, refs, inventory_number="INV-2", status=AssetStatus.IN_USE, owner_id=employee.id
    )

    response = await client.post(
        "/api/assets/issue",
        headers=admin_headers,
        json={"owner_id": employee.id, "asset_ids": [free.id, taken.id, 999999]},
    )

    assert response.status_code == 409
    assert _error_code(response) == "assets_unavailable"
    assert response.json()["error"]["details"] == [
        {"asset_id": taken.id, "inventory_number": "INV-2", "status": "in_use"},
        {"asset_id": 999999, "inventory_number": None, "status": None},
    ]
    await db_session.refresh(free)
    assert free.status == AssetStatus.IN_STOCK
```

Создать `backend/tests/modules/assets/test_concurrency.py`:

```python
"""Параллельная выдача одного актива: реальные транзакции в двух соединениях (п. 3.2 ТЗ)."""

import asyncio
from collections.abc import AsyncIterator
from datetime import date

import pytest
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.audit import AuditLog
from app.core.config import get_settings
from app.core.errors import ConflictError
from app.modules.assets import operations
from app.modules.assets.models import Asset, AssetEvent, AssetStatus
from app.modules.assets.schemas import IssueOperation
from app.modules.assets.transitions import Operation
from app.modules.directories.models import AssetType, Location
from app.modules.users_auth.models import User, UserRole
from app.modules.users_auth.service import CurrentUser
from tests.factories import make_user


@pytest.fixture
async def engine() -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(get_settings().database_url, poolclass=NullPool)
    yield engine
    await engine.dispose()


async def test_parallel_issue_of_same_asset_one_wins(engine: AsyncEngine) -> None:
    async with AsyncSession(engine, expire_on_commit=False) as setup:
        admin = await make_user(setup, email="race-admin@company.ru", role=UserRole.ADMIN)
        first = await make_user(setup, email="race-1@company.ru")
        second = await make_user(setup, email="race-2@company.ru")
        asset_type = AssetType(name="Гонка: ноутбук")
        location = Location(name="Гонка: склад")
        setup.add_all([asset_type, location])
        await setup.flush()
        asset = Asset(
            asset_type_id=asset_type.id,
            inventory_number="RACE-1",
            model="Модель",
            status=AssetStatus.IN_STOCK,
            location_id=location.id,
            accepted_at=date(2026, 1, 1),
            needs_review=False,
            version=1,
        )
        setup.add(asset)
        await setup.commit()

    actor = CurrentUser(
        id=admin.id,
        email=admin.email,
        full_name=admin.full_name,
        role=UserRole.ADMIN,
        department_id=None,
        must_change_password=False,
    )

    async def issue_to(owner: User) -> str:
        async with AsyncSession(engine, expire_on_commit=False) as session:
            try:
                await operations.apply_operation(
                    session,
                    actor,
                    asset.id,
                    IssueOperation(operation=Operation.ISSUE, owner_id=owner.id),
                )
            except ConflictError as exc:
                return exc.code
            return "ok"

    try:
        results = await asyncio.gather(issue_to(first), issue_to(second))

        assert sorted(results) == ["ok", "operation_not_allowed"]
        async with AsyncSession(engine) as check:
            stored = await check.get(Asset, asset.id)
            assert stored is not None
            assert stored.status == AssetStatus.IN_USE
            assert stored.version == 2
    finally:
        async with AsyncSession(engine) as cleanup:
            await cleanup.execute(delete(AssetEvent).where(AssetEvent.asset_id == asset.id))
            await cleanup.execute(delete(AuditLog).where(AuditLog.user_id == admin.id))
            await cleanup.execute(delete(Asset).where(Asset.id == asset.id))
            await cleanup.execute(delete(AssetType).where(AssetType.id == asset_type.id))
            await cleanup.execute(delete(Location).where(Location.id == location.id))
            await cleanup.execute(delete(User).where(User.id.in_([admin.id, first.id, second.id])))
            await cleanup.commit()
```

- [ ] **Step 2: Убедиться, что тесты падают**

Run: `cd backend && uv run pytest -q tests/modules/assets/test_operations_api.py tests/modules/assets/test_concurrency.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.modules.assets.operations'`

- [ ] **Step 3: Операции**

Создать `backend/app/modules/assets/operations.py`:

```python
"""Операции над активами по таблице переходов: одиночные и массовые выдача и возврат.

Строки активов блокируются SELECT … FOR UPDATE (массово — в порядке id, чтобы не было
взаимных блокировок); статус проверяется уже под блокировкой, поэтому параллельная
выдача того же актива получает 409 (п. 3.2 ТЗ).
"""

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError, ValidationFailedError
from app.modules.assets.access import get_visible_asset
from app.modules.assets.checks import check_location, check_reason, check_recipient
from app.modules.assets.history import Placement, record_event
from app.modules.assets.models import Asset, AssetStatus
from app.modules.assets.schemas import (
    AssetOperationRequest,
    IssueOperation,
    MoveOperation,
    ReturnOperation,
    UnavailableAsset,
    WriteOffOperation,
)
from app.modules.assets.transitions import TRANSITIONS, Operation, OwnerRule, is_allowed
from app.modules.users_auth.service import CurrentUser


@dataclass(frozen=True)
class OperationInput:
    """Поля операции после разбора запроса; None — не задано."""

    operation: Operation
    owner_id: int | None = None
    location_id: int | None = None
    reason_id: int | None = None
    comment: str | None = None


def _to_input(request: AssetOperationRequest) -> OperationInput:
    operation = Operation(request.operation)
    match request:
        case IssueOperation():
            return OperationInput(
                operation,
                owner_id=request.owner_id,
                reason_id=request.reason_id,
                comment=request.comment,
            )
        case ReturnOperation() | MoveOperation():
            return OperationInput(
                operation, location_id=request.location_id, comment=request.comment
            )
        case WriteOffOperation():
            return OperationInput(operation, reason_id=request.reason_id, comment=request.comment)
        case _:
            return OperationInput(operation, comment=request.comment)


async def _validate(session: AsyncSession, data: OperationInput) -> None:
    if data.operation == Operation.WRITE_OFF and data.reason_id is None:
        raise ValidationFailedError("Укажите причину списания", code="reason_required")
    if data.owner_id is not None:
        await check_recipient(session, data.owner_id)
    if data.reason_id is not None:
        await check_reason(session, data.reason_id)
    if data.location_id is not None:
        await check_location(session, data.location_id)


def _apply(session: AsyncSession, asset: Asset, data: OperationInput, actor_id: int) -> None:
    transition = TRANSITIONS[data.operation]
    before = Placement.of(asset)
    if transition.to_status is not None:
        asset.status = transition.to_status
    if transition.owner == OwnerRule.SET:
        asset.owner_id = data.owner_id
    elif transition.owner == OwnerRule.CLEAR:
        asset.owner_id = None
    if data.location_id is not None:
        asset.location_id = data.location_id
    asset.version += 1
    record_event(
        session,
        asset,
        event_type=transition.event_type,
        actor_id=actor_id,
        before=before,
        operation=data.operation.value,
        reason_id=data.reason_id,
        comment=data.comment,
    )


async def apply_operation(
    session: AsyncSession, actor: CurrentUser, asset_id: int, request: AssetOperationRequest
) -> Asset:
    data = _to_input(request)
    await _validate(session, data)
    asset = await get_visible_asset(session, actor, asset_id, for_update=True)
    if not is_allowed(data.operation, asset.status, asset.owner_id):
        raise ConflictError(
            "Операция недоступна в текущем статусе техники",
            code="operation_not_allowed",
            details={"status": asset.status.value},
        )
    _apply(session, asset, data, actor.id)
    await session.flush()
    await session.commit()
    return asset


async def _lock_for_bulk(
    session: AsyncSession, asset_ids: list[int], required_status: AssetStatus
) -> list[Asset]:
    """Блокирует активы; если хоть один не найден или не в нужном статусе — 409 целиком."""
    unique_ids = sorted(set(asset_ids))
    assets = list(
        await session.scalars(
            select(Asset).where(Asset.id.in_(unique_ids)).order_by(Asset.id).with_for_update()
        )
    )
    found = {asset.id: asset for asset in assets}
    unavailable = [
        UnavailableAsset(
            asset_id=asset_id,
            inventory_number=found[asset_id].inventory_number if asset_id in found else None,
            status=found[asset_id].status if asset_id in found else None,
        )
        for asset_id in unique_ids
        if asset_id not in found or found[asset_id].status != required_status
    ]
    if unavailable:
        raise ConflictError(
            "Часть техники недоступна для операции",
            code="assets_unavailable",
            details=[item.model_dump(mode="json") for item in unavailable],
        )
    return assets


async def issue_assets(
    session: AsyncSession,
    actor: CurrentUser,
    *,
    owner_id: int,
    asset_ids: list[int],
    reason_id: int | None,
    comment: str | None,
) -> list[Asset]:
    data = OperationInput(Operation.ISSUE, owner_id=owner_id, reason_id=reason_id, comment=comment)
    await _validate(session, data)
    assets = await _lock_for_bulk(session, asset_ids, AssetStatus.IN_STOCK)
    for asset in assets:
        _apply(session, asset, data, actor.id)
    await session.flush()
    await session.commit()
    return assets


async def return_assets(
    session: AsyncSession,
    actor: CurrentUser,
    *,
    asset_ids: list[int],
    location_id: int | None,
    comment: str | None,
) -> list[Asset]:
    data = OperationInput(Operation.RETURN, location_id=location_id, comment=comment)
    await _validate(session, data)
    assets = await _lock_for_bulk(session, asset_ids, AssetStatus.IN_USE)
    for asset in assets:
        _apply(session, asset, data, actor.id)
    await session.flush()
    await session.commit()
    return assets
```

- [ ] **Step 4: Эндпоинты**

В `backend/app/modules/assets/router.py` заменить:

```python
from fastapi import APIRouter, Query
```

на:

```python
from fastapi import APIRouter, Body, Query
```

В `backend/app/modules/assets/router.py` заменить:

```python
from app.modules.assets import registry
```

на:

```python
from app.modules.assets import operations, registry
```

В `backend/app/modules/assets/router.py` заменить:

```python
    AssetEventRead,
    AssetRead,
    AssetUpdate,
```

на:

```python
    AssetEventRead,
    AssetIssueRequest,
    AssetOperationRequest,
    AssetRead,
    AssetReturnRequest,
    AssetUpdate,
```

Дописать в конец `backend/app/modules/assets/router.py`:

```python


@router.post("/issue", response_model=list[AssetRead])
async def issue_assets(
    body: AssetIssueRequest, session: SessionDep, admin: AdminDep
) -> list[AssetRead]:
    assets = await operations.issue_assets(
        session,
        admin,
        owner_id=body.owner_id,
        asset_ids=body.asset_ids,
        reason_id=body.reason_id,
        comment=body.comment,
    )
    return await assets_to_read(session, assets, admin)


@router.post("/return", response_model=list[AssetRead])
async def return_assets(
    body: AssetReturnRequest, session: SessionDep, admin: AdminDep
) -> list[AssetRead]:
    assets = await operations.return_assets(
        session, admin, asset_ids=body.asset_ids, location_id=body.location_id, comment=body.comment
    )
    return await assets_to_read(session, assets, admin)


@router.post("/{asset_id}/operations", response_model=AssetRead)
async def apply_operation(
    asset_id: int,
    body: Annotated[AssetOperationRequest, Body()],
    session: SessionDep,
    admin: AdminDep,
) -> AssetRead:
    asset = await operations.apply_operation(session, admin, asset_id, body)
    return await asset_to_read(session, asset, admin)
```

- [ ] **Step 5: Тесты проходят; OpenAPI и типы обновлены**

Run: `cd backend && uv run pytest -q tests/modules/assets`
Expected: PASS

Run: `make gen-api`
Expected: `openapi.json` и `schema.d.ts` перезаписаны

Run: `make test`
Expected: PASS

Run: `make lint`
Expected: ruff, mypy и import-linter без ошибок (`Contracts: N kept, 0 broken.`)

- [ ] **Step 6: Коммит**

```bash
git add backend frontend/src/api/schema.d.ts && git commit -m "feat(assets): операции над техникой, массовые выдача и возврат"
```

### Task 6: Блокер деактивации владельца техники

Закрывает п. 3.2 ТЗ для техники: пользователя с активами «В работе» или «В ремонте» нельзя деактивировать. `users_auth` публикует `UserDeactivationRequested`, `assets` добавляет блокеры — зависимость только через событие, как у `directories` в спринте 1. Диалог причин на фронтенде уже есть.

**Files:**
- Create: `backend/app/modules/assets/handlers.py`
- Modify: `backend/app/wiring.py`
- Modify: `backend/tests/test_openapi.py`
- Test: `backend/tests/modules/assets/test_deactivation_blocker.py`

**Interfaces:**
- Consumes: `UserDeactivationRequested`, `Blocker` из `app.modules.users_auth.events`; `event_bus` из `app.core.events`.
- Produces: блокер `Blocker(kind="asset_owner", entity_id=<asset.id>, title="Техника <инв. номер> — <модель>")`, по возрастанию инвентарного номера.

- [ ] **Step 1: Написать падающий тест**

Создать `backend/tests/modules/assets/test_deactivation_blocker.py`:

```python
from typing import Any

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.assets.models import Asset, AssetStatus
from app.modules.users_auth.models import User
from tests.factories import make_user
from tests.modules.assets.conftest import Refs, make_asset


def _error_code(response: Any) -> str:
    code: str = response.json()["error"]["code"]
    return code


async def test_deactivation_blocked_by_owned_assets(
    client: AsyncClient, admin_headers: dict[str, str], refs: Refs, db_session: AsyncSession
) -> None:
    owner = await make_user(db_session)
    in_use = await make_asset(
        db_session, refs, inventory_number="INV-1", status=AssetStatus.IN_USE, owner_id=owner.id
    )
    await make_asset(
        db_session, refs, inventory_number="INV-2", status=AssetStatus.IN_REPAIR, owner_id=owner.id
    )

    blocked = await client.post(f"/api/admin/users/{owner.id}/deactivate", headers=admin_headers)

    assert blocked.status_code == 409
    assert _error_code(blocked) == "deactivation_blocked"
    details = blocked.json()["error"]["details"]
    assert [item["kind"] for item in details] == ["asset_owner", "asset_owner"]
    assert details[0] == {
        "kind": "asset_owner",
        "entity_id": in_use.id,
        "title": "Техника INV-1 — Lenovo ThinkPad T14",
    }


async def test_user_without_assets_can_be_deactivated(
    client: AsyncClient, admin_headers: dict[str, str], refs: Refs, db_session: AsyncSession
) -> None:
    user: User = await make_user(db_session)
    asset: Asset = await make_asset(db_session, refs, inventory_number="INV-1")
    assert asset.owner_id is None

    response = await client.post(f"/api/admin/users/{user.id}/deactivate", headers=admin_headers)

    assert response.status_code == 200
```

В `backend/tests/test_openapi.py` заменить:

```python
        "/api/directories/locations",
```

на:

```python
        "/api/directories/locations",
        "/api/assets",
        "/api/assets/{asset_id}/operations",
```

- [ ] **Step 2: Убедиться, что тест падает**

Run: `cd backend && uv run pytest -q tests/modules/assets/test_deactivation_blocker.py`
Expected: FAIL — деактивация возвращает 200 вместо 409

- [ ] **Step 3: Обработчик и регистрация**

Создать `backend/app/modules/assets/handlers.py`:

```python
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.events import event_bus
from app.modules.assets.models import Asset, AssetStatus
from app.modules.users_auth.events import Blocker, UserDeactivationRequested

# Статусы, в которых техника числится за владельцем (п. 3.2 ТЗ: деактивация требует передачи).
_OWNED_STATUSES = (AssetStatus.IN_USE, AssetStatus.IN_REPAIR)


@event_bus.subscribe(UserDeactivationRequested)
async def block_deactivation_of_asset_owner(
    session: AsyncSession, event: UserDeactivationRequested
) -> None:
    rows = await session.execute(
        select(Asset.id, Asset.inventory_number, Asset.model)
        .where(Asset.owner_id == event.user_id, Asset.status.in_(_OWNED_STATUSES))
        .order_by(Asset.inventory_number)
    )
    event.blockers.extend(
        Blocker(kind="asset_owner", entity_id=asset_id, title=f"Техника {number} — {model}")
        for asset_id, number, model in rows
    )
```

В `backend/app/wiring.py` заменить:

```python
HANDLER_MODULES: tuple[str, ...] = ("app.modules.directories.handlers",)
```

на:

```python
HANDLER_MODULES: tuple[str, ...] = (
    "app.modules.assets.handlers",
    "app.modules.directories.handlers",
)
```

- [ ] **Step 4: Весь backend зелёный**

Run: `make test`
Expected: PASS (все тесты backend)

Run: `make lint`
Expected: ruff, mypy и import-linter без ошибок (`Contracts: N kept, 0 broken.`)

- [ ] **Step 5: Коммит**

```bash
git add backend && git commit -m "feat(assets): деактивация владельца техники блокируется"
```

### Task 7: Фронтенд: основа фичи — подписи, запросы, справочники, меню

Типы API уже сгенерированы в Task 4–5. Здесь — всё, на что опираются экраны: подписи статусов и операций, строки истории «было → стало», хуки запросов, справочники для форм, варианты сотрудников, `rules` у `FormSelect`/`FormAutocomplete` и раздел меню «Склад и техника» (пункт «Выдать / принять» — только Admin; маршруты появятся в Task 8 и 10).

**Files:**
- Create: `frontend/src/features/assets/labels.ts`, `AssetStatusChip.tsx`, `api.ts`
- Create: `frontend/src/shared/lookups/directories.ts`
- Modify: `frontend/src/shared/lookups/queryKeys.ts`, `frontend/src/shared/lookups/users.ts`
- Modify: `frontend/src/shared/ui/form/FormSelect.tsx`, `frontend/src/shared/ui/form/FormAutocomplete.tsx`
- Modify: `frontend/src/layout/menu.ts`
- Modify: `frontend/src/test/fixtures.ts`
- Test: `frontend/src/features/assets/labels.test.ts`, `frontend/src/app/shell.test.tsx`

**Interfaces:**
- Consumes: `Schemas["AssetRead"]`, `Schemas["AssetEventRead"]`, `Schemas["Operation"]`, пути `/api/assets*` из `schema.d.ts`.
- Produces:
  - `labels.ts`: типы `Asset`, `AssetEvent`, `AssetStatus`, `Operation`; `STATUS_LABELS`, `STATUS_COLORS`, `ASSET_STATUSES`, `OPERATION_LABELS`, `FIELD_LABELS`, `eventTitle(event)`, `eventChanges(event) -> string[]`.
  - `AssetStatusChip({ status })`.
  - `api.ts`: `AssetListParams`, `fetchAssets(params)`, `useAssets(params, enabled?)`, `useAsset(id)`, `useAssetEvents(id, limit, offset)`, `useCreateAsset()`, `useUpdateAsset()`, `OperationBody`, `useAssetOperation()`, `useIssueAssets()`, `useReturnAssets()`; все мутации после завершения инвалидируют `queryKeys.assets`.
  - `shared/lookups/directories.ts`: `useLocations()`, `useAssetTypes()`, `useAssetIssueReasons()` (без `applicability = stock`).
  - `shared/lookups/users.ts`: `searchActiveUserOptions(query)`, `ACTIVE_USER_OPTIONS_KEY`.
  - `FormSelect` и `FormAutocomplete` принимают `rules`.
  - `MenuItem.roles` — пункт виден только этим ролям.
  - `test/fixtures.ts`: `makeAsset(overrides)`, `makeAssetEvent(overrides)`.

- [ ] **Step 1: Написать падающие тесты**

Дописать в конец `frontend/src/test/fixtures.ts`:

```ts

export function makeAsset(overrides: Partial<Schemas["AssetRead"]> = {}): Schemas["AssetRead"] {
  return {
    id: 100,
    asset_type_id: 1,
    asset_type_name: "Ноутбук",
    inventory_number: "INV-001",
    serial_number: "SN-001",
    model: "Lenovo ThinkPad T14",
    status: "in_stock",
    location_id: 5,
    location_name: "Склад",
    owner_id: null,
    owner_name: null,
    accepted_at: "2026-01-15",
    purchased_at: null,
    warranty_until: "2028-01-15",
    initial_cost: "95000.00",
    needs_review: false,
    version: 1,
    created_at: "2026-09-01T09:00:00Z",
    updated_at: "2026-09-01T09:00:00Z",
    allowed_operations: ["issue", "reserve", "to_repair", "write_off", "move"],
    ...overrides,
  };
}

export function makeAssetEvent(
  overrides: Partial<Schemas["AssetEventRead"]> = {},
): Schemas["AssetEventRead"] {
  return {
    id: 1,
    event_type: "created",
    operation: null,
    from_owner_id: null,
    from_owner_name: null,
    to_owner_id: null,
    to_owner_name: null,
    from_status: null,
    to_status: "in_stock",
    from_location_id: null,
    from_location_name: null,
    to_location_id: 5,
    to_location_name: "Склад",
    reason_id: null,
    reason_name: null,
    changes: null,
    comment: null,
    performed_by: 1,
    performed_by_name: "Иванов Иван",
    created_at: "2026-09-01T09:00:00Z",
    ...overrides,
  };
}
```

Создать `frontend/src/features/assets/labels.test.ts`:

```ts
import { makeAssetEvent } from "../../test/fixtures";
import { eventChanges, eventTitle } from "./labels";

test("заголовок события: операция важнее типа", () => {
  expect(eventTitle(makeAssetEvent())).toBe("Поставлена на учёт");
  expect(eventTitle(makeAssetEvent({ event_type: "status_changed", operation: "to_repair" }))).toBe(
    "Передать в ремонт",
  );
});

test("строки «было → стало» только для заполненных пар", () => {
  const lines = eventChanges(
    makeAssetEvent({
      event_type: "returned",
      from_status: "in_use",
      to_status: "in_stock",
      from_owner_name: "Петров Пётр",
      to_location_id: null,
      to_location_name: null,
      changes: { needs_review: [true, false] },
    }),
  );

  expect(lines).toEqual([
    "Статус: В работе → На складе",
    "Владелец: Петров Пётр → —",
    "Требует проверки: да → нет",
  ]);
});
```

В `frontend/src/app/shell.test.tsx` (тест администратора) заменить:

```tsx
  expect(within(nav).getByText("Администрирование")).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "Главная" })).toBeInTheDocument();
```

на:

```tsx
  expect(within(nav).getByText("Администрирование")).toBeInTheDocument();
  expect(within(nav).getByRole("link", { name: "Выдать / принять" })).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "Главная" })).toBeInTheDocument();
```

В `frontend/src/app/shell.test.tsx` (новый тест перед тестом 404) заменить:

```tsx
test("неизвестный путь показывает страницу 404"
```

на:

```tsx
test("раздел «Склад и техника»: реестр всем, выдача только администратору", async () => {
  mockSignedIn(makeMe({ role: "manager" }));
  renderShell("/");

  const nav = await screen.findByRole("navigation", { name: "Основное меню" });
  expect(within(nav).getByRole("link", { name: "Реестр техники" })).toHaveAttribute(
    "href",
    "/equipment/assets",
  );
  expect(within(nav).queryByRole("link", { name: "Выдать / принять" })).not.toBeInTheDocument();
});

test("неизвестный путь показывает страницу 404"
```

- [ ] **Step 2: Убедиться, что тесты падают**

Run: `cd frontend && npx vitest run src/features/assets/labels.test.ts src/app/shell.test.tsx`
Expected: FAIL — `labels.ts` не найден, в меню нет «Реестр техники»

- [ ] **Step 3: Справочники, варианты сотрудников, `rules` у полей форм**

В `frontend/src/shared/lookups/queryKeys.ts` заменить:

```ts
  directories: ["directories"] as const,
```

на:

```ts
  directories: ["directories"] as const,
  assets: ["assets"] as const,
```

Создать `frontend/src/shared/lookups/directories.ts`:

```ts
import { useQuery } from "@tanstack/react-query";

import { api, unwrap } from "../../api/client";
import { queryKeys } from "./queryKeys";

/** Активные элементы справочников для выпадающих списков форм. */
export function useLocations() {
  return useQuery({
    queryKey: [...queryKeys.directories, "locations", { includeInactive: false }],
    queryFn: () => unwrap(api.GET("/api/directories/locations")),
  });
}

export function useAssetTypes() {
  return useQuery({
    queryKey: [...queryKeys.directories, "asset-types", { includeInactive: false }],
    queryFn: () => unwrap(api.GET("/api/directories/asset-types")),
  });
}

/** Причины выдачи, применимые к технике (applicability assets или both). */
export function useAssetIssueReasons() {
  return useQuery({
    queryKey: [...queryKeys.directories, "issue-reasons", { includeInactive: false }],
    queryFn: () => unwrap(api.GET("/api/directories/issue-reasons")),
    select: (items) => items.filter((item) => item.applicability !== "stock"),
  });
}
```

Дописать в конец `frontend/src/shared/lookups/users.ts`:

```ts

/** Варианты активных сотрудников любой роли (для выдачи техники; только администратор). */
export async function searchActiveUserOptions(query: string): Promise<EntityOption[]> {
  const page = await unwrap(
    api.GET("/api/admin/users", {
      params: { query: { q: query.trim() || undefined, is_active: true, limit: 50 } },
    }),
  );
  return page.items.map((user) => ({ id: user.id, label: user.full_name }));
}

export const ACTIVE_USER_OPTIONS_KEY = [...queryKeys.users, "active-options"] as const;
```

Создать `frontend/src/shared/ui/form/FormSelect.tsx` — целиком: добавлен `rules`:

```tsx
import { MenuItem, TextField } from "@mui/material";
import {
  Controller,
  type Control,
  type FieldPath,
  type FieldValues,
  type RegisterOptions,
} from "react-hook-form";

export interface SelectOption<V extends string | number> {
  value: V;
  label: string;
}

interface FormSelectProps<T extends FieldValues, V extends string | number> {
  control: Control<T>;
  name: FieldPath<T>;
  label: string;
  options: readonly SelectOption<V>[];
  /** Подпись пустого значения; если задана, поле допускает null. */
  emptyLabel?: string;
  disabled?: boolean;
  rules?: RegisterOptions<T, FieldPath<T>>;
}

export function FormSelect<T extends FieldValues, V extends string | number>({
  control,
  name,
  label,
  options,
  emptyLabel,
  disabled,
  rules,
}: FormSelectProps<T, V>) {
  return (
    <Controller
      control={control}
      name={name}
      rules={rules}
      render={({ field, fieldState }) => (
        <TextField
          select
          fullWidth
          label={label}
          name={field.name}
          inputRef={field.ref}
          value={field.value === null || field.value === undefined ? "" : String(field.value)}
          onChange={(event) => {
            const option = options.find((item) => String(item.value) === event.target.value);
            field.onChange(option ? option.value : null);
          }}
          onBlur={field.onBlur}
          disabled={disabled}
          error={Boolean(fieldState.error)}
          helperText={fieldState.error?.message}
        >
          {emptyLabel !== undefined && <MenuItem value="">{emptyLabel}</MenuItem>}
          {options.map((option) => (
            <MenuItem key={String(option.value)} value={String(option.value)}>
              {option.label}
            </MenuItem>
          ))}
        </TextField>
      )}
    />
  );
}
```

Создать `frontend/src/shared/ui/form/FormAutocomplete.tsx` — целиком: добавлен `rules`:

```tsx
import {
  Controller,
  type Control,
  type FieldPath,
  type FieldValues,
  type RegisterOptions,
} from "react-hook-form";

import { EntityAutocomplete, type EntityAutocompleteProps } from "../EntityAutocomplete";

type FormAutocompleteProps<T extends FieldValues> = {
  control: Control<T>;
  name: FieldPath<T>;
  rules?: RegisterOptions<T, FieldPath<T>>;
} & Omit<EntityAutocompleteProps, "value" | "onChange" | "error" | "helperText" | "onBlur">;

export function FormAutocomplete<T extends FieldValues>({
  control,
  name,
  rules,
  ...props
}: FormAutocompleteProps<T>) {
  return (
    <Controller
      control={control}
      name={name}
      rules={rules}
      render={({ field, fieldState }) => (
        <EntityAutocomplete
          {...props}
          value={(field.value as number | null | undefined) ?? null}
          onChange={field.onChange}
          onBlur={field.onBlur}
          error={Boolean(fieldState.error)}
          helperText={fieldState.error?.message}
        />
      )}
    />
  );
}
```

- [ ] **Step 4: Подписи, метка статуса, запросы**

Создать `frontend/src/features/assets/labels.ts`:

```ts
import type { Schemas } from "../../api/types";

export type Asset = Schemas["AssetRead"];
export type AssetEvent = Schemas["AssetEventRead"];
export type AssetStatus = Schemas["AssetStatus"];
export type Operation = Schemas["Operation"];

export const STATUS_LABELS: Record<AssetStatus, string> = {
  in_stock: "На складе",
  reserved: "Резерв",
  in_use: "В работе",
  in_repair: "В ремонте",
  written_off: "Списана",
};

export const STATUS_COLORS: Record<
  AssetStatus,
  "success" | "info" | "primary" | "warning" | "default"
> = {
  in_stock: "success",
  reserved: "info",
  in_use: "primary",
  in_repair: "warning",
  written_off: "default",
};

export const ASSET_STATUSES = Object.keys(STATUS_LABELS) as AssetStatus[];

export const OPERATION_LABELS: Record<Operation, string> = {
  issue: "Выдать",
  return: "Принять на склад",
  reserve: "Зарезервировать",
  unreserve: "Снять резерв",
  to_repair: "Передать в ремонт",
  repair_to_owner: "Вернуть из ремонта владельцу",
  repair_to_stock: "Вернуть из ремонта на склад",
  write_off: "Списать",
  move: "Переместить",
};

const EVENT_LABELS: Record<Schemas["AssetEventType"], string> = {
  created: "Поставлена на учёт",
  issued: "Выдача",
  returned: "Возврат на склад",
  status_changed: "Смена статуса",
  moved: "Перемещение",
  edited: "Редактирование",
  written_off: "Списание",
};

/** Заголовок события: название операции, если есть, иначе тип события. */
export function eventTitle(event: AssetEvent): string {
  return event.operation ? OPERATION_LABELS[event.operation] : EVENT_LABELS[event.event_type];
}

export const FIELD_LABELS: Record<string, string> = {
  asset_type_id: "Тип",
  inventory_number: "Инв. номер",
  serial_number: "Серийный номер",
  model: "Модель",
  accepted_at: "Дата принятия к учёту",
  purchased_at: "Дата покупки",
  warranty_until: "Гарантия до",
  initial_cost: "Стоимость",
  needs_review: "Требует проверки",
};

function formatValue(value: unknown): string | null {
  if (value === null || value === undefined) return null;
  if (typeof value === "boolean") return value ? "да" : "нет";
  return String(value);
}

/** Строки «было → стало» для события: владелец, статус, локация и изменённые поля. */
export function eventChanges(event: AssetEvent): string[] {
  const lines: string[] = [];
  const pair = (label: string, from: string | null, to: string | null) => {
    if (from !== null || to !== null) lines.push(`${label}: ${from ?? "—"} → ${to ?? "—"}`);
  };
  pair(
    "Статус",
    event.from_status ? STATUS_LABELS[event.from_status] : null,
    event.to_status ? STATUS_LABELS[event.to_status] : null,
  );
  pair("Владелец", event.from_owner_name, event.to_owner_name);
  pair("Локация", event.from_location_name, event.to_location_name);
  for (const [field, value] of Object.entries(event.changes ?? {})) {
    const [from, to] = value as [unknown, unknown];
    pair(FIELD_LABELS[field] ?? field, formatValue(from), formatValue(to));
  }
  return lines;
}
```

Создать `frontend/src/features/assets/AssetStatusChip.tsx`:

```tsx
import { Chip } from "@mui/material";

import { STATUS_COLORS, STATUS_LABELS, type AssetStatus } from "./labels";

export function AssetStatusChip({ status }: { status: AssetStatus }) {
  return <Chip size="small" label={STATUS_LABELS[status]} color={STATUS_COLORS[status]} />;
}
```

Создать `frontend/src/features/assets/api.ts`:

```ts
import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api, unwrap } from "../../api/client";
import type { Schemas } from "../../api/types";
import { queryKeys } from "../../shared/lookups/queryKeys";
import type { AssetStatus } from "./labels";

export interface AssetListParams {
  q?: string;
  status?: AssetStatus | null;
  assetTypeId?: number | null;
  ownerId?: number | null;
  locationId?: number | null;
  needsReview?: boolean | null;
  limit: number;
  offset: number;
}

export function fetchAssets(params: AssetListParams) {
  return unwrap(
    api.GET("/api/assets", {
      params: {
        query: {
          q: params.q?.trim() || undefined,
          status: params.status ? [params.status] : undefined,
          asset_type_id: params.assetTypeId ?? undefined,
          owner_id: params.ownerId ?? undefined,
          location_id: params.locationId ?? undefined,
          needs_review: params.needsReview ?? undefined,
          limit: params.limit,
          offset: params.offset,
        },
      },
    }),
  );
}

export function useAssets(params: AssetListParams, enabled = true) {
  return useQuery({
    queryKey: [...queryKeys.assets, "list", params],
    queryFn: () => fetchAssets(params),
    placeholderData: keepPreviousData,
    enabled,
  });
}

export function useAsset(id: number) {
  return useQuery({
    queryKey: [...queryKeys.assets, "detail", id],
    queryFn: () =>
      unwrap(api.GET("/api/assets/{asset_id}", { params: { path: { asset_id: id } } })),
  });
}

export function useAssetEvents(id: number, limit: number, offset: number) {
  return useQuery({
    queryKey: [...queryKeys.assets, "events", id, { limit, offset }],
    queryFn: () =>
      unwrap(
        api.GET("/api/assets/{asset_id}/events", {
          params: { path: { asset_id: id }, query: { limit, offset } },
        }),
      ),
    placeholderData: keepPreviousData,
  });
}

/** Мутация, после которой перезапрашиваются все данные техники (реестр, карточка, история). */
function useAssetsMutation<V, R>(mutationFn: (variables: V) => Promise<R>) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn,
    onSettled: () => queryClient.invalidateQueries({ queryKey: queryKeys.assets }),
  });
}

export function useCreateAsset() {
  return useAssetsMutation((body: Schemas["AssetCreate"]) =>
    unwrap(api.POST("/api/assets", { body })),
  );
}

export function useUpdateAsset() {
  return useAssetsMutation(({ id, body }: { id: number; body: Schemas["AssetUpdate"] }) =>
    unwrap(api.PATCH("/api/assets/{asset_id}", { params: { path: { asset_id: id } }, body })),
  );
}

export type OperationBody =
  | Schemas["IssueOperation"]
  | Schemas["ReturnOperation"]
  | Schemas["StatusOperation"]
  | Schemas["WriteOffOperation"]
  | Schemas["MoveOperation"];

export function useAssetOperation() {
  return useAssetsMutation(({ id, body }: { id: number; body: OperationBody }) =>
    unwrap(
      api.POST("/api/assets/{asset_id}/operations", { params: { path: { asset_id: id } }, body }),
    ),
  );
}

export function useIssueAssets() {
  return useAssetsMutation((body: Schemas["AssetIssueRequest"]) =>
    unwrap(api.POST("/api/assets/issue", { body })),
  );
}

export function useReturnAssets() {
  return useAssetsMutation((body: Schemas["AssetReturnRequest"]) =>
    unwrap(api.POST("/api/assets/return", { body })),
  );
}
```

- [ ] **Step 5: Меню**

Создать `frontend/src/layout/menu.ts` — целиком:

```ts
import {
  IconArrowsExchange,
  IconBook2,
  IconBuildingCommunity,
  IconDeviceLaptop,
  IconLayoutDashboard,
  IconUserCircle,
  IconUsers,
} from "@tabler/icons-react";
import type { ComponentType } from "react";

import type { UserRole } from "../api/types";

export interface MenuItem {
  label: string;
  to: string;
  icon: ComponentType<{ size?: string | number; stroke?: string | number }>;
  roles?: readonly UserRole[];
}

export interface MenuSection {
  title?: string;
  roles?: readonly UserRole[];
  items: MenuItem[];
}

export const MENU: readonly MenuSection[] = [
  {
    items: [
      { label: "Главная", to: "/", icon: IconLayoutDashboard },
      { label: "Профиль", to: "/profile", icon: IconUserCircle },
    ],
  },
  {
    title: "Склад и техника",
    items: [
      { label: "Реестр техники", to: "/equipment/assets", icon: IconDeviceLaptop },
      {
        label: "Выдать / принять",
        to: "/equipment/issue",
        icon: IconArrowsExchange,
        roles: ["admin"],
      },
    ],
  },
  {
    title: "Администрирование",
    roles: ["admin"],
    items: [
      { label: "Пользователи", to: "/admin/users", icon: IconUsers },
      { label: "Отделы", to: "/admin/departments", icon: IconBuildingCommunity },
      { label: "Справочники", to: "/admin/directories", icon: IconBook2 },
    ],
  },
];

const allowed = (roles: readonly UserRole[] | undefined, role: UserRole) =>
  !roles || roles.includes(role);

export function menuForRole(role: UserRole): MenuSection[] {
  return MENU.filter((section) => allowed(section.roles, role)).map((section) => ({
    ...section,
    items: section.items.filter((item) => allowed(item.roles, role)),
  }));
}
```

- [ ] **Step 6: Проверки проходят**

Run: `cd frontend && npm run format && npm run check`
Expected: типы, ESLint, Prettier, `check:api` и все тесты Vitest проходят

- [ ] **Step 7: Коммит**

```bash
git add frontend && git commit -m "feat(frontend): основа фичи техники — подписи, запросы, справочники, меню"
```

### Task 8: Фронтенд: реестр техники и добавление

Реестр для всех ролей с подписью области видимости; фильтры в URL; Admin — фильтры «Владелец» и «Требует проверки», кнопка «Добавить». `AssetFormDialog` сразу умеет и правку (используется карточкой в Task 9): отправляются только изменённые поля и `version`, при `version_conflict` форма закрывается с предупреждением. Стоимость принимает запятую («1200,50» → `"1200.50"`).

**Files:**
- Create: `frontend/src/features/assets/testing.ts`, `AssetsPage.tsx`, `AssetFormDialog.tsx`, `index.ts`
- Modify: `frontend/src/app/routes.tsx`
- Test: `frontend/src/features/assets/AssetsPage.test.tsx`

**Interfaces:**
- Consumes: всё из Task 7.
- Produces: `AssetsPage` (маршрут `/equipment/assets`, `/equipment` → редирект), `AssetFormDialog({ asset: Asset | null, onClose, onSaved? })`, `mockAssetLookups()` в `features/assets/testing.ts` (MSW: локации 5 «Склад» и 6 «Офис, каб. 101», тип 1 «Ноутбук», причины 7 «Новый сотрудник» (both), 8 «Заправка» (stock), 9 «Неисправность» (assets), пользователь 10 «Петров Пётр»).

- [ ] **Step 1: Написать падающий тест**

Создать `frontend/src/features/assets/testing.ts`:

```ts
import { http, HttpResponse } from "msw";

import { makeUser, page } from "../../test/fixtures";
import { server } from "../../test/server";

/** Справочники и пользователи, которые запрашивают экраны техники. */
export function mockAssetLookups() {
  server.use(
    http.get("*/api/directories/locations", () =>
      HttpResponse.json([
        { id: 5, name: "Склад", description: null, is_active: true },
        { id: 6, name: "Офис, каб. 101", description: null, is_active: true },
      ]),
    ),
    http.get("*/api/directories/asset-types", () =>
      HttpResponse.json([{ id: 1, name: "Ноутбук", is_active: true }]),
    ),
    http.get("*/api/directories/issue-reasons", () =>
      HttpResponse.json([
        { id: 7, name: "Новый сотрудник", applicability: "both", is_active: true },
        { id: 8, name: "Заправка", applicability: "stock", is_active: true },
        { id: 9, name: "Неисправность", applicability: "assets", is_active: true },
      ]),
    ),
    http.get("*/api/admin/users", () =>
      HttpResponse.json(page([makeUser({ id: 10, full_name: "Петров Пётр" })])),
    ),
  );
}
```

Создать `frontend/src/features/assets/AssetsPage.test.tsx`:

```tsx
import { screen, waitFor, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";

import { renderApp } from "../../test/app";
import { makeMe, mockSignedIn } from "../../test/auth";
import { makeAsset, page } from "../../test/fixtures";
import { server } from "../../test/server";
import { mockAssetLookups } from "./testing";

function mockAssets(seen: URL[] = []) {
  server.use(
    http.get("*/api/assets", ({ request }) => {
      seen.push(new URL(request.url));
      return HttpResponse.json(
        page([makeAsset({ status: "in_use", owner_id: 10, owner_name: "Петров Пётр" })]),
      );
    }),
  );
  return seen;
}

test("реестр: строки, фильтры из URL и поиск", async () => {
  mockSignedIn();
  mockAssetLookups();
  const seen = mockAssets();
  const { user, router } = renderApp("/equipment/assets?status=in_use&type=1");

  const row = (await screen.findByRole("link", { name: "INV-001" })).closest("tr")!;
  expect(within(row).getByText("В работе")).toBeInTheDocument();
  expect(within(row).getByText("Петров Пётр")).toBeInTheDocument();
  expect(seen.at(-1)?.searchParams.getAll("status")).toEqual(["in_use"]);
  expect(seen.at(-1)?.searchParams.get("asset_type_id")).toBe("1");

  await user.type(screen.getByLabelText("Инв. номер, серийный номер, модель"), "t14");
  await waitFor(() => expect(seen.at(-1)?.searchParams.get("q")).toBe("t14"));
  expect(router.state.location.search).toContain("q=t14");

  await user.click(screen.getByRole("link", { name: "INV-001" }));
  expect(router.state.location.pathname).toBe("/equipment/assets/100");
});

test("сотрудник видит свою технику без кнопки «Добавить» и фильтра владельца", async () => {
  mockSignedIn(makeMe({ role: "employee" }));
  mockAssetLookups();
  mockAssets();
  renderApp("/equipment/assets");

  expect(await screen.findByText("Ваша техника")).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Добавить" })).not.toBeInTheDocument();
  expect(screen.queryByLabelText("Владелец")).not.toBeInTheDocument();
});

test("руководитель видит подпись области отдела", async () => {
  mockSignedIn(makeMe({ role: "manager", department_id: 3 }));
  mockAssetLookups();
  mockAssets();
  renderApp("/equipment/assets");

  expect(await screen.findByText("Техника сотрудников вашего отдела")).toBeInTheDocument();
});

test("администратор добавляет технику и попадает в карточку", async () => {
  mockSignedIn();
  mockAssetLookups();
  mockAssets();
  let created: Record<string, unknown> | null = null;
  server.use(
    http.post("*/api/assets", async ({ request }) => {
      created = (await request.json()) as Record<string, unknown>;
      return HttpResponse.json(makeAsset({ id: 101 }), { status: 201 });
    }),
    http.get("*/api/assets/101", () => HttpResponse.json(makeAsset({ id: 101 }))),
  );
  const { user, router } = renderApp("/equipment/assets");

  await user.click(await screen.findByRole("button", { name: "Добавить" }));
  const dialog = await screen.findByRole("dialog");
  await user.click(within(dialog).getByLabelText("Тип"));
  await user.click(await screen.findByRole("option", { name: "Ноутбук" }));
  await user.type(within(dialog).getByLabelText("Инвентарный номер"), "INV-777");
  await user.type(within(dialog).getByLabelText("Модель"), "Dell Latitude");
  await user.click(within(dialog).getByLabelText("Локация"));
  await user.click(await screen.findByRole("option", { name: "Склад" }));
  await user.type(within(dialog).getByLabelText("Стоимость, ₽"), "1200,50");
  await user.click(within(dialog).getByRole("button", { name: "Добавить" }));

  await waitFor(() => expect(router.state.location.pathname).toBe("/equipment/assets/101"));
  expect(created).toMatchObject({
    asset_type_id: 1,
    inventory_number: "INV-777",
    model: "Dell Latitude",
    location_id: 5,
    serial_number: null,
    initial_cost: "1200.50",
  });
});
```

- [ ] **Step 2: Убедиться, что тест падает**

Run: `cd frontend && npx vitest run src/features/assets/AssetsPage.test.tsx`
Expected: FAIL — на `/equipment/assets` страница 404

- [ ] **Step 3: Форма и страница**

Создать `frontend/src/features/assets/AssetFormDialog.tsx`:

```tsx
import { useSnackbar } from "notistack";
import { useState } from "react";
import { useForm } from "react-hook-form";

import { ApiError } from "../../api/errors";
import { applyApiErrors, fieldByCode } from "../../shared/lib/applyApiErrors";
import { useAssetTypes, useLocations } from "../../shared/lookups/directories";
import { FormDialog } from "../../shared/ui/FormDialog";
import { FormSelect } from "../../shared/ui/form/FormSelect";
import { FormSwitch } from "../../shared/ui/form/FormSwitch";
import { FormTextField } from "../../shared/ui/form/FormTextField";
import { useCreateAsset, useUpdateAsset } from "./api";
import type { Asset } from "./labels";

interface AssetFormValues {
  asset_type_id: number | null;
  inventory_number: string;
  serial_number: string;
  model: string;
  location_id: number | null;
  accepted_at: string;
  purchased_at: string;
  warranty_until: string;
  initial_cost: string;
  needs_review: boolean;
}

const FIELDS = [
  "asset_type_id",
  "inventory_number",
  "serial_number",
  "model",
  "location_id",
  "accepted_at",
  "purchased_at",
  "warranty_until",
  "initial_cost",
] as const;

const fieldForError = fieldByCode<AssetFormValues>({
  inventory_number_taken: "inventory_number",
  inventory_number_blank: "inventory_number",
  serial_number_taken: "serial_number",
  model_blank: "model",
  asset_type_invalid: "asset_type_id",
  location_invalid: "location_id",
});

const required = { required: "Обязательное поле" };
const optional = (value: string) => value.trim() || null;

/** Варианты справочника; деактивированное текущее значение добавляется, чтобы форма его показала. */
function withCurrent(
  items: { id: number; name: string }[] | undefined,
  currentId?: number,
  currentName?: string,
) {
  const options = (items ?? []).map((item) => ({ value: item.id, label: item.name }));
  if (currentId !== undefined && !options.some((option) => option.value === currentId)) {
    options.push({ value: currentId, label: currentName ?? "" });
  }
  return options;
}

function toValues(asset: Asset | null): AssetFormValues {
  return {
    asset_type_id: asset?.asset_type_id ?? null,
    inventory_number: asset?.inventory_number ?? "",
    serial_number: asset?.serial_number ?? "",
    model: asset?.model ?? "",
    location_id: asset?.location_id ?? null,
    accepted_at: asset?.accepted_at ?? new Date().toISOString().slice(0, 10),
    purchased_at: asset?.purchased_at ?? "",
    warranty_until: asset?.warranty_until ?? "",
    initial_cost: asset?.initial_cost ?? "",
    needs_review: asset?.needs_review ?? false,
  };
}

interface AssetFormDialogProps {
  /** Актив для редактирования; без него диалог создаёт новый. */
  asset: Asset | null;
  onClose: () => void;
  /** Вызывается с сохранённым активом (после создания — чтобы открыть карточку). */
  onSaved?: (asset: Asset) => void;
}

export function AssetFormDialog({ asset, onClose, onSaved }: AssetFormDialogProps) {
  const { enqueueSnackbar } = useSnackbar();
  const createAsset = useCreateAsset();
  const updateAsset = useUpdateAsset();
  const types = useAssetTypes();
  const locations = useLocations();
  const [formError, setFormError] = useState<string | null>(null);
  const {
    control,
    handleSubmit,
    setError,
    formState: { isSubmitting, dirtyFields },
  } = useForm<AssetFormValues>({ defaultValues: toValues(asset) });

  const typeOptions = withCurrent(types.data, asset?.asset_type_id, asset?.asset_type_name);
  const locationOptions = withCurrent(locations.data);

  const onSubmit = handleSubmit(async (values) => {
    setFormError(null);
    const body = {
      asset_type_id: values.asset_type_id!,
      inventory_number: values.inventory_number,
      serial_number: optional(values.serial_number),
      model: values.model,
      accepted_at: values.accepted_at,
      purchased_at: optional(values.purchased_at),
      warranty_until: optional(values.warranty_until),
      initial_cost: optional(values.initial_cost.replace(",", ".")),
    };
    try {
      let saved: Asset;
      if (asset) {
        const changed = Object.fromEntries(
          Object.entries({ ...body, needs_review: values.needs_review }).filter(
            ([key]) => dirtyFields[key as keyof AssetFormValues],
          ),
        );
        saved = await updateAsset.mutateAsync({
          id: asset.id,
          body: { ...changed, version: asset.version },
        });
      } else {
        saved = await createAsset.mutateAsync({
          ...body,
          location_id: values.location_id!,
          needs_review: false,
        });
      }
      onSaved?.(saved);
      onClose();
    } catch (error) {
      if (error instanceof ApiError && error.code === "version_conflict") {
        enqueueSnackbar(
          "Данные изменил другой пользователь — карточка обновлена, внесите правки заново",
          {
            variant: "warning",
          },
        );
        onClose();
        return;
      }
      setFormError(applyApiErrors(error, setError, { fields: FIELDS, fieldForError }));
    }
  });

  return (
    <FormDialog
      open
      title={asset ? "Редактирование техники" : "Новая техника"}
      submitting={isSubmitting}
      formError={formError}
      onSubmit={onSubmit}
      onClose={onClose}
      submitLabel={asset ? "Сохранить" : "Добавить"}
    >
      <FormSelect
        control={control}
        name="asset_type_id"
        label="Тип"
        options={typeOptions}
        rules={required}
      />
      <FormTextField
        control={control}
        name="inventory_number"
        label="Инвентарный номер"
        rules={required}
      />
      <FormTextField control={control} name="serial_number" label="Серийный номер" />
      <FormTextField control={control} name="model" label="Модель" rules={required} />
      {!asset && (
        <FormSelect
          control={control}
          name="location_id"
          label="Локация"
          options={locationOptions}
          rules={required}
        />
      )}
      <FormTextField
        control={control}
        name="accepted_at"
        label="Дата принятия к учёту"
        type="date"
        rules={required}
        slotProps={{ inputLabel: { shrink: true } }}
      />
      <FormTextField
        control={control}
        name="purchased_at"
        label="Дата покупки"
        type="date"
        slotProps={{ inputLabel: { shrink: true } }}
      />
      <FormTextField
        control={control}
        name="warranty_until"
        label="Гарантия до"
        type="date"
        slotProps={{ inputLabel: { shrink: true } }}
      />
      <FormTextField
        control={control}
        name="initial_cost"
        label="Стоимость, ₽"
        rules={{
          validate: (value) =>
            value.trim() === "" ||
            /^\d{1,10}([.,]\d{1,2})?$/.test(value.trim()) ||
            "Введите сумму, например 95000.00",
        }}
      />
      {asset && <FormSwitch control={control} name="needs_review" label="Требует проверки" />}
    </FormDialog>
  );
}
```

Создать `frontend/src/features/assets/AssetsPage.tsx`:

```tsx
import { Button, FormControlLabel, Link as MuiLink, Switch, Typography } from "@mui/material";
import { IconPlus } from "@tabler/icons-react";
import { useState } from "react";
import { Link, useNavigate } from "react-router";

import { useAuth } from "../auth";
import { formatDate } from "../../shared/lib/format";
import {
  booleanParam,
  enumParam,
  idParam,
  textParam,
  useUrlFilters,
} from "../../shared/lib/useUrlFilters";
import { useAssetTypes, useLocations } from "../../shared/lookups/directories";
import {
  ACTIVE_USER_OPTIONS_KEY,
  searchActiveUserOptions,
  useUserNames,
} from "../../shared/lookups/users";
import { DataTable, type Column } from "../../shared/ui/DataTable";
import { EntityAutocomplete } from "../../shared/ui/EntityAutocomplete";
import { FilterBar, FilterSelect, SearchField } from "../../shared/ui/FilterBar";
import { PageContainer } from "../../shared/ui/PageContainer";
import { useAssets } from "./api";
import { AssetFormDialog } from "./AssetFormDialog";
import { AssetStatusChip } from "./AssetStatusChip";
import { ASSET_STATUSES, STATUS_LABELS, type Asset } from "./labels";

const FILTERS = {
  q: textParam,
  status: enumParam(ASSET_STATUSES),
  type: idParam,
  owner: idParam,
  location: idParam,
  review: booleanParam,
};

const STATUS_OPTIONS = ASSET_STATUSES.map((status) => ({
  value: status,
  label: STATUS_LABELS[status],
}));

const SCOPE_TEXT = {
  employee: "Ваша техника",
  manager: "Техника сотрудников вашего отдела",
  admin: null,
} as const;

export function AssetsPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const isAdmin = user?.role === "admin";
  const { filters, limit, offset, setFilter, setPage } = useUrlFilters(FILTERS);
  const assets = useAssets({
    q: filters.q,
    status: filters.status,
    assetTypeId: filters.type,
    ownerId: isAdmin ? filters.owner : null,
    locationId: filters.location,
    needsReview: isAdmin ? filters.review : null,
    limit,
    offset,
  });
  const types = useAssetTypes();
  const locations = useLocations();
  const [creating, setCreating] = useState(false);

  const columns: Column<Asset>[] = [
    {
      key: "inventory_number",
      header: "Инв. номер",
      render: (asset) => (
        <MuiLink component={Link} to={`/equipment/assets/${asset.id}`}>
          {asset.inventory_number}
        </MuiLink>
      ),
    },
    { key: "type", header: "Тип", render: (asset) => asset.asset_type_name },
    { key: "model", header: "Модель", render: (asset) => asset.model },
    {
      key: "status",
      header: "Статус",
      render: (asset) => <AssetStatusChip status={asset.status} />,
    },
    { key: "owner", header: "Владелец", render: (asset) => asset.owner_name ?? "—" },
    { key: "location", header: "Локация", render: (asset) => asset.location_name },
    {
      key: "warranty",
      header: "Гарантия до",
      render: (asset) => (asset.warranty_until ? formatDate(asset.warranty_until) : "—"),
    },
  ];

  const scopeText = user ? SCOPE_TEXT[user.role] : null;

  return (
    <PageContainer
      title="Реестр техники"
      breadcrumbs={[{ label: "Склад и техника" }, { label: "Реестр техники" }]}
      actions={
        isAdmin && (
          <Button
            variant="contained"
            startIcon={<IconPlus size={18} />}
            onClick={() => setCreating(true)}
          >
            Добавить
          </Button>
        )
      }
    >
      {scopeText && (
        <Typography color="text.secondary" sx={{ mb: 2 }}>
          {scopeText}
        </Typography>
      )}
      <FilterBar>
        <SearchField
          value={filters.q}
          onChange={(value) => setFilter("q", value)}
          placeholder="Инв. номер, серийный номер, модель"
        />
        <FilterSelect
          label="Статус"
          value={filters.status}
          options={STATUS_OPTIONS}
          allLabel="Все, кроме списанных"
          onChange={(value) => setFilter("status", value)}
        />
        <FilterSelect
          label="Тип"
          value={filters.type}
          options={(types.data ?? []).map((item) => ({ value: item.id, label: item.name }))}
          onChange={(value) => setFilter("type", value)}
        />
        <FilterSelect
          label="Локация"
          value={filters.location}
          options={(locations.data ?? []).map((item) => ({ value: item.id, label: item.name }))}
          onChange={(value) => setFilter("location", value)}
        />
        {isAdmin && <OwnerFilter value={filters.owner} onChange={(id) => setFilter("owner", id)} />}
        {isAdmin && (
          <FormControlLabel
            label="Требует проверки"
            control={
              <Switch
                checked={filters.review === true}
                onChange={(event) => setFilter("review", event.target.checked ? true : null)}
              />
            }
          />
        )}
      </FilterBar>

      <DataTable
        columns={columns}
        rows={assets.data?.items}
        getRowId={(asset) => asset.id}
        loading={assets.isLoading}
        error={assets.error}
        onRetry={() => void assets.refetch()}
        emptyText="Техника не найдена"
        paging={{ limit, offset, total: assets.data?.total ?? 0, onChange: setPage }}
      />

      {creating && (
        <AssetFormDialog
          asset={null}
          onClose={() => setCreating(false)}
          onSaved={(asset) => void navigate(`/equipment/assets/${asset.id}`)}
        />
      )}
    </PageContainer>
  );
}

function OwnerFilter({
  value,
  onChange,
}: {
  value: number | null;
  onChange: (id: number | null) => void;
}) {
  const { nameOf } = useUserNames();
  return (
    <EntityAutocomplete
      label="Владелец"
      value={value}
      onChange={onChange}
      fetchOptions={searchActiveUserOptions}
      queryKey={ACTIVE_USER_OPTIONS_KEY}
      labelFor={nameOf}
    />
  );
}
```

Создать `frontend/src/features/assets/index.ts`:

```ts
export { AssetsPage } from "./AssetsPage";
```

- [ ] **Step 4: Маршруты**

В `frontend/src/app/routes.tsx` заменить:

```tsx
import { DepartmentsPage } from "../features/departments";
```

на:

```tsx
import { AssetsPage } from "../features/assets";
import { DepartmentsPage } from "../features/departments";
```

В `frontend/src/app/routes.tsx` заменить:

```tsx
          { path: "/profile", element: <ProfilePage /> },
```

на:

```tsx
          { path: "/profile", element: <ProfilePage /> },
          { path: "/equipment", element: <Navigate to="/equipment/assets" replace /> },
          { path: "/equipment/assets", element: <AssetsPage /> },
```

- [ ] **Step 5: Проверки проходят**

Run: `cd frontend && npm run format && npm run check`
Expected: типы, ESLint, Prettier, `check:api` и все тесты Vitest проходят

- [ ] **Step 6: Коммит**

```bash
git add frontend && git commit -m "feat(frontend): реестр техники и добавление"
```

### Task 9: Фронтенд: карточка техники — информация, история, операции, правка

Меню «Действия» строится только из `allowed_operations`; один `AssetOperationDialog` показывает поля по таблице `OPERATION_FIELDS` (п. 3 спецификации). На 409 `operation_not_allowed` диалог закрывается, уведомление «Статус техники изменился — данные обновлены», карточка перезапрашивается (инвалидация в `useAssetOperation`). Чужая или несуществующая техника — страница «Техника не найдена» (фичам нельзя импортировать `layout/NotFoundPage`, поэтому используется `StatusPage`).

**Files:**
- Create: `frontend/src/features/assets/AssetOperationDialog.tsx`, `AssetHistory.tsx`, `AssetPage.tsx`
- Modify: `frontend/src/features/assets/index.ts`, `frontend/src/app/routes.tsx`
- Test: `frontend/src/features/assets/AssetPage.test.tsx`

**Interfaces:**
- Consumes: Task 7, `AssetFormDialog` и `mockAssetLookups` (Task 8).
- Produces: `AssetPage` (маршрут `/equipment/assets/:id`), `AssetOperationDialog({ asset, operation, onClose })`, `AssetHistory({ assetId })`.

- [ ] **Step 1: Написать падающий тест**

Создать `frontend/src/features/assets/AssetPage.test.tsx`:

```tsx
import { screen, waitFor, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";

import { renderApp } from "../../test/app";
import { makeMe, mockSignedIn } from "../../test/auth";
import { makeAsset, makeAssetEvent, page } from "../../test/fixtures";
import { errorBody } from "../../test/http";
import { server } from "../../test/server";
import { mockAssetLookups } from "./testing";

function mockCard(asset = makeAsset()) {
  let loads = 0;
  server.use(
    http.get("*/api/assets/100", () => {
      loads += 1;
      return HttpResponse.json(asset);
    }),
  );
  return { loads: () => loads };
}

test("меню «Действия» строится из allowed_operations", async () => {
  mockSignedIn();
  mockAssetLookups();
  mockCard(makeAsset({ allowed_operations: ["issue", "write_off"] }));
  const { user } = renderApp("/equipment/assets/100");

  await user.click(await screen.findByRole("button", { name: "Действия" }));

  const items = screen.getAllByRole("menuitem").map((item) => item.textContent);
  expect(items).toEqual(["Выдать", "Списать"]);
});

test("сотрудник видит карточку без действий", async () => {
  mockSignedIn(makeMe({ role: "employee", id: 10 }));
  mockCard(
    makeAsset({
      status: "in_use",
      owner_id: 10,
      owner_name: "Петров Пётр",
      allowed_operations: [],
    }),
  );
  renderApp("/equipment/assets/100");

  expect(await screen.findByText("INV-001 — Lenovo ThinkPad T14")).toBeInTheDocument();
  expect(screen.getByText("Петров Пётр")).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Действия" })).not.toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Редактировать" })).not.toBeInTheDocument();
});

test("выдача из карточки отправляет сотрудника и причину", async () => {
  mockSignedIn();
  mockAssetLookups();
  mockCard();
  let body: unknown = null;
  server.use(
    http.post("*/api/assets/100/operations", async ({ request }) => {
      body = await request.json();
      return HttpResponse.json(makeAsset({ status: "in_use" }));
    }),
  );
  const { user } = renderApp("/equipment/assets/100");

  await user.click(await screen.findByRole("button", { name: "Действия" }));
  await user.click(screen.getByRole("menuitem", { name: "Выдать" }));
  const dialog = await screen.findByRole("dialog");
  expect(within(dialog).queryByLabelText(/Локация/)).not.toBeInTheDocument();
  await user.click(within(dialog).getByLabelText("Сотрудник"));
  await user.click(await screen.findByRole("option", { name: "Петров Пётр" }));
  await user.click(within(dialog).getByLabelText("Причина"));
  const reasons = (await screen.findAllByRole("option")).map((option) => option.textContent);
  expect(reasons).toEqual(["Не указана", "Новый сотрудник", "Неисправность"]);
  await user.click(screen.getByRole("option", { name: "Новый сотрудник" }));
  await user.click(within(dialog).getByRole("button", { name: "Выдать" }));

  await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
  expect(body).toEqual({ operation: "issue", owner_id: 10, reason_id: 7, comment: null });
});

test("списание требует причину на клиенте", async () => {
  mockSignedIn();
  mockAssetLookups();
  mockCard();
  let called = false;
  server.use(
    http.post("*/api/assets/100/operations", () => {
      called = true;
      return HttpResponse.json(makeAsset());
    }),
  );
  const { user } = renderApp("/equipment/assets/100");

  await user.click(await screen.findByRole("button", { name: "Действия" }));
  await user.click(screen.getByRole("menuitem", { name: "Списать" }));
  const dialog = await screen.findByRole("dialog");
  expect(within(dialog).getByText(/Списание необратимо/)).toBeInTheDocument();
  await user.click(within(dialog).getByRole("button", { name: "Списать" }));

  expect(await within(dialog).findByText("Обязательное поле")).toBeInTheDocument();
  expect(called).toBe(false);
});

test("409 operation_not_allowed закрывает диалог и перезагружает карточку", async () => {
  mockSignedIn();
  mockAssetLookups();
  const card = mockCard();
  server.use(
    http.post("*/api/assets/100/operations", () =>
      HttpResponse.json(
        errorBody("operation_not_allowed", "Операция недоступна", { status: "in_use" }),
        {
          status: 409,
        },
      ),
    ),
  );
  const { user } = renderApp("/equipment/assets/100");

  await user.click(await screen.findByRole("button", { name: "Действия" }));
  await user.click(screen.getByRole("menuitem", { name: "Зарезервировать" }));
  await user.click(
    within(await screen.findByRole("dialog")).getByRole("button", { name: "Зарезервировать" }),
  );

  expect(
    await screen.findByText("Статус техники изменился — данные обновлены"),
  ).toBeInTheDocument();
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  await waitFor(() => expect(card.loads()).toBe(2));
});

test("история показывает переходы и изменённые поля", async () => {
  mockSignedIn();
  mockCard();
  server.use(
    http.get("*/api/assets/100/events", () =>
      HttpResponse.json(
        page([
          makeAssetEvent({
            id: 3,
            event_type: "edited",
            to_status: null,
            to_location_id: null,
            to_location_name: null,
            changes: { model: ["T14", "T14 Gen 5"] },
          }),
          makeAssetEvent({
            id: 2,
            event_type: "issued",
            operation: "issue",
            from_status: "in_stock",
            to_status: "in_use",
            to_owner_id: 10,
            to_owner_name: "Петров Пётр",
            to_location_id: null,
            to_location_name: null,
            reason_name: "Новый сотрудник",
            comment: "Под подпись",
          }),
        ]),
      ),
    ),
  );
  const { user } = renderApp("/equipment/assets/100");

  await user.click(await screen.findByRole("tab", { name: "История" }));

  expect(await screen.findByText("Модель: T14 → T14 Gen 5")).toBeInTheDocument();
  expect(screen.getByText("Статус: На складе → В работе")).toBeInTheDocument();
  expect(screen.getByText("Владелец: — → Петров Пётр")).toBeInTheDocument();
  expect(screen.getByText("Причина: Новый сотрудник")).toBeInTheDocument();
  expect(screen.getByText("Под подпись")).toBeInTheDocument();
});

test("правка при конфликте версий закрывает форму и предупреждает", async () => {
  mockSignedIn();
  mockAssetLookups();
  mockCard();
  let sent: unknown = null;
  server.use(
    http.patch("*/api/assets/100", async ({ request }) => {
      sent = await request.json();
      return HttpResponse.json(
        errorBody("version_conflict", "Данные изменил другой пользователь"),
        {
          status: 409,
        },
      );
    }),
  );
  const { user } = renderApp("/equipment/assets/100");

  await user.click(await screen.findByRole("button", { name: "Редактировать" }));
  const dialog = await screen.findByRole("dialog");
  const model = within(dialog).getByLabelText("Модель");
  await user.clear(model);
  await user.type(model, "T14 Gen 5");
  await user.click(within(dialog).getByRole("button", { name: "Сохранить" }));

  expect(await screen.findByText(/внесите правки заново/)).toBeInTheDocument();
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  expect(sent).toEqual({ model: "T14 Gen 5", version: 1 });
});

test("чужая или несуществующая техника — страница «не найдена»", async () => {
  mockSignedIn(makeMe({ role: "employee" }));
  server.use(
    http.get("*/api/assets/100", () =>
      HttpResponse.json(errorBody("asset_not_found", "Техника не найдена"), { status: 404 }),
    ),
  );
  renderApp("/equipment/assets/100");

  expect(await screen.findByRole("heading", { name: "Техника не найдена" })).toBeInTheDocument();
});
```

- [ ] **Step 2: Убедиться, что тест падает**

Run: `cd frontend && npx vitest run src/features/assets/AssetPage.test.tsx`
Expected: FAIL — на `/equipment/assets/100` страница 404

- [ ] **Step 3: Диалог операции, история, карточка**

Создать `frontend/src/features/assets/AssetOperationDialog.tsx`:

```tsx
import { Alert } from "@mui/material";
import { useSnackbar } from "notistack";
import { useState } from "react";
import { useForm } from "react-hook-form";

import { ApiError } from "../../api/errors";
import { applyApiErrors, fieldByCode } from "../../shared/lib/applyApiErrors";
import { useAssetIssueReasons, useLocations } from "../../shared/lookups/directories";
import {
  ACTIVE_USER_OPTIONS_KEY,
  searchActiveUserOptions,
  useUserNames,
} from "../../shared/lookups/users";
import { FormDialog } from "../../shared/ui/FormDialog";
import { FormAutocomplete } from "../../shared/ui/form/FormAutocomplete";
import { FormSelect } from "../../shared/ui/form/FormSelect";
import { FormTextField } from "../../shared/ui/form/FormTextField";
import { useAssetOperation, type OperationBody } from "./api";
import { OPERATION_LABELS, type Asset, type Operation } from "./labels";

interface OperationFormValues {
  owner_id: number | null;
  reason_id: number | null;
  location_id: number | null;
  comment: string;
}

type FieldMode = "required" | "optional";

/** Поля формы для каждой операции (п. 3 спецификации). */
const OPERATION_FIELDS: Record<
  Operation,
  Partial<Record<"owner_id" | "reason_id" | "location_id", FieldMode>>
> = {
  issue: { owner_id: "required", reason_id: "optional" },
  return: { location_id: "optional" },
  reserve: {},
  unreserve: {},
  to_repair: {},
  repair_to_owner: {},
  repair_to_stock: { location_id: "optional" },
  write_off: { reason_id: "required" },
  move: { location_id: "required" },
};

const fieldForError = fieldByCode<OperationFormValues>({
  recipient_invalid: "owner_id",
  reason_invalid: "reason_id",
  reason_required: "reason_id",
  location_invalid: "location_id",
});

function buildBody(operation: Operation, values: OperationFormValues): OperationBody {
  const comment = values.comment.trim() || null;
  switch (operation) {
    case "issue":
      return { operation, owner_id: values.owner_id!, reason_id: values.reason_id, comment };
    case "return":
    case "repair_to_stock":
      return { operation, location_id: values.location_id, comment };
    case "write_off":
      return { operation, reason_id: values.reason_id, comment };
    case "move":
      return { operation, location_id: values.location_id!, comment };
    default:
      return { operation, comment };
  }
}

interface AssetOperationDialogProps {
  asset: Asset;
  operation: Operation;
  onClose: () => void;
}

export function AssetOperationDialog({ asset, operation, onClose }: AssetOperationDialogProps) {
  const { enqueueSnackbar } = useSnackbar();
  const mutation = useAssetOperation();
  const reasons = useAssetIssueReasons();
  const locations = useLocations();
  const { nameOf } = useUserNames();
  const [formError, setFormError] = useState<string | null>(null);
  const fields = OPERATION_FIELDS[operation];
  const {
    control,
    handleSubmit,
    setError,
    formState: { isSubmitting },
  } = useForm<OperationFormValues>({
    defaultValues: { owner_id: null, reason_id: null, location_id: null, comment: "" },
  });
  const rulesFor = (field: keyof typeof fields) =>
    fields[field] === "required" ? { required: "Обязательное поле" } : undefined;

  const onSubmit = handleSubmit(async (values) => {
    setFormError(null);
    try {
      await mutation.mutateAsync({ id: asset.id, body: buildBody(operation, values) });
      enqueueSnackbar(`${OPERATION_LABELS[operation]}: готово`, { variant: "success" });
      onClose();
    } catch (error) {
      if (error instanceof ApiError && error.code === "operation_not_allowed") {
        enqueueSnackbar("Статус техники изменился — данные обновлены", { variant: "warning" });
        onClose();
        return;
      }
      setFormError(
        applyApiErrors(error, setError, {
          fields: ["owner_id", "reason_id", "location_id", "comment"],
          fieldForError,
        }),
      );
    }
  });

  return (
    <FormDialog
      open
      title={`${OPERATION_LABELS[operation]}: ${asset.inventory_number}`}
      submitting={isSubmitting}
      formError={formError}
      onSubmit={onSubmit}
      onClose={onClose}
      submitLabel={OPERATION_LABELS[operation]}
    >
      {operation === "write_off" && (
        <Alert severity="warning">
          Списание необратимо: техника больше не будет доступна для операций.
        </Alert>
      )}
      {fields.owner_id && (
        <FormAutocomplete
          control={control}
          name="owner_id"
          label="Сотрудник"
          fetchOptions={searchActiveUserOptions}
          queryKey={ACTIVE_USER_OPTIONS_KEY}
          labelFor={nameOf}
          rules={rulesFor("owner_id")}
        />
      )}
      {fields.reason_id && (
        <FormSelect
          control={control}
          name="reason_id"
          label="Причина"
          emptyLabel={fields.reason_id === "optional" ? "Не указана" : undefined}
          options={(reasons.data ?? []).map((item) => ({ value: item.id, label: item.name }))}
          rules={rulesFor("reason_id")}
        />
      )}
      {fields.location_id && (
        <FormSelect
          control={control}
          name="location_id"
          label={fields.location_id === "optional" ? "Локация (если меняется)" : "Локация"}
          emptyLabel={fields.location_id === "optional" ? "Не менять" : undefined}
          options={(locations.data ?? []).map((item) => ({ value: item.id, label: item.name }))}
          rules={rulesFor("location_id")}
        />
      )}
      <FormTextField control={control} name="comment" label="Комментарий" multiline minRows={2} />
    </FormDialog>
  );
}
```

Создать `frontend/src/features/assets/AssetHistory.tsx`:

```tsx
import { Box, Stack, Typography } from "@mui/material";

import { useState } from "react";

import { formatDateTime } from "../../shared/lib/format";
import { DataTable, type Column } from "../../shared/ui/DataTable";
import { useAssetEvents } from "./api";
import { eventChanges, eventTitle, type AssetEvent } from "./labels";

const PAGE_SIZE = 25;

const columns: Column<AssetEvent>[] = [
  {
    key: "created_at",
    header: "Когда",
    width: 160,
    render: (event) => formatDateTime(event.created_at),
  },
  {
    key: "event",
    header: "Событие",
    render: (event) => (
      <Stack spacing={0.5}>
        <Typography sx={{ fontWeight: 600 }}>{eventTitle(event)}</Typography>
        {eventChanges(event).map((line) => (
          <Typography key={line} variant="body2" color="text.secondary">
            {line}
          </Typography>
        ))}
        {event.reason_name && (
          <Typography variant="body2" color="text.secondary">
            Причина: {event.reason_name}
          </Typography>
        )}
        {event.comment && (
          <Box component="q" sx={{ typography: "body2" }}>
            {event.comment}
          </Box>
        )}
      </Stack>
    ),
  },
  { key: "performed_by", header: "Кто", render: (event) => event.performed_by_name },
];

export function AssetHistory({ assetId }: { assetId: number }) {
  const [offset, setOffset] = useState(0);
  const events = useAssetEvents(assetId, PAGE_SIZE, offset);
  return (
    <DataTable
      columns={columns}
      rows={events.data?.items}
      getRowId={(event) => event.id}
      loading={events.isLoading}
      error={events.error}
      onRetry={() => void events.refetch()}
      emptyText="Событий нет"
      paging={{
        limit: PAGE_SIZE,
        offset,
        total: events.data?.total ?? 0,
        onChange: (nextOffset) => setOffset(nextOffset),
      }}
    />
  );
}
```

Создать `frontend/src/features/assets/AssetPage.tsx`:

```tsx
import {
  Alert,
  Button,
  Card,
  CardContent,
  Grid,
  Menu,
  MenuItem,
  Stack,
  Tab,
  Tabs,
  Typography,
} from "@mui/material";
import { IconChevronDown, IconPencil } from "@tabler/icons-react";
import { useState, type ReactNode } from "react";
import { useParams } from "react-router";

import { ApiError, UNKNOWN_ERROR_MESSAGE } from "../../api/errors";
import { useAuth } from "../auth";
import { formatDate } from "../../shared/lib/format";
import { FullScreenLoader } from "../../shared/ui/FullScreenLoader";
import { PageContainer } from "../../shared/ui/PageContainer";
import { StatusPage } from "../../shared/ui/StatusPage";
import { useAsset } from "./api";
import { AssetFormDialog } from "./AssetFormDialog";
import { AssetHistory } from "./AssetHistory";
import { AssetOperationDialog } from "./AssetOperationDialog";
import { AssetStatusChip } from "./AssetStatusChip";
import { OPERATION_LABELS, type Asset, type Operation } from "./labels";

function AssetNotFound() {
  return (
    <StatusPage
      code={404}
      title="Техника не найдена"
      text="Возможно, она не входит в вашу область видимости или ссылка устарела."
    />
  );
}

export function AssetPage() {
  const { id } = useParams();
  const assetId = Number(id);
  if (!Number.isInteger(assetId) || assetId <= 0) return <AssetNotFound />;
  return <AssetScreen key={assetId} assetId={assetId} />;
}

function AssetScreen({ assetId }: { assetId: number }) {
  const asset = useAsset(assetId);
  if (asset.isLoading) return <FullScreenLoader />;
  if (asset.error) {
    if (asset.error instanceof ApiError && asset.error.status === 404) return <AssetNotFound />;
    return (
      <Alert severity="error">
        {asset.error instanceof ApiError ? asset.error.message : UNKNOWN_ERROR_MESSAGE}
      </Alert>
    );
  }
  return asset.data ? <AssetCard asset={asset.data} /> : null;
}

function AssetCard({ asset }: { asset: Asset }) {
  const [tab, setTab] = useState<"info" | "history">("info");
  const [editing, setEditing] = useState(false);
  const [operation, setOperation] = useState<Operation | null>(null);
  const [menuAnchor, setMenuAnchor] = useState<HTMLElement | null>(null);
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";

  return (
    <PageContainer
      title={`${asset.inventory_number} — ${asset.model}`}
      breadcrumbs={[
        { label: "Склад и техника" },
        { label: "Реестр техники", to: "/equipment/assets" },
        { label: asset.inventory_number },
      ]}
      actions={
        isAdmin && (
          <>
            {asset.status !== "written_off" && (
              <Button
                variant="outlined"
                startIcon={<IconPencil size={18} />}
                onClick={() => setEditing(true)}
              >
                Редактировать
              </Button>
            )}
            {asset.allowed_operations.length > 0 && (
              <Button
                variant="contained"
                endIcon={<IconChevronDown size={18} />}
                onClick={(event) => setMenuAnchor(event.currentTarget)}
              >
                Действия
              </Button>
            )}
            <Menu
              anchorEl={menuAnchor}
              open={Boolean(menuAnchor)}
              onClose={() => setMenuAnchor(null)}
            >
              {asset.allowed_operations.map((item) => (
                <MenuItem
                  key={item}
                  onClick={() => {
                    setMenuAnchor(null);
                    setOperation(item);
                  }}
                  sx={item === "write_off" ? { color: "error.main" } : undefined}
                >
                  {OPERATION_LABELS[item]}
                </MenuItem>
              ))}
            </Menu>
          </>
        )
      }
    >
      <Stack direction="row" spacing={1} sx={{ mb: 2, alignItems: "center" }}>
        <AssetStatusChip status={asset.status} />
        {asset.needs_review && <Typography color="warning.main">Требует проверки</Typography>}
      </Stack>
      <Tabs value={tab} onChange={(_, value: "info" | "history") => setTab(value)} sx={{ mb: 2 }}>
        <Tab value="info" label="Информация" />
        <Tab value="history" label="История" />
      </Tabs>
      {tab === "info" ? <AssetInfo asset={asset} /> : <AssetHistory assetId={asset.id} />}

      {editing && <AssetFormDialog asset={asset} onClose={() => setEditing(false)} />}
      {operation && (
        <AssetOperationDialog
          asset={asset}
          operation={operation}
          onClose={() => setOperation(null)}
        />
      )}
    </PageContainer>
  );
}

function AssetInfo({ asset }: { asset: Asset }) {
  const date = (value: string | null) => (value ? formatDate(value) : "—");
  const rows: [string, ReactNode][] = [
    ["Тип", asset.asset_type_name],
    ["Инвентарный номер", asset.inventory_number],
    ["Серийный номер", asset.serial_number ?? "—"],
    ["Модель", asset.model],
    ["Владелец", asset.owner_name ?? "—"],
    ["Локация", asset.location_name],
    ["Дата принятия к учёту", date(asset.accepted_at)],
    ["Дата покупки", date(asset.purchased_at)],
    ["Гарантия до", date(asset.warranty_until)],
    ["Стоимость", asset.initial_cost ? `${asset.initial_cost} ₽` : "—"],
  ];
  return (
    <Card variant="outlined">
      <CardContent>
        <Grid container spacing={2}>
          {rows.map(([label, value]) => (
            <Grid key={label} size={{ xs: 12, sm: 6, md: 4 }}>
              <Typography variant="body2" color="text.secondary">
                {label}
              </Typography>
              <Typography>{value}</Typography>
            </Grid>
          ))}
        </Grid>
      </CardContent>
    </Card>
  );
}
```

Создать `frontend/src/features/assets/index.ts` — целиком:

```ts
export { AssetPage } from "./AssetPage";
export { AssetsPage } from "./AssetsPage";
```

- [ ] **Step 4: Маршрут**

В `frontend/src/app/routes.tsx` заменить:

```tsx
import { AssetsPage } from "../features/assets";
```

на:

```tsx
import { AssetPage, AssetsPage } from "../features/assets";
```

В `frontend/src/app/routes.tsx` заменить:

```tsx
          { path: "/equipment/assets", element: <AssetsPage /> },
```

на:

```tsx
          { path: "/equipment/assets", element: <AssetsPage /> },
          { path: "/equipment/assets/:id", element: <AssetPage /> },
```

- [ ] **Step 5: Проверки проходят**

Run: `cd frontend && npm run format && npm run check`
Expected: типы, ESLint, Prettier, `check:api` и все тесты Vitest проходят

- [ ] **Step 6: Коммит**

```bash
git add frontend && git commit -m "feat(frontend): карточка техники — история, операции, правка"
```

### Task 10: Фронтенд: «Выдать / принять»

Только Admin (п. 4.2.1 ТЗ). «Выдать»: кому, несколько активов «На складе» (`AssetMultiPicker` — поиск на сервере), причина, комментарий; при 409 `assets_unavailable` форма остаётся, недоступные активы — красные метки. «Принять»: сотрудник → его техника «В работе» с флажками, локация (необязательно), комментарий.

**Files:**
- Create: `frontend/src/features/assets/AssetMultiPicker.tsx`, `IssuePage.tsx`
- Modify: `frontend/src/features/assets/index.ts`, `frontend/src/app/routes.tsx`
- Test: `frontend/src/features/assets/IssuePage.test.tsx`

**Interfaces:**
- Consumes: `fetchAssets`, `useAssets`, `useIssueAssets`, `useReturnAssets` (Task 7), `mockAssetLookups` (Task 8).
- Produces: `IssuePage` (маршрут `/equipment/issue` внутри `RequireRole role="admin"`), `AssetMultiPicker({ value, onChange, unavailableIds, error? })`.

- [ ] **Step 1: Написать падающий тест**

Создать `frontend/src/features/assets/IssuePage.test.tsx`:

```tsx
import { screen, waitFor, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";

import { renderApp } from "../../test/app";
import { makeMe, mockSignedIn } from "../../test/auth";
import { makeAsset, page } from "../../test/fixtures";
import { errorBody } from "../../test/http";
import { server } from "../../test/server";
import { mockAssetLookups } from "./testing";

const FREE = [
  makeAsset({ id: 100, inventory_number: "INV-001" }),
  makeAsset({ id: 101, inventory_number: "INV-002", model: "Dell Latitude" }),
];

async function pickEmployee(
  user: ReturnType<typeof renderApp>["user"],
  section: HTMLElement,
  label: string,
) {
  await user.click(within(section).getByLabelText(label));
  await user.click(await screen.findByRole("option", { name: "Петров Пётр" }));
}

test("выдача: при 409 недоступная техника подсвечивается, форма остаётся", async () => {
  mockSignedIn();
  mockAssetLookups();
  let body: unknown = null;
  server.use(
    http.get("*/api/assets", ({ request }) => {
      const url = new URL(request.url);
      expect(url.searchParams.getAll("status")).toEqual(["in_stock"]);
      return HttpResponse.json(page(FREE));
    }),
    http.post("*/api/assets/issue", async ({ request }) => {
      body = await request.json();
      return HttpResponse.json(
        errorBody("assets_unavailable", "Часть техники недоступна", [
          { asset_id: 101, inventory_number: "INV-002", status: "in_use" },
        ]),
        { status: 409 },
      );
    }),
  );
  const { user } = renderApp("/equipment/issue");

  const section = await screen.findByRole("region", { name: "Выдать" });
  await pickEmployee(user, section, "Кому");
  await user.click(within(section).getByLabelText("Техника"));
  await user.click(await screen.findByRole("option", { name: "INV-001 — Lenovo ThinkPad T14" }));
  await user.click(within(section).getByLabelText("Техника"));
  await user.click(await screen.findByRole("option", { name: "INV-002 — Dell Latitude" }));
  await user.click(within(section).getByRole("button", { name: "Выдать" }));

  expect(await within(section).findByText(/выделена красным/)).toBeInTheDocument();
  expect(body).toEqual({ owner_id: 10, asset_ids: [100, 101], reason_id: null, comment: null });
  const taken = within(section).getByText("INV-002 — Dell Latitude").closest(".MuiChip-root")!;
  expect(taken).toHaveClass("MuiChip-colorError");
});

test("выдача без сотрудника и техники подсказывает поля и не отправляет запрос", async () => {
  mockSignedIn();
  mockAssetLookups();
  const { user } = renderApp("/equipment/issue");

  const section = await screen.findByRole("region", { name: "Выдать" });
  await user.click(within(section).getByRole("button", { name: "Выдать" }));

  expect(within(section).getByText("Выберите сотрудника")).toBeInTheDocument();
  expect(within(section).getByText("Выберите технику")).toBeInTheDocument();
});

test("приём: техника сотрудника в работе, отмеченное уходит на склад", async () => {
  mockSignedIn();
  mockAssetLookups();
  let body: unknown = null;
  server.use(
    http.get("*/api/assets", ({ request }) => {
      const url = new URL(request.url);
      expect(url.searchParams.get("owner_id")).toBe("10");
      expect(url.searchParams.getAll("status")).toEqual(["in_use"]);
      return HttpResponse.json(
        page(FREE.map((asset) => ({ ...asset, status: "in_use" as const, owner_id: 10 }))),
      );
    }),
    http.post("*/api/assets/return", async ({ request }) => {
      body = await request.json();
      return HttpResponse.json([makeAsset({ id: 101 })]);
    }),
  );
  const { user } = renderApp("/equipment/issue");

  const section = await screen.findByRole("region", { name: "Принять" });
  expect(within(section).getByRole("button", { name: "Принять на склад" })).toBeDisabled();
  await pickEmployee(user, section, "От кого");
  await user.click(await within(section).findByLabelText("INV-002 — Dell Latitude"));
  await user.click(within(section).getByLabelText("Локация (если меняется)"));
  await user.click(await screen.findByRole("option", { name: "Офис, каб. 101" }));
  await user.click(within(section).getByRole("button", { name: "Принять на склад" }));

  expect(await screen.findByText("Принято на склад: 1")).toBeInTheDocument();
  expect(body).toEqual({ asset_ids: [101], location_id: 6, comment: null });
});

test("страница выдачи доступна только администратору", async () => {
  mockSignedIn(makeMe({ role: "manager" }));
  renderApp("/equipment/issue");

  await waitFor(() =>
    expect(screen.queryByRole("region", { name: "Выдать" })).not.toBeInTheDocument(),
  );
  expect(
    await screen.findByRole("heading", { name: /нет доступа|не найдена/i }),
  ).toBeInTheDocument();
});
```

- [ ] **Step 2: Убедиться, что тест падает**

Run: `cd frontend && npx vitest run src/features/assets/IssuePage.test.tsx`
Expected: FAIL — на `/equipment/issue` нет разделов «Выдать» и «Принять»

- [ ] **Step 3: Выбор техники и страница**

Создать `frontend/src/features/assets/AssetMultiPicker.tsx`:

```tsx
import { Autocomplete, Chip, TextField } from "@mui/material";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { useDebouncedValue } from "../../shared/lib/useDebouncedValue";
import { queryKeys } from "../../shared/lookups/queryKeys";
import { fetchAssets } from "./api";
import type { Asset } from "./labels";

interface AssetMultiPickerProps {
  value: Asset[];
  onChange: (assets: Asset[]) => void;
  /** Активы, которые стали недоступны (ответ 409): подсвечиваются красным. */
  unavailableIds: ReadonlySet<number>;
  error?: string;
}

const assetLabel = (asset: Asset) => `${asset.inventory_number} — ${asset.model}`;

/** Выбор нескольких активов со статусом «На складе» с поиском на сервере. */
export function AssetMultiPicker({
  value,
  onChange,
  unavailableIds,
  error,
}: AssetMultiPickerProps) {
  const [open, setOpen] = useState(false);
  const [input, setInput] = useState("");
  const query = useDebouncedValue(input);
  const options = useQuery({
    queryKey: [...queryKeys.assets, "in-stock-options", query],
    queryFn: () => fetchAssets({ q: query, status: "in_stock", limit: 50, offset: 0 }),
    enabled: open,
  });

  return (
    <Autocomplete<Asset, true>
      multiple
      open={open}
      onOpen={() => setOpen(true)}
      onClose={() => setOpen(false)}
      value={value}
      options={options.data?.items ?? []}
      loading={options.isFetching}
      filterOptions={(items) => items}
      filterSelectedOptions
      isOptionEqualToValue={(option, current) => option.id === current.id}
      getOptionLabel={assetLabel}
      onChange={(_, assets) => onChange(assets)}
      onInputChange={(_, text, reason) => {
        if (reason === "input") setInput(text);
        if (reason === "clear" || reason === "reset") setInput("");
      }}
      noOptionsText="Свободной техники не найдено"
      loadingText="Загрузка…"
      renderValue={(assets, getItemProps) =>
        assets.map((asset, index) => {
          const { key, ...itemProps } = getItemProps({ index });
          return (
            <Chip
              key={key}
              {...itemProps}
              label={assetLabel(asset)}
              color={unavailableIds.has(asset.id) ? "error" : "default"}
            />
          );
        })
      }
      renderInput={(params) => (
        <TextField {...params} label="Техника" error={Boolean(error)} helperText={error} />
      )}
    />
  );
}
```

Создать `frontend/src/features/assets/IssuePage.tsx`:

```tsx
import {
  Alert,
  Button,
  Card,
  CardContent,
  Checkbox,
  FormControlLabel,
  MenuItem,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import { useSnackbar } from "notistack";
import { useState } from "react";

import { ApiError, UNKNOWN_ERROR_MESSAGE } from "../../api/errors";
import { useAssetIssueReasons, useLocations } from "../../shared/lookups/directories";
import {
  ACTIVE_USER_OPTIONS_KEY,
  searchActiveUserOptions,
  useUserNames,
} from "../../shared/lookups/users";
import { EntityAutocomplete } from "../../shared/ui/EntityAutocomplete";
import { PageContainer } from "../../shared/ui/PageContainer";
import { useAssets, useIssueAssets, useReturnAssets } from "./api";
import { AssetMultiPicker } from "./AssetMultiPicker";
import type { Asset } from "./labels";

const errorMessage = (error: unknown) =>
  error instanceof ApiError ? error.message : UNKNOWN_ERROR_MESSAGE;

/** Элемент details ошибки assets_unavailable (backend: UnavailableAsset). */
interface UnavailableAsset {
  asset_id: number;
}

/** id активов из details ошибки assets_unavailable. */
function unavailableOf(error: unknown): Set<number> {
  if (!(error instanceof ApiError) || error.code !== "assets_unavailable") return new Set();
  const details = error.details as UnavailableAsset[] | null;
  return new Set((details ?? []).map((item) => item.asset_id));
}

export function IssuePage() {
  return (
    <PageContainer
      title="Выдать / принять"
      breadcrumbs={[{ label: "Склад и техника" }, { label: "Выдать / принять" }]}
    >
      <Stack spacing={3}>
        <IssueSection />
        <ReturnSection />
      </Stack>
    </PageContainer>
  );
}

function IssueSection() {
  const { enqueueSnackbar } = useSnackbar();
  const { nameOf } = useUserNames();
  const reasons = useAssetIssueReasons();
  const issue = useIssueAssets();
  const [ownerId, setOwnerId] = useState<number | null>(null);
  const [assets, setAssets] = useState<Asset[]>([]);
  const [reasonId, setReasonId] = useState<number | null>(null);
  const [comment, setComment] = useState("");
  const [unavailable, setUnavailable] = useState<ReadonlySet<number>>(new Set());
  const [error, setError] = useState<string | null>(null);
  const [touched, setTouched] = useState(false);

  const submit = async () => {
    setTouched(true);
    if (ownerId === null || assets.length === 0) return;
    setError(null);
    try {
      const issued = await issue.mutateAsync({
        owner_id: ownerId,
        asset_ids: assets.map((asset) => asset.id),
        reason_id: reasonId,
        comment: comment.trim() || null,
      });
      enqueueSnackbar(`Выдано: ${issued.length}`, { variant: "success" });
      setAssets([]);
      setComment("");
      setUnavailable(new Set());
      setTouched(false);
    } catch (caught) {
      setUnavailable(unavailableOf(caught));
      setError(
        caught instanceof ApiError && caught.code === "assets_unavailable"
          ? "Часть техники уже недоступна — она выделена красным. Уберите её и повторите."
          : errorMessage(caught),
      );
    }
  };

  return (
    <Card variant="outlined">
      <CardContent>
        <Stack spacing={2.5} component="section" aria-label="Выдать">
          <Typography variant="h5" component="h2">
            Выдать
          </Typography>
          {error && <Alert severity="error">{error}</Alert>}
          <EntityAutocomplete
            label="Кому"
            value={ownerId}
            onChange={setOwnerId}
            fetchOptions={searchActiveUserOptions}
            queryKey={ACTIVE_USER_OPTIONS_KEY}
            labelFor={nameOf}
            error={touched && ownerId === null}
            helperText={touched && ownerId === null ? "Выберите сотрудника" : undefined}
          />
          <AssetMultiPicker
            value={assets}
            onChange={(next) => {
              setAssets(next);
              setUnavailable(new Set());
            }}
            unavailableIds={unavailable}
            error={touched && assets.length === 0 ? "Выберите технику" : undefined}
          />
          <TextField
            select
            label="Причина"
            value={reasonId === null ? "" : String(reasonId)}
            onChange={(event) =>
              setReasonId(event.target.value ? Number(event.target.value) : null)
            }
          >
            <MenuItem value="">Не указана</MenuItem>
            {(reasons.data ?? []).map((item) => (
              <MenuItem key={item.id} value={String(item.id)}>
                {item.name}
              </MenuItem>
            ))}
          </TextField>
          <TextField
            label="Комментарий"
            value={comment}
            onChange={(event) => setComment(event.target.value)}
            multiline
            minRows={2}
          />
          <Stack direction="row">
            <Button variant="contained" loading={issue.isPending} onClick={() => void submit()}>
              Выдать
            </Button>
          </Stack>
        </Stack>
      </CardContent>
    </Card>
  );
}

function ReturnSection() {
  const { enqueueSnackbar } = useSnackbar();
  const { nameOf } = useUserNames();
  const locations = useLocations();
  const returnAssets = useReturnAssets();
  const [ownerId, setOwnerId] = useState<number | null>(null);
  const [selected, setSelected] = useState<ReadonlySet<number>>(new Set());
  const [locationId, setLocationId] = useState<number | null>(null);
  const [comment, setComment] = useState("");
  const [error, setError] = useState<string | null>(null);
  const owned = useAssets({ ownerId, status: "in_use", limit: 100, offset: 0 }, ownerId !== null);

  const toggle = (id: number) =>
    setSelected((current) => {
      const next = new Set(current);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });

  const submit = async () => {
    setError(null);
    try {
      const returned = await returnAssets.mutateAsync({
        asset_ids: [...selected],
        location_id: locationId,
        comment: comment.trim() || null,
      });
      enqueueSnackbar(`Принято на склад: ${returned.length}`, { variant: "success" });
      setSelected(new Set());
      setComment("");
    } catch (caught) {
      setSelected(new Set());
      setError(
        caught instanceof ApiError && caught.code === "assets_unavailable"
          ? "Список техники изменился — он обновлён. Отметьте технику заново."
          : errorMessage(caught),
      );
    }
  };

  const items = owned.data?.items ?? [];

  return (
    <Card variant="outlined">
      <CardContent>
        <Stack spacing={2.5} component="section" aria-label="Принять">
          <Typography variant="h5" component="h2">
            Принять
          </Typography>
          {error && <Alert severity="error">{error}</Alert>}
          <EntityAutocomplete
            label="От кого"
            value={ownerId}
            onChange={(id) => {
              setOwnerId(id);
              setSelected(new Set());
              setError(null);
            }}
            fetchOptions={searchActiveUserOptions}
            queryKey={ACTIVE_USER_OPTIONS_KEY}
            labelFor={nameOf}
          />
          {ownerId !== null && owned.isSuccess && items.length === 0 && (
            <Typography color="text.secondary">У сотрудника нет техники в работе</Typography>
          )}
          {owned.error && <Alert severity="error">{errorMessage(owned.error)}</Alert>}
          {items.length > 0 && (
            <Stack>
              {items.map((asset) => (
                <FormControlLabel
                  key={asset.id}
                  label={`${asset.inventory_number} — ${asset.model}`}
                  control={
                    <Checkbox checked={selected.has(asset.id)} onChange={() => toggle(asset.id)} />
                  }
                />
              ))}
            </Stack>
          )}
          <TextField
            select
            label="Локация (если меняется)"
            value={locationId === null ? "" : String(locationId)}
            onChange={(event) =>
              setLocationId(event.target.value ? Number(event.target.value) : null)
            }
          >
            <MenuItem value="">Не менять</MenuItem>
            {(locations.data ?? []).map((item) => (
              <MenuItem key={item.id} value={String(item.id)}>
                {item.name}
              </MenuItem>
            ))}
          </TextField>
          <TextField
            label="Комментарий"
            value={comment}
            onChange={(event) => setComment(event.target.value)}
            multiline
            minRows={2}
          />
          <Stack direction="row">
            <Button
              variant="contained"
              disabled={selected.size === 0}
              loading={returnAssets.isPending}
              onClick={() => void submit()}
            >
              Принять на склад
            </Button>
          </Stack>
        </Stack>
      </CardContent>
    </Card>
  );
}
```

Создать `frontend/src/features/assets/index.ts` — целиком:

```ts
export { AssetPage } from "./AssetPage";
export { AssetsPage } from "./AssetsPage";
export { IssuePage } from "./IssuePage";
```

- [ ] **Step 4: Маршрут**

В `frontend/src/app/routes.tsx` заменить:

```tsx
import { AssetPage, AssetsPage } from "../features/assets";
```

на:

```tsx
import { AssetPage, AssetsPage, IssuePage } from "../features/assets";
```

В `frontend/src/app/routes.tsx` заменить:

```tsx
            element: <RequireRole role="admin" />,
            children: [
```

на:

```tsx
            element: <RequireRole role="admin" />,
            children: [
              { path: "/equipment/issue", element: <IssuePage /> },
```

- [ ] **Step 5: Проверки проходят**

Run: `cd frontend && npm run format && npm run check`
Expected: типы, ESLint, Prettier, `check:api` и все тесты Vitest проходят

- [ ] **Step 6: Коммит**

```bash
git add frontend && git commit -m "feat(frontend): выдача и приём техники"
```

### Task 11: README, полная проверка, ручная проверка в браузере

**Files:**
- Modify: `README.md`

**Interfaces:**
- Consumes: всё предыдущее. Produces: раздел «Оргтехника» и пункты 8–13 чек-листа ручной проверки в README.

- [ ] **Step 1: README**

В `README.md` (чек-лист ручной проверки) заменить:

```markdown
7. Выход в одной вкладке завершает сессию в другой.
```

на:

```markdown
7. Выход в одной вкладке завершает сессию в другой.
8. Оргтехника: создание актива (типы и локации — из справочников), дубль инвентарного номера показывается под полем.
9. «Выдать / принять»: выдача нескольких активов сотруднику; приём части из них на склад с другой локацией.
10. Карточка: резерв → снятие резерва, ремонт → возврат владельцу, списание (без причины не проходит); история показывает каждый шаг.
11. Конфликт двух вкладок: одна выдаёт актив, вторая пытается зарезервировать его же → «Статус техники изменился», карточка обновилась.
12. Под сотрудником виден только свой реестр, под руководителем — техника отдела; «Выдать / принять» и «Действия» им недоступны.
13. Деактивация сотрудника с техникой «В работе» → в списке причин блокировки есть эта техника.
```

В `README.md` (новый раздел перед «Архитектура») заменить:

```markdown
## Архитектура
```

на:

```markdown
## Оргтехника

Модуль `backend/app/modules/assets` (схема БД `equipment`), экраны — `frontend/src/features/assets`. Правила переходов статусов (п. 4.2.2 ТЗ) описаны одной таблицей в `assets/transitions.py`: из неё backend проверяет операции и отдаёт в карточке `allowed_operations`, по которым фронтенд строит меню «Действия». Статус, владелец и локация меняются только операциями (`POST /api/assets/{id}/operations`, массово — `/api/assets/issue` и `/api/assets/return`); `PATCH` меняет только описательные поля с проверкой `version`. Строки активов блокируются `SELECT … FOR UPDATE`, поэтому параллельная выдача одного актива даёт 409.

## Архитектура
```

- [ ] **Step 2: Полная проверка**

Run: `make lint && make test`
Expected: всё зелёное

Run: `cd frontend && npm run check && npm run build`
Expected: всё зелёное, сборка без предупреждений

- [ ] **Step 3: Проверка на запущенном стеке**

Run: `docker compose up -d --build && sleep 5 && curl -s -o /dev/null -w '%{http_code}\n' localhost:8080/api/assets`
Expected: `401` (эндпоинт есть, требуется вход); миграция `0005` применилась при старте backend

- [ ] **Step 4: Ручная проверка в браузере — передать пользователю**

Агент браузерную проверку выполнить не может. В отчёте перечислить пункты 8–13 чек-листа README и попросить пользователя пройти их на http://localhost:8080 до слияния ветки.

- [ ] **Step 5: Коммит**

```bash
git add README.md && git commit -m "docs: раздел «Оргтехника» и чек-лист ручной проверки"
```
