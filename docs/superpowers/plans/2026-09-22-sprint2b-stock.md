# Спринт 2, часть 2b — расходники, журнал движений, единая выдача: план реализации

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Расходники (позиции на складах, приход, списание, корректировка, перемещение), единая выдача техники и расходников одной операцией и общий журнал движений — backend и фронтенд, только для Admin.

**Architecture:** Код расходников — в модуле `backend/app/modules/assets` отдельными файлами `stock_*.py` (схема БД `equipment`, миграция `0006`). Остаток меняется только через `stock_operations.record_movement` вместе с записью `StockMovement` и аудитом; строки блокируются `SELECT … FOR UPDATE` в порядке id. Единая выдача (`checkout.py`) и журнал (`journal.py`, `UNION ALL` по двум таблицам модуля) — под роутером `/api/equipment`. Фронтенд — фичи `features/stock` (расходники, строки выдачи) и `features/movements` (журнал) на общих компонентах спринта 1.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2 (async) + asyncpg, Alembic, pydantic 2, pytest; React 19 + TypeScript 5.9, MUI 9, TanStack Query 5, react-hook-form 7, openapi-fetch, Vitest + Testing Library + MSW.

**Spec:** `docs/superpowers/specs/2026-09-22-sprint2b-stock-design.md`; ТЗ — `docs/spec/TZ_IT_platforma_v1.2.md` (п. 2.2, 3.1, 3.2, 4.2).

**Как проверен план.** Весь код плана написан и прогнан задача за задачей в отдельном worktree (ветка `draft/sprint2b` от `feature/sprint2b-stock`): для каждой задачи шаг RED действительно падал с указанной ошибкой, шаги GREEN, `make lint`, `make test` и `npm run check` проходили; код в шагах извлечён из этих коммитов (новые файлы — целиком, изменённые — диффом). Итог: backend — 296 тестов, фронтенд — 115, `alembic check` и `npm run build` чистые. Тест гонки списания проверен на то, что без `FOR UPDATE` он падает. Не проверялось агентом: работа в браузере — пункты 14–21 чек-листа README выполняет пользователь.

## Уточнения к спецификации

Найдены при проверке реализации; вносятся в спецификацию отдельным коммитом вместе с планом:

1. **`populate_existing` при блокировке.** Перемещение читает позицию-источник без блокировки (нужны наименование и склад), затем блокирует обе позиции. Без `execution_options(populate_existing=True)` ORM возвращает объект из identity map с остатком до блокировки — параллельные перемещения теряют обновление. Опция стоит в `lock_stock_items` и в `get_stock_item(for_update=True)`.
2. **Часовой пояс компании** — новый `app/core/timezone.py` (`company_today`, `company_day_bounds`): дата документа по умолчанию и границы периода журнала.
3. **Журнал на фронтенде — отдельная фича `features/movements`**, а не часть `features/stock`: иначе цикл импортов `assets → stock → assets`.
4. **Низкий остаток** показывается красным `Chip` остатка (и подписью в карточке); подсветки всей строки нет — общий `DataTable` не меняется.
5. **`StockMovementRead.counterpart_location_id/name`** — склад второй половины перемещения («Куда» / «Откуда» в истории позиции).
6. **Строки журнала расходников:** у движений, кроме перемещений, `to_location` — склад позиции, `from_location` пуст; у перемещения — «откуда → куда» на обеих строках. Фильтр `location_id` проверяет обе колонки.
7. **Порядок в списке расходников:** наименование без учёта регистра, затем id склада.
8. **Страница «Выдать» переходит на `/api/equipment/checkout` в задаче backend-выдачи (Task 4)**, чтобы каждый коммит оставался зелёным; строки расходников добавляются в Task 9.
9. **`check_reason(session, reason_id, *, assets=True, stock=False)`** — единая проверка применимости причины к составу операции (списание расходника, выдача, операции с техникой).
10. **ESLint:** в список изолированных фич добавлены `assets` (пропущен в 2a), `stock`, `movements`.
11. **Уведомление об успешной выдаче** — «Выдано позиций: N» (техника + строки расходников).

## Global Constraints

- Ветка `feature/sprint2b-stock` (от `feature/sprint2a-assets`); команды — из корня репозитория, если не сказано иное. Тестовая БД — `it_platform_test` (если осталась на чужой ревизии — пересоздать: в ней только тестовые данные).
- Модули обращаются друг к другу только через `service.py` и `events.py`; `users_auth` и `directories` не импортируют `assets` — проверяет `make lint` (import-linter). Межсхемные JOIN в бизнес-логике запрещены; журнал объединяет две таблицы одного модуля `assets`.
- Все новые эндпоинты — только Admin (`AdminDep`, иначе 403 `insufficient_role`).
- Формат ошибок API — `{"error": {"code", "message", "details"}}`; коды — ровно из спецификации: `stock_item_not_found`, `stock_item_name_taken`, `name_blank`, `unit_blank`, `category_invalid`, `location_invalid`, `reason_invalid`, `reason_required`, `document_date_in_future`, `same_location`, `comment_required`, `adjustment_no_change`, `insufficient_stock`, `stock_item_inactive`, `stock_not_empty`, `version_conflict`, `checkout_empty`, `duplicate_asset`, `duplicate_stock_line`, `recipient_invalid`, `checkout_unavailable`.
- Остаток меняется только вместе с `StockMovement` и `AuditLog` (`entity_type = "stock_item"`) в одной транзакции; `CHECK (quantity >= 0)` — последняя линия защиты.
- Количество — целое; строки выдачи — до 50 активов и до 50 позиций.
- После изменения API — `make gen-api` (обновляет `backend/openapi.json` и `frontend/src/api/schema.d.ts`), оба файла коммитятся вместе с кодом: CI проверяет их актуальность. Модели и миграции должны совпадать: `alembic check` в CI.
- Интерфейс на русском; тексты ошибок для пользователя — из `message` backend. Минус в количествах — типографский «−».
- Фронтенд: фича импортирует другие фичи только через `index.ts`, не импортирует `layout/` и `app/` (ESLint); типы API — только из `schema.d.ts`.
- TDD: тест пишется и падает до кода. Перед коммитом backend — `make format && make lint` и тесты задачи; фронтенд — `npm run format && npm run check`.
- Сообщения коммитов заканчиваются строкой `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>` (в шагах опущено для краткости).

## Структура файлов

```
backend/app/core/timezone.py              часовой пояс компании: сегодня, границы дней в UTC
backend/app/modules/assets/
├── stock_models.py        StockItem, StockMovement, StockMovementType
├── stock_schemas.py       запросы и ответы API расходников, схемы операций
├── stock_registry.py      позиции: список, карточка, создание, правка, история движений
├── stock_operations.py    record_movement, блокировки, приход/списание/корректировка/перемещение
├── stock_presenter.py     ответы API расходников с названиями через service других модулей
├── stock_router.py        /api/stock-items…
├── checkout.py            единая выдача техники и расходников
├── journal.py             журнал движений: UNION ALL, фильтры, группы операций
├── journal_presenter.py   строки журнала с ФИО, складами, причинами
├── equipment_schemas.py   CheckoutRequest/Result, CheckoutUnavailable, JournalEntryRead
├── equipment_router.py    /api/equipment/checkout, /api/equipment/movements
├── operations.py          (изм.) lock_assets, unavailable_assets, apply_transition; без массовой выдачи
└── checks.py              (изм.) check_stock_category, check_reason по составу
backend/app/modules/directories/service.py   (изм.) вид справочника stock-categories
backend/migrations/versions/0006_stock.py
backend/tests/modules/assets/  test_stock_models, test_stock_items_api, test_stock_operations_api,
                               test_stock_concurrency, test_checkout_api, test_journal_api
backend/tests/core/test_timezone.py

frontend/src/features/stock/       labels, api, testing, StockPage, StockItemPage, StockItemFormDialog,
                                   StockOperationDialog, StockHistory, StockItemPicker,
                                   StockQuantityChip, StockLinesField
frontend/src/features/movements/   labels, api, MovementsPage
frontend/src/features/assets/      (изм.) IssuePage — единая выдача, api — useCheckout, labels — assetEventLabel
frontend/src/shared/lookups/directories.ts   (изм.) категории, причины по составу (reasonFits)
frontend/src/shared/lib/           (изм.) localDateIso, dateParam
```

---

### Task 1: Модели и миграция `equipment.stock_items`, `equipment.stock_movements`

Таблицы расходников и движений (п. 2 спецификации). Правила знака, даты документа, получателя, перемещения и комментария корректировки закреплены `CHECK`-ограничениями: остаток не уйдёт в минус даже в обход сервиса. Уникальность наименования на складе — функциональный индекс `lower(name), location_id`; в модели он объявлен после класса, потому что ссылается на колонку.

**Files:**
- Modify: `backend/app/model_registry.py`
- Create: `backend/app/modules/assets/stock_models.py`
- Create: `backend/migrations/versions/0006_stock.py`
- Test (create): `backend/tests/modules/assets/test_stock_models.py`

**Interfaces:**
- Produces: `app.modules.assets.stock_models` — `StockItem`, `StockMovement`, `StockMovementType` (`receipt`, `issue`, `write_off`, `adjustment`, `transfer_out`, `transfer_in`).
- Produces: имя индекса `uq_stock_items_name_location` (по нему Task 2 распознаёт `stock_item_name_taken`).

- [ ] **Step 1: Написать падающие тесты**

Создать `backend/tests/modules/assets/test_stock_models.py`:

```python
"""Ограничения БД страхуют правила остатков и движений независимо от кода (п. 2 спецификации 2b)."""

import uuid
from datetime import date

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.assets.stock_models import StockItem, StockMovement, StockMovementType
from app.modules.directories.models import Location, StockCategory
from tests.factories import make_user


async def _item(session: AsyncSession, **overrides: object) -> StockItem:
    category = StockCategory(name="Картриджи")
    location = Location(name="Склад")
    session.add_all([category, location])
    await session.flush()
    values: dict[str, object] = {
        "name": "Картридж HP 85A",
        "stock_category_id": category.id,
        "unit": "шт",
        "location_id": location.id,
        "quantity": 5,
        "min_quantity": 0,
        "is_active": True,
        "version": 1,
    }
    values.update(overrides)
    item = StockItem(**values)
    session.add(item)
    await session.flush()
    return item


async def test_quantity_cannot_go_negative(db_session: AsyncSession) -> None:
    item = await _item(db_session)

    with pytest.raises(IntegrityError):
        async with db_session.begin_nested():
            await db_session.execute(
                text("UPDATE equipment.stock_items SET quantity = -1 WHERE id = :id"),
                {"id": item.id},
            )


async def test_inactive_item_must_be_empty(db_session: AsyncSession) -> None:
    item = await _item(db_session)

    with pytest.raises(IntegrityError):
        async with db_session.begin_nested():
            await db_session.execute(
                text("UPDATE equipment.stock_items SET is_active = false WHERE id = :id"),
                {"id": item.id},
            )


async def test_name_unique_per_location_ignoring_case(db_session: AsyncSession) -> None:
    item = await _item(db_session)

    with pytest.raises(IntegrityError):
        async with db_session.begin_nested():
            db_session.add(
                StockItem(
                    name="КАРТРИДЖ hp 85a",
                    stock_category_id=item.stock_category_id,
                    unit="шт",
                    location_id=item.location_id,
                    quantity=0,
                    min_quantity=0,
                    is_active=True,
                    version=1,
                )
            )


def _movement(item: StockItem, actor_id: int, **overrides: object) -> StockMovement:
    values: dict[str, object] = {
        "stock_item_id": item.id,
        "movement_type": StockMovementType.WRITE_OFF,
        "delta": -1,
        "quantity_after": 4,
        "performed_by": actor_id,
    }
    values.update(overrides)
    return StockMovement(**values)


@pytest.mark.parametrize(
    "overrides",
    [
        pytest.param({"movement_type": StockMovementType.RECEIPT, "delta": -1}, id="receipt-sign"),
        pytest.param({"delta": 1}, id="write-off-sign"),
        pytest.param({"delta": 0, "movement_type": StockMovementType.ADJUSTMENT}, id="zero"),
        pytest.param({"quantity_after": -1}, id="negative-after"),
        pytest.param(
            {"movement_type": StockMovementType.RECEIPT, "delta": 1}, id="receipt-no-date"
        ),
        pytest.param({"document_date": date(2026, 9, 1)}, id="date-not-receipt"),
        pytest.param({"movement_type": StockMovementType.ISSUE}, id="issue-no-recipient"),
        pytest.param({"movement_type": StockMovementType.TRANSFER_OUT}, id="transfer-no-id"),
        pytest.param({"transfer_id": uuid.uuid4()}, id="transfer-id-not-transfer"),
        pytest.param(
            {"movement_type": StockMovementType.ADJUSTMENT, "comment": None}, id="adjust-comment"
        ),
    ],
)
async def test_movement_rules_enforced_by_database(
    db_session: AsyncSession, overrides: dict[str, object]
) -> None:
    item = await _item(db_session)
    actor = await make_user(db_session)

    with pytest.raises(IntegrityError):
        async with db_session.begin_nested():
            db_session.add(_movement(item, actor.id, **overrides))


async def test_recipient_only_on_issue(db_session: AsyncSession) -> None:
    item = await _item(db_session)
    actor = await make_user(db_session)

    with pytest.raises(IntegrityError):
        async with db_session.begin_nested():
            db_session.add(_movement(item, actor.id, recipient_id=actor.id))


async def test_valid_movements_accepted(db_session: AsyncSession) -> None:
    item = await _item(db_session)
    actor = await make_user(db_session)
    transfer_id = uuid.uuid4()

    db_session.add_all(
        [
            _movement(
                item,
                actor.id,
                movement_type=StockMovementType.RECEIPT,
                delta=3,
                quantity_after=8,
                document_date=date(2026, 9, 1),
            ),
            _movement(item, actor.id, movement_type=StockMovementType.ISSUE, recipient_id=actor.id),
            _movement(
                item,
                actor.id,
                movement_type=StockMovementType.ADJUSTMENT,
                delta=-2,
                comment="Инвентаризация",
            ),
            _movement(
                item,
                actor.id,
                movement_type=StockMovementType.TRANSFER_OUT,
                transfer_id=transfer_id,
            ),
            _movement(
                item,
                actor.id,
                movement_type=StockMovementType.TRANSFER_IN,
                delta=1,
                transfer_id=transfer_id,
            ),
        ]
    )
    await db_session.flush()
```

- [ ] **Step 2: Убедиться, что тесты падают**

Run: `cd backend && uv run pytest -q tests/modules/assets/test_stock_models.py`
Expected: FAIL — ошибка сбора: `ModuleNotFoundError: No module named 'app.modules.assets.stock_models'`

- [ ] **Step 3: Реализация**

Изменить `backend/app/model_registry.py` (применить дифф):

```diff
@@ -7,5 +7,6 @@ users.department_id → common.departments) не разрешаются при f
 
 from app.core import audit  # noqa: F401
 from app.modules.assets import models as assets_models  # noqa: F401
+from app.modules.assets import stock_models  # noqa: F401
 from app.modules.directories import models as directories_models  # noqa: F401
 from app.modules.users_auth import models as users_auth_models  # noqa: F401
```

Создать `backend/app/modules/assets/stock_models.py`:

```python
"""Расходники: позиции на складах и движения остатков (п. 2 спецификации 2b)."""

import uuid
from datetime import date, datetime
from enum import StrEnum

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class StockMovementType(StrEnum):
    RECEIPT = "receipt"
    ISSUE = "issue"
    WRITE_OFF = "write_off"
    ADJUSTMENT = "adjustment"
    TRANSFER_OUT = "transfer_out"
    TRANSFER_IN = "transfer_in"


class StockItem(Base):
    __tablename__ = "stock_items"
    __table_args__ = (
        CheckConstraint("quantity >= 0", name="quantity"),
        CheckConstraint("min_quantity >= 0", name="min_quantity"),
        CheckConstraint("is_active OR quantity = 0", name="inactive_is_empty"),
        {"schema": "equipment"},
    )
    __mapper_args__ = {"eager_defaults": True}  # noqa: RUF012

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    stock_category_id: Mapped[int] = mapped_column(
        ForeignKey("common.stock_categories.id"), index=True
    )
    unit: Mapped[str] = mapped_column(String(20))
    location_id: Mapped[int] = mapped_column(ForeignKey("common.locations.id"), index=True)
    quantity: Mapped[int] = mapped_column(Integer, default=0)
    min_quantity: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


# Уникальность наименования на складе без учёта регистра; по этой паре перемещение
# находит позицию на складе-получателе.
Index(
    "uq_stock_items_name_location",
    func.lower(StockItem.name),
    StockItem.location_id,
    unique=True,
)


class StockMovement(Base):
    __tablename__ = "stock_movements"
    __table_args__ = (
        CheckConstraint("delta <> 0", name="delta_not_zero"),
        CheckConstraint("quantity_after >= 0", name="quantity_after"),
        CheckConstraint(
            "movement_type NOT IN ('receipt', 'transfer_in') OR delta > 0", name="incoming_sign"
        ),
        CheckConstraint(
            "movement_type NOT IN ('issue', 'write_off', 'transfer_out') OR delta < 0",
            name="outgoing_sign",
        ),
        CheckConstraint(
            "(movement_type = 'receipt') = (document_date IS NOT NULL)", name="document_date"
        ),
        CheckConstraint(
            "(movement_type IN ('transfer_out', 'transfer_in')) = (transfer_id IS NOT NULL)",
            name="transfer_id",
        ),
        CheckConstraint("(movement_type = 'issue') = (recipient_id IS NOT NULL)", name="recipient"),
        CheckConstraint(
            "movement_type <> 'adjustment' OR comment IS NOT NULL", name="adjustment_comment"
        ),
        Index("ix_stock_movements_stock_item_id_id", "stock_item_id", "id"),
        {"schema": "equipment"},
    )
    __mapper_args__ = {"eager_defaults": True}  # noqa: RUF012

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    stock_item_id: Mapped[int] = mapped_column(ForeignKey("equipment.stock_items.id"))
    movement_type: Mapped[StockMovementType] = mapped_column(
        # CHECK ck_stock_movements_movement_type создаётся миграцией 0006 вручную, как в 0005.
        SAEnum(
            StockMovementType,
            native_enum=False,
            create_constraint=False,
            length=16,
            values_callable=lambda members: [member.value for member in members],
        )
    )
    delta: Mapped[int] = mapped_column(Integer)
    quantity_after: Mapped[int] = mapped_column(Integer)
    document_date: Mapped[date | None] = mapped_column(Date)
    transfer_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, index=True)
    reason_id: Mapped[int | None] = mapped_column(ForeignKey("common.issue_reasons.id"))
    recipient_id: Mapped[int | None] = mapped_column(ForeignKey("common.users.id"))
    comment: Mapped[str | None] = mapped_column(Text)
    performed_by: Mapped[int] = mapped_column(ForeignKey("common.users.id"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
```

Создать `backend/migrations/versions/0006_stock.py`:

```python
"""Расходники: позиции на складах и движения остатков

Revision ID: 0006
Revises: 0005
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_MOVEMENT_TYPES = "'receipt', 'issue', 'write_off', 'adjustment', 'transfer_out', 'transfer_in'"


def upgrade() -> None:
    op.create_table(
        "stock_items",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("stock_category_id", sa.Integer(), nullable=False),
        sa.Column("unit", sa.String(20), nullable=False),
        sa.Column("location_id", sa.Integer(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("min_quantity", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint("quantity >= 0", name="ck_stock_items_quantity"),
        sa.CheckConstraint("min_quantity >= 0", name="ck_stock_items_min_quantity"),
        sa.CheckConstraint("is_active OR quantity = 0", name="ck_stock_items_inactive_is_empty"),
        sa.ForeignKeyConstraint(
            ["stock_category_id"],
            ["common.stock_categories.id"],
            name="fk_stock_items_stock_category_id_stock_categories",
        ),
        sa.ForeignKeyConstraint(
            ["location_id"], ["common.locations.id"], name="fk_stock_items_location_id_locations"
        ),
        schema="equipment",
    )
    for column in ("stock_category_id", "location_id"):
        op.create_index(f"ix_stock_items_{column}", "stock_items", [column], schema="equipment")
    op.create_index(
        "uq_stock_items_name_location",
        "stock_items",
        [sa.text("lower(name)"), "location_id"],
        unique=True,
        schema="equipment",
    )

    op.create_table(
        "stock_movements",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("stock_item_id", sa.BigInteger(), nullable=False),
        sa.Column("movement_type", sa.String(16), nullable=False),
        sa.Column("delta", sa.Integer(), nullable=False),
        sa.Column("quantity_after", sa.Integer(), nullable=False),
        sa.Column("document_date", sa.Date(), nullable=True),
        sa.Column("transfer_id", sa.Uuid(), nullable=True),
        sa.Column("reason_id", sa.Integer(), nullable=True),
        sa.Column("recipient_id", sa.Integer(), nullable=True),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("performed_by", sa.Integer(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint(
            f"movement_type IN ({_MOVEMENT_TYPES})", name="ck_stock_movements_movement_type"
        ),
        sa.CheckConstraint("delta <> 0", name="ck_stock_movements_delta_not_zero"),
        sa.CheckConstraint("quantity_after >= 0", name="ck_stock_movements_quantity_after"),
        sa.CheckConstraint(
            "movement_type NOT IN ('receipt', 'transfer_in') OR delta > 0",
            name="ck_stock_movements_incoming_sign",
        ),
        sa.CheckConstraint(
            "movement_type NOT IN ('issue', 'write_off', 'transfer_out') OR delta < 0",
            name="ck_stock_movements_outgoing_sign",
        ),
        sa.CheckConstraint(
            "(movement_type = 'receipt') = (document_date IS NOT NULL)",
            name="ck_stock_movements_document_date",
        ),
        sa.CheckConstraint(
            "(movement_type IN ('transfer_out', 'transfer_in')) = (transfer_id IS NOT NULL)",
            name="ck_stock_movements_transfer_id",
        ),
        sa.CheckConstraint(
            "(movement_type = 'issue') = (recipient_id IS NOT NULL)",
            name="ck_stock_movements_recipient",
        ),
        sa.CheckConstraint(
            "movement_type <> 'adjustment' OR comment IS NOT NULL",
            name="ck_stock_movements_adjustment_comment",
        ),
        sa.ForeignKeyConstraint(
            ["stock_item_id"],
            ["equipment.stock_items.id"],
            name="fk_stock_movements_stock_item_id_stock_items",
        ),
        sa.ForeignKeyConstraint(
            ["reason_id"],
            ["common.issue_reasons.id"],
            name="fk_stock_movements_reason_id_issue_reasons",
        ),
        sa.ForeignKeyConstraint(
            ["recipient_id"], ["common.users.id"], name="fk_stock_movements_recipient_id_users"
        ),
        sa.ForeignKeyConstraint(
            ["performed_by"], ["common.users.id"], name="fk_stock_movements_performed_by_users"
        ),
        schema="equipment",
    )
    op.create_index(
        "ix_stock_movements_stock_item_id_id",
        "stock_movements",
        ["stock_item_id", "id"],
        schema="equipment",
    )
    op.create_index(
        "ix_stock_movements_transfer_id", "stock_movements", ["transfer_id"], schema="equipment"
    )
    op.create_index(
        "ix_stock_movements_created_at", "stock_movements", ["created_at"], schema="equipment"
    )


def downgrade() -> None:
    op.drop_table("stock_movements", schema="equipment")
    op.drop_table("stock_items", schema="equipment")
```

- [ ] **Step 4: Проверить**

Run: `cd backend && uv run pytest -q tests/modules/assets/test_stock_models.py tests/test_migrations.py`
Expected: `17 passed`

Run: `cd backend && DATABASE_URL=postgresql+asyncpg://app:app@localhost:5432/it_platform_test uv run alembic upgrade head && DATABASE_URL=postgresql+asyncpg://app:app@localhost:5432/it_platform_test uv run alembic check`
Expected: `No new upgrade operations detected.`

Run: `make format && make lint`
Expected: `Contracts: 5 kept, 0 broken.`, ошибок нет

- [ ] **Step 5: Коммит**

```bash
git add backend/app/model_registry.py backend/app/modules/assets/stock_models.py backend/migrations/versions/0006_stock.py backend/tests/modules/assets/test_stock_models.py
git commit -m "feat(backend): модели и миграция расходников (stock_items, stock_movements)"
```

---

### Task 2: Позиции расходников: создание, список, карточка, правка

`/api/stock-items` (только Admin): создание с нулевым остатком, список с фильтрами, карточка, правка по `version`. Склад правкой не меняется; деактивация — только при нулевом остатке (409 `stock_not_empty`). `directories.service` получает вид справочника `stock-categories`; `check_reason` обобщается на состав операции (техника / расходники / оба) — пригодится в Task 3 и 4.

**Files:**
- Modify: `backend/app/main.py`
- Modify: `backend/app/modules/assets/checks.py`
- Create: `backend/app/modules/assets/stock_presenter.py`
- Create: `backend/app/modules/assets/stock_registry.py`
- Create: `backend/app/modules/assets/stock_router.py`
- Create: `backend/app/modules/assets/stock_schemas.py`
- Modify: `backend/app/modules/directories/service.py`
- Test (modify): `backend/tests/modules/assets/conftest.py`
- Test (create): `backend/tests/modules/assets/test_stock_items_api.py`
- Test (modify): `backend/tests/modules/test_cross_module_services.py`
- Generated: `backend/openapi.json` (`make gen-api`)
- Generated: `frontend/src/api/schema.d.ts` (`make gen-api`)

**Interfaces:**
- Consumes: `StockItem` (Task 1).
- Produces: `directories.service.ReferenceKind` += `"stock-categories"`.
- Produces: `checks.check_stock_category(session, category_id)`; `checks.check_reason(session, reason_id, *, assets=True, stock=False)` — причина должна покрывать весь состав.
- Produces: `stock_registry` — `ENTITY_TYPE = "stock_item"`, `get_stock_item(session, item_id, *, for_update=False) -> StockItem` (404 `stock_item_not_found`), `list_stock_items`, `create_stock_item`, `update_stock_item`, `is_low(item)`, `item_snapshot(item)`.
- Produces: `stock_presenter.stock_items_to_read(session, items)`, `stock_item_to_read(session, item)`; схемы `StockItemCreate`, `StockItemUpdate`, `StockItemRead`.
- Produces (тесты): фикстура `stock_refs` и хелперы `make_stock_item`, `stock_item_payload` в `tests/modules/assets/conftest.py`.

- [ ] **Step 1: Написать падающие тесты**

Изменить `backend/tests/modules/assets/conftest.py` (применить дифф):

```diff
@@ -7,11 +7,13 @@ from httpx import AsyncClient
 from sqlalchemy.ext.asyncio import AsyncSession
 
 from app.modules.assets.models import Asset, AssetStatus
+from app.modules.assets.stock_models import StockItem
 from app.modules.directories.models import (
     AssetType,
     IssueReason,
     IssueReasonApplicability,
     Location,
+    StockCategory,
 )
 
 
@@ -89,3 +91,58 @@ async def create_via_api(
     assert response.status_code == 201, response.text
     body: dict[str, Any] = response.json()
     return body
+
+
+@dataclass(frozen=True)
+class StockRefs:
+    cartridges: StockCategory
+    paper: StockCategory
+    warehouse: Location
+    office: Location
+
+
+@pytest.fixture
+async def stock_refs(db_session: AsyncSession, refs: Refs) -> StockRefs:
+    cartridges = StockCategory(name="Картриджи")
+    paper = StockCategory(name="Бумага")
+    db_session.add_all([cartridges, paper])
+    await db_session.flush()
+    return StockRefs(cartridges, paper, refs.warehouse, refs.office)
+
+
+async def make_stock_item(
+    session: AsyncSession,
+    stock_refs: StockRefs,
+    *,
+    name: str = "Картридж HP 85A",
+    quantity: int = 0,
+    min_quantity: int = 0,
+    location: Location | None = None,
+    category: StockCategory | None = None,
+    is_active: bool = True,
+) -> StockItem:
+    item = StockItem(
+        name=name,
+        stock_category_id=(category or stock_refs.cartridges).id,
+        unit="шт",
+        location_id=(location or stock_refs.warehouse).id,
+        quantity=quantity,
+        min_quantity=min_quantity,
+        is_active=is_active,
+        version=1,
+    )
+    session.add(item)
+    await session.flush()
+    return item
+
+
+def stock_item_payload(stock_refs: StockRefs, **overrides: object) -> dict[str, object]:
+    payload: dict[str, object] = {
+        "name": "Картридж HP 85A",
+        "stock_category_id": stock_refs.cartridges.id,
+        "unit": "шт",
+        "location_id": stock_refs.warehouse.id,
+        "min_quantity": 2,
+    }
+    payload.update(overrides)
+    return payload
```

Создать `backend/tests/modules/assets/test_stock_items_api.py`:

```python
"""Позиции расходников: создание, список, карточка, правка (п. 3 и 5 спецификации 2b)."""

from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import AuditLog
from app.modules.users_auth.models import UserRole
from tests.factories import login, make_user
from tests.modules.assets.conftest import StockRefs, make_stock_item, stock_item_payload


async def _create(
    client: AsyncClient, headers: dict[str, str], stock_refs: StockRefs, **overrides: object
) -> dict[str, Any]:
    response = await client.post(
        "/api/stock-items", headers=headers, json=stock_item_payload(stock_refs, **overrides)
    )
    assert response.status_code == 201, response.text
    body: dict[str, Any] = response.json()
    return body


async def test_admin_creates_item_with_zero_quantity(
    client: AsyncClient,
    admin_headers: dict[str, str],
    stock_refs: StockRefs,
    db_session: AsyncSession,
) -> None:
    created = await _create(client, admin_headers, stock_refs, name="  Картридж HP 85A ")

    assert created["name"] == "Картридж HP 85A"
    assert created["quantity"] == 0
    assert created["min_quantity"] == 2
    assert created["category_name"] == "Картриджи"
    assert created["location_name"] == "Склад"
    assert created["unit"] == "шт"
    assert created["is_active"] is True
    assert created["is_low"] is True
    assert created["version"] == 1
    audit = await db_session.scalars(
        select(AuditLog.action).where(
            AuditLog.entity_type == "stock_item", AuditLog.entity_id == str(created["id"])
        )
    )
    assert list(audit) == ["created"]


async def test_name_unique_per_location_ignoring_case(
    client: AsyncClient, admin_headers: dict[str, str], stock_refs: StockRefs
) -> None:
    await _create(client, admin_headers, stock_refs)

    same = await client.post(
        "/api/stock-items",
        headers=admin_headers,
        json=stock_item_payload(stock_refs, name="картридж hp 85a"),
    )
    other_location = await client.post(
        "/api/stock-items",
        headers=admin_headers,
        json=stock_item_payload(stock_refs, location_id=stock_refs.office.id),
    )

    assert same.status_code == 409
    assert same.json()["error"]["code"] == "stock_item_name_taken"
    assert other_location.status_code == 201


@pytest.mark.parametrize(
    ("overrides", "code"),
    [
        ({"name": "   "}, "name_blank"),
        ({"unit": " "}, "unit_blank"),
        ({"stock_category_id": 999999}, "category_invalid"),
        ({"location_id": 999999}, "location_invalid"),
    ],
)
async def test_create_validation(
    client: AsyncClient,
    admin_headers: dict[str, str],
    stock_refs: StockRefs,
    overrides: dict[str, object],
    code: str,
) -> None:
    response = await client.post(
        "/api/stock-items", headers=admin_headers, json=stock_item_payload(stock_refs, **overrides)
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == code


async def test_inactive_category_rejected(
    client: AsyncClient,
    admin_headers: dict[str, str],
    stock_refs: StockRefs,
    db_session: AsyncSession,
) -> None:
    stock_refs.paper.is_active = False
    await db_session.flush()

    response = await client.post(
        "/api/stock-items",
        headers=admin_headers,
        json=stock_item_payload(stock_refs, stock_category_id=stock_refs.paper.id),
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "category_invalid"


async def test_list_filters(
    client: AsyncClient,
    admin_headers: dict[str, str],
    stock_refs: StockRefs,
    db_session: AsyncSession,
) -> None:
    low = await make_stock_item(
        db_session, stock_refs, name="Картридж HP 85A", quantity=1, min_quantity=2
    )
    ok = await make_stock_item(
        db_session,
        stock_refs,
        name="Бумага A4",
        quantity=50,
        min_quantity=10,
        category=stock_refs.paper,
    )
    no_min = await make_stock_item(
        db_session, stock_refs, name="Картридж HP 85A", location=stock_refs.office
    )
    inactive = await make_stock_item(db_session, stock_refs, name="Старый тонер", is_active=False)

    async def ids(**params: str | int | bool) -> list[int]:
        response = await client.get("/api/stock-items", headers=admin_headers, params=params)
        assert response.status_code == 200, response.text
        return [item["id"] for item in response.json()["items"]]

    # Наименование без учёта регистра, затем склад (офис в refs создан раньше склада).
    assert await ids() == [ok.id, no_min.id, low.id]
    assert await ids(category_id=stock_refs.paper.id) == [ok.id]
    assert await ids(location_id=stock_refs.office.id) == [no_min.id]
    assert await ids(q="hp") == [no_min.id, low.id]
    assert await ids(low_stock=True) == [low.id]
    assert inactive.id in await ids(include_inactive=True)


async def test_get_item_and_404(
    client: AsyncClient,
    admin_headers: dict[str, str],
    stock_refs: StockRefs,
    db_session: AsyncSession,
) -> None:
    item = await make_stock_item(db_session, stock_refs, quantity=3)

    found = await client.get(f"/api/stock-items/{item.id}", headers=admin_headers)
    missing = await client.get("/api/stock-items/999999", headers=admin_headers)

    assert found.status_code == 200
    assert found.json()["quantity"] == 3
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "stock_item_not_found"


async def test_update_changes_fields_and_version(
    client: AsyncClient,
    admin_headers: dict[str, str],
    stock_refs: StockRefs,
    db_session: AsyncSession,
) -> None:
    created = await _create(client, admin_headers, stock_refs)

    response = await client.patch(
        f"/api/stock-items/{created['id']}",
        headers=admin_headers,
        json={"version": 1, "name": "Картридж HP 85A (оригинал)", "min_quantity": 5},
    )
    unchanged = await client.patch(
        f"/api/stock-items/{created['id']}",
        headers=admin_headers,
        json={"version": 2, "min_quantity": 5},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["name"] == "Картридж HP 85A (оригинал)"
    assert body["min_quantity"] == 5
    assert body["version"] == 2
    assert unchanged.json()["version"] == 2
    diff = await db_session.scalar(
        select(AuditLog.diff).where(
            AuditLog.entity_type == "stock_item",
            AuditLog.entity_id == str(created["id"]),
            AuditLog.action == "edited",
        )
    )
    assert diff == {
        "name": ["Картридж HP 85A", "Картридж HP 85A (оригинал)"],
        "min_quantity": [2, 5],
    }


async def test_update_version_conflict(
    client: AsyncClient, admin_headers: dict[str, str], stock_refs: StockRefs
) -> None:
    created = await _create(client, admin_headers, stock_refs)

    response = await client.patch(
        f"/api/stock-items/{created['id']}",
        headers=admin_headers,
        json={"version": 7, "unit": "уп"},
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "version_conflict"


async def test_update_name_conflict_and_blank(
    client: AsyncClient, admin_headers: dict[str, str], stock_refs: StockRefs
) -> None:
    await _create(client, admin_headers, stock_refs, name="Бумага A4")
    created = await _create(client, admin_headers, stock_refs)

    taken = await client.patch(
        f"/api/stock-items/{created['id']}",
        headers=admin_headers,
        json={"version": 1, "name": "БУМАГА a4"},
    )
    blank = await client.patch(
        f"/api/stock-items/{created['id']}", headers=admin_headers, json={"version": 1, "name": " "}
    )

    assert taken.status_code == 409
    assert taken.json()["error"]["code"] == "stock_item_name_taken"
    assert blank.status_code == 422
    assert blank.json()["error"]["code"] == "name_blank"


async def test_deactivate_only_when_empty(
    client: AsyncClient,
    admin_headers: dict[str, str],
    stock_refs: StockRefs,
    db_session: AsyncSession,
) -> None:
    full = await make_stock_item(db_session, stock_refs, quantity=3)
    empty = await make_stock_item(db_session, stock_refs, name="Бумага A4")

    rejected = await client.patch(
        f"/api/stock-items/{full.id}",
        headers=admin_headers,
        json={"version": 1, "is_active": False},
    )
    accepted = await client.patch(
        f"/api/stock-items/{empty.id}",
        headers=admin_headers,
        json={"version": 1, "is_active": False},
    )

    assert rejected.status_code == 409
    assert rejected.json()["error"]["code"] == "stock_not_empty"
    assert rejected.json()["error"]["details"] == {"quantity": 3}
    assert accepted.status_code == 200
    assert accepted.json()["is_active"] is False


@pytest.mark.parametrize("role", [UserRole.EMPLOYEE, UserRole.MANAGER])
async def test_non_admin_forbidden(
    client: AsyncClient,
    stock_refs: StockRefs,
    db_session: AsyncSession,
    role: UserRole,
) -> None:
    user = await make_user(db_session, email=f"{role.value}@company.ru", role=role)
    item = await make_stock_item(db_session, stock_refs)
    headers = await login(client, user.email)

    responses = [
        await client.get("/api/stock-items", headers=headers),
        await client.get(f"/api/stock-items/{item.id}", headers=headers),
        await client.post("/api/stock-items", headers=headers, json=stock_item_payload(stock_refs)),
        await client.patch(
            f"/api/stock-items/{item.id}", headers=headers, json={"version": 1, "unit": "уп"}
        ),
    ]

    assert [response.status_code for response in responses] == [403, 403, 403, 403]
    assert responses[0].json()["error"]["code"] == "insufficient_role"
```

Изменить `backend/tests/modules/test_cross_module_services.py` (применить дифф):

```diff
@@ -7,6 +7,7 @@ from app.modules.directories.models import (
     IssueReason,
     IssueReasonApplicability,
     Location,
+    StockCategory,
 )
 from app.modules.directories.service import get_reference_item, get_reference_names
 from app.modules.users_auth.service import get_user_names, list_department_user_ids
@@ -62,3 +63,17 @@ async def test_get_reference_names(db_session: AsyncSession) -> None:
     assert await get_reference_names(db_session, "locations", {location.id}) == {
         location.id: "Склад"
     }
+
+
+async def test_stock_categories_reference(db_session: AsyncSession) -> None:
+    category = StockCategory(name="Картриджи", is_active=False)
+    db_session.add(category)
+    await db_session.flush()
+
+    info = await get_reference_item(db_session, "stock-categories", category.id)
+
+    assert info is not None
+    assert info.is_active is False
+    assert await get_reference_names(db_session, "stock-categories", {category.id}) == {
+        category.id: "Картриджи"
+    }
```

- [ ] **Step 2: Убедиться, что тесты падают**

Run: `cd backend && uv run pytest -q tests/modules/assets/test_stock_items_api.py tests/modules/test_cross_module_services.py`
Expected: FAIL — `16 failed, 4 passed` — эндпоинтов нет (404), `get_reference_item(..., "stock-categories", ...)` падает с `KeyError`

- [ ] **Step 3: Реализация**

Изменить `backend/app/main.py` (применить дифф):

```diff
@@ -7,6 +7,7 @@ from app.core.health import router as health_router
 from app.core.logging import configure_logging
 from app.core.middleware import RequestIdMiddleware
 from app.modules.assets.router import router as assets_router
+from app.modules.assets.stock_router import router as stock_router
 from app.modules.directories.router import routers as directories_routers
 from app.modules.users_auth.router import admin_users_router, auth_router, users_router
 from app.wiring import register_event_handlers
@@ -42,6 +43,7 @@ def create_app() -> FastAPI:
         users_router,
         *directories_routers,
         assets_router,
+        stock_router,
     ):
         app.include_router(router, prefix="/api", responses=ERROR_RESPONSES)
     return app
```

Изменить `backend/app/modules/assets/checks.py` (применить дифф):

```diff
@@ -23,11 +23,34 @@ async def check_location(session: AsyncSession, location_id: int) -> None:
         )
 
 
-async def check_reason(session: AsyncSession, reason_id: int) -> None:
+async def check_stock_category(session: AsyncSession, category_id: int) -> None:
+    item = await get_reference_item(session, "stock-categories", category_id)
+    if item is None or not item.is_active:
+        raise ValidationFailedError(
+            "Категория не найдена или деактивирована", code="category_invalid"
+        )
+
+
+def _reason_fits(applicability: str | None, *, assets: bool, stock: bool) -> bool:
+    """Причина покрывает весь состав операции: техника, расходники или и то и другое."""
+    if applicability == "both":
+        return True
+    if assets and stock:
+        return False
+    return applicability == ("assets" if assets else "stock")
+
+
+async def check_reason(
+    session: AsyncSession, reason_id: int, *, assets: bool = True, stock: bool = False
+) -> None:
     item = await get_reference_item(session, "issue-reasons", reason_id)
-    if item is None or not item.is_active or item.applicability == "stock":
+    if (
+        item is None
+        or not item.is_active
+        or not _reason_fits(item.applicability, assets=assets, stock=stock)
+    ):
         raise ValidationFailedError(
-            "Причина не найдена, деактивирована или не применяется к технике",
+            "Причина не найдена, деактивирована или не подходит к операции",
             code="reason_invalid",
         )
```

Создать `backend/app/modules/assets/stock_presenter.py`:

```python
"""Ответы API расходников: названия справочников и ФИО через service других модулей."""

from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.assets.stock_models import StockItem
from app.modules.assets.stock_registry import is_low
from app.modules.assets.stock_schemas import StockItemRead
from app.modules.directories.service import get_reference_names


async def stock_items_to_read(
    session: AsyncSession, items: Sequence[StockItem]
) -> list[StockItemRead]:
    categories = await get_reference_names(
        session, "stock-categories", {item.stock_category_id for item in items}
    )
    locations = await get_reference_names(
        session, "locations", {item.location_id for item in items}
    )
    return [
        StockItemRead(
            id=item.id,
            name=item.name,
            stock_category_id=item.stock_category_id,
            category_name=categories.get(item.stock_category_id, ""),
            unit=item.unit,
            location_id=item.location_id,
            location_name=locations.get(item.location_id, ""),
            quantity=item.quantity,
            min_quantity=item.min_quantity,
            is_low=is_low(item),
            is_active=item.is_active,
            version=item.version,
            created_at=item.created_at,
            updated_at=item.updated_at,
        )
        for item in items
    ]


async def stock_item_to_read(session: AsyncSession, item: StockItem) -> StockItemRead:
    return (await stock_items_to_read(session, [item]))[0]
```

Создать `backend/app/modules/assets/stock_registry.py`:

```python
"""Позиции расходников: список, карточка, создание и правка (остаток меняют только движения)."""

from dataclasses import dataclass
from typing import Any, NoReturn

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import diff_values, record_audit
from app.core.db import constraint_name
from app.core.errors import ConflictError, NotFoundError
from app.core.text import normalize_text_field
from app.modules.assets.checks import check_location, check_stock_category
from app.modules.assets.history import changed_fields
from app.modules.assets.stock_models import StockItem

ENTITY_TYPE = "stock_item"


@dataclass(frozen=True)
class StockItemFilters:
    category_id: int | None = None
    location_id: int | None = None
    q: str | None = None
    low_stock: bool = False
    include_inactive: bool = False


def is_low(item: StockItem) -> bool:
    return item.min_quantity > 0 and item.quantity <= item.min_quantity


def raise_stock_integrity_error(exc: IntegrityError) -> NoReturn:
    if constraint_name(exc) == "uq_stock_items_name_location":
        raise ConflictError(
            "На этом складе уже есть позиция с таким наименованием",
            code="stock_item_name_taken",
        ) from exc
    raise exc


def _normalize(values: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(values)
    if isinstance(normalized.get("name"), str):
        normalized["name"] = normalize_text_field(
            normalized["name"], code="name_blank", message="Наименование не может быть пустым"
        )
    if isinstance(normalized.get("unit"), str):
        normalized["unit"] = normalize_text_field(
            normalized["unit"], code="unit_blank", message="Единица измерения не может быть пустой"
        )
    return normalized


def item_snapshot(item: StockItem) -> dict[str, Any]:
    """Поля позиции для аудита создания."""
    return {
        "name": item.name,
        "stock_category_id": item.stock_category_id,
        "unit": item.unit,
        "location_id": item.location_id,
        "min_quantity": item.min_quantity,
    }


async def get_stock_item(
    session: AsyncSession, item_id: int, *, for_update: bool = False
) -> StockItem:
    stmt = select(StockItem).where(StockItem.id == item_id)
    if for_update:
        stmt = stmt.with_for_update()
    item = await session.scalar(stmt)
    if item is None:
        raise NotFoundError("Позиция не найдена", code="stock_item_not_found")
    return item


async def list_stock_items(
    session: AsyncSession, filters: StockItemFilters, *, limit: int, offset: int
) -> tuple[list[StockItem], int]:
    stmt = select(StockItem)
    if not filters.include_inactive:
        stmt = stmt.where(StockItem.is_active.is_(True))
    if filters.category_id is not None:
        stmt = stmt.where(StockItem.stock_category_id == filters.category_id)
    if filters.location_id is not None:
        stmt = stmt.where(StockItem.location_id == filters.location_id)
    if filters.low_stock:
        stmt = stmt.where(StockItem.min_quantity > 0, StockItem.quantity <= StockItem.min_quantity)
    if filters.q and filters.q.strip():
        stmt = stmt.where(StockItem.name.ilike(f"%{filters.q.strip()}%"))
    total = await session.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = await session.scalars(
        stmt.order_by(func.lower(StockItem.name), StockItem.location_id, StockItem.id)
        .limit(limit)
        .offset(offset)
    )
    return list(rows), total


async def create_stock_item(
    session: AsyncSession, *, actor_id: int, data: dict[str, Any]
) -> StockItem:
    data = _normalize(data)
    await check_stock_category(session, data["stock_category_id"])
    await check_location(session, data["location_id"])
    item = StockItem(**data, quantity=0, is_active=True, version=1)
    try:
        async with session.begin_nested():
            session.add(item)
    except IntegrityError as exc:
        raise_stock_integrity_error(exc)
    record_audit(
        session,
        entity_type=ENTITY_TYPE,
        entity_id=item.id,
        user_id=actor_id,
        action="created",
        diff=diff_values({}, item_snapshot(item)),
    )
    await session.commit()
    return item


async def update_stock_item(
    session: AsyncSession,
    *,
    actor_id: int,
    item_id: int,
    version: int,
    updates: dict[str, Any],
) -> StockItem:
    item = await get_stock_item(session, item_id, for_update=True)
    if item.version != version:
        raise ConflictError(
            "Данные изменил другой пользователь",
            code="version_conflict",
            details={"version": item.version},
        )
    updates = _normalize(updates)
    changes = changed_fields({key: getattr(item, key) for key in updates}, updates)
    if not changes:
        return item
    if "stock_category_id" in changes:
        await check_stock_category(session, updates["stock_category_id"])
    if changes.get("is_active") == [True, False] and item.quantity > 0:
        raise ConflictError(
            "Деактивировать можно только позицию с нулевым остатком",
            code="stock_not_empty",
            details={"quantity": item.quantity},
        )
    try:
        async with session.begin_nested():
            for key in changes:
                setattr(item, key, updates[key])
            item.version += 1
    except IntegrityError as exc:
        raise_stock_integrity_error(exc)
    record_audit(
        session,
        entity_type=ENTITY_TYPE,
        entity_id=item.id,
        user_id=actor_id,
        action="edited",
        diff=changes,
    )
    await session.commit()
    return item
```

Создать `backend/app/modules/assets/stock_router.py`:

```python
"""API расходников — только Admin (раздел скрыт от Employee и Manager)."""

from typing import Annotated

from fastapi import APIRouter, Query

from app.core.db import SessionDep
from app.core.schemas import Page, PaginationDep
from app.modules.assets import stock_registry
from app.modules.assets.stock_presenter import stock_item_to_read, stock_items_to_read
from app.modules.assets.stock_schemas import StockItemCreate, StockItemRead, StockItemUpdate
from app.modules.users_auth.service import AdminDep

router = APIRouter(prefix="/stock-items", tags=["stock"])


@router.get("", response_model=Page[StockItemRead])
async def list_stock_items(
    session: SessionDep,
    admin: AdminDep,
    pagination: PaginationDep,
    category_id: int | None = None,
    location_id: int | None = None,
    q: Annotated[str | None, Query(max_length=100)] = None,
    low_stock: bool = False,
    include_inactive: bool = False,
) -> Page[StockItemRead]:
    filters = stock_registry.StockItemFilters(
        category_id=category_id,
        location_id=location_id,
        q=q,
        low_stock=low_stock,
        include_inactive=include_inactive,
    )
    items, total = await stock_registry.list_stock_items(
        session, filters, limit=pagination.limit, offset=pagination.offset
    )
    return Page(
        items=await stock_items_to_read(session, items),
        total=total,
        limit=pagination.limit,
        offset=pagination.offset,
    )


@router.post("", response_model=StockItemRead, status_code=201)
async def create_stock_item(
    body: StockItemCreate, session: SessionDep, admin: AdminDep
) -> StockItemRead:
    item = await stock_registry.create_stock_item(
        session, actor_id=admin.id, data=body.model_dump()
    )
    return await stock_item_to_read(session, item)


@router.get("/{item_id}", response_model=StockItemRead)
async def get_stock_item(item_id: int, session: SessionDep, admin: AdminDep) -> StockItemRead:
    item = await stock_registry.get_stock_item(session, item_id)
    return await stock_item_to_read(session, item)


@router.patch("/{item_id}", response_model=StockItemRead)
async def update_stock_item(
    item_id: int, body: StockItemUpdate, session: SessionDep, admin: AdminDep
) -> StockItemRead:
    item = await stock_registry.update_stock_item(
        session,
        actor_id=admin.id,
        item_id=item_id,
        version=body.version,
        updates=body.model_dump(exclude_unset=True, exclude={"version"}),
    )
    return await stock_item_to_read(session, item)
```

Создать `backend/app/modules/assets/stock_schemas.py`:

```python
from datetime import datetime
from typing import Annotated, ClassVar

from pydantic import BaseModel, Field

from app.core.schemas import PartialUpdate

StockName = Annotated[str, Field(min_length=1, max_length=200)]
Unit = Annotated[str, Field(min_length=1, max_length=20)]
MinQuantity = Annotated[int, Field(ge=0, le=1_000_000)]


class StockItemCreate(BaseModel):
    name: StockName
    stock_category_id: int
    unit: Unit
    location_id: int
    min_quantity: MinQuantity = 0


class StockItemUpdate(PartialUpdate):
    """Склад не меняется правкой — только перемещением количества."""

    non_nullable: ClassVar[frozenset[str]] = frozenset(
        {"name", "stock_category_id", "unit", "min_quantity", "is_active"}
    )

    version: int
    name: StockName | None = None
    stock_category_id: int | None = None
    unit: Unit | None = None
    min_quantity: MinQuantity | None = None
    is_active: bool | None = None


class StockItemRead(BaseModel):
    id: int
    name: str
    stock_category_id: int
    category_name: str
    unit: str
    location_id: int
    location_name: str
    quantity: int
    min_quantity: int
    is_low: bool
    is_active: bool
    version: int
    created_at: datetime
    updated_at: datetime
```

Изменить `backend/app/modules/directories/service.py` (применить дифф):

```diff
@@ -9,15 +9,22 @@ from typing import Literal
 from sqlalchemy import select
 from sqlalchemy.ext.asyncio import AsyncSession
 
-from app.modules.directories.models import AssetType, Department, IssueReason, Location
+from app.modules.directories.models import (
+    AssetType,
+    Department,
+    IssueReason,
+    Location,
+    StockCategory,
+)
 
-ReferenceKind = Literal["locations", "asset-types", "issue-reasons"]
+ReferenceKind = Literal["locations", "asset-types", "stock-categories", "issue-reasons"]
 
-_ReferenceModel = Location | AssetType | IssueReason
+_ReferenceModel = Location | AssetType | StockCategory | IssueReason
 
 _REFERENCE_MODELS: dict[ReferenceKind, type[_ReferenceModel]] = {
     "locations": Location,
     "asset-types": AssetType,
+    "stock-categories": StockCategory,
     "issue-reasons": IssueReason,
 }
```

- [ ] **Step 4: Проверить**

Run: `cd backend && uv run pytest -q tests/modules/assets/test_stock_items_api.py tests/modules/test_cross_module_services.py`
Expected: `20 passed`

Run: `make format && make lint`
Expected: без ошибок

Run: `make gen-api && make test`
Expected: `263 passed` (обновлены `backend/openapi.json` и `frontend/src/api/schema.d.ts`)

- [ ] **Step 5: Коммит**

```bash
git add backend/app/main.py backend/app/modules/assets/checks.py backend/app/modules/assets/stock_presenter.py backend/app/modules/assets/stock_registry.py backend/app/modules/assets/stock_router.py backend/app/modules/assets/stock_schemas.py backend/app/modules/directories/service.py backend/openapi.json backend/tests/modules/assets/conftest.py backend/tests/modules/assets/test_stock_items_api.py backend/tests/modules/test_cross_module_services.py frontend/src/api/schema.d.ts
git commit -m "feat(backend): позиции расходников — создание, список, карточка, правка"
```

---

### Task 3: Операции с расходниками: приход, списание, корректировка, перемещение; гонки

`POST /api/stock-items/{id}/operations` (размеченное объединение по `operation`) и `GET /api/stock-items/{id}/movements`. Остаток меняет только `record_movement` — вместе с движением и аудитом. Блокирующие запросы используют `populate_existing=True`: перемещение сначала читает позицию без блокировки, и без этой опции `SELECT … FOR UPDATE` вернул бы объект из identity map с устаревшим остатком (тест параллельных перемещений ловит потерянное обновление: 8 вместо 6). Часовой пояс компании — новый `app/core/timezone.py` (дата документа по умолчанию, в Task 5 — границы периода журнала).

**Files:**
- Create: `backend/app/core/timezone.py`
- Create: `backend/app/modules/assets/stock_operations.py`
- Modify: `backend/app/modules/assets/stock_presenter.py`
- Modify: `backend/app/modules/assets/stock_registry.py`
- Modify: `backend/app/modules/assets/stock_router.py`
- Modify: `backend/app/modules/assets/stock_schemas.py`
- Test (create): `backend/tests/core/test_timezone.py`
- Test (create): `backend/tests/modules/assets/test_stock_concurrency.py`
- Test (create): `backend/tests/modules/assets/test_stock_operations_api.py`
- Generated: `backend/openapi.json` (`make gen-api`)
- Generated: `frontend/src/api/schema.d.ts` (`make gen-api`)

**Interfaces:**
- Consumes: `get_stock_item`, `item_snapshot`, `ENTITY_TYPE` (Task 2); `check_reason(..., assets=False, stock=True)`, `check_location`.
- Produces: `app.core.timezone` — `company_tz()`, `company_today() -> date`, `company_day_bounds(date_from, date_to) -> (start_utc | None, end_utc | None)` (полуинтервал).
- Produces: `stock_operations` — `require_active(item)` (409 `stock_item_inactive`), `require_available(item, quantity)` (409 `insufficient_stock`, `details: {stock_item_id, requested, available}`), `record_movement(session, item, *, movement_type, delta, actor_id, document_date=None, transfer_id=None, reason_id=None, recipient_id=None, comment=None)`, `lock_stock_items(session, ids) -> dict[int, StockItem]`, `apply_stock_operation(session, actor, item_id, request)`.
- Produces: схемы `Quantity`, `StockReceiptOperation`, `StockWriteOffOperation`, `StockAdjustmentOperation`, `StockTransferOperation`, `StockOperationRequest`, `StockMovementRead` (с `counterpart_location_id/name` — склад второй половины перемещения).
- Produces: `stock_registry.list_movements`, `stock_registry.transfer_locations`; `stock_presenter.movements_to_read`.

- [ ] **Step 1: Написать падающие тесты**

Создать `backend/tests/core/test_timezone.py`:

```python
from datetime import UTC, date, datetime

from app.core.timezone import company_day_bounds


def test_company_day_bounds_in_utc() -> None:
    # Europe/Moscow = UTC+3: сутки 22.09 по Москве — с 21.09 21:00 до 22.09 21:00 UTC.
    start, end = company_day_bounds(date(2026, 9, 22), date(2026, 9, 22))

    assert start == datetime(2026, 9, 21, 21, 0, tzinfo=UTC)
    assert end == datetime(2026, 9, 22, 21, 0, tzinfo=UTC)


def test_company_day_bounds_open_ends() -> None:
    assert company_day_bounds(None, None) == (None, None)
```

Создать `backend/tests/modules/assets/test_stock_concurrency.py`:

```python
"""Параллельные операции с остатками: реальные транзакции в разных соединениях (п. 3.2 ТЗ)."""

import asyncio
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass

import pytest
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.audit import AuditLog
from app.core.config import get_settings
from app.core.errors import AppError
from app.modules.assets import stock_operations
from app.modules.assets.stock_models import StockItem, StockMovement
from app.modules.assets.stock_schemas import (
    StockOperationRequest,
    StockTransferOperation,
    StockWriteOffOperation,
)
from app.modules.directories.models import (
    IssueReason,
    IssueReasonApplicability,
    Location,
    StockCategory,
)
from app.modules.users_auth.models import User, UserRole
from app.modules.users_auth.service import CurrentUser
from tests.factories import make_user


@dataclass(frozen=True)
class RaceSetup:
    engine: AsyncEngine
    actor: CurrentUser
    category_id: int
    first_location_id: int
    second_location_id: int
    reason_id: int

    async def make_item(self, name: str, location_id: int, quantity: int) -> int:
        async with AsyncSession(self.engine, expire_on_commit=False) as session:
            item = StockItem(
                name=name,
                stock_category_id=self.category_id,
                unit="шт",
                location_id=location_id,
                quantity=quantity,
                min_quantity=0,
                is_active=True,
                version=1,
            )
            session.add(item)
            await session.commit()
            return item.id

    async def run(self, item_id: int, request: StockOperationRequest) -> str:
        async with AsyncSession(self.engine, expire_on_commit=False) as session:
            try:
                await stock_operations.apply_stock_operation(session, self.actor, item_id, request)
            except AppError as exc:
                return exc.code
            return "ok"


@pytest.fixture
async def race() -> AsyncIterator[RaceSetup]:
    engine = create_async_engine(get_settings().database_url, poolclass=NullPool)
    async with AsyncSession(engine, expire_on_commit=False) as setup:
        admin = await make_user(setup, email="stock-race@company.ru", role=UserRole.ADMIN)
        category = StockCategory(name="Гонка: картриджи")
        first = Location(name="Гонка: склад 1")
        second = Location(name="Гонка: склад 2")
        reason = IssueReason(name="Гонка: брак", applicability=IssueReasonApplicability.STOCK)
        setup.add_all([category, first, second, reason])
        await setup.commit()
    actor = CurrentUser(
        id=admin.id,
        email=admin.email,
        full_name=admin.full_name,
        role=UserRole.ADMIN,
        department_id=None,
        must_change_password=False,
    )
    try:
        yield RaceSetup(engine, actor, category.id, first.id, second.id, reason.id)
    finally:
        async with AsyncSession(engine) as cleanup:
            item_ids = select(StockItem.id).where(StockItem.stock_category_id == category.id)
            await cleanup.execute(
                delete(StockMovement).where(StockMovement.stock_item_id.in_(item_ids))
            )
            await cleanup.execute(
                delete(StockItem).where(StockItem.stock_category_id == category.id)
            )
            await cleanup.execute(delete(AuditLog).where(AuditLog.user_id == admin.id))
            await cleanup.execute(delete(StockCategory).where(StockCategory.id == category.id))
            await cleanup.execute(delete(Location).where(Location.id.in_([first.id, second.id])))
            await cleanup.execute(delete(IssueReason).where(IssueReason.id == reason.id))
            await cleanup.execute(delete(User).where(User.id == admin.id))
            await cleanup.commit()
        await engine.dispose()


async def _quantity(engine: AsyncEngine, item_id: int) -> int:
    async with AsyncSession(engine) as session:
        item = await session.get(StockItem, item_id)
        assert item is not None
        return item.quantity


async def _gather(*calls: Callable[[], Awaitable[str]]) -> list[str]:
    return list(await asyncio.gather(*(call() for call in calls)))


async def test_parallel_write_off_of_last_units_one_wins(race: RaceSetup) -> None:
    item_id = await race.make_item("Картридж", race.first_location_id, 3)
    request = StockWriteOffOperation(operation="write_off", quantity=2, reason_id=race.reason_id)

    results = await _gather(lambda: race.run(item_id, request), lambda: race.run(item_id, request))

    assert sorted(results) == ["insufficient_stock", "ok"]
    assert await _quantity(race.engine, item_id) == 1


async def test_opposite_transfers_do_not_deadlock(race: RaceSetup) -> None:
    first = await race.make_item("Бумага A4", race.first_location_id, 10)
    second = await race.make_item("Бумага A4", race.second_location_id, 10)

    results = await asyncio.wait_for(
        _gather(
            lambda: race.run(
                first,
                StockTransferOperation(
                    operation="transfer", quantity=3, to_location_id=race.second_location_id
                ),
            ),
            lambda: race.run(
                second,
                StockTransferOperation(
                    operation="transfer", quantity=4, to_location_id=race.first_location_id
                ),
            ),
        ),
        timeout=10,
    )

    assert results == ["ok", "ok"]
    assert await _quantity(race.engine, first) == 10 - 3 + 4
    assert await _quantity(race.engine, second) == 10 + 3 - 4


async def test_parallel_transfers_create_one_target_item(race: RaceSetup) -> None:
    source = await race.make_item("Мышь USB", race.first_location_id, 10)
    request = StockTransferOperation(
        operation="transfer", quantity=2, to_location_id=race.second_location_id
    )

    results = await _gather(lambda: race.run(source, request), lambda: race.run(source, request))

    assert results == ["ok", "ok"]
    async with AsyncSession(race.engine) as session:
        targets = list(
            await session.scalars(
                select(StockItem).where(
                    StockItem.location_id == race.second_location_id,
                    func.lower(StockItem.name) == "мышь usb",
                )
            )
        )
    assert [target.quantity for target in targets] == [4]
    assert await _quantity(race.engine, source) == 6
```

Создать `backend/tests/modules/assets/test_stock_operations_api.py`:

```python
"""Операции с расходниками: приход, списание, корректировка, перемещение (п. 3 спецификации 2b)."""

from datetime import timedelta
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import AuditLog
from app.core.timezone import company_today
from app.modules.assets.stock_models import StockItem, StockMovement
from app.modules.users_auth.models import User, UserRole
from tests.factories import login, make_user
from tests.modules.assets.conftest import Refs, StockRefs, make_stock_item


async def _operate(
    client: AsyncClient, headers: dict[str, str], item_id: int, **body: Any
) -> tuple[int, dict[str, Any]]:
    response = await client.post(
        f"/api/stock-items/{item_id}/operations", headers=headers, json=body
    )
    payload: dict[str, Any] = response.json()
    return response.status_code, payload


async def _movements(
    client: AsyncClient, headers: dict[str, str], item_id: int
) -> list[dict[str, Any]]:
    response = await client.get(f"/api/stock-items/{item_id}/movements", headers=headers)
    assert response.status_code == 200, response.text
    items: list[dict[str, Any]] = response.json()["items"]
    return items


async def test_receipt_adds_quantity_with_document_date(
    client: AsyncClient,
    admin_headers: dict[str, str],
    admin_user: User,
    stock_refs: StockRefs,
    db_session: AsyncSession,
) -> None:
    item = await make_stock_item(db_session, stock_refs, quantity=2)

    status, body = await _operate(
        client,
        admin_headers,
        item.id,
        operation="receipt",
        quantity=10,
        document_date="2026-09-01",
        comment="Накладная 15",
    )
    _, default_date = await _operate(
        client, admin_headers, item.id, operation="receipt", quantity=1
    )

    assert status == 200, body
    assert body["quantity"] == 10 + 2
    assert body["version"] == 2
    assert default_date["quantity"] == 13
    newest, first = await _movements(client, admin_headers, item.id)
    assert first["movement_type"] == "receipt"
    assert first["delta"] == 10
    assert first["quantity_after"] == 12
    assert first["document_date"] == "2026-09-01"
    assert first["comment"] == "Накладная 15"
    assert first["performed_by_name"] == admin_user.full_name
    assert newest["document_date"] == company_today().isoformat()
    audit = await db_session.scalars(
        select(AuditLog.diff)
        .where(
            AuditLog.entity_type == "stock_item",
            AuditLog.entity_id == str(item.id),
            AuditLog.action == "receipt",
        )
        .order_by(AuditLog.id)
    )
    assert list(audit) == [{"quantity": [2, 12]}, {"quantity": [12, 13]}]


async def test_receipt_rejects_future_date_and_inactive_item(
    client: AsyncClient,
    admin_headers: dict[str, str],
    stock_refs: StockRefs,
    db_session: AsyncSession,
) -> None:
    item = await make_stock_item(db_session, stock_refs)
    inactive = await make_stock_item(db_session, stock_refs, name="Старый тонер", is_active=False)
    tomorrow = (company_today() + timedelta(days=1)).isoformat()

    future_status, future = await _operate(
        client, admin_headers, item.id, operation="receipt", quantity=1, document_date=tomorrow
    )
    inactive_status, inactive_body = await _operate(
        client, admin_headers, inactive.id, operation="receipt", quantity=1
    )

    assert future_status == 422
    assert future["error"]["code"] == "document_date_in_future"
    assert inactive_status == 409
    assert inactive_body["error"]["code"] == "stock_item_inactive"


async def test_write_off_requires_stock_reason_and_quantity(
    client: AsyncClient,
    admin_headers: dict[str, str],
    stock_refs: StockRefs,
    refs: Refs,
    db_session: AsyncSession,
) -> None:
    item = await make_stock_item(db_session, stock_refs, quantity=3)

    no_reason = await _operate(client, admin_headers, item.id, operation="write_off", quantity=1)
    asset_reason = await _operate(
        client, admin_headers, item.id, operation="write_off", quantity=1, reason_id=refs.broken.id
    )
    too_many = await _operate(
        client,
        admin_headers,
        item.id,
        operation="write_off",
        quantity=4,
        reason_id=refs.stock_only.id,
    )
    ok = await _operate(
        client,
        admin_headers,
        item.id,
        operation="write_off",
        quantity=3,
        reason_id=refs.stock_only.id,
    )

    assert no_reason[0] == 422
    assert no_reason[1]["error"]["code"] == "reason_required"
    assert asset_reason[0] == 422
    assert asset_reason[1]["error"]["code"] == "reason_invalid"
    assert too_many[0] == 409
    assert too_many[1]["error"]["code"] == "insufficient_stock"
    assert too_many[1]["error"]["details"] == {
        "stock_item_id": item.id,
        "requested": 4,
        "available": 3,
    }
    assert ok[0] == 200
    assert ok[1]["quantity"] == 0
    [movement] = await _movements(client, admin_headers, item.id)
    assert movement["delta"] == -3
    assert movement["reason_name"] == "Заправка"


async def test_adjustment_sets_actual_quantity(
    client: AsyncClient,
    admin_headers: dict[str, str],
    stock_refs: StockRefs,
    db_session: AsyncSession,
) -> None:
    item = await make_stock_item(db_session, stock_refs, quantity=7)

    down = await _operate(
        client,
        admin_headers,
        item.id,
        operation="adjustment",
        actual_quantity=5,
        comment="Инвентаризация",
    )
    same = await _operate(
        client, admin_headers, item.id, operation="adjustment", actual_quantity=5, comment="Снова"
    )
    no_comment = await _operate(
        client, admin_headers, item.id, operation="adjustment", actual_quantity=6, comment="  "
    )

    assert down[0] == 200
    assert down[1]["quantity"] == 5
    assert same[0] == 422
    assert same[1]["error"]["code"] == "adjustment_no_change"
    assert no_comment[0] == 422
    assert no_comment[1]["error"]["code"] == "comment_required"
    [movement] = await _movements(client, admin_headers, item.id)
    assert movement["movement_type"] == "adjustment"
    assert movement["delta"] == -2
    assert movement["quantity_after"] == 5


async def test_transfer_creates_target_item(
    client: AsyncClient,
    admin_headers: dict[str, str],
    stock_refs: StockRefs,
    db_session: AsyncSession,
) -> None:
    item = await make_stock_item(db_session, stock_refs, quantity=5, min_quantity=3)

    status, body = await _operate(
        client,
        admin_headers,
        item.id,
        operation="transfer",
        quantity=2,
        to_location_id=stock_refs.office.id,
    )

    assert status == 200, body
    assert body["quantity"] == 3
    target = await db_session.scalar(
        select(StockItem).where(
            StockItem.location_id == stock_refs.office.id, StockItem.name == item.name
        )
    )
    assert target is not None
    await db_session.refresh(target)
    assert target.quantity == 2
    assert target.min_quantity == 0
    assert target.stock_category_id == item.stock_category_id
    assert target.unit == item.unit
    [out] = await _movements(client, admin_headers, item.id)
    [incoming] = await _movements(client, admin_headers, target.id)
    assert out["movement_type"] == "transfer_out"
    assert out["counterpart_location_name"] == "Офис, каб. 101"
    assert incoming["movement_type"] == "transfer_in"
    assert incoming["counterpart_location_name"] == "Склад"
    assert out["transfer_id"] == incoming["transfer_id"]


async def test_transfer_to_existing_inactive_item_reactivates_it(
    client: AsyncClient,
    admin_headers: dict[str, str],
    stock_refs: StockRefs,
    db_session: AsyncSession,
) -> None:
    item = await make_stock_item(db_session, stock_refs, quantity=5)
    target = await make_stock_item(
        db_session,
        stock_refs,
        name="КАРТРИДЖ HP 85A",
        location=stock_refs.office,
        is_active=False,
    )

    status, _ = await _operate(
        client,
        admin_headers,
        item.id,
        operation="transfer",
        quantity=5,
        to_location_id=stock_refs.office.id,
    )

    assert status == 200
    await db_session.refresh(target)
    assert target.is_active is True
    assert target.quantity == 5
    movement_types = await db_session.scalars(
        select(StockMovement.movement_type).where(StockMovement.stock_item_id == target.id)
    )
    assert list(movement_types) == ["transfer_in"]


@pytest.mark.parametrize(
    ("body", "status", "code"),
    [
        ({"quantity": 1, "to_location_id": None}, 422, "same_location"),
        ({"quantity": 1, "to_location_id": 999999}, 422, "location_invalid"),
        ({"quantity": 9, "to_location_id": "office"}, 409, "insufficient_stock"),
    ],
)
async def test_transfer_validation(
    client: AsyncClient,
    admin_headers: dict[str, str],
    stock_refs: StockRefs,
    db_session: AsyncSession,
    body: dict[str, Any],
    status: int,
    code: str,
) -> None:
    item = await make_stock_item(db_session, stock_refs, quantity=5)
    targets = {None: stock_refs.warehouse.id, "office": stock_refs.office.id}
    to_location = body["to_location_id"]
    body = {**body, "to_location_id": targets.get(to_location, to_location)}

    actual_status, payload = await _operate(
        client, admin_headers, item.id, operation="transfer", **body
    )

    assert actual_status == status
    assert payload["error"]["code"] == code


async def test_operations_forbidden_for_non_admin(
    client: AsyncClient, stock_refs: StockRefs, db_session: AsyncSession
) -> None:
    manager = await make_user(db_session, email="manager@company.ru", role=UserRole.MANAGER)
    item = await make_stock_item(db_session, stock_refs, quantity=5)
    headers = await login(client, manager.email)

    status, _ = await _operate(client, headers, item.id, operation="receipt", quantity=1)
    history = await client.get(f"/api/stock-items/{item.id}/movements", headers=headers)

    assert status == 403
    assert history.status_code == 403
```

- [ ] **Step 2: Убедиться, что тесты падают**

Run: `cd backend && uv run pytest -q tests/core/test_timezone.py tests/modules/assets/test_stock_operations_api.py tests/modules/assets/test_stock_concurrency.py`
Expected: FAIL — ошибки сбора: `ModuleNotFoundError: No module named 'app.core.timezone'` / `cannot import name 'stock_operations'`

- [ ] **Step 3: Реализация**

Создать `backend/app/core/timezone.py`:

```python
"""Даты в часовом поясе компании (п. 7.6 ТЗ): хранение в UTC, календарные дни — по компании."""

from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from app.core.config import get_settings


def company_tz() -> ZoneInfo:
    return ZoneInfo(get_settings().company_timezone)


def company_today() -> date:
    return datetime.now(company_tz()).date()


def _day_start_utc(day: date) -> datetime:
    return datetime.combine(day, time.min, tzinfo=company_tz()).astimezone(UTC)


def company_day_bounds(
    date_from: date | None, date_to: date | None
) -> tuple[datetime | None, datetime | None]:
    """Период «с — по» включительно в днях компании → полуинтервал [start, end) в UTC."""
    start = _day_start_utc(date_from) if date_from is not None else None
    end = _day_start_utc(date_to + timedelta(days=1)) if date_to is not None else None
    return start, end
```

Создать `backend/app/modules/assets/stock_operations.py`:

```python
"""Операции с остатками расходников: приход, списание, корректировка, перемещение.

Остаток меняется только здесь и только вместе с записью StockMovement (п. 3.2 ТЗ).
Строки позиций блокируются SELECT … FOR UPDATE (несколько — в порядке id, чтобы встречные
операции не заблокировали друг друга); остаток проверяется уже под блокировкой.
"""

import uuid
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import diff_values, record_audit
from app.core.errors import ConflictError, ValidationFailedError
from app.core.timezone import company_today
from app.modules.assets.checks import check_location, check_reason
from app.modules.assets.stock_models import StockItem, StockMovement, StockMovementType
from app.modules.assets.stock_registry import ENTITY_TYPE, get_stock_item, item_snapshot
from app.modules.assets.stock_schemas import (
    StockAdjustmentOperation,
    StockOperationRequest,
    StockReceiptOperation,
    StockTransferOperation,
    StockWriteOffOperation,
)
from app.modules.users_auth.service import CurrentUser


def require_active(item: StockItem) -> None:
    if not item.is_active:
        raise ConflictError(
            "Позиция деактивирована", code="stock_item_inactive", details={"stock_item_id": item.id}
        )


def require_available(item: StockItem, quantity: int) -> None:
    if item.quantity < quantity:
        raise ConflictError(
            "Недостаточно остатка",
            code="insufficient_stock",
            details={"stock_item_id": item.id, "requested": quantity, "available": item.quantity},
        )


def record_movement(
    session: AsyncSession,
    item: StockItem,
    *,
    movement_type: StockMovementType,
    delta: int,
    actor_id: int,
    document_date: date | None = None,
    transfer_id: uuid.UUID | None = None,
    reason_id: int | None = None,
    recipient_id: int | None = None,
    comment: str | None = None,
) -> None:
    """Меняет остаток заблокированной позиции и пишет движение и аудит в той же транзакции."""
    before = item.quantity
    item.quantity += delta
    item.version += 1
    session.add(
        StockMovement(
            stock_item_id=item.id,
            movement_type=movement_type,
            delta=delta,
            quantity_after=item.quantity,
            document_date=document_date,
            transfer_id=transfer_id,
            reason_id=reason_id,
            recipient_id=recipient_id,
            comment=comment,
            performed_by=actor_id,
        )
    )
    record_audit(
        session,
        entity_type=ENTITY_TYPE,
        entity_id=item.id,
        user_id=actor_id,
        action=movement_type.value,
        diff={"quantity": [before, item.quantity]},
    )


async def lock_stock_items(session: AsyncSession, item_ids: list[int]) -> dict[int, StockItem]:
    """Блокирует позиции в порядке id; отсутствующих в ответе нет.

    populate_existing: позиция могла быть прочитана в этой сессии до блокировки —
    без него ORM вернёт объект из identity map с устаревшим остатком.
    """
    rows = await session.scalars(
        select(StockItem)
        .where(StockItem.id.in_(sorted(set(item_ids))))
        .order_by(StockItem.id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    return {item.id: item for item in rows}


async def _receipt(
    session: AsyncSession, actor_id: int, item_id: int, request: StockReceiptOperation
) -> StockItem:
    today = company_today()
    document_date = request.document_date or today
    if document_date > today:
        raise ValidationFailedError(
            "Дата документа не может быть в будущем", code="document_date_in_future"
        )
    item = await get_stock_item(session, item_id, for_update=True)
    require_active(item)
    record_movement(
        session,
        item,
        movement_type=StockMovementType.RECEIPT,
        delta=request.quantity,
        actor_id=actor_id,
        document_date=document_date,
        comment=request.comment,
    )
    return item


async def _write_off(
    session: AsyncSession, actor_id: int, item_id: int, request: StockWriteOffOperation
) -> StockItem:
    if request.reason_id is None:
        raise ValidationFailedError("Укажите причину списания", code="reason_required")
    await check_reason(session, request.reason_id, assets=False, stock=True)
    item = await get_stock_item(session, item_id, for_update=True)
    require_active(item)
    require_available(item, request.quantity)
    record_movement(
        session,
        item,
        movement_type=StockMovementType.WRITE_OFF,
        delta=-request.quantity,
        actor_id=actor_id,
        reason_id=request.reason_id,
        comment=request.comment,
    )
    return item


async def _adjustment(
    session: AsyncSession, actor_id: int, item_id: int, request: StockAdjustmentOperation
) -> StockItem:
    if request.comment is None:
        raise ValidationFailedError("Укажите комментарий к корректировке", code="comment_required")
    item = await get_stock_item(session, item_id, for_update=True)
    require_active(item)
    delta = request.actual_quantity - item.quantity
    if delta == 0:
        raise ValidationFailedError(
            "Фактический остаток совпадает с учётным", code="adjustment_no_change"
        )
    record_movement(
        session,
        item,
        movement_type=StockMovementType.ADJUSTMENT,
        delta=delta,
        actor_id=actor_id,
        comment=request.comment,
    )
    return item


async def _find_or_create_target(
    session: AsyncSession, actor_id: int, source: StockItem, location_id: int
) -> int:
    """id позиции с тем же наименованием на складе-получателе; нет — создаётся (min = 0)."""
    stmt = select(StockItem.id).where(
        func.lower(StockItem.name) == source.name.lower(), StockItem.location_id == location_id
    )
    existing = await session.scalar(stmt)
    if existing is not None:
        return existing
    target = StockItem(
        name=source.name,
        stock_category_id=source.stock_category_id,
        unit=source.unit,
        location_id=location_id,
        quantity=0,
        min_quantity=0,
        is_active=True,
        version=1,
    )
    try:
        async with session.begin_nested():
            session.add(target)
    except IntegrityError:
        # Параллельное перемещение уже создало позицию — берём её.
        created = await session.scalar(stmt)
        if created is None:
            raise
        return created
    record_audit(
        session,
        entity_type=ENTITY_TYPE,
        entity_id=target.id,
        user_id=actor_id,
        action="created",
        diff=diff_values({}, item_snapshot(target)),
    )
    return target.id


async def _transfer(
    session: AsyncSession, actor_id: int, item_id: int, request: StockTransferOperation
) -> StockItem:
    source = await get_stock_item(session, item_id)
    if request.to_location_id == source.location_id:
        raise ValidationFailedError(
            "Склад-получатель совпадает с текущим складом позиции", code="same_location"
        )
    await check_location(session, request.to_location_id)
    target_id = await _find_or_create_target(session, actor_id, source, request.to_location_id)
    locked = await lock_stock_items(session, [source.id, target_id])
    source, target = locked[source.id], locked[target_id]
    require_active(source)
    require_available(source, request.quantity)
    if not target.is_active:
        target.is_active = True
        target.version += 1
        record_audit(
            session,
            entity_type=ENTITY_TYPE,
            entity_id=target.id,
            user_id=actor_id,
            action="edited",
            diff={"is_active": [False, True]},
        )
    transfer_id = uuid.uuid4()
    for item, movement_type, delta in (
        (source, StockMovementType.TRANSFER_OUT, -request.quantity),
        (target, StockMovementType.TRANSFER_IN, request.quantity),
    ):
        record_movement(
            session,
            item,
            movement_type=movement_type,
            delta=delta,
            actor_id=actor_id,
            transfer_id=transfer_id,
            comment=request.comment,
        )
    return source


async def apply_stock_operation(
    session: AsyncSession, actor: CurrentUser, item_id: int, request: StockOperationRequest
) -> StockItem:
    match request:
        case StockReceiptOperation():
            item = await _receipt(session, actor.id, item_id, request)
        case StockWriteOffOperation():
            item = await _write_off(session, actor.id, item_id, request)
        case StockAdjustmentOperation():
            item = await _adjustment(session, actor.id, item_id, request)
        case StockTransferOperation():
            item = await _transfer(session, actor.id, item_id, request)
    await session.flush()
    await session.commit()
    return item
```

Изменить `backend/app/modules/assets/stock_presenter.py` (применить дифф):

```diff
@@ -4,10 +4,16 @@ from collections.abc import Sequence
 
 from sqlalchemy.ext.asyncio import AsyncSession
 
-from app.modules.assets.stock_models import StockItem
-from app.modules.assets.stock_registry import is_low
-from app.modules.assets.stock_schemas import StockItemRead
+from app.modules.assets.stock_models import StockItem, StockMovement, StockMovementType
+from app.modules.assets.stock_registry import is_low, transfer_locations
+from app.modules.assets.stock_schemas import StockItemRead, StockMovementRead
 from app.modules.directories.service import get_reference_names
+from app.modules.users_auth.service import get_user_names
+
+_COUNTERPART = {
+    StockMovementType.TRANSFER_OUT: StockMovementType.TRANSFER_IN,
+    StockMovementType.TRANSFER_IN: StockMovementType.TRANSFER_OUT,
+}
 
 
 async def stock_items_to_read(
@@ -42,3 +48,56 @@ async def stock_items_to_read(
 
 async def stock_item_to_read(session: AsyncSession, item: StockItem) -> StockItemRead:
     return (await stock_items_to_read(session, [item]))[0]
+
+
+def _ids(*values: int | None) -> set[int]:
+    return {value for value in values if value is not None}
+
+
+async def movements_to_read(
+    session: AsyncSession, movements: Sequence[StockMovement]
+) -> list[StockMovementRead]:
+    pairs = await transfer_locations(
+        session, {m.transfer_id for m in movements if m.transfer_id is not None}
+    )
+
+    def counterpart(movement: StockMovement) -> int | None:
+        if movement.transfer_id is None:
+            return None
+        return pairs.get((movement.transfer_id, _COUNTERPART[movement.movement_type]))
+
+    counterparts = {movement.id: counterpart(movement) for movement in movements}
+    users = await get_user_names(
+        session,
+        _ids(*(m.recipient_id for m in movements), *(m.performed_by for m in movements)),
+    )
+    locations = await get_reference_names(session, "locations", _ids(*counterparts.values()))
+    reasons = await get_reference_names(
+        session, "issue-reasons", _ids(*(m.reason_id for m in movements))
+    )
+
+    def name(names: dict[int, str], item_id: int | None) -> str | None:
+        return names.get(item_id) if item_id is not None else None
+
+    return [
+        StockMovementRead(
+            id=movement.id,
+            stock_item_id=movement.stock_item_id,
+            movement_type=movement.movement_type,
+            delta=movement.delta,
+            quantity_after=movement.quantity_after,
+            document_date=movement.document_date,
+            transfer_id=movement.transfer_id,
+            counterpart_location_id=counterparts[movement.id],
+            counterpart_location_name=name(locations, counterparts[movement.id]),
+            reason_id=movement.reason_id,
+            reason_name=name(reasons, movement.reason_id),
+            recipient_id=movement.recipient_id,
+            recipient_name=name(users, movement.recipient_id),
+            comment=movement.comment,
+            performed_by=movement.performed_by,
+            performed_by_name=users.get(movement.performed_by, ""),
+            created_at=movement.created_at,
+        )
+        for movement in movements
+    ]
```

Изменить `backend/app/modules/assets/stock_registry.py` (применить дифф):

```diff
@@ -1,5 +1,6 @@
 """Позиции расходников: список, карточка, создание и правка (остаток меняют только движения)."""
 
+import uuid
 from dataclasses import dataclass
 from typing import Any, NoReturn
 
@@ -13,7 +14,7 @@ from app.core.errors import ConflictError, NotFoundError
 from app.core.text import normalize_text_field
 from app.modules.assets.checks import check_location, check_stock_category
 from app.modules.assets.history import changed_fields
-from app.modules.assets.stock_models import StockItem
+from app.modules.assets.stock_models import StockItem, StockMovement, StockMovementType
 
 ENTITY_TYPE = "stock_item"
 
@@ -69,7 +70,8 @@ async def get_stock_item(
 ) -> StockItem:
     stmt = select(StockItem).where(StockItem.id == item_id)
     if for_update:
-        stmt = stmt.with_for_update()
+        # populate_existing: перечитать остаток под блокировкой, даже если объект уже в сессии.
+        stmt = stmt.with_for_update().execution_options(populate_existing=True)
     item = await session.scalar(stmt)
     if item is None:
         raise NotFoundError("Позиция не найдена", code="stock_item_not_found")
@@ -167,3 +169,39 @@ async def update_stock_item(
     )
     await session.commit()
     return item
+
+
+async def list_movements(
+    session: AsyncSession, item_id: int, *, limit: int, offset: int
+) -> tuple[list[StockMovement], int]:
+    await get_stock_item(session, item_id)
+    condition = StockMovement.stock_item_id == item_id
+    total = (
+        await session.scalar(select(func.count()).select_from(StockMovement).where(condition)) or 0
+    )
+    rows = await session.scalars(
+        select(StockMovement)
+        .where(condition)
+        .order_by(StockMovement.id.desc())
+        .limit(limit)
+        .offset(offset)
+    )
+    return list(rows), total
+
+
+async def transfer_locations(
+    session: AsyncSession, transfer_ids: set[uuid.UUID]
+) -> dict[tuple[uuid.UUID, StockMovementType], int]:
+    """Склад каждой половины перемещения: (transfer_id, тип движения) → location_id."""
+    if not transfer_ids:
+        return {}
+    rows = await session.execute(
+        select(StockMovement.transfer_id, StockMovement.movement_type, StockItem.location_id)
+        .join(StockItem, StockItem.id == StockMovement.stock_item_id)
+        .where(StockMovement.transfer_id.in_(transfer_ids))
+    )
+    return {
+        (transfer_id, movement_type): location_id
+        for transfer_id, movement_type, location_id in rows.tuples()
+        if transfer_id is not None
+    }
```

Изменить `backend/app/modules/assets/stock_router.py` (применить дифф):

```diff
@@ -2,13 +2,23 @@
 
 from typing import Annotated
 
-from fastapi import APIRouter, Query
+from fastapi import APIRouter, Body, Query
 
 from app.core.db import SessionDep
 from app.core.schemas import Page, PaginationDep
-from app.modules.assets import stock_registry
-from app.modules.assets.stock_presenter import stock_item_to_read, stock_items_to_read
-from app.modules.assets.stock_schemas import StockItemCreate, StockItemRead, StockItemUpdate
+from app.modules.assets import stock_operations, stock_registry
+from app.modules.assets.stock_presenter import (
+    movements_to_read,
+    stock_item_to_read,
+    stock_items_to_read,
+)
+from app.modules.assets.stock_schemas import (
+    StockItemCreate,
+    StockItemRead,
+    StockItemUpdate,
+    StockMovementRead,
+    StockOperationRequest,
+)
 from app.modules.users_auth.service import AdminDep
 
 router = APIRouter(prefix="/stock-items", tags=["stock"])
@@ -71,3 +81,29 @@ async def update_stock_item(
         updates=body.model_dump(exclude_unset=True, exclude={"version"}),
     )
     return await stock_item_to_read(session, item)
+
+
+@router.post("/{item_id}/operations", response_model=StockItemRead)
+async def apply_stock_operation(
+    item_id: int,
+    body: Annotated[StockOperationRequest, Body()],
+    session: SessionDep,
+    admin: AdminDep,
+) -> StockItemRead:
+    item = await stock_operations.apply_stock_operation(session, admin, item_id, body)
+    return await stock_item_to_read(session, item)
+
+
+@router.get("/{item_id}/movements", response_model=Page[StockMovementRead])
+async def list_stock_movements(
+    item_id: int, session: SessionDep, admin: AdminDep, pagination: PaginationDep
+) -> Page[StockMovementRead]:
+    movements, total = await stock_registry.list_movements(
+        session, item_id, limit=pagination.limit, offset=pagination.offset
+    )
+    return Page(
+        items=await movements_to_read(session, movements),
+        total=total,
+        limit=pagination.limit,
+        offset=pagination.offset,
+    )
```

Изменить `backend/app/modules/assets/stock_schemas.py` (применить дифф):

```diff
@@ -1,9 +1,12 @@
-from datetime import datetime
-from typing import Annotated, ClassVar
+import uuid
+from datetime import date, datetime
+from typing import Annotated, ClassVar, Literal
 
 from pydantic import BaseModel, Field
 
 from app.core.schemas import PartialUpdate
+from app.modules.assets.schemas import Comment
+from app.modules.assets.stock_models import StockMovementType
 
 StockName = Annotated[str, Field(min_length=1, max_length=200)]
 Unit = Annotated[str, Field(min_length=1, max_length=20)]
@@ -48,3 +51,67 @@ class StockItemRead(BaseModel):
     version: int
     created_at: datetime
     updated_at: datetime
+
+
+Quantity = Annotated[int, Field(ge=1, le=1_000_000)]
+
+
+class StockReceiptOperation(BaseModel):
+    operation: Literal["receipt"]
+    quantity: Quantity
+    document_date: date | None = None
+    """Дата по накладной; не задана — сегодня в часовом поясе компании."""
+    comment: Comment = None
+
+
+class StockWriteOffOperation(BaseModel):
+    operation: Literal["write_off"]
+    quantity: Quantity
+    reason_id: int | None = None
+    """Обязательна; проверяется сервисом, чтобы вернуть код reason_required."""
+    comment: Comment = None
+
+
+class StockAdjustmentOperation(BaseModel):
+    operation: Literal["adjustment"]
+    actual_quantity: Annotated[int, Field(ge=0, le=1_000_000)]
+    """Фактический остаток по итогам пересчёта; изменение вычисляет сервер."""
+    comment: Comment = None
+    """Обязателен; проверяется сервисом, чтобы вернуть код comment_required."""
+
+
+class StockTransferOperation(BaseModel):
+    operation: Literal["transfer"]
+    quantity: Quantity
+    to_location_id: int
+    comment: Comment = None
+
+
+StockOperationRequest = Annotated[
+    StockReceiptOperation
+    | StockWriteOffOperation
+    | StockAdjustmentOperation
+    | StockTransferOperation,
+    Field(discriminator="operation"),
+]
+
+
+class StockMovementRead(BaseModel):
+    id: int
+    stock_item_id: int
+    movement_type: StockMovementType
+    delta: int
+    quantity_after: int
+    document_date: date | None
+    transfer_id: uuid.UUID | None
+    counterpart_location_id: int | None
+    """Для перемещения: склад-получатель у transfer_out, склад-источник у transfer_in."""
+    counterpart_location_name: str | None
+    reason_id: int | None
+    reason_name: str | None
+    recipient_id: int | None
+    recipient_name: str | None
+    comment: str | None
+    performed_by: int
+    performed_by_name: str
+    created_at: datetime
```

- [ ] **Step 4: Проверить**

Run: `cd backend && uv run pytest -q tests/core/test_timezone.py tests/modules/assets/test_stock_operations_api.py tests/modules/assets/test_stock_concurrency.py`
Expected: `15 passed`; тест гонок прогнать 3 раза — стабильно зелёный

Run: `make format && make lint`
Expected: без ошибок

Run: `make gen-api && make test`
Expected: `278 passed`

Проверка теста гонки: временно убрать `.with_for_update()` в `get_stock_item` — `test_parallel_write_off_of_last_units_one_wins` падает; вернуть правку (`git diff` должен быть пустым для этого файла относительно шага 3). Не откатывать файл через `git checkout` до коммита — потеряются незакоммиченные изменения задачи.

- [ ] **Step 5: Коммит**

```bash
git add backend/app/core/timezone.py backend/app/modules/assets/stock_operations.py backend/app/modules/assets/stock_presenter.py backend/app/modules/assets/stock_registry.py backend/app/modules/assets/stock_router.py backend/app/modules/assets/stock_schemas.py backend/openapi.json backend/tests/core/test_timezone.py backend/tests/modules/assets/test_stock_concurrency.py backend/tests/modules/assets/test_stock_operations_api.py frontend/src/api/schema.d.ts
git commit -m "feat(backend): операции с расходниками — приход, списание, корректировка, перемещение"
```

---

### Task 4: Единая выдача `POST /api/equipment/checkout`, удаление `POST /api/assets/issue`

Техника и расходники одному сотруднику одной транзакцией (п. 4 спецификации): активы, затем позиции блокируются в порядке id, собираются все проблемы, при любой — 409 `checkout_unavailable` и ничего не меняется. Из `operations.py` выносятся переиспользуемые `lock_assets` / `unavailable_assets` / `apply_transition`; массовая выдача 2a удаляется, её тесты переносятся в `test_checkout_api.py`, возврат остаётся. Чтобы коммит был зелёным целиком, страница «Выдать» во фронтенде в этой же задаче переходит на новый эндпоинт (пока только техника; строки расходников — Task 9).

**Files:**
- Modify: `backend/app/main.py`
- Create: `backend/app/modules/assets/checkout.py`
- Create: `backend/app/modules/assets/equipment_router.py`
- Create: `backend/app/modules/assets/equipment_schemas.py`
- Modify: `backend/app/modules/assets/operations.py`
- Modify: `backend/app/modules/assets/router.py`
- Modify: `backend/app/modules/assets/schemas.py`
- Modify: `frontend/src/features/assets/IssuePage.tsx`
- Modify: `frontend/src/features/assets/api.ts`
- Test (create): `backend/tests/modules/assets/test_checkout_api.py`
- Test (modify): `backend/tests/modules/assets/test_operations_api.py`
- Test (modify): `backend/tests/modules/assets/test_stock_concurrency.py`
- Test (modify): `frontend/src/features/assets/IssuePage.test.tsx`
- Generated: `backend/openapi.json` (`make gen-api`)
- Generated: `frontend/src/api/schema.d.ts` (`make gen-api`)

**Interfaces:**
- Consumes: `lock_stock_items`, `record_movement` (Task 3); `check_recipient`, `check_reason(assets=…, stock=…)`.
- Produces: `operations.OperationInput`, `operations.apply_transition(session, asset, data, actor_id)`, `operations.lock_assets(session, ids) -> dict[int, Asset]`, `operations.unavailable_assets(found, ids, required_status) -> list[UnavailableAsset]`.
- Produces: `checkout.checkout(session, actor, request) -> (list[Asset], list[StockItem])`; схемы `StockLine`, `CheckoutRequest`, `CheckoutResult`, `UnavailableStockLine`, `CheckoutUnavailable` (`equipment_schemas.py`); роутер `/equipment` (`equipment_router.py`).
- Produces (фронтенд): `useCheckout()` в `features/assets/api.ts` вместо `useIssueAssets()`.

- [ ] **Step 1: Написать падающие тесты**

Создать `backend/tests/modules/assets/test_checkout_api.py`:

```python
"""Единая выдача техники и расходников одной транзакцией (п. 4 спецификации 2b)."""

from typing import Any

import pytest
from httpx import AsyncClient, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.assets.models import AssetEvent, AssetStatus
from app.modules.assets.stock_models import StockMovement
from app.modules.users_auth.models import User, UserRole
from tests.factories import login, make_user
from tests.modules.assets.conftest import Refs, StockRefs, make_asset, make_stock_item


async def _checkout(client: AsyncClient, headers: dict[str, str], **body: Any) -> Response:
    return await client.post("/api/equipment/checkout", headers=headers, json=body)


def _error(response: Response) -> tuple[int, str]:
    return response.status_code, response.json()["error"]["code"]


@pytest.fixture
async def employee(db_session: AsyncSession) -> User:
    return await make_user(db_session, full_name="Петров Пётр")


async def test_checkout_issues_assets_and_stock_together(
    client: AsyncClient,
    admin_headers: dict[str, str],
    refs: Refs,
    stock_refs: StockRefs,
    employee: User,
    db_session: AsyncSession,
) -> None:
    first = await make_asset(db_session, refs, inventory_number="INV-1")
    second = await make_asset(db_session, refs, inventory_number="INV-2")
    cartridge = await make_stock_item(db_session, stock_refs, quantity=5)
    paper = await make_stock_item(
        db_session, stock_refs, name="Бумага A4", quantity=10, category=stock_refs.paper
    )

    response = await _checkout(
        client,
        admin_headers,
        recipient_id=employee.id,
        asset_ids=[second.id, first.id],
        stock_lines=[
            {"stock_item_id": cartridge.id, "quantity": 2},
            {"stock_item_id": paper.id, "quantity": 10},
        ],
        reason_id=refs.new_employee.id,
        comment="Новый сотрудник",
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert [asset["inventory_number"] for asset in body["assets"]] == ["INV-1", "INV-2"]
    assert {asset["owner_id"] for asset in body["assets"]} == {employee.id}
    assert {asset["status"] for asset in body["assets"]} == {"in_use"}
    assert [(item["id"], item["quantity"]) for item in body["stock_items"]] == [
        (cartridge.id, 3),
        (paper.id, 0),
    ]
    movements = list(
        await db_session.scalars(select(StockMovement).order_by(StockMovement.stock_item_id))
    )
    assert [(m.movement_type, m.delta, m.recipient_id) for m in movements] == [
        ("issue", -2, employee.id),
        ("issue", -10, employee.id),
    ]
    assert {m.reason_id for m in movements} == {refs.new_employee.id}
    assert {m.comment for m in movements} == {"Новый сотрудник"}
    events = list(
        await db_session.scalars(select(AssetEvent).where(AssetEvent.event_type == "issued"))
    )
    assert {event.asset_id for event in events} == {first.id, second.id}


async def test_checkout_only_stock(
    client: AsyncClient,
    admin_headers: dict[str, str],
    refs: Refs,
    stock_refs: StockRefs,
    employee: User,
    db_session: AsyncSession,
) -> None:
    item = await make_stock_item(db_session, stock_refs, quantity=5)

    response = await _checkout(
        client,
        admin_headers,
        recipient_id=employee.id,
        stock_lines=[{"stock_item_id": item.id, "quantity": 1}],
        reason_id=refs.stock_only.id,
    )

    assert response.status_code == 200, response.text
    assert response.json()["assets"] == []


async def test_checkout_is_all_or_nothing_and_lists_every_problem(
    client: AsyncClient,
    admin_headers: dict[str, str],
    refs: Refs,
    stock_refs: StockRefs,
    employee: User,
    db_session: AsyncSession,
) -> None:
    free = await make_asset(db_session, refs, inventory_number="INV-1")
    taken = await make_asset(
        db_session, refs, inventory_number="INV-2", status=AssetStatus.IN_USE, owner_id=employee.id
    )
    enough = await make_stock_item(db_session, stock_refs, quantity=5)
    short = await make_stock_item(db_session, stock_refs, name="Бумага A4", quantity=1)
    inactive = await make_stock_item(db_session, stock_refs, name="Старый тонер", is_active=False)

    response = await _checkout(
        client,
        admin_headers,
        recipient_id=employee.id,
        asset_ids=[free.id, taken.id, 999999],
        stock_lines=[
            {"stock_item_id": enough.id, "quantity": 2},
            {"stock_item_id": short.id, "quantity": 3},
            {"stock_item_id": inactive.id, "quantity": 1},
            {"stock_item_id": 999999, "quantity": 1},
        ],
    )

    assert _error(response) == (409, "checkout_unavailable")
    assert response.json()["error"]["details"] == {
        "assets": [
            {"asset_id": taken.id, "inventory_number": "INV-2", "status": "in_use"},
            {"asset_id": 999999, "inventory_number": None, "status": None},
        ],
        "stock": [
            {"stock_item_id": short.id, "name": "Бумага A4", "requested": 3, "available": 1},
            {"stock_item_id": inactive.id, "name": "Старый тонер", "requested": 1, "available": 0},
            {"stock_item_id": 999999, "name": None, "requested": 1, "available": None},
        ],
    }
    await db_session.refresh(free)
    await db_session.refresh(enough)
    assert free.status == AssetStatus.IN_STOCK
    assert enough.quantity == 5
    assert await db_session.scalar(select(StockMovement.id)) is None


@pytest.mark.parametrize(
    ("kind", "status", "code"),
    [
        ("empty", 422, "checkout_empty"),
        ("duplicate_stock", 422, "duplicate_stock_line"),
        ("duplicate_asset", 422, "duplicate_asset"),
        ("inactive_recipient", 422, "recipient_invalid"),
        ("asset_reason_for_stock", 422, "reason_invalid"),
        ("stock_reason_for_mixed", 422, "reason_invalid"),
    ],
)
async def test_checkout_validation(
    client: AsyncClient,
    admin_headers: dict[str, str],
    refs: Refs,
    stock_refs: StockRefs,
    employee: User,
    db_session: AsyncSession,
    kind: str,
    status: int,
    code: str,
) -> None:
    asset = await make_asset(db_session, refs, inventory_number="INV-1")
    item = await make_stock_item(db_session, stock_refs, quantity=5)
    inactive = await make_user(db_session, is_active=False)
    line = {"stock_item_id": item.id, "quantity": 1}
    bodies: dict[str, dict[str, Any]] = {
        "empty": {"recipient_id": employee.id},
        "duplicate_stock": {"recipient_id": employee.id, "stock_lines": [line, line]},
        "duplicate_asset": {"recipient_id": employee.id, "asset_ids": [asset.id, asset.id]},
        "inactive_recipient": {"recipient_id": inactive.id, "asset_ids": [asset.id]},
        "asset_reason_for_stock": {
            "recipient_id": employee.id,
            "stock_lines": [line],
            "reason_id": refs.broken.id,
        },
        "stock_reason_for_mixed": {
            "recipient_id": employee.id,
            "asset_ids": [asset.id],
            "stock_lines": [line],
            "reason_id": refs.stock_only.id,
        },
    }

    response = await _checkout(client, admin_headers, **bodies[kind])

    assert _error(response) == (status, code)


async def test_checkout_limits_lines(
    client: AsyncClient, admin_headers: dict[str, str], employee: User
) -> None:
    response = await _checkout(
        client, admin_headers, recipient_id=employee.id, asset_ids=list(range(1, 52))
    )

    assert response.status_code == 422


async def test_checkout_requires_admin(client: AsyncClient, db_session: AsyncSession) -> None:
    manager = await make_user(db_session, role=UserRole.MANAGER)
    headers = await login(client, manager.email)

    response = await _checkout(client, headers, recipient_id=manager.id, asset_ids=[1])

    assert _error(response) == (403, "insufficient_role")
```

Изменить `backend/tests/modules/assets/test_operations_api.py` (применить дифф):

```diff
@@ -154,64 +154,67 @@ async def test_operations_require_admin(
     headers = await login(client, manager.email)
 
     single = await _operate(client, headers, asset.id, operation="reserve")
-    bulk = await client.post(
-        "/api/assets/issue", headers=headers, json={"owner_id": manager.id, "asset_ids": [asset.id]}
-    )
+    bulk = await client.post("/api/assets/return", headers=headers, json={"asset_ids": [asset.id]})
 
     assert single.status_code == 403
     assert bulk.status_code == 403
 
 
-async def test_bulk_issue_and_return(
+async def test_bulk_return(
     client: AsyncClient, admin_headers: dict[str, str], refs: Refs, db_session: AsyncSession
 ) -> None:
     employee = await make_user(db_session)
-    first = await make_asset(db_session, refs, inventory_number="INV-1")
-    second = await make_asset(db_session, refs, inventory_number="INV-2")
-
-    issued = await client.post(
-        "/api/assets/issue",
-        headers=admin_headers,
-        json={
-            "owner_id": employee.id,
-            "asset_ids": [second.id, first.id, first.id],
-            "reason_id": refs.new_employee.id,
-        },
+    first = await make_asset(
+        db_session, refs, inventory_number="INV-1", status=AssetStatus.IN_USE, owner_id=employee.id
+    )
+    second = await make_asset(
+        db_session, refs, inventory_number="INV-2", status=AssetStatus.IN_USE, owner_id=employee.id
     )
-    assert issued.status_code == 200, issued.text
-    assert [item["inventory_number"] for item in issued.json()] == ["INV-1", "INV-2"]
-    assert {item["owner_id"] for item in issued.json()} == {employee.id}
 
     returned = await client.post(
         "/api/assets/return",
         headers=admin_headers,
-        json={"asset_ids": [first.id, second.id], "location_id": refs.office.id},
+        json={"asset_ids": [second.id, first.id, first.id], "location_id": refs.office.id},
     )
+
     assert returned.status_code == 200, returned.text
+    assert [item["inventory_number"] for item in returned.json()] == ["INV-1", "INV-2"]
     assert {item["status"] for item in returned.json()} == {"in_stock"}
+    assert {item["owner_id"] for item in returned.json()} == {None}
     assert {item["location_id"] for item in returned.json()} == {refs.office.id}
 
 
-async def test_bulk_issue_is_all_or_nothing(
+async def test_bulk_return_is_all_or_nothing(
     client: AsyncClient, admin_headers: dict[str, str], refs: Refs, db_session: AsyncSession
 ) -> None:
     employee = await make_user(db_session)
-    free = await make_asset(db_session, refs, inventory_number="INV-1")
-    taken = await make_asset(
-        db_session, refs, inventory_number="INV-2", status=AssetStatus.IN_USE, owner_id=employee.id
+    in_use = await make_asset(
+        db_session, refs, inventory_number="INV-1", status=AssetStatus.IN_USE, owner_id=employee.id
     )
+    free = await make_asset(db_session, refs, inventory_number="INV-2")
 
     response = await client.post(
-        "/api/assets/issue",
+        "/api/assets/return",
         headers=admin_headers,
-        json={"owner_id": employee.id, "asset_ids": [free.id, taken.id, 999999]},
+        json={"asset_ids": [in_use.id, free.id, 999999]},
     )
 
     assert response.status_code == 409
     assert _error_code(response) == "assets_unavailable"
     assert response.json()["error"]["details"] == [
-        {"asset_id": taken.id, "inventory_number": "INV-2", "status": "in_use"},
+        {"asset_id": free.id, "inventory_number": "INV-2", "status": "in_stock"},
         {"asset_id": 999999, "inventory_number": None, "status": None},
     ]
-    await db_session.refresh(free)
-    assert free.status == AssetStatus.IN_STOCK
+    await db_session.refresh(in_use)
+    assert in_use.status == AssetStatus.IN_USE
+
+
+async def test_bulk_issue_endpoint_removed(
+    client: AsyncClient, admin_headers: dict[str, str]
+) -> None:
+    """Выдача нескольких единиц — только через POST /api/equipment/checkout."""
+    response = await client.post(
+        "/api/assets/issue", headers=admin_headers, json={"owner_id": 1, "asset_ids": [1]}
+    )
+
+    assert response.status_code == 405
```

Изменить `backend/tests/modules/assets/test_stock_concurrency.py` (применить дифф):

```diff
@@ -13,6 +13,8 @@ from app.core.audit import AuditLog
 from app.core.config import get_settings
 from app.core.errors import AppError
 from app.modules.assets import stock_operations
+from app.modules.assets.checkout import checkout
+from app.modules.assets.equipment_schemas import CheckoutRequest, StockLine
 from app.modules.assets.stock_models import StockItem, StockMovement
 from app.modules.assets.stock_schemas import (
     StockOperationRequest,
@@ -171,3 +173,23 @@ async def test_parallel_transfers_create_one_target_item(race: RaceSetup) -> Non
         )
     assert [target.quantity for target in targets] == [4]
     assert await _quantity(race.engine, source) == 6
+
+
+async def test_parallel_checkout_of_last_units_one_wins(race: RaceSetup) -> None:
+    item_id = await race.make_item("Клавиатура", race.first_location_id, 1)
+    request = CheckoutRequest(
+        recipient_id=race.actor.id, stock_lines=[StockLine(stock_item_id=item_id, quantity=1)]
+    )
+
+    async def run() -> str:
+        async with AsyncSession(race.engine, expire_on_commit=False) as session:
+            try:
+                await checkout(session, race.actor, request)
+            except AppError as exc:
+                return exc.code
+            return "ok"
+
+    results = await _gather(run, run)
+
+    assert sorted(results) == ["checkout_unavailable", "ok"]
+    assert await _quantity(race.engine, item_id) == 0
```

Изменить `frontend/src/features/assets/IssuePage.test.tsx` (применить дифф):

```diff
@@ -32,12 +32,13 @@ test("выдача: при 409 недоступная техника подсв
       expect(url.searchParams.getAll("status")).toEqual(["in_stock"]);
       return HttpResponse.json(page(FREE));
     }),
-    http.post("*/api/assets/issue", async ({ request }) => {
+    http.post("*/api/equipment/checkout", async ({ request }) => {
       body = await request.json();
       return HttpResponse.json(
-        errorBody("assets_unavailable", "Часть техники недоступна", [
-          { asset_id: 101, inventory_number: "INV-002", status: "in_use" },
-        ]),
+        errorBody("checkout_unavailable", "Часть техники недоступна", {
+          assets: [{ asset_id: 101, inventory_number: "INV-002", status: "in_use" }],
+          stock: [],
+        }),
         { status: 409 },
       );
     }),
@@ -53,7 +54,13 @@ test("выдача: при 409 недоступная техника подсв
   await user.click(within(section).getByRole("button", { name: "Выдать" }));
 
   expect(await within(section).findByText(/выделена красным/)).toBeInTheDocument();
-  expect(body).toEqual({ owner_id: 10, asset_ids: [100, 101], reason_id: null, comment: null });
+  expect(body).toEqual({
+    recipient_id: 10,
+    asset_ids: [100, 101],
+    stock_lines: [],
+    reason_id: null,
+    comment: null,
+  });
   const taken = within(section).getByText("INV-002 — Dell Latitude").closest(".MuiChip-root")!;
   expect(taken).toHaveClass("MuiChip-colorError");
 });
@@ -63,7 +70,7 @@ test("выдача: 422 recipient_invalid показывает ошибку у 
   mockAssetLookups();
   server.use(
     http.get("*/api/assets", () => HttpResponse.json(page(FREE))),
-    http.post("*/api/assets/issue", () =>
+    http.post("*/api/equipment/checkout", () =>
       HttpResponse.json(errorBody("recipient_invalid", "Сотрудник недоступен для выдачи"), {
         status: 422,
       }),
```

- [ ] **Step 2: Убедиться, что тесты падают**

Run: `cd backend && uv run pytest -q tests/modules/assets/test_checkout_api.py tests/modules/assets/test_operations_api.py`
Expected: FAIL — `12 failed, 7 passed` — `/api/equipment/checkout` отвечает 404, `/api/assets/issue` ещё существует

- [ ] **Step 3: Реализация**

Изменить `backend/app/main.py` (применить дифф):

```diff
@@ -6,6 +6,7 @@ from app.core.errors import ERROR_RESPONSES, register_error_handlers
 from app.core.health import router as health_router
 from app.core.logging import configure_logging
 from app.core.middleware import RequestIdMiddleware
+from app.modules.assets.equipment_router import router as equipment_router
 from app.modules.assets.router import router as assets_router
 from app.modules.assets.stock_router import router as stock_router
 from app.modules.directories.router import routers as directories_routers
@@ -44,6 +45,7 @@ def create_app() -> FastAPI:
         *directories_routers,
         assets_router,
         stock_router,
+        equipment_router,
     ):
         app.include_router(router, prefix="/api", responses=ERROR_RESPONSES)
     return app
```

Создать `backend/app/modules/assets/checkout.py`:

```python
"""Единая выдача: техника и расходники одному сотруднику одной транзакцией (п. 4.2.1 ТЗ).

Сначала блокируются активы, затем позиции (каждые — в порядке id), и собираются все
проблемы сразу: если хоть одна единица недоступна, ничего не меняется (409).
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError, ValidationFailedError
from app.modules.assets.checks import check_reason, check_recipient
from app.modules.assets.equipment_schemas import (
    CheckoutRequest,
    CheckoutUnavailable,
    UnavailableStockLine,
)
from app.modules.assets.models import Asset, AssetStatus
from app.modules.assets.operations import (
    OperationInput,
    apply_transition,
    lock_assets,
    unavailable_assets,
)
from app.modules.assets.stock_models import StockItem, StockMovementType
from app.modules.assets.stock_operations import lock_stock_items, record_movement
from app.modules.assets.transitions import Operation
from app.modules.users_auth.service import CurrentUser


async def _validate(session: AsyncSession, request: CheckoutRequest) -> None:
    if not request.asset_ids and not request.stock_lines:
        raise ValidationFailedError("Выберите технику или расходники", code="checkout_empty")
    if len(set(request.asset_ids)) != len(request.asset_ids):
        raise ValidationFailedError("Техника указана дважды", code="duplicate_asset")
    item_ids = [line.stock_item_id for line in request.stock_lines]
    if len(set(item_ids)) != len(item_ids):
        raise ValidationFailedError("Позиция указана дважды", code="duplicate_stock_line")
    await check_recipient(session, request.recipient_id)
    if request.reason_id is not None:
        await check_reason(
            session,
            request.reason_id,
            assets=bool(request.asset_ids),
            stock=bool(request.stock_lines),
        )


def _unavailable_stock(
    request: CheckoutRequest, items: dict[int, StockItem]
) -> list[UnavailableStockLine]:
    problems = []
    for line in request.stock_lines:
        item = items.get(line.stock_item_id)
        if item is not None and item.is_active and item.quantity >= line.quantity:
            continue
        problems.append(
            UnavailableStockLine(
                stock_item_id=line.stock_item_id,
                name=item.name if item else None,
                requested=line.quantity,
                available=item.quantity if item else None,
            )
        )
    return problems


async def checkout(
    session: AsyncSession, actor: CurrentUser, request: CheckoutRequest
) -> tuple[list[Asset], list[StockItem]]:
    await _validate(session, request)
    assets = await lock_assets(session, request.asset_ids)
    items = await lock_stock_items(session, [line.stock_item_id for line in request.stock_lines])
    unavailable = CheckoutUnavailable(
        assets=unavailable_assets(assets, request.asset_ids, AssetStatus.IN_STOCK),
        stock=_unavailable_stock(request, items),
    )
    if unavailable.assets or unavailable.stock:
        raise ConflictError(
            "Часть техники или расходников недоступна для выдачи",
            code="checkout_unavailable",
            details=unavailable.model_dump(mode="json"),
        )

    issue = OperationInput(
        Operation.ISSUE,
        owner_id=request.recipient_id,
        reason_id=request.reason_id,
        comment=request.comment,
    )
    for asset in assets.values():
        apply_transition(session, asset, issue, actor.id)
    for line in request.stock_lines:
        record_movement(
            session,
            items[line.stock_item_id],
            movement_type=StockMovementType.ISSUE,
            delta=-line.quantity,
            actor_id=actor.id,
            reason_id=request.reason_id,
            recipient_id=request.recipient_id,
            comment=request.comment,
        )
    await session.flush()
    await session.commit()
    return list(assets.values()), [items[line.stock_item_id] for line in request.stock_lines]
```

Создать `backend/app/modules/assets/equipment_router.py`:

```python
"""API, общее для техники и расходников: единая выдача — только Admin."""

from fastapi import APIRouter

from app.core.db import SessionDep
from app.modules.assets import checkout as checkout_service
from app.modules.assets.equipment_schemas import CheckoutRequest, CheckoutResult
from app.modules.assets.presenter import assets_to_read
from app.modules.assets.stock_presenter import stock_items_to_read
from app.modules.users_auth.service import AdminDep

router = APIRouter(prefix="/equipment", tags=["equipment"])


@router.post("/checkout", response_model=CheckoutResult)
async def checkout(body: CheckoutRequest, session: SessionDep, admin: AdminDep) -> CheckoutResult:
    assets, items = await checkout_service.checkout(session, admin, body)
    return CheckoutResult(
        assets=await assets_to_read(session, assets, admin),
        stock_items=await stock_items_to_read(session, items),
    )
```

Создать `backend/app/modules/assets/equipment_schemas.py`:

```python
"""Схемы операций, общих для техники и расходников: единая выдача."""

from typing import Annotated

from pydantic import BaseModel, Field

from app.modules.assets.schemas import AssetRead, Comment, UnavailableAsset
from app.modules.assets.stock_schemas import Quantity, StockItemRead

MAX_CHECKOUT_LINES = 50


class StockLine(BaseModel):
    stock_item_id: int
    quantity: Quantity


class CheckoutRequest(BaseModel):
    recipient_id: int
    asset_ids: Annotated[list[int], Field(max_length=MAX_CHECKOUT_LINES)] = []
    stock_lines: Annotated[list[StockLine], Field(max_length=MAX_CHECKOUT_LINES)] = []
    reason_id: int | None = None
    comment: Comment = None


class CheckoutResult(BaseModel):
    assets: list[AssetRead]
    stock_items: list[StockItemRead]


class UnavailableStockLine(BaseModel):
    """Строка расходников, которую нельзя выдать: позиция не найдена, неактивна или мало остатка."""

    stock_item_id: int
    name: str | None
    requested: int
    available: int | None


class CheckoutUnavailable(BaseModel):
    """details ошибки checkout_unavailable."""

    assets: list[UnavailableAsset]
    stock: list[UnavailableStockLine]
```

Изменить `backend/app/modules/assets/operations.py` (применить дифф):

```diff
@@ -1,4 +1,6 @@
-"""Операции над активами по таблице переходов: одиночные и массовые выдача и возврат.
+"""Операции над активами по таблице переходов: одиночные и массовый возврат.
+
+Массовая выдача — в составе единой выдачи (checkout.py).
 
 Строки активов блокируются SELECT … FOR UPDATE (массово — в порядке id, чтобы не было
 взаимных блокировок); статус проверяется уже под блокировкой, поэтому параллельная
@@ -69,7 +71,9 @@ async def _validate(session: AsyncSession, data: OperationInput) -> None:
         await check_location(session, data.location_id)
 
 
-def _apply(session: AsyncSession, asset: Asset, data: OperationInput, actor_id: int) -> None:
+def apply_transition(
+    session: AsyncSession, asset: Asset, data: OperationInput, actor_id: int
+) -> None:
     transition = TRANSITIONS[data.operation]
     before = Placement.of(asset)
     if transition.to_status is not None:
@@ -105,60 +109,35 @@ async def apply_operation(
             code="operation_not_allowed",
             details={"status": asset.status.value},
         )
-    _apply(session, asset, data, actor.id)
+    apply_transition(session, asset, data, actor.id)
     await session.flush()
     await session.commit()
     return asset
 
 
-async def _lock_for_bulk(
-    session: AsyncSession, asset_ids: list[int], required_status: AssetStatus
-) -> list[Asset]:
-    """Блокирует активы; если хоть один не найден или не в нужном статусе — 409 целиком."""
-    # Без фильтра видимости: эндпоинты массовых операций доступны только Admin;
+async def lock_assets(session: AsyncSession, asset_ids: list[int]) -> dict[int, Asset]:
+    """Блокирует активы в порядке id (без взаимных блокировок); отсутствующих в ответе нет."""
+    # Без фильтра видимости: массовые операции доступны только Admin;
     # добавить visibility_filter, если это когда-нибудь откроют другим ролям.
-    unique_ids = sorted(set(asset_ids))
-    assets = list(
-        await session.scalars(
-            select(Asset).where(Asset.id.in_(unique_ids)).order_by(Asset.id).with_for_update()
-        )
+    rows = await session.scalars(
+        select(Asset).where(Asset.id.in_(set(asset_ids))).order_by(Asset.id).with_for_update()
     )
-    found = {asset.id: asset for asset in assets}
-    unavailable = [
+    return {asset.id: asset for asset in rows}
+
+
+def unavailable_assets(
+    found: dict[int, Asset], asset_ids: list[int], required_status: AssetStatus
+) -> list[UnavailableAsset]:
+    """Активы из asset_ids (в их порядке), которые не найдены или не в нужном статусе."""
+    return [
         UnavailableAsset(
             asset_id=asset_id,
             inventory_number=found[asset_id].inventory_number if asset_id in found else None,
             status=found[asset_id].status if asset_id in found else None,
         )
-        for asset_id in unique_ids
+        for asset_id in asset_ids
         if asset_id not in found or found[asset_id].status != required_status
     ]
-    if unavailable:
-        raise ConflictError(
-            "Часть техники недоступна для операции",
-            code="assets_unavailable",
-            details=[item.model_dump(mode="json") for item in unavailable],
-        )
-    return assets
-
-
-async def issue_assets(
-    session: AsyncSession,
-    actor: CurrentUser,
-    *,
-    owner_id: int,
-    asset_ids: list[int],
-    reason_id: int | None,
-    comment: str | None,
-) -> list[Asset]:
-    data = OperationInput(Operation.ISSUE, owner_id=owner_id, reason_id=reason_id, comment=comment)
-    await _validate(session, data)
-    assets = await _lock_for_bulk(session, asset_ids, AssetStatus.IN_STOCK)
-    for asset in assets:
-        _apply(session, asset, data, actor.id)
-    await session.flush()
-    await session.commit()
-    return assets
 
 
 async def return_assets(
@@ -171,9 +150,18 @@ async def return_assets(
 ) -> list[Asset]:
     data = OperationInput(Operation.RETURN, location_id=location_id, comment=comment)
     await _validate(session, data)
-    assets = await _lock_for_bulk(session, asset_ids, AssetStatus.IN_USE)
+    unique_ids = sorted(set(asset_ids))
+    found = await lock_assets(session, unique_ids)
+    unavailable = unavailable_assets(found, unique_ids, AssetStatus.IN_USE)
+    if unavailable:
+        raise ConflictError(
+            "Часть техники недоступна для операции",
+            code="assets_unavailable",
+            details=[item.model_dump(mode="json") for item in unavailable],
+        )
+    assets = list(found.values())
     for asset in assets:
-        _apply(session, asset, data, actor.id)
+        apply_transition(session, asset, data, actor.id)
     await session.flush()
     await session.commit()
     return assets
```

Изменить `backend/app/modules/assets/router.py` (применить дифф):

```diff
@@ -11,7 +11,6 @@ from app.modules.assets.presenter import asset_to_read, assets_to_read, events_t
 from app.modules.assets.schemas import (
     AssetCreate,
     AssetEventRead,
-    AssetIssueRequest,
     AssetOperationRequest,
     AssetRead,
     AssetReturnRequest,
@@ -91,21 +90,6 @@ async def list_asset_events(
     )
 
 
-@router.post("/issue", response_model=list[AssetRead])
-async def issue_assets(
-    body: AssetIssueRequest, session: SessionDep, admin: AdminDep
-) -> list[AssetRead]:
-    assets = await operations.issue_assets(
-        session,
-        admin,
-        owner_id=body.owner_id,
-        asset_ids=body.asset_ids,
-        reason_id=body.reason_id,
-        comment=body.comment,
-    )
-    return await assets_to_read(session, assets, admin)
-
-
 @router.post("/return", response_model=list[AssetRead])
 async def return_assets(
     body: AssetReturnRequest, session: SessionDep, admin: AdminDep
```

Изменить `backend/app/modules/assets/schemas.py` (применить дифф):

```diff
@@ -142,13 +142,6 @@ AssetOperationRequest = Annotated[
 ]
 
 
-class AssetIssueRequest(BaseModel):
-    owner_id: int
-    asset_ids: AssetIds
-    reason_id: int | None = None
-    comment: Comment = None
-
-
 class AssetReturnRequest(BaseModel):
     asset_ids: AssetIds
     location_id: int | None = None
@@ -156,7 +149,7 @@ class AssetReturnRequest(BaseModel):
 
 
 class UnavailableAsset(BaseModel):
-    """Элемент details ошибки assets_unavailable."""
+    """Элемент details ошибок assets_unavailable и checkout_unavailable."""
 
     asset_id: int
     inventory_number: str | None
```

Изменить `frontend/src/features/assets/IssuePage.tsx` (применить дифф):

```diff
@@ -25,7 +25,7 @@ import { PageContainer } from "../../shared/ui/PageContainer";
 import { FormAutocomplete } from "../../shared/ui/form/FormAutocomplete";
 import { FormSelect } from "../../shared/ui/form/FormSelect";
 import { FormTextField } from "../../shared/ui/form/FormTextField";
-import { useAssets, useIssueAssets, useReturnAssets } from "./api";
+import { useAssets, useCheckout, useReturnAssets } from "./api";
 import { AssetMultiPicker } from "./AssetMultiPicker";
 import type { Asset } from "./labels";
 
@@ -36,16 +36,16 @@ const errorMessage = (error: unknown) =>
 const MAX_BULK_SELECTION = 50;
 const BULK_LIMIT_MESSAGE = `Не больше ${MAX_BULK_SELECTION} единиц за раз`;
 
-/** Элемент details ошибки assets_unavailable (backend: UnavailableAsset). */
-interface UnavailableAsset {
-  asset_id: number;
+/** details ошибки checkout_unavailable (backend: CheckoutUnavailable). */
+interface CheckoutUnavailable {
+  assets: { asset_id: number }[];
 }
 
-/** id активов из details ошибки assets_unavailable. */
+/** id активов из details ошибки checkout_unavailable. */
 function unavailableOf(error: unknown): Set<number> {
-  if (!(error instanceof ApiError) || error.code !== "assets_unavailable") return new Set();
-  const details = error.details as UnavailableAsset[] | null;
-  return new Set((details ?? []).map((item) => item.asset_id));
+  if (!(error instanceof ApiError) || error.code !== "checkout_unavailable") return new Set();
+  const details = error.details as CheckoutUnavailable | null;
+  return new Set((details?.assets ?? []).map((item) => item.asset_id));
 }
 
 export function IssuePage() {
@@ -79,7 +79,7 @@ function IssueSection() {
   const { enqueueSnackbar } = useSnackbar();
   const { nameOf } = useUserNames();
   const reasons = useAssetIssueReasons();
-  const issue = useIssueAssets();
+  const issue = useCheckout();
   const [unavailable, setUnavailable] = useState<ReadonlySet<number>>(new Set());
   const [formError, setFormError] = useState<string | null>(null);
   const {
@@ -96,16 +96,17 @@ function IssueSection() {
     setFormError(null);
     try {
       const issued = await issue.mutateAsync({
-        owner_id: values.owner_id!,
+        recipient_id: values.owner_id!,
         asset_ids: values.asset_ids.map((asset) => asset.id),
+        stock_lines: [],
         reason_id: values.reason_id,
         comment: values.comment.trim() || null,
       });
-      enqueueSnackbar(`Выдано: ${issued.length}`, { variant: "success" });
+      enqueueSnackbar(`Выдано: ${issued.assets.length}`, { variant: "success" });
       reset({ owner_id: values.owner_id, asset_ids: [], reason_id: null, comment: "" });
       setUnavailable(new Set());
     } catch (caught) {
-      if (caught instanceof ApiError && caught.code === "assets_unavailable") {
+      if (caught instanceof ApiError && caught.code === "checkout_unavailable") {
         setUnavailable(unavailableOf(caught));
         setFormError(
           "Часть техники уже недоступна — она выделена красным. Уберите её и повторите.",
```

Изменить `frontend/src/features/assets/api.ts` (применить дифф):

```diff
@@ -101,9 +101,10 @@ export function useAssetOperation() {
   );
 }
 
-export function useIssueAssets() {
-  return useAssetsMutation((body: Schemas["AssetIssueRequest"]) =>
-    unwrap(api.POST("/api/assets/issue", { body })),
+/** Единая выдача техники и расходников (POST /api/equipment/checkout). */
+export function useCheckout() {
+  return useAssetsMutation((body: Schemas["CheckoutRequest"]) =>
+    unwrap(api.POST("/api/equipment/checkout", { body })),
   );
 }
```

- [ ] **Step 4: Проверить**

Run: `cd backend && uv run pytest -q tests/modules/assets/`
Expected: `138 passed` (включая гонку checkout в `test_stock_concurrency.py`)

Run: `make format && make lint && make gen-api && make test`
Expected: `291 passed`

Run: `cd frontend && npm run format && npm run check`
Expected: `Tests 88 passed`, typecheck и `check:api` без ошибок

Генератор типов помечает поля со значением по умолчанию обязательными, поэтому фронтенд передаёт `stock_lines: []` явно. `CheckoutUnavailable` приходит только в `details` ошибки и в OpenAPI не попадает — на фронтенде это локальный интерфейс.

- [ ] **Step 5: Коммит**

```bash
git add backend/app/main.py backend/app/modules/assets/checkout.py backend/app/modules/assets/equipment_router.py backend/app/modules/assets/equipment_schemas.py backend/app/modules/assets/operations.py backend/app/modules/assets/router.py backend/app/modules/assets/schemas.py backend/openapi.json backend/tests/modules/assets/test_checkout_api.py backend/tests/modules/assets/test_operations_api.py backend/tests/modules/assets/test_stock_concurrency.py frontend/src/api/schema.d.ts frontend/src/features/assets/IssuePage.test.tsx frontend/src/features/assets/IssuePage.tsx frontend/src/features/assets/api.ts
git commit -m "feat: единая выдача POST /api/equipment/checkout вместо POST /api/assets/issue"
```

---

### Task 5: Журнал движений `GET /api/equipment/movements`

Один запрос `UNION ALL` по `asset_events` и `stock_movements` (обе таблицы — модуля `assets`). Колонки с enum приводятся к `String`: иначе SQLAlchemy разбирал бы значения второй части объединения типом первой (`LookupError` на `receipt`). Склад второй половины перемещения — коррелированный подзапрос по `transfer_id`, поэтому фильтр по складу находит перемещение с обеих сторон. Сортировка `created_at DESC, kind, id DESC`.

**Files:**
- Modify: `backend/app/modules/assets/equipment_router.py`
- Modify: `backend/app/modules/assets/equipment_schemas.py`
- Create: `backend/app/modules/assets/journal.py`
- Create: `backend/app/modules/assets/journal_presenter.py`
- Test (create): `backend/tests/modules/assets/test_journal_api.py`
- Generated: `backend/openapi.json` (`make gen-api`)
- Generated: `frontend/src/api/schema.d.ts` (`make gen-api`)

**Interfaces:**
- Consumes: `company_day_bounds` (Task 3).
- Produces: `journal.JournalKind`, `journal.JournalGroup`, `journal.GROUPS`, `journal.JournalFilters`, `journal.list_journal(session, filters, *, limit, offset) -> (list[RowMapping], total)`; `journal_presenter.journal_to_read`; схема `JournalEntryRead` (поля `asset_event_type`, `asset_operation`, `movement_type`, `object_id`, `object_label`, `delta`, `unit`, `from/to_owner_*`, `from/to_status`, `from/to_location_*`, …).

- [ ] **Step 1: Написать падающие тесты**

Создать `backend/tests/modules/assets/test_journal_api.py`:

```python
"""Журнал движений: техника и расходники одним списком (п. 5 спецификации 2b)."""

from datetime import UTC, datetime
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.assets.models import AssetEvent, AssetEventType, AssetStatus
from app.modules.assets.stock_models import StockMovement, StockMovementType
from app.modules.users_auth.models import User, UserRole
from tests.factories import login, make_user
from tests.modules.assets.conftest import Refs, StockRefs, make_asset, make_stock_item

Params = dict[str, str | int | list[str]]


async def _journal(
    client: AsyncClient, headers: dict[str, str], params: Params | None = None
) -> dict[str, Any]:
    response = await client.get("/api/equipment/movements", headers=headers, params=params)
    assert response.status_code == 200, response.text
    body: dict[str, Any] = response.json()
    return body


def _keys(body: dict[str, Any]) -> list[tuple[str, int]]:
    return [(entry["kind"], entry["id"]) for entry in body["items"]]


async def test_journal_combines_asset_events_and_stock_movements(
    client: AsyncClient,
    admin_headers: dict[str, str],
    admin_user: User,
    refs: Refs,
    stock_refs: StockRefs,
    db_session: AsyncSession,
) -> None:
    employee = await make_user(db_session, full_name="Петров Пётр")
    asset = await make_asset(db_session, refs, inventory_number="INV-1")
    item = await make_stock_item(db_session, stock_refs, quantity=5)
    checkout = await client.post(
        "/api/equipment/checkout",
        headers=admin_headers,
        json={
            "recipient_id": employee.id,
            "asset_ids": [asset.id],
            "stock_lines": [{"stock_item_id": item.id, "quantity": 2}],
            "reason_id": refs.new_employee.id,
        },
    )
    transfer = await client.post(
        f"/api/stock-items/{item.id}/operations",
        headers=admin_headers,
        json={"operation": "transfer", "quantity": 1, "to_location_id": stock_refs.office.id},
    )
    assert checkout.status_code == 200, checkout.text
    assert transfer.status_code == 200, transfer.text

    issues = await _journal(client, admin_headers, {"group": "issue"})
    transfers = await _journal(client, admin_headers, {"group": "transfer"})

    assert issues["total"] == 2
    by_kind = {entry["kind"]: entry for entry in issues["items"]}
    asset_entry, stock_entry = by_kind["asset"], by_kind["stock"]
    assert asset_entry["asset_event_type"] == "issued"
    assert asset_entry["asset_operation"] == "issue"
    assert asset_entry["object_id"] == asset.id
    assert asset_entry["object_label"] == "INV-1 — Lenovo ThinkPad T14"
    assert asset_entry["to_owner_name"] == "Петров Пётр"
    assert asset_entry["from_status"] == "in_stock"
    assert asset_entry["to_status"] == "in_use"
    assert stock_entry["movement_type"] == "issue"
    assert stock_entry["object_id"] == item.id
    assert stock_entry["object_label"] == "Картридж HP 85A"
    assert stock_entry["delta"] == -2
    assert stock_entry["quantity_after"] == 3
    assert stock_entry["unit"] == "шт"
    assert stock_entry["to_owner_name"] == "Петров Пётр"
    assert stock_entry["to_location_name"] == "Склад"
    assert stock_entry["reason_name"] == "Новый сотрудник"
    assert stock_entry["performed_by_name"] == admin_user.full_name

    assert {entry["movement_type"] for entry in transfers["items"]} == {
        "transfer_out",
        "transfer_in",
    }
    for entry in transfers["items"]:
        assert entry["from_location_name"] == "Склад"
        assert entry["to_location_name"] == "Офис, каб. 101"


async def _asset_event(
    session: AsyncSession, asset_id: int, actor_id: int, at: datetime, **values: Any
) -> AssetEvent:
    event = AssetEvent(
        asset_id=asset_id,
        event_type=values.pop("event_type", AssetEventType.EDITED),
        performed_by=actor_id,
        created_at=at,
        **values,
    )
    session.add(event)
    await session.flush()
    return event


async def _movement(
    session: AsyncSession, item_id: int, actor_id: int, at: datetime, **values: Any
) -> StockMovement:
    movement = StockMovement(
        stock_item_id=item_id,
        movement_type=values.pop("movement_type", StockMovementType.ADJUSTMENT),
        delta=values.pop("delta", 1),
        quantity_after=values.pop("quantity_after", 1),
        comment=values.pop("comment", "Пересчёт"),
        performed_by=actor_id,
        created_at=at,
        **values,
    )
    session.add(movement)
    await session.flush()
    return movement


def _utc(day: int, hour: int, minute: int, second: int = 0) -> datetime:
    """Сентябрь 2026, UTC."""
    return datetime(2026, 9, day, hour, minute, second, tzinfo=UTC)


async def test_journal_period_in_company_timezone_and_order(
    client: AsyncClient,
    admin_headers: dict[str, str],
    admin_user: User,
    refs: Refs,
    stock_refs: StockRefs,
    db_session: AsyncSession,
) -> None:
    asset = await make_asset(db_session, refs, inventory_number="INV-1")
    item = await make_stock_item(db_session, stock_refs)
    actor = admin_user.id
    # Europe/Moscow = UTC+3: 22.09 по Москве — [21.09 21:00, 22.09 21:00) UTC.
    before = await _asset_event(db_session, asset.id, actor, _utc(21, 20, 59))
    first = await _movement(db_session, item.id, actor, _utc(21, 21, 0))
    same_time = await _asset_event(db_session, asset.id, actor, _utc(22, 12, 0))
    same_time_stock = await _movement(db_session, item.id, actor, _utc(22, 12, 0))
    last = await _asset_event(db_session, asset.id, actor, _utc(22, 20, 59, 59))
    after = await _movement(db_session, item.id, actor, _utc(22, 21, 0))

    everything = await _journal(client, admin_headers)
    day = await _journal(
        client, admin_headers, {"date_from": "2026-09-22", "date_to": "2026-09-22"}
    )
    since = await _journal(client, admin_headers, {"date_from": "2026-09-22"})
    page = await _journal(client, admin_headers, {"limit": 2, "offset": 1})

    assert _keys(everything) == [
        ("stock", after.id),
        ("asset", last.id),
        ("asset", same_time.id),
        ("stock", same_time_stock.id),
        ("stock", first.id),
        ("asset", before.id),
    ]
    assert _keys(day) == _keys(everything)[1:5]
    assert _keys(since) == _keys(everything)[:5]
    assert page["total"] == 6
    assert _keys(page) == _keys(everything)[1:3]


async def test_journal_filters(
    client: AsyncClient,
    admin_headers: dict[str, str],
    admin_user: User,
    refs: Refs,
    stock_refs: StockRefs,
    db_session: AsyncSession,
) -> None:
    employee = await make_user(db_session)
    other_admin = await make_user(db_session, role=UserRole.ADMIN)
    asset = await make_asset(db_session, refs, inventory_number="INV-1")
    item = await make_stock_item(db_session, stock_refs)
    moment = _utc(22, 9, 0)
    returned = await _asset_event(
        db_session,
        asset.id,
        admin_user.id,
        moment,
        event_type=AssetEventType.RETURNED,
        from_owner_id=employee.id,
        from_status=AssetStatus.IN_USE,
        to_status=AssetStatus.IN_STOCK,
        from_location_id=refs.office.id,
        to_location_id=refs.warehouse.id,
    )
    status = await _asset_event(
        db_session,
        asset.id,
        other_admin.id,
        moment,
        event_type=AssetEventType.STATUS_CHANGED,
        operation="reserve",
        from_status=AssetStatus.IN_STOCK,
        to_status=AssetStatus.RESERVED,
    )
    issued = await _movement(
        db_session,
        item.id,
        admin_user.id,
        moment,
        movement_type=StockMovementType.ISSUE,
        delta=-1,
        recipient_id=employee.id,
        comment=None,
    )
    receipt = await _movement(
        db_session,
        item.id,
        other_admin.id,
        moment,
        movement_type=StockMovementType.RECEIPT,
        document_date=datetime(2026, 9, 20).date(),
        comment=None,
    )

    async def keys(params: Params) -> set[tuple[str, int]]:
        return set(_keys(await _journal(client, admin_headers, params)))

    assert await keys({"kind": "asset"}) == {("asset", returned.id), ("asset", status.id)}
    assert await keys({"group": ["return", "receipt"]}) == {
        ("asset", returned.id),
        ("stock", receipt.id),
    }
    assert await keys({"group": "status"}) == {("asset", status.id)}
    assert await keys({"person_id": employee.id}) == {
        ("asset", returned.id),
        ("stock", issued.id),
    }
    assert await keys({"performed_by": other_admin.id}) == {
        ("asset", status.id),
        ("stock", receipt.id),
    }
    assert await keys({"location_id": refs.office.id}) == {("asset", returned.id)}
    assert await keys({"location_id": refs.warehouse.id}) == {
        ("asset", returned.id),
        ("stock", issued.id),
        ("stock", receipt.id),
    }
    [receipt_entry] = (await _journal(client, admin_headers, {"group": "receipt"}))["items"]
    assert receipt_entry["document_date"] == "2026-09-20"


@pytest.mark.parametrize("role", [UserRole.EMPLOYEE, UserRole.MANAGER])
async def test_journal_admin_only(
    client: AsyncClient, db_session: AsyncSession, role: UserRole
) -> None:
    user = await make_user(db_session, role=role)
    headers = await login(client, user.email)

    response = await client.get("/api/equipment/movements", headers=headers)

    assert response.status_code == 403
```

- [ ] **Step 2: Убедиться, что тесты падают**

Run: `cd backend && uv run pytest -q tests/modules/assets/test_journal_api.py`
Expected: FAIL — `5 failed` — эндпоинт отвечает 404

- [ ] **Step 3: Реализация**

Изменить `backend/app/modules/assets/equipment_router.py` (применить дифф):

```diff
@@ -1,10 +1,20 @@
-"""API, общее для техники и расходников: единая выдача — только Admin."""
+"""API, общее для техники и расходников: единая выдача и журнал движений — только Admin."""
 
-from fastapi import APIRouter
+from datetime import date
+from typing import Annotated
+
+from fastapi import APIRouter, Query
 
 from app.core.db import SessionDep
+from app.core.schemas import Page, PaginationDep
 from app.modules.assets import checkout as checkout_service
-from app.modules.assets.equipment_schemas import CheckoutRequest, CheckoutResult
+from app.modules.assets import journal
+from app.modules.assets.equipment_schemas import (
+    CheckoutRequest,
+    CheckoutResult,
+    JournalEntryRead,
+)
+from app.modules.assets.journal_presenter import journal_to_read
 from app.modules.assets.presenter import assets_to_read
 from app.modules.assets.stock_presenter import stock_items_to_read
 from app.modules.users_auth.service import AdminDep
@@ -19,3 +29,36 @@ async def checkout(body: CheckoutRequest, session: SessionDep, admin: AdminDep)
         assets=await assets_to_read(session, assets, admin),
         stock_items=await stock_items_to_read(session, items),
     )
+
+
+@router.get("/movements", response_model=Page[JournalEntryRead])
+async def list_movements(
+    session: SessionDep,
+    admin: AdminDep,
+    pagination: PaginationDep,
+    date_from: date | None = None,
+    date_to: date | None = None,
+    kind: journal.JournalKind | None = None,
+    group: Annotated[list[journal.JournalGroup] | None, Query()] = None,
+    person_id: int | None = None,
+    performed_by: int | None = None,
+    location_id: int | None = None,
+) -> Page[JournalEntryRead]:
+    filters = journal.JournalFilters(
+        date_from=date_from,
+        date_to=date_to,
+        kind=kind,
+        groups=group,
+        person_id=person_id,
+        performed_by=performed_by,
+        location_id=location_id,
+    )
+    rows, total = await journal.list_journal(
+        session, filters, limit=pagination.limit, offset=pagination.offset
+    )
+    return Page(
+        items=await journal_to_read(session, rows),
+        total=total,
+        limit=pagination.limit,
+        offset=pagination.offset,
+    )
```

Изменить `backend/app/modules/assets/equipment_schemas.py` (применить дифф):

```diff
@@ -1,11 +1,16 @@
-"""Схемы операций, общих для техники и расходников: единая выдача."""
+"""Схемы, общие для техники и расходников: единая выдача и журнал движений."""
 
+from datetime import date, datetime
 from typing import Annotated
 
 from pydantic import BaseModel, Field
 
+from app.modules.assets.journal import JournalKind
+from app.modules.assets.models import AssetEventType, AssetStatus
 from app.modules.assets.schemas import AssetRead, Comment, UnavailableAsset
+from app.modules.assets.stock_models import StockMovementType
 from app.modules.assets.stock_schemas import Quantity, StockItemRead
+from app.modules.assets.transitions import Operation
 
 MAX_CHECKOUT_LINES = 50
 
@@ -42,3 +47,37 @@ class CheckoutUnavailable(BaseModel):
 
     assets: list[UnavailableAsset]
     stock: list[UnavailableStockLine]
+
+
+class JournalEntryRead(BaseModel):
+    """Строка журнала: событие техники (kind = asset) или движение расходника (kind = stock)."""
+
+    kind: JournalKind
+    id: int
+    created_at: datetime
+    asset_event_type: AssetEventType | None
+    asset_operation: Operation | None
+    movement_type: StockMovementType | None
+    object_id: int
+    """id актива или позиции — для ссылки на карточку."""
+    object_label: str
+    delta: int | None
+    quantity_after: int | None
+    unit: str | None
+    document_date: date | None
+    from_owner_id: int | None
+    from_owner_name: str | None
+    to_owner_id: int | None
+    """Новый владелец актива или получатель расходника."""
+    to_owner_name: str | None
+    from_status: AssetStatus | None
+    to_status: AssetStatus | None
+    from_location_id: int | None
+    from_location_name: str | None
+    to_location_id: int | None
+    to_location_name: str | None
+    reason_id: int | None
+    reason_name: str | None
+    comment: str | None
+    performed_by: int
+    performed_by_name: str
```

Создать `backend/app/modules/assets/journal.py`:

```python
"""Журнал движений: события техники и движения расходников одним запросом UNION ALL.

Обе таблицы принадлежат модулю assets, поэтому межмодульного JOIN нет. Колонки приводятся
к общему виду; фильтры, сортировка и пагинация выполняются в БД.
"""

from dataclasses import dataclass
from datetime import date
from enum import StrEnum

from sqlalchemy import (
    Date,
    Integer,
    Select,
    String,
    and_,
    case,
    cast,
    func,
    literal,
    null,
    or_,
    select,
    union_all,
)
from sqlalchemy.engine import RowMapping
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.core.timezone import company_day_bounds
from app.modules.assets.models import Asset, AssetEvent, AssetEventType
from app.modules.assets.stock_models import StockItem, StockMovement, StockMovementType


class JournalKind(StrEnum):
    ASSET = "asset"
    STOCK = "stock"


class JournalGroup(StrEnum):
    ISSUE = "issue"
    RETURN = "return"
    RECEIPT = "receipt"
    WRITE_OFF = "write_off"
    ADJUSTMENT = "adjustment"
    TRANSFER = "transfer"
    STATUS = "status"
    RECORD = "record"


_E = AssetEventType
_M = StockMovementType

# Группа операций → типы событий техники и типы движений расходников.
GROUPS: dict[JournalGroup, tuple[tuple[AssetEventType, ...], tuple[StockMovementType, ...]]] = {
    JournalGroup.ISSUE: ((_E.ISSUED,), (_M.ISSUE,)),
    JournalGroup.RETURN: ((_E.RETURNED,), ()),
    JournalGroup.RECEIPT: ((), (_M.RECEIPT,)),
    JournalGroup.WRITE_OFF: ((_E.WRITTEN_OFF,), (_M.WRITE_OFF,)),
    JournalGroup.ADJUSTMENT: ((), (_M.ADJUSTMENT,)),
    JournalGroup.TRANSFER: ((_E.MOVED,), (_M.TRANSFER_OUT, _M.TRANSFER_IN)),
    JournalGroup.STATUS: ((_E.STATUS_CHANGED,), ()),
    JournalGroup.RECORD: ((_E.CREATED, _E.EDITED), ()),
}


@dataclass(frozen=True)
class JournalFilters:
    date_from: date | None = None
    date_to: date | None = None
    kind: JournalKind | None = None
    groups: list[JournalGroup] | None = None
    person_id: int | None = None
    performed_by: int | None = None
    location_id: int | None = None


def _asset_rows() -> Select[tuple[object, ...]]:
    return select(
        literal(JournalKind.ASSET.value, String).label("kind"),
        AssetEvent.id.label("id"),
        AssetEvent.created_at.label("created_at"),
        cast(AssetEvent.event_type, String).label("event_type"),
        AssetEvent.operation.label("asset_operation"),
        AssetEvent.asset_id.label("object_id"),
        (Asset.inventory_number + " — " + Asset.model).label("object_label"),
        null().cast(Integer).label("delta"),
        null().cast(Integer).label("quantity_after"),
        null().cast(String).label("unit"),
        null().cast(Date).label("document_date"),
        AssetEvent.from_owner_id.label("from_owner_id"),
        AssetEvent.to_owner_id.label("to_owner_id"),
        cast(AssetEvent.from_status, String).label("from_status"),
        cast(AssetEvent.to_status, String).label("to_status"),
        AssetEvent.from_location_id.label("from_location_id"),
        AssetEvent.to_location_id.label("to_location_id"),
        AssetEvent.reason_id.label("reason_id"),
        AssetEvent.comment.label("comment"),
        AssetEvent.performed_by.label("performed_by"),
    ).join(Asset, Asset.id == AssetEvent.asset_id)


def _stock_rows() -> Select[tuple[object, ...]]:
    other = aliased(StockMovement)
    other_item = aliased(StockItem)
    # Склад второй половины перемещения (у прочих движений — NULL).
    counterpart = (
        select(other_item.location_id)
        .join(other, other.stock_item_id == other_item.id)
        .where(other.transfer_id == StockMovement.transfer_id, other.id != StockMovement.id)
        .limit(1)
        .scalar_subquery()
    )
    return select(
        literal(JournalKind.STOCK.value, String).label("kind"),
        StockMovement.id.label("id"),
        StockMovement.created_at.label("created_at"),
        cast(StockMovement.movement_type, String).label("event_type"),
        null().cast(String).label("asset_operation"),
        StockMovement.stock_item_id.label("object_id"),
        StockItem.name.label("object_label"),
        StockMovement.delta.label("delta"),
        StockMovement.quantity_after.label("quantity_after"),
        StockItem.unit.label("unit"),
        StockMovement.document_date.label("document_date"),
        null().cast(Integer).label("from_owner_id"),
        StockMovement.recipient_id.label("to_owner_id"),
        null().cast(String).label("from_status"),
        null().cast(String).label("to_status"),
        case(
            (StockMovement.movement_type == _M.TRANSFER_IN, counterpart),
            (StockMovement.movement_type == _M.TRANSFER_OUT, StockItem.location_id),
            else_=None,
        ).label("from_location_id"),
        case(
            (StockMovement.movement_type == _M.TRANSFER_OUT, counterpart),
            else_=StockItem.location_id,
        ).label("to_location_id"),
        StockMovement.reason_id.label("reason_id"),
        StockMovement.comment.label("comment"),
        StockMovement.performed_by.label("performed_by"),
    ).join(StockItem, StockItem.id == StockMovement.stock_item_id)


async def list_journal(
    session: AsyncSession, filters: JournalFilters, *, limit: int, offset: int
) -> tuple[list[RowMapping], int]:
    journal = union_all(_asset_rows(), _stock_rows()).subquery("journal")
    c = journal.c
    conditions = []
    start, end = company_day_bounds(filters.date_from, filters.date_to)
    if start is not None:
        conditions.append(c.created_at >= start)
    if end is not None:
        conditions.append(c.created_at < end)
    if filters.kind is not None:
        conditions.append(c.kind == filters.kind.value)
    if filters.groups:
        asset_types = [t.value for g in filters.groups for t in GROUPS[g][0]]
        stock_types = [t.value for g in filters.groups for t in GROUPS[g][1]]
        conditions.append(
            or_(
                and_(c.kind == JournalKind.ASSET.value, c.event_type.in_(asset_types)),
                and_(c.kind == JournalKind.STOCK.value, c.event_type.in_(stock_types)),
            )
        )
    if filters.person_id is not None:
        conditions.append(
            or_(c.from_owner_id == filters.person_id, c.to_owner_id == filters.person_id)
        )
    if filters.performed_by is not None:
        conditions.append(c.performed_by == filters.performed_by)
    if filters.location_id is not None:
        conditions.append(
            or_(
                c.from_location_id == filters.location_id,
                c.to_location_id == filters.location_id,
            )
        )
    stmt = select(journal).where(*conditions)
    total = await session.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = await session.execute(
        stmt.order_by(c.created_at.desc(), c.kind, c.id.desc()).limit(limit).offset(offset)
    )
    return list(rows.mappings()), total
```

Создать `backend/app/modules/assets/journal_presenter.py`:

```python
"""Строки журнала для API: ФИО, склады и причины через service других модулей."""

from collections.abc import Sequence

from sqlalchemy.engine import RowMapping
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.assets.equipment_schemas import JournalEntryRead
from app.modules.assets.journal import JournalKind
from app.modules.assets.models import AssetEventType, AssetStatus
from app.modules.assets.stock_models import StockMovementType
from app.modules.assets.transitions import Operation
from app.modules.directories.service import get_reference_names
from app.modules.users_auth.service import get_user_names


def _ids(rows: Sequence[RowMapping], *columns: str) -> set[int]:
    return {row[column] for row in rows for column in columns if row[column] is not None}


async def journal_to_read(
    session: AsyncSession, rows: Sequence[RowMapping]
) -> list[JournalEntryRead]:
    users = await get_user_names(
        session, _ids(rows, "from_owner_id", "to_owner_id", "performed_by")
    )
    locations = await get_reference_names(
        session, "locations", _ids(rows, "from_location_id", "to_location_id")
    )
    reasons = await get_reference_names(session, "issue-reasons", _ids(rows, "reason_id"))

    def name(names: dict[int, str], item_id: int | None) -> str | None:
        return names.get(item_id) if item_id is not None else None

    def status(value: str | None) -> AssetStatus | None:
        return AssetStatus(value) if value is not None else None

    entries = []
    for row in rows:
        is_asset = row["kind"] == JournalKind.ASSET
        entries.append(
            JournalEntryRead(
                kind=JournalKind(row["kind"]),
                id=row["id"],
                created_at=row["created_at"],
                asset_event_type=AssetEventType(row["event_type"]) if is_asset else None,
                asset_operation=Operation(row["asset_operation"])
                if row["asset_operation"]
                else None,
                movement_type=None if is_asset else StockMovementType(row["event_type"]),
                object_id=row["object_id"],
                object_label=row["object_label"],
                delta=row["delta"],
                quantity_after=row["quantity_after"],
                unit=row["unit"],
                document_date=row["document_date"],
                from_owner_id=row["from_owner_id"],
                from_owner_name=name(users, row["from_owner_id"]),
                to_owner_id=row["to_owner_id"],
                to_owner_name=name(users, row["to_owner_id"]),
                from_status=status(row["from_status"]),
                to_status=status(row["to_status"]),
                from_location_id=row["from_location_id"],
                from_location_name=name(locations, row["from_location_id"]),
                to_location_id=row["to_location_id"],
                to_location_name=name(locations, row["to_location_id"]),
                reason_id=row["reason_id"],
                reason_name=name(reasons, row["reason_id"]),
                comment=row["comment"],
                performed_by=row["performed_by"],
                performed_by_name=users.get(row["performed_by"], ""),
            )
        )
    return entries
```

- [ ] **Step 4: Проверить**

Run: `cd backend && uv run pytest -q tests/modules/assets/test_journal_api.py`
Expected: `5 passed`

Run: `make format && make lint && make gen-api && make test`
Expected: `296 passed`

Run: `cd frontend && npm run check`
Expected: зелёный (обновились только типы)

В тестах все записи внутри одной транзакции получают одинаковый `now()`, поэтому порядок и границы периода проверяются на строках с явным `created_at`.

- [ ] **Step 5: Коммит**

```bash
git add backend/app/modules/assets/equipment_router.py backend/app/modules/assets/equipment_schemas.py backend/app/modules/assets/journal.py backend/app/modules/assets/journal_presenter.py backend/openapi.json backend/tests/modules/assets/test_journal_api.py frontend/src/api/schema.d.ts
git commit -m "feat(backend): журнал движений техники и расходников GET /api/equipment/movements"
```

---

### Task 6: Фронтенд: основа расходников — подписи, запросы, справочники, фикстуры

Подписи движений и операций, запросы `features/stock/api.ts`, справочник категорий и фильтр причин по составу (`reasonFits` — зеркало backend `_reason_fits`), фикстуры для тестов. Мутации техники и единой выдачи теперь сбрасывают кэш журнала (`queryKeys.movements`), выдача — ещё и расходников. В ESLint-правило изоляции фич добавлены `assets` (в 2a его забыли), `stock`, `movements`.

**Files:**
- Modify: `frontend/eslint.config.js`
- Modify: `frontend/src/features/assets/api.ts`
- Create: `frontend/src/features/stock/api.ts`
- Create: `frontend/src/features/stock/labels.ts`
- Modify: `frontend/src/shared/lookups/directories.ts`
- Modify: `frontend/src/shared/lookups/queryKeys.ts`
- Test (create): `frontend/src/features/stock/labels.test.ts`
- Test (create): `frontend/src/features/stock/testing.ts`
- Test (create): `frontend/src/shared/lookups/directories.test.ts`
- Test (modify): `frontend/src/test/fixtures.ts`

**Interfaces:**
- Produces: `shared/lookups/directories.ts` — `useStockCategories()`, `useIssueReasons()`, `useStockIssueReasons()`, `reasonFits(applicability, {assets, stock})`, тип `ReasonScope`; `queryKeys.stock`, `queryKeys.movements`.
- Produces: `features/stock/labels.ts` — типы `StockItem`, `StockMovement`, `StockMovementType`, `StockOperation`; `MOVEMENT_LABELS`, `STOCK_OPERATION_LABELS`, `STOCK_OPERATIONS`, `movementTitle(type)`, `formatDelta(delta, unit)` («+10 шт» / «−3 шт»), `movementDetails(movement)`.
- Produces: `features/stock/api.ts` — `fetchStockItems`, `useStockItems`, `useStockItem`, `useStockMovements`, `useCreateStockItem`, `useUpdateStockItem`, `useStockOperation`, тип `StockOperationBody`; `features/stock/testing.ts` — `mockStockLookups()`.
- Produces (тесты): `makeStockItem`, `makeStockMovement`, `makeJournalEntry` в `src/test/fixtures.ts`.

- [ ] **Step 1: Написать падающие тесты**

Создать `frontend/src/features/stock/labels.test.ts`:

```ts
import { makeStockMovement } from "../../test/fixtures";
import { formatDelta, movementDetails, movementTitle } from "./labels";

test("изменение количества со знаком и единицей", () => {
  expect(formatDelta(10, "шт")).toBe("+10 шт");
  expect(formatDelta(-3, "уп")).toBe("−3 уп");
});

test("заголовок движения по типу", () => {
  expect(movementTitle("receipt")).toBe("Приход");
  expect(movementTitle("transfer_out")).toBe("Перемещение: отправлено");
});

test("подробности движения: получатель, склад, дата документа, причина", () => {
  expect(
    movementDetails(
      makeStockMovement({
        movement_type: "issue",
        recipient_name: "Петров Пётр",
        reason_name: "Новый сотрудник",
      }),
    ),
  ).toEqual(["Кому: Петров Пётр", "Причина: Новый сотрудник"]);
  expect(
    movementDetails(
      makeStockMovement({ movement_type: "transfer_out", counterpart_location_name: "Офис" }),
    ),
  ).toEqual(["Куда: Офис"]);
  expect(
    movementDetails(
      makeStockMovement({ movement_type: "transfer_in", counterpart_location_name: "Склад" }),
    ),
  ).toEqual(["Откуда: Склад"]);
  expect(
    movementDetails(makeStockMovement({ movement_type: "receipt", document_date: "2026-09-01" })),
  ).toEqual(["Дата документа: 01.09.2026"]);
});
```

Создать `frontend/src/features/stock/testing.ts`:

```ts
import { http, HttpResponse } from "msw";

import { makeUser, page } from "../../test/fixtures";
import { server } from "../../test/server";

/** Справочники и пользователи, которые запрашивают экраны расходников. */
export function mockStockLookups() {
  server.use(
    http.get("*/api/directories/locations", () =>
      HttpResponse.json([
        { id: 5, name: "Склад", description: null, is_active: true },
        { id: 6, name: "Офис, каб. 101", description: null, is_active: true },
      ]),
    ),
    http.get("*/api/directories/stock-categories", () =>
      HttpResponse.json([
        { id: 3, name: "Картриджи", is_active: true },
        { id: 4, name: "Бумага", is_active: true },
      ]),
    ),
    http.get("*/api/directories/issue-reasons", () =>
      HttpResponse.json([
        { id: 7, name: "Новый сотрудник", applicability: "both", is_active: true },
        { id: 8, name: "Брак", applicability: "stock", is_active: true },
        { id: 9, name: "Неисправность", applicability: "assets", is_active: true },
      ]),
    ),
    http.get("*/api/admin/users", () =>
      HttpResponse.json(page([makeUser({ id: 10, full_name: "Петров Пётр" })])),
    ),
  );
}
```

Создать `frontend/src/shared/lookups/directories.test.ts`:

```ts
import { reasonFits } from "./directories";

test("причина подходит к составу операции", () => {
  expect(reasonFits("both", { assets: true, stock: true })).toBe(true);
  expect(reasonFits("assets", { assets: true, stock: false })).toBe(true);
  expect(reasonFits("assets", { assets: true, stock: true })).toBe(false);
  expect(reasonFits("stock", { assets: false, stock: true })).toBe(true);
  expect(reasonFits("stock", { assets: true, stock: false })).toBe(false);
});
```

Изменить `frontend/src/test/fixtures.ts` (применить дифф):

```diff
@@ -71,3 +71,85 @@ export function makeAssetEvent(
     ...overrides,
   };
 }
+
+export function makeStockItem(
+  overrides: Partial<Schemas["StockItemRead"]> = {},
+): Schemas["StockItemRead"] {
+  return {
+    id: 200,
+    name: "Картридж HP 85A",
+    stock_category_id: 3,
+    category_name: "Картриджи",
+    unit: "шт",
+    location_id: 5,
+    location_name: "Склад",
+    quantity: 12,
+    min_quantity: 5,
+    is_low: false,
+    is_active: true,
+    version: 1,
+    created_at: "2026-09-01T09:00:00Z",
+    updated_at: "2026-09-01T09:00:00Z",
+    ...overrides,
+  };
+}
+
+export function makeStockMovement(
+  overrides: Partial<Schemas["StockMovementRead"]> = {},
+): Schemas["StockMovementRead"] {
+  return {
+    id: 1,
+    stock_item_id: 200,
+    movement_type: "receipt",
+    delta: 10,
+    quantity_after: 10,
+    document_date: null,
+    transfer_id: null,
+    counterpart_location_id: null,
+    counterpart_location_name: null,
+    reason_id: null,
+    reason_name: null,
+    recipient_id: null,
+    recipient_name: null,
+    comment: null,
+    performed_by: 1,
+    performed_by_name: "Иванов Иван",
+    created_at: "2026-09-01T09:00:00Z",
+    ...overrides,
+  };
+}
+
+export function makeJournalEntry(
+  overrides: Partial<Schemas["JournalEntryRead"]> = {},
+): Schemas["JournalEntryRead"] {
+  return {
+    kind: "stock",
+    id: 1,
+    created_at: "2026-09-22T09:00:00Z",
+    asset_event_type: null,
+    asset_operation: null,
+    movement_type: "issue",
+    object_id: 200,
+    object_label: "Картридж HP 85A",
+    delta: -2,
+    quantity_after: 10,
+    unit: "шт",
+    document_date: null,
+    from_owner_id: null,
+    from_owner_name: null,
+    to_owner_id: 10,
+    to_owner_name: "Петров Пётр",
+    from_status: null,
+    to_status: null,
+    from_location_id: null,
+    from_location_name: null,
+    to_location_id: 5,
+    to_location_name: "Склад",
+    reason_id: null,
+    reason_name: null,
+    comment: null,
+    performed_by: 1,
+    performed_by_name: "Иванов Иван",
+    ...overrides,
+  };
+}
```

- [ ] **Step 2: Убедиться, что тесты падают**

Run: `cd frontend && npx vitest run src/features/stock/labels.test.ts src/shared/lookups/directories.test.ts`
Expected: FAIL — `Failed to resolve import "./labels"` и `TypeError: reasonFits is not a function`

- [ ] **Step 3: Реализация**

Изменить `frontend/eslint.config.js` (применить дифф):

```diff
@@ -4,7 +4,16 @@ import reactHooks from "eslint-plugin-react-hooks";
 import globals from "globals";
 import tseslint from "typescript-eslint";
 
-const FEATURES = ["auth", "home", "users", "departments", "directories"];
+const FEATURES = [
+  "auth",
+  "home",
+  "users",
+  "departments",
+  "directories",
+  "assets",
+  "stock",
+  "movements",
+];
 
 // Фича импортирует другую фичу только через её публичный index.ts.
 const featureZones = FEATURES.flatMap((target) =>
```

Изменить `frontend/src/features/assets/api.ts` (применить дифф):

```diff
@@ -65,12 +65,17 @@ export function useAssetEvents(id: number, limit: number, offset: number) {
   });
 }
 
-/** Мутация, после которой перезапрашиваются все данные техники (реестр, карточка, история). */
+/** Мутация, после которой перезапрашиваются данные техники (реестр, карточка, история) и журнал. */
 function useAssetsMutation<V, R>(mutationFn: (variables: V) => Promise<R>) {
   const queryClient = useQueryClient();
   return useMutation({
     mutationFn,
-    onSettled: () => queryClient.invalidateQueries({ queryKey: queryKeys.assets }),
+    onSettled: async () => {
+      await Promise.all([
+        queryClient.invalidateQueries({ queryKey: queryKeys.assets }),
+        queryClient.invalidateQueries({ queryKey: queryKeys.movements }),
+      ]);
+    },
   });
 }
 
@@ -101,11 +106,20 @@ export function useAssetOperation() {
   );
 }
 
-/** Единая выдача техники и расходников (POST /api/equipment/checkout). */
+/** Единая выдача техники и расходников: перезапрашивает и технику, и расходники. */
 export function useCheckout() {
-  return useAssetsMutation((body: Schemas["CheckoutRequest"]) =>
-    unwrap(api.POST("/api/equipment/checkout", { body })),
-  );
+  const queryClient = useQueryClient();
+  return useMutation({
+    mutationFn: (body: Schemas["CheckoutRequest"]) =>
+      unwrap(api.POST("/api/equipment/checkout", { body })),
+    onSettled: async () => {
+      await Promise.all(
+        [queryKeys.assets, queryKeys.stock, queryKeys.movements].map((queryKey) =>
+          queryClient.invalidateQueries({ queryKey }),
+        ),
+      );
+    },
+  });
 }
 
 export function useReturnAssets() {
```

Создать `frontend/src/features/stock/api.ts`:

```ts
import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api, unwrap } from "../../api/client";
import type { Schemas } from "../../api/types";
import { queryKeys } from "../../shared/lookups/queryKeys";

export interface StockListParams {
  q?: string;
  categoryId?: number | null;
  locationId?: number | null;
  lowStock?: boolean;
  includeInactive?: boolean;
  limit: number;
  offset: number;
}

export function fetchStockItems(params: StockListParams) {
  return unwrap(
    api.GET("/api/stock-items", {
      params: {
        query: {
          q: params.q?.trim() || undefined,
          category_id: params.categoryId ?? undefined,
          location_id: params.locationId ?? undefined,
          low_stock: params.lowStock || undefined,
          include_inactive: params.includeInactive || undefined,
          limit: params.limit,
          offset: params.offset,
        },
      },
    }),
  );
}

export function useStockItems(params: StockListParams) {
  return useQuery({
    queryKey: [...queryKeys.stock, "list", params],
    queryFn: () => fetchStockItems(params),
    placeholderData: keepPreviousData,
  });
}

export function useStockItem(id: number) {
  return useQuery({
    queryKey: [...queryKeys.stock, "detail", id],
    queryFn: () =>
      unwrap(api.GET("/api/stock-items/{item_id}", { params: { path: { item_id: id } } })),
  });
}

export function useStockMovements(id: number, limit: number, offset: number) {
  return useQuery({
    queryKey: [...queryKeys.stock, "movements", id, { limit, offset }],
    queryFn: () =>
      unwrap(
        api.GET("/api/stock-items/{item_id}/movements", {
          params: { path: { item_id: id }, query: { limit, offset } },
        }),
      ),
    placeholderData: keepPreviousData,
  });
}

/** Мутация, после которой перезапрашиваются расходники и журнал движений. */
function useStockMutation<V, R>(mutationFn: (variables: V) => Promise<R>) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn,
    onSettled: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: queryKeys.stock }),
        queryClient.invalidateQueries({ queryKey: queryKeys.movements }),
      ]);
    },
  });
}

export function useCreateStockItem() {
  return useStockMutation((body: Schemas["StockItemCreate"]) =>
    unwrap(api.POST("/api/stock-items", { body })),
  );
}

export function useUpdateStockItem() {
  return useStockMutation(({ id, body }: { id: number; body: Schemas["StockItemUpdate"] }) =>
    unwrap(api.PATCH("/api/stock-items/{item_id}", { params: { path: { item_id: id } }, body })),
  );
}

export type StockOperationBody =
  | Schemas["StockReceiptOperation"]
  | Schemas["StockWriteOffOperation"]
  | Schemas["StockAdjustmentOperation"]
  | Schemas["StockTransferOperation"];

export function useStockOperation() {
  return useStockMutation(({ id, body }: { id: number; body: StockOperationBody }) =>
    unwrap(
      api.POST("/api/stock-items/{item_id}/operations", {
        params: { path: { item_id: id } },
        body,
      }),
    ),
  );
}
```

Создать `frontend/src/features/stock/labels.ts`:

```ts
import type { Schemas } from "../../api/types";
import { formatDate } from "../../shared/lib/format";

export type StockItem = Schemas["StockItemRead"];
export type StockMovement = Schemas["StockMovementRead"];
export type StockMovementType = Schemas["StockMovementType"];
export type StockOperation = "receipt" | "write_off" | "adjustment" | "transfer";

export const MOVEMENT_LABELS: Record<StockMovementType, string> = {
  receipt: "Приход",
  issue: "Выдача",
  write_off: "Списание",
  adjustment: "Корректировка",
  transfer_out: "Перемещение: отправлено",
  transfer_in: "Перемещение: получено",
};

export const STOCK_OPERATION_LABELS: Record<StockOperation, string> = {
  receipt: "Приход",
  write_off: "Списать",
  adjustment: "Корректировка",
  transfer: "Переместить",
};

export const STOCK_OPERATIONS = Object.keys(STOCK_OPERATION_LABELS) as StockOperation[];

export function movementTitle(type: StockMovementType): string {
  return MOVEMENT_LABELS[type];
}

/** «+10 шт» / «−3 шт» (минус — типографский). */
export function formatDelta(delta: number, unit: string): string {
  return `${delta > 0 ? "+" : "−"}${Math.abs(delta)} ${unit}`;
}

/** Строки подробностей движения для истории позиции. */
export function movementDetails(movement: StockMovement): string[] {
  const lines: string[] = [];
  if (movement.recipient_name) lines.push(`Кому: ${movement.recipient_name}`);
  if (movement.counterpart_location_name) {
    const label = movement.movement_type === "transfer_out" ? "Куда" : "Откуда";
    lines.push(`${label}: ${movement.counterpart_location_name}`);
  }
  if (movement.document_date) lines.push(`Дата документа: ${formatDate(movement.document_date)}`);
  if (movement.reason_name) lines.push(`Причина: ${movement.reason_name}`);
  return lines;
}
```

Изменить `frontend/src/shared/lookups/directories.ts` (применить дифф):

```diff
@@ -1,6 +1,7 @@
 import { useQuery } from "@tanstack/react-query";
 
 import { api, unwrap } from "../../api/client";
+import type { Schemas } from "../../api/types";
 import { queryKeys } from "./queryKeys";
 
 /** Активные элементы справочников для выпадающих списков форм. */
@@ -18,11 +19,53 @@ export function useAssetTypes() {
   });
 }
 
+export function useStockCategories() {
+  return useQuery({
+    queryKey: [...queryKeys.directories, "stock-categories", { includeInactive: false }],
+    queryFn: () => unwrap(api.GET("/api/directories/stock-categories")),
+  });
+}
+
+/** Состав операции: есть ли в ней техника и расходники. */
+export interface ReasonScope {
+  assets: boolean;
+  stock: boolean;
+}
+
+/** Причина покрывает весь состав операции (backend: checks._reason_fits). */
+export function reasonFits(
+  applicability: Schemas["IssueReasonApplicability"],
+  scope: ReasonScope,
+): boolean {
+  if (applicability === "both") return true;
+  if (scope.assets && scope.stock) return false;
+  return applicability === (scope.assets ? "assets" : "stock");
+}
+
+/** Все активные причины выдачи; фильтр по составу — reasonFits. */
+export function useIssueReasons() {
+  return useQuery({
+    queryKey: [...queryKeys.directories, "issue-reasons", { includeInactive: false }],
+    queryFn: () => unwrap(api.GET("/api/directories/issue-reasons")),
+  });
+}
+
 /** Причины выдачи, применимые к технике (applicability assets или both). */
 export function useAssetIssueReasons() {
   return useQuery({
     queryKey: [...queryKeys.directories, "issue-reasons", { includeInactive: false }],
     queryFn: () => unwrap(api.GET("/api/directories/issue-reasons")),
-    select: (items) => items.filter((item) => item.applicability !== "stock"),
+    select: (items) =>
+      items.filter((item) => reasonFits(item.applicability, { assets: true, stock: false })),
+  });
+}
+
+/** Причины, применимые к расходникам (applicability stock или both). */
+export function useStockIssueReasons() {
+  return useQuery({
+    queryKey: [...queryKeys.directories, "issue-reasons", { includeInactive: false }],
+    queryFn: () => unwrap(api.GET("/api/directories/issue-reasons")),
+    select: (items) =>
+      items.filter((item) => reasonFits(item.applicability, { assets: false, stock: true })),
   });
 }
```

Изменить `frontend/src/shared/lookups/queryKeys.ts` (применить дифф):

```diff
@@ -3,4 +3,6 @@ export const queryKeys = {
   departments: ["departments"] as const,
   directories: ["directories"] as const,
   assets: ["assets"] as const,
+  stock: ["stock"] as const,
+  movements: ["movements"] as const,
 };
```

- [ ] **Step 4: Проверить**

Run: `cd frontend && npx vitest run src/features/stock/labels.test.ts src/shared/lookups/directories.test.ts`
Expected: `Tests 4 passed`

Run: `cd frontend && npm run format && npm run check`
Expected: `Tests 92 passed`, ESLint без нарушений

- [ ] **Step 5: Коммит**

```bash
git add frontend/eslint.config.js frontend/src/features/assets/api.ts frontend/src/features/stock/api.ts frontend/src/features/stock/labels.test.ts frontend/src/features/stock/labels.ts frontend/src/features/stock/testing.ts frontend/src/shared/lookups/directories.test.ts frontend/src/shared/lookups/directories.ts frontend/src/shared/lookups/queryKeys.ts frontend/src/test/fixtures.ts
git commit -m "feat(frontend): основа расходников — подписи, запросы, справочники, фикстуры"
```

---

### Task 7: Фронтенд: страница «Расходники» и добавление позиции

`/equipment/stock` (только Admin): таблица с остатком (`StockQuantityChip` — красный при низком остатке), фильтры в URL, «Добавить позицию» → карточка. Пункт меню «Расходники». Здесь же — таймаут 15 с для теста «нельзя отметить больше 50 единиц» из 2a: он кликает 51 флажок (≈4,4 с) и при параллельном прогоне большего числа файлов перестаёт укладываться в 5 с.

**Files:**
- Modify: `frontend/src/app/routes.tsx`
- Create: `frontend/src/features/stock/StockItemFormDialog.tsx`
- Create: `frontend/src/features/stock/StockPage.tsx`
- Create: `frontend/src/features/stock/StockQuantityChip.tsx`
- Create: `frontend/src/features/stock/index.ts`
- Modify: `frontend/src/layout/menu.ts`
- Test (modify): `frontend/src/app/shell.test.tsx`
- Test (modify): `frontend/src/features/assets/IssuePage.test.tsx`
- Test (create): `frontend/src/features/stock/StockPage.test.tsx`

**Interfaces:**
- Consumes: `useStockItems`, `useCreateStockItem`, `useUpdateStockItem`, `useStockCategories`, `useLocations` (Task 6).
- Produces: `StockPage`, `StockItemFormDialog({item, onClose, onSaved?})` (создание и правка; `version_conflict` → закрытие с предупреждением), `StockQuantityChip({item})`; `features/stock/index.ts`.

- [ ] **Step 1: Написать падающие тесты**

Изменить `frontend/src/app/shell.test.tsx` (применить дифф):

```diff
@@ -48,6 +48,10 @@ test("администратор видит раздел «Администри
   );
   expect(within(nav).getByText("Администрирование")).toBeInTheDocument();
   expect(within(nav).getByRole("link", { name: "Выдать / принять" })).toBeInTheDocument();
+  expect(within(nav).getByRole("link", { name: "Расходники" })).toHaveAttribute(
+    "href",
+    "/equipment/stock",
+  );
   expect(screen.getByRole("heading", { name: "Главная" })).toBeInTheDocument();
   expect(screen.getByText("Здравствуйте, Иванов Иван")).toBeInTheDocument();
 });
@@ -61,7 +65,7 @@ test("сотрудник не видит раздел «Администриро
   expect(within(nav).queryByText("Администрирование")).not.toBeInTheDocument();
 });
 
-test("раздел «Склад и техника»: реестр всем, выдача только администратору", async () => {
+test("раздел «Склад и техника»: реестр всем, расходники и выдача только администратору", async () => {
   mockSignedIn(makeMe({ role: "manager" }));
   renderShell("/");
 
@@ -71,6 +75,7 @@ test("раздел «Склад и техника»: реестр всем, вы
     "/equipment/assets",
   );
   expect(within(nav).queryByRole("link", { name: "Выдать / принять" })).not.toBeInTheDocument();
+  expect(within(nav).queryByRole("link", { name: "Расходники" })).not.toBeInTheDocument();
 });
 
 test("неизвестный путь показывает страницу 404", async () => {
```

Изменить `frontend/src/features/assets/IssuePage.test.tsx` (применить дифф):

```diff
@@ -213,7 +213,7 @@ test("приём: нельзя отметить больше 50 единиц т
   expect(within(section).getByText("Не больше 50 единиц за раз")).toBeInTheDocument();
   const checkboxes = within(section).getAllByRole("checkbox") as HTMLInputElement[];
   expect(checkboxes.filter((box) => box.checked)).toHaveLength(50);
-});
+}, 15_000); // 51 клик: при параллельном прогоне всех файлов не укладывается в 5 с по умолчанию
 
 test("страница выдачи доступна только администратору", async () => {
   mockSignedIn(makeMe({ role: "manager" }));
```

Создать `frontend/src/features/stock/StockPage.test.tsx`:

```tsx
import { screen, waitFor, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";

import { renderApp } from "../../test/app";
import { makeMe, mockSignedIn } from "../../test/auth";
import { makeStockItem, page } from "../../test/fixtures";
import { errorBody } from "../../test/http";
import { server } from "../../test/server";
import { mockStockLookups } from "./testing";

function mockItems(seen: URL[] = []) {
  server.use(
    http.get("*/api/stock-items", ({ request }) => {
      seen.push(new URL(request.url));
      return HttpResponse.json(
        page([
          makeStockItem({ id: 200, quantity: 3, is_low: true }),
          makeStockItem({
            id: 201,
            name: "Бумага A4",
            category_name: "Бумага",
            unit: "пачка",
            quantity: 40,
            min_quantity: 0,
          }),
        ]),
      );
    }),
  );
  return seen;
}

test("расходники: остатки, низкий остаток красным, фильтры из URL", async () => {
  mockSignedIn();
  mockStockLookups();
  const seen = mockItems();
  const { user, router } = renderApp("/equipment/stock?category=3&low=true");

  const low = (await screen.findByRole("link", { name: "Картридж HP 85A" })).closest("tr")!;
  expect(within(low).getByText("3 шт").closest(".MuiChip-root")).toHaveClass("MuiChip-colorError");
  expect(within(low).getByText("5 шт")).toBeInTheDocument();
  const paper = screen.getByRole("link", { name: "Бумага A4" }).closest("tr")!;
  expect(within(paper).getByText("40 пачка").closest(".MuiChip-root")).not.toHaveClass(
    "MuiChip-colorError",
  );
  expect(within(paper).getByText("—")).toBeInTheDocument();
  expect(seen.at(-1)?.searchParams.get("category_id")).toBe("3");
  expect(seen.at(-1)?.searchParams.get("low_stock")).toBe("true");

  await user.click(screen.getByLabelText("Показать неактивные"));
  await waitFor(() => expect(seen.at(-1)?.searchParams.get("include_inactive")).toBe("true"));
  expect(router.state.location.search).toContain("inactive=true");
});

test("администратор добавляет позицию и попадает в её карточку", async () => {
  mockSignedIn();
  mockStockLookups();
  mockItems();
  let created: unknown = null;
  server.use(
    http.post("*/api/stock-items", async ({ request }) => {
      created = await request.json();
      return HttpResponse.json(makeStockItem({ id: 202, quantity: 0 }), { status: 201 });
    }),
  );
  const { user, router } = renderApp("/equipment/stock");

  await user.click(await screen.findByRole("button", { name: "Добавить позицию" }));
  const dialog = await screen.findByRole("dialog");
  await user.type(within(dialog).getByLabelText("Наименование"), "Тонер Kyocera");
  await user.click(within(dialog).getByLabelText("Категория"));
  await user.click(await screen.findByRole("option", { name: "Картриджи" }));
  await user.clear(within(dialog).getByLabelText("Единица измерения"));
  await user.type(within(dialog).getByLabelText("Единица измерения"), "шт");
  await user.click(within(dialog).getByLabelText("Склад"));
  await user.click(await screen.findByRole("option", { name: "Офис, каб. 101" }));
  await user.type(within(dialog).getByLabelText("Минимальный остаток"), "2");
  await user.click(within(dialog).getByRole("button", { name: "Добавить" }));

  await waitFor(() => expect(router.state.location.pathname).toBe("/equipment/stock/202"));
  expect(created).toEqual({
    name: "Тонер Kyocera",
    stock_category_id: 3,
    unit: "шт",
    location_id: 6,
    min_quantity: 2,
  });
});

test("добавление: наименование занято — ошибка у поля", async () => {
  mockSignedIn();
  mockStockLookups();
  mockItems();
  server.use(
    http.post("*/api/stock-items", () =>
      HttpResponse.json(
        errorBody("stock_item_name_taken", "На этом складе уже есть позиция с таким наименованием"),
        { status: 409 },
      ),
    ),
  );
  const { user } = renderApp("/equipment/stock");

  await user.click(await screen.findByRole("button", { name: "Добавить позицию" }));
  const dialog = await screen.findByRole("dialog");
  await user.type(within(dialog).getByLabelText("Наименование"), "Картридж HP 85A");
  await user.click(within(dialog).getByLabelText("Категория"));
  await user.click(await screen.findByRole("option", { name: "Картриджи" }));
  await user.click(within(dialog).getByLabelText("Склад"));
  await user.click(await screen.findByRole("option", { name: "Склад" }));
  await user.click(within(dialog).getByRole("button", { name: "Добавить" }));

  expect(
    await within(dialog).findByText("На этом складе уже есть позиция с таким наименованием"),
  ).toBeInTheDocument();
});

test("расходники доступны только администратору", async () => {
  mockSignedIn(makeMe({ role: "manager" }));
  renderApp("/equipment/stock");

  expect(await screen.findByRole("heading", { name: "Нет доступа" })).toBeInTheDocument();
});
```

- [ ] **Step 2: Убедиться, что тесты падают**

Run: `cd frontend && npx vitest run src/features/stock/StockPage.test.tsx`
Expected: FAIL — `Failed Tests 4` — маршрута `/equipment/stock` нет

- [ ] **Step 3: Реализация**

Изменить `frontend/src/app/routes.tsx` (применить дифф):

```diff
@@ -13,6 +13,7 @@ import { AssetPage, AssetsPage, IssuePage } from "../features/assets";
 import { DepartmentsPage } from "../features/departments";
 import { DirectoriesPage } from "../features/directories";
 import { HomePage } from "../features/home";
+import { StockPage } from "../features/stock";
 import { UsersPage } from "../features/users";
 import { BlankLayout } from "../layout/BlankLayout";
 import { FullLayout } from "../layout/FullLayout";
@@ -53,6 +54,7 @@ export const routes: RouteObject[] = [
           {
             element: <RequireRole role="admin" />,
             children: [
+              { path: "/equipment/stock", element: <StockPage /> },
               { path: "/equipment/issue", element: <IssuePage /> },
               { path: "/admin/users", element: <UsersPage /> },
               { path: "/admin/departments", element: <DepartmentsPage /> },
```

Создать `frontend/src/features/stock/StockItemFormDialog.tsx`:

```tsx
import { useSnackbar } from "notistack";
import { useState } from "react";
import { useForm } from "react-hook-form";

import { ApiError } from "../../api/errors";
import { applyApiErrors, fieldByCode } from "../../shared/lib/applyApiErrors";
import { useLocations, useStockCategories } from "../../shared/lookups/directories";
import { FormDialog } from "../../shared/ui/FormDialog";
import { FormSelect } from "../../shared/ui/form/FormSelect";
import { FormSwitch } from "../../shared/ui/form/FormSwitch";
import { FormTextField } from "../../shared/ui/form/FormTextField";
import { useCreateStockItem, useUpdateStockItem } from "./api";
import type { StockItem } from "./labels";

interface StockItemFormValues {
  name: string;
  stock_category_id: number | null;
  unit: string;
  location_id: number | null;
  min_quantity: string;
  is_active: boolean;
}

const FIELDS = ["name", "stock_category_id", "unit", "location_id", "min_quantity"] as const;

const fieldForError = fieldByCode<StockItemFormValues>({
  stock_item_name_taken: "name",
  name_blank: "name",
  unit_blank: "unit",
  category_invalid: "stock_category_id",
  location_invalid: "location_id",
});

const required = { required: "Обязательное поле" };

function toValues(item: StockItem | null): StockItemFormValues {
  return {
    name: item?.name ?? "",
    stock_category_id: item?.stock_category_id ?? null,
    unit: item?.unit ?? "шт",
    location_id: item?.location_id ?? null,
    min_quantity: item && item.min_quantity > 0 ? String(item.min_quantity) : "",
    is_active: item?.is_active ?? true,
  };
}

/** Варианты справочника; деактивированное текущее значение добавляется, чтобы форма его показала. */
function withCurrent(
  items: { id: number; name: string }[] | undefined,
  currentId?: number,
  currentName?: string,
) {
  const options = (items ?? []).map((entry) => ({ value: entry.id, label: entry.name }));
  if (currentId !== undefined && !options.some((option) => option.value === currentId)) {
    options.push({ value: currentId, label: currentName ?? "" });
  }
  return options;
}

interface StockItemFormDialogProps {
  /** Позиция для редактирования; без неё диалог создаёт новую. */
  item: StockItem | null;
  onClose: () => void;
  onSaved?: (item: StockItem) => void;
}

export function StockItemFormDialog({ item, onClose, onSaved }: StockItemFormDialogProps) {
  const { enqueueSnackbar } = useSnackbar();
  const createItem = useCreateStockItem();
  const updateItem = useUpdateStockItem();
  const categories = useStockCategories();
  const locations = useLocations();
  const [formError, setFormError] = useState<string | null>(null);
  const {
    control,
    handleSubmit,
    setError,
    formState: { isSubmitting, dirtyFields },
  } = useForm<StockItemFormValues>({ defaultValues: toValues(item) });

  const onSubmit = handleSubmit(async (values) => {
    setFormError(null);
    const body = {
      name: values.name,
      stock_category_id: values.stock_category_id!,
      unit: values.unit,
      min_quantity: values.min_quantity.trim() === "" ? 0 : Number(values.min_quantity),
    };
    try {
      let saved: StockItem;
      if (item) {
        const changed = Object.fromEntries(
          Object.entries({ ...body, is_active: values.is_active }).filter(
            ([key]) => dirtyFields[key as keyof StockItemFormValues],
          ),
        );
        saved = await updateItem.mutateAsync({
          id: item.id,
          body: { ...changed, version: item.version },
        });
      } else {
        saved = await createItem.mutateAsync({ ...body, location_id: values.location_id! });
      }
      onSaved?.(saved);
      onClose();
    } catch (error) {
      if (error instanceof ApiError && error.code === "version_conflict") {
        enqueueSnackbar(
          "Данные изменил другой пользователь — карточка обновлена, внесите правки заново",
          { variant: "warning" },
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
      title={item ? "Редактирование позиции" : "Новая позиция"}
      submitting={isSubmitting}
      formError={formError}
      onSubmit={onSubmit}
      onClose={onClose}
      submitLabel={item ? "Сохранить" : "Добавить"}
    >
      <FormTextField control={control} name="name" label="Наименование" rules={required} />
      <FormSelect
        control={control}
        name="stock_category_id"
        label="Категория"
        options={withCurrent(categories.data, item?.stock_category_id, item?.category_name)}
        rules={required}
      />
      <FormTextField control={control} name="unit" label="Единица измерения" rules={required} />
      {!item && (
        <FormSelect
          control={control}
          name="location_id"
          label="Склад"
          options={withCurrent(locations.data)}
          rules={required}
        />
      )}
      <FormTextField
        control={control}
        name="min_quantity"
        label="Минимальный остаток"
        helperText="Ниже или равно — позиция подсвечивается. Пусто — без контроля"
        rules={{
          validate: (value) =>
            value.trim() === "" || /^\d{1,7}$/.test(value.trim()) || "Целое число от 0",
        }}
      />
      {item && <FormSwitch control={control} name="is_active" label="Активна" />}
    </FormDialog>
  );
}
```

Создать `frontend/src/features/stock/StockPage.tsx`:

```tsx
import {
  Button,
  FormControlLabel,
  Link as MuiLink,
  Stack,
  Switch,
  Typography,
} from "@mui/material";
import { IconPlus } from "@tabler/icons-react";
import { useState } from "react";
import { Link, useNavigate } from "react-router";

import { booleanParam, idParam, textParam, useUrlFilters } from "../../shared/lib/useUrlFilters";
import { useLocations, useStockCategories } from "../../shared/lookups/directories";
import { DataTable, type Column } from "../../shared/ui/DataTable";
import { FilterBar, FilterSelect, SearchField } from "../../shared/ui/FilterBar";
import { PageContainer } from "../../shared/ui/PageContainer";
import { useStockItems } from "./api";
import type { StockItem } from "./labels";
import { StockItemFormDialog } from "./StockItemFormDialog";
import { StockQuantityChip } from "./StockQuantityChip";

const FILTERS = {
  q: textParam,
  category: idParam,
  location: idParam,
  low: booleanParam,
  inactive: booleanParam,
};

const columns: Column<StockItem>[] = [
  {
    key: "name",
    header: "Наименование",
    render: (item) => (
      <Stack direction="row" spacing={1} sx={{ alignItems: "center" }}>
        <MuiLink component={Link} to={`/equipment/stock/${item.id}`}>
          {item.name}
        </MuiLink>
        {!item.is_active && (
          <Typography variant="body2" color="text.secondary">
            неактивна
          </Typography>
        )}
      </Stack>
    ),
  },
  { key: "category", header: "Категория", render: (item) => item.category_name },
  { key: "location", header: "Склад", render: (item) => item.location_name },
  { key: "quantity", header: "Остаток", render: (item) => <StockQuantityChip item={item} /> },
  {
    key: "min_quantity",
    header: "Минимум",
    render: (item) => (item.min_quantity > 0 ? `${item.min_quantity} ${item.unit}` : "—"),
  },
];

export function StockPage() {
  const navigate = useNavigate();
  const { filters, limit, offset, setFilter, setPage } = useUrlFilters(FILTERS);
  const items = useStockItems({
    q: filters.q,
    categoryId: filters.category,
    locationId: filters.location,
    lowStock: filters.low === true,
    includeInactive: filters.inactive === true,
    limit,
    offset,
  });
  const categories = useStockCategories();
  const locations = useLocations();
  const [creating, setCreating] = useState(false);

  const toggle = (key: "low" | "inactive", label: string) => (
    <FormControlLabel
      label={label}
      control={
        <Switch
          checked={filters[key] === true}
          onChange={(event) => setFilter(key, event.target.checked ? true : null)}
        />
      }
    />
  );

  return (
    <PageContainer
      title="Расходники"
      breadcrumbs={[{ label: "Склад и техника" }, { label: "Расходники" }]}
      actions={
        <Button
          variant="contained"
          startIcon={<IconPlus size={18} />}
          onClick={() => setCreating(true)}
        >
          Добавить позицию
        </Button>
      }
    >
      <FilterBar>
        <SearchField
          value={filters.q}
          onChange={(value) => setFilter("q", value)}
          placeholder="Наименование"
        />
        <FilterSelect
          label="Категория"
          value={filters.category}
          options={(categories.data ?? []).map((item) => ({ value: item.id, label: item.name }))}
          onChange={(value) => setFilter("category", value)}
        />
        <FilterSelect
          label="Склад"
          value={filters.location}
          options={(locations.data ?? []).map((item) => ({ value: item.id, label: item.name }))}
          onChange={(value) => setFilter("location", value)}
        />
        {toggle("low", "Только низкий остаток")}
        {toggle("inactive", "Показать неактивные")}
      </FilterBar>

      <DataTable
        columns={columns}
        rows={items.data?.items}
        getRowId={(item) => item.id}
        loading={items.isLoading}
        error={items.error}
        onRetry={() => void items.refetch()}
        emptyText="Позиции не найдены"
        paging={{ limit, offset, total: items.data?.total ?? 0, onChange: setPage }}
      />

      {creating && (
        <StockItemFormDialog
          item={null}
          onClose={() => setCreating(false)}
          onSaved={(item) => void navigate(`/equipment/stock/${item.id}`)}
        />
      )}
    </PageContainer>
  );
}
```

Создать `frontend/src/features/stock/StockQuantityChip.tsx`:

```tsx
import { Chip } from "@mui/material";

import type { StockItem } from "./labels";

/** Остаток с единицей; ниже минимума — красным. */
export function StockQuantityChip({ item }: { item: StockItem }) {
  return (
    <Chip
      size="small"
      label={`${item.quantity} ${item.unit}`}
      color={item.is_low ? "error" : "default"}
      variant={item.is_low ? "filled" : "outlined"}
    />
  );
}
```

Создать `frontend/src/features/stock/index.ts`:

```ts
export { StockPage } from "./StockPage";
```

Изменить `frontend/src/layout/menu.ts` (применить дифф):

```diff
@@ -4,6 +4,7 @@ import {
   IconBuildingCommunity,
   IconDeviceLaptop,
   IconLayoutDashboard,
+  IconPackage,
   IconUserCircle,
   IconUsers,
 } from "@tabler/icons-react";
@@ -35,6 +36,7 @@ export const MENU: readonly MenuSection[] = [
     title: "Склад и техника",
     items: [
       { label: "Реестр техники", to: "/equipment/assets", icon: IconDeviceLaptop },
+      { label: "Расходники", to: "/equipment/stock", icon: IconPackage, roles: ["admin"] },
       {
         label: "Выдать / принять",
         to: "/equipment/issue",
```

- [ ] **Step 4: Проверить**

Run: `cd frontend && npx vitest run src/features/stock/StockPage.test.tsx src/app/shell.test.tsx`
Expected: `Tests 10 passed`

Run: `cd frontend && npm run format && npm run check`
Expected: `Tests 96 passed`; прогнать `npx vitest run` 5–6 раз подряд — без таймаутов

- [ ] **Step 5: Коммит**

```bash
git add frontend/src/app/routes.tsx frontend/src/app/shell.test.tsx frontend/src/features/assets/IssuePage.test.tsx frontend/src/features/stock/StockItemFormDialog.tsx frontend/src/features/stock/StockPage.test.tsx frontend/src/features/stock/StockPage.tsx frontend/src/features/stock/StockQuantityChip.tsx frontend/src/features/stock/index.ts frontend/src/layout/menu.ts
git commit -m "feat(frontend): страница «Расходники» — остатки, фильтры, добавление позиции"
```

---

### Task 8: Фронтенд: карточка позиции — история, правка, операции

`/equipment/stock/:id`: шапка с остатком, «Низкий остаток» / «Неактивна», вкладки «Информация» и «История», «Редактировать», меню «Действия» (нет у неактивной позиции). Один `StockOperationDialog` на четыре операции; при `item = null` позиция выбирается в диалоге — так работает кнопка «Приход» на странице списка. `insufficient_stock` / `stock_item_inactive` → «Остаток изменился — данные обновлены» и перезагрузка. Дата документа по умолчанию — `localDateIso()` (дата по часам браузера; `toISOString` дал бы дату по UTC).

**Files:**
- Modify: `frontend/src/app/routes.tsx`
- Create: `frontend/src/features/stock/StockHistory.tsx`
- Create: `frontend/src/features/stock/StockItemPage.tsx`
- Create: `frontend/src/features/stock/StockItemPicker.tsx`
- Create: `frontend/src/features/stock/StockOperationDialog.tsx`
- Modify: `frontend/src/features/stock/StockPage.tsx`
- Modify: `frontend/src/features/stock/index.ts`
- Modify: `frontend/src/shared/lib/format.ts`
- Test (create): `frontend/src/features/stock/StockItemPage.test.tsx`
- Test (modify): `frontend/src/shared/lib/format.test.ts`

**Interfaces:**
- Consumes: `useStockItem`, `useStockMovements`, `useStockOperation`, `useStockIssueReasons`, `formatDelta`, `movementDetails` (Task 6); `StockItemFormDialog`, `StockQuantityChip` (Task 7).
- Produces: `StockItemPage`, `StockHistory({itemId, unit})`, `StockOperationDialog({item, operation, onClose})`, `StockItemPicker({label?, value, onChange, onlyAvailable?, excludeIds?, error?})`, `stockItemLabel(item)` («Наименование · Склад · остаток N ед.»); `shared/lib/format.ts` — `localDateIso(date?)`.

- [ ] **Step 1: Написать падающие тесты**

Создать `frontend/src/features/stock/StockItemPage.test.tsx`:

```tsx
import { screen, waitFor, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";

import { renderApp } from "../../test/app";
import { mockSignedIn } from "../../test/auth";
import { makeStockItem, makeStockMovement, page } from "../../test/fixtures";
import { errorBody } from "../../test/http";
import { server } from "../../test/server";
import { localDateIso } from "../../shared/lib/format";
import { mockStockLookups } from "./testing";

function mockCard(item = makeStockItem()) {
  let loads = 0;
  server.use(
    http.get("*/api/stock-items/200", () => {
      loads += 1;
      return HttpResponse.json(item);
    }),
  );
  return { loads: () => loads };
}

function mockOperation(respond: () => Response | Promise<Response>) {
  const bodies: unknown[] = [];
  server.use(
    http.post("*/api/stock-items/200/operations", async ({ request }) => {
      bodies.push(await request.json());
      return respond();
    }),
  );
  return bodies;
}

async function openOperation(user: ReturnType<typeof renderApp>["user"], name: string) {
  await user.click(await screen.findByRole("button", { name: "Действия" }));
  await user.click(screen.getByRole("menuitem", { name }));
  return screen.findByRole("dialog");
}

test("карточка: сведения, низкий остаток и история движений", async () => {
  mockSignedIn();
  mockStockLookups();
  mockCard(makeStockItem({ quantity: 3, is_low: true }));
  server.use(
    http.get("*/api/stock-items/200/movements", () =>
      HttpResponse.json(
        page([
          makeStockMovement({
            id: 2,
            movement_type: "transfer_out",
            delta: -2,
            quantity_after: 3,
            counterpart_location_name: "Офис, каб. 101",
          }),
          makeStockMovement({ id: 1, document_date: "2026-09-01", comment: "Накладная 15" }),
        ]),
      ),
    ),
  );
  const { user } = renderApp("/equipment/stock/200");

  expect(await screen.findByRole("heading", { name: "Картридж HP 85A" })).toBeInTheDocument();
  expect(screen.getByText("Низкий остаток")).toBeInTheDocument();
  expect(screen.getByText("Картриджи")).toBeInTheDocument();

  await user.click(screen.getByRole("tab", { name: "История" }));
  const transfer = (await screen.findByText("Перемещение: отправлено")).closest("tr")!;
  expect(within(transfer).getByText("Куда: Офис, каб. 101")).toBeInTheDocument();
  expect(within(transfer).getByText("−2 шт")).toBeInTheDocument();
  const receipt = screen.getByText("Приход").closest("tr")!;
  expect(within(receipt).getByText("Дата документа: 01.09.2026")).toBeInTheDocument();
  expect(within(receipt).getByText("Накладная 15")).toBeInTheDocument();
});

test("приход: количество и дата документа по умолчанию — сегодня", async () => {
  mockSignedIn();
  mockStockLookups();
  const card = mockCard();
  const bodies = mockOperation(() => HttpResponse.json(makeStockItem({ quantity: 17 })));
  const { user } = renderApp("/equipment/stock/200");

  const dialog = await openOperation(user, "Приход");
  expect(within(dialog).getByLabelText("Дата документа")).toHaveValue(localDateIso());
  await user.type(within(dialog).getByLabelText("Количество, шт"), "5");
  await user.click(within(dialog).getByRole("button", { name: "Приход" }));

  await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
  expect(bodies).toEqual([
    { operation: "receipt", quantity: 5, document_date: localDateIso(), comment: null },
  ]);
  await waitFor(() => expect(card.loads()).toBeGreaterThan(1));
});

test("списание: причина обязательна, количество не больше остатка", async () => {
  mockSignedIn();
  mockStockLookups();
  mockCard();
  const bodies = mockOperation(() => HttpResponse.json(makeStockItem({ quantity: 10 })));
  const { user } = renderApp("/equipment/stock/200");

  const dialog = await openOperation(user, "Списать");
  await user.type(within(dialog).getByLabelText("Количество, шт"), "13");
  await user.click(within(dialog).getByRole("button", { name: "Списать" }));
  expect(within(dialog).getByText("Не больше остатка: 12 шт")).toBeInTheDocument();
  expect(within(dialog).getByText("Обязательное поле")).toBeInTheDocument();

  await user.clear(within(dialog).getByLabelText("Количество, шт"));
  await user.type(within(dialog).getByLabelText("Количество, шт"), "2");
  await user.click(within(dialog).getByLabelText("Причина"));
  const reasons = (await screen.findAllByRole("option")).map((option) => option.textContent);
  expect(reasons).toEqual(["Новый сотрудник", "Брак"]);
  await user.click(screen.getByRole("option", { name: "Брак" }));
  await user.click(within(dialog).getByRole("button", { name: "Списать" }));

  await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
  expect(bodies).toEqual([{ operation: "write_off", quantity: 2, reason_id: 8, comment: null }]);
});

test("операция при изменившемся остатке: уведомление и перезагрузка карточки", async () => {
  mockSignedIn();
  mockStockLookups();
  const card = mockCard();
  mockOperation(() =>
    HttpResponse.json(
      errorBody("insufficient_stock", "Недостаточно остатка", {
        stock_item_id: 200,
        requested: 12,
        available: 1,
      }),
      { status: 409 },
    ),
  );
  const { user } = renderApp("/equipment/stock/200");

  const dialog = await openOperation(user, "Переместить");
  const options = async () => {
    await user.click(within(dialog).getByLabelText("Куда"));
    return (await screen.findAllByRole("option")).map((option) => option.textContent);
  };
  expect(await options()).toEqual(["Офис, каб. 101"]);
  await user.click(screen.getByRole("option", { name: "Офис, каб. 101" }));
  await user.type(within(dialog).getByLabelText("Количество, шт"), "12");
  await user.click(within(dialog).getByRole("button", { name: "Переместить" }));

  expect(await screen.findByText("Остаток изменился — данные обновлены")).toBeInTheDocument();
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  await waitFor(() => expect(card.loads()).toBeGreaterThan(1));
});

test("корректировка: вводится фактический остаток, изменение считается на форме", async () => {
  mockSignedIn();
  mockStockLookups();
  mockCard();
  const bodies = mockOperation(() => HttpResponse.json(makeStockItem({ quantity: 9 })));
  const { user } = renderApp("/equipment/stock/200");

  const dialog = await openOperation(user, "Корректировка");
  expect(within(dialog).getByText("Учётный остаток: 12 шт")).toBeInTheDocument();
  await user.type(within(dialog).getByLabelText("Фактический остаток, шт"), "9");
  expect(within(dialog).getByText("Изменение: −3 шт")).toBeInTheDocument();
  await user.click(within(dialog).getByRole("button", { name: "Корректировка" }));
  expect(within(dialog).getByText("Обязательное поле")).toBeInTheDocument();
  await user.type(within(dialog).getByLabelText("Комментарий"), "Инвентаризация");
  await user.click(within(dialog).getByRole("button", { name: "Корректировка" }));

  await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
  expect(bodies).toEqual([
    { operation: "adjustment", actual_quantity: 9, comment: "Инвентаризация" },
  ]);
});

test("деактивация позиции с остатком: сообщение backend в форме", async () => {
  mockSignedIn();
  mockStockLookups();
  mockCard();
  let body: unknown = null;
  server.use(
    http.patch("*/api/stock-items/200", async ({ request }) => {
      body = await request.json();
      return HttpResponse.json(
        errorBody("stock_not_empty", "Деактивировать можно только позицию с нулевым остатком", {
          quantity: 12,
        }),
        { status: 409 },
      );
    }),
  );
  const { user } = renderApp("/equipment/stock/200");

  await user.click(await screen.findByRole("button", { name: "Редактировать" }));
  const dialog = await screen.findByRole("dialog");
  await user.click(within(dialog).getByLabelText("Активна"));
  await user.click(within(dialog).getByRole("button", { name: "Сохранить" }));

  expect(
    await within(dialog).findByText("Деактивировать можно только позицию с нулевым остатком"),
  ).toBeInTheDocument();
  expect(body).toEqual({ is_active: false, version: 1 });
});

test("у неактивной позиции нет меню «Действия»", async () => {
  mockSignedIn();
  mockStockLookups();
  mockCard(makeStockItem({ is_active: false, quantity: 0 }));
  renderApp("/equipment/stock/200");

  expect(await screen.findByRole("heading", { name: "Картридж HP 85A" })).toBeInTheDocument();
  expect(screen.getByText("Неактивна", { selector: ".MuiChip-label" })).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Действия" })).not.toBeInTheDocument();
});

test("несуществующая позиция — 404", async () => {
  mockSignedIn();
  server.use(
    http.get("*/api/stock-items/999", () =>
      HttpResponse.json(errorBody("stock_item_not_found", "Позиция не найдена"), { status: 404 }),
    ),
  );
  renderApp("/equipment/stock/999");

  expect(await screen.findByRole("heading", { name: "Позиция не найдена" })).toBeInTheDocument();
});

test("приход со страницы списка: позиция выбирается в диалоге", async () => {
  mockSignedIn();
  mockStockLookups();
  const bodies = mockOperation(() => HttpResponse.json(makeStockItem({ quantity: 20 })));
  server.use(
    http.get("*/api/stock-items", () =>
      HttpResponse.json(page([makeStockItem(), makeStockItem({ id: 201, name: "Бумага A4" })])),
    ),
  );
  const { user } = renderApp("/equipment/stock");

  await user.click(await screen.findByRole("button", { name: "Приход" }));
  const dialog = await screen.findByRole("dialog");
  await user.click(within(dialog).getByLabelText("Позиция"));
  await user.click(
    await screen.findByRole("option", { name: "Картридж HP 85A · Склад · остаток 12 шт" }),
  );
  await user.type(within(dialog).getByLabelText("Количество, шт"), "8");
  await user.click(within(dialog).getByRole("button", { name: "Приход" }));

  await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
  expect(bodies).toEqual([
    { operation: "receipt", quantity: 8, document_date: localDateIso(), comment: null },
  ]);
});
```

Изменить `frontend/src/shared/lib/format.test.ts` (применить дифф):

```diff
@@ -1,4 +1,4 @@
-import { formatDate, formatDateTime, initialsOf, ROLE_LABELS } from "./format";
+import { formatDate, formatDateTime, initialsOf, localDateIso, ROLE_LABELS } from "./format";
 
 test("даты форматируются по-русски", () => {
   expect(formatDate("2026-09-17T10:00:00Z")).toBe("17.09.2026");
@@ -9,3 +9,7 @@ test("названия ролей и инициалы", () => {
   expect(ROLE_LABELS.manager).toBe("Руководитель");
   expect(initialsOf("Иванов  Пётр Сергеевич")).toBe("ИП");
 });
+
+test("локальная дата в формате ISO", () => {
+  expect(localDateIso(new Date(2026, 8, 5, 23, 30))).toBe("2026-09-05");
+});
```

- [ ] **Step 2: Убедиться, что тесты падают**

Run: `cd frontend && npx vitest run src/features/stock/StockItemPage.test.tsx src/shared/lib/format.test.ts`
Expected: FAIL — `Failed Tests 10`

- [ ] **Step 3: Реализация**

Изменить `frontend/src/app/routes.tsx` (применить дифф):

```diff
@@ -13,7 +13,7 @@ import { AssetPage, AssetsPage, IssuePage } from "../features/assets";
 import { DepartmentsPage } from "../features/departments";
 import { DirectoriesPage } from "../features/directories";
 import { HomePage } from "../features/home";
-import { StockPage } from "../features/stock";
+import { StockItemPage, StockPage } from "../features/stock";
 import { UsersPage } from "../features/users";
 import { BlankLayout } from "../layout/BlankLayout";
 import { FullLayout } from "../layout/FullLayout";
@@ -55,6 +55,7 @@ export const routes: RouteObject[] = [
             element: <RequireRole role="admin" />,
             children: [
               { path: "/equipment/stock", element: <StockPage /> },
+              { path: "/equipment/stock/:id", element: <StockItemPage /> },
               { path: "/equipment/issue", element: <IssuePage /> },
               { path: "/admin/users", element: <UsersPage /> },
               { path: "/admin/departments", element: <DepartmentsPage /> },
```

Создать `frontend/src/features/stock/StockHistory.tsx`:

```tsx
import { Box, Stack, Typography } from "@mui/material";
import { useState } from "react";

import { formatDateTime } from "../../shared/lib/format";
import { DataTable, type Column } from "../../shared/ui/DataTable";
import { useStockMovements } from "./api";
import { formatDelta, movementDetails, movementTitle, type StockMovement } from "./labels";

const PAGE_SIZE = 25;

export function StockHistory({ itemId, unit }: { itemId: number; unit: string }) {
  const [offset, setOffset] = useState(0);
  const movements = useStockMovements(itemId, PAGE_SIZE, offset);
  const columns: Column<StockMovement>[] = [
    {
      key: "created_at",
      header: "Когда",
      width: 160,
      render: (movement) => formatDateTime(movement.created_at),
    },
    {
      key: "movement",
      header: "Операция",
      render: (movement) => (
        <Stack spacing={0.5}>
          <Typography sx={{ fontWeight: 600 }}>{movementTitle(movement.movement_type)}</Typography>
          {movementDetails(movement).map((line) => (
            <Typography key={line} variant="body2" color="text.secondary">
              {line}
            </Typography>
          ))}
          {movement.comment && (
            <Box component="q" sx={{ typography: "body2" }}>
              {movement.comment}
            </Box>
          )}
        </Stack>
      ),
    },
    {
      key: "delta",
      header: "Изменение",
      render: (movement) => formatDelta(movement.delta, unit),
    },
    {
      key: "quantity_after",
      header: "Остаток после",
      render: (movement) => `${movement.quantity_after} ${unit}`,
    },
    { key: "performed_by", header: "Кто", render: (movement) => movement.performed_by_name },
  ];
  return (
    <DataTable
      columns={columns}
      rows={movements.data?.items}
      getRowId={(movement) => movement.id}
      loading={movements.isLoading}
      error={movements.error}
      onRetry={() => void movements.refetch()}
      emptyText="Движений нет"
      paging={{
        limit: PAGE_SIZE,
        offset,
        total: movements.data?.total ?? 0,
        onChange: (nextOffset) => setOffset(nextOffset),
      }}
    />
  );
}
```

Создать `frontend/src/features/stock/StockItemPage.tsx`:

```tsx
import {
  Alert,
  Button,
  Card,
  CardContent,
  Chip,
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
import { FullScreenLoader } from "../../shared/ui/FullScreenLoader";
import { PageContainer } from "../../shared/ui/PageContainer";
import { StatusPage } from "../../shared/ui/StatusPage";
import { useStockItem } from "./api";
import {
  STOCK_OPERATION_LABELS,
  STOCK_OPERATIONS,
  type StockItem,
  type StockOperation,
} from "./labels";
import { StockHistory } from "./StockHistory";
import { StockItemFormDialog } from "./StockItemFormDialog";
import { StockOperationDialog } from "./StockOperationDialog";
import { StockQuantityChip } from "./StockQuantityChip";

function StockItemNotFound() {
  return <StatusPage code={404} title="Позиция не найдена" text="Возможно, ссылка устарела." />;
}

export function StockItemPage() {
  const { id } = useParams();
  const itemId = Number(id);
  if (!Number.isInteger(itemId) || itemId <= 0) return <StockItemNotFound />;
  return <StockItemScreen key={itemId} itemId={itemId} />;
}

function StockItemScreen({ itemId }: { itemId: number }) {
  const item = useStockItem(itemId);
  if (item.isLoading) return <FullScreenLoader />;
  if (item.error) {
    if (item.error instanceof ApiError && item.error.status === 404) return <StockItemNotFound />;
    return (
      <Alert severity="error">
        {item.error instanceof ApiError ? item.error.message : UNKNOWN_ERROR_MESSAGE}
      </Alert>
    );
  }
  return item.data ? <StockItemCard item={item.data} /> : null;
}

function StockItemCard({ item }: { item: StockItem }) {
  const [tab, setTab] = useState<"info" | "history">("info");
  const [editing, setEditing] = useState(false);
  const [operation, setOperation] = useState<StockOperation | null>(null);
  const [menuAnchor, setMenuAnchor] = useState<HTMLElement | null>(null);

  return (
    <PageContainer
      title={item.name}
      breadcrumbs={[
        { label: "Склад и техника" },
        { label: "Расходники", to: "/equipment/stock" },
        { label: item.name },
      ]}
      actions={
        <>
          <Button
            variant="outlined"
            startIcon={<IconPencil size={18} />}
            onClick={() => setEditing(true)}
          >
            Редактировать
          </Button>
          {item.is_active && (
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
            {STOCK_OPERATIONS.map((item) => (
              <MenuItem
                key={item}
                onClick={() => {
                  setMenuAnchor(null);
                  setOperation(item);
                }}
              >
                {STOCK_OPERATION_LABELS[item]}
              </MenuItem>
            ))}
          </Menu>
        </>
      }
    >
      <Stack direction="row" spacing={1} sx={{ mb: 2, alignItems: "center" }}>
        <StockQuantityChip item={item} />
        {item.is_low && <Typography color="error.main">Низкий остаток</Typography>}
        {!item.is_active && <Chip size="small" label="Неактивна" />}
      </Stack>
      <Tabs value={tab} onChange={(_, value: "info" | "history") => setTab(value)} sx={{ mb: 2 }}>
        <Tab value="info" label="Информация" />
        <Tab value="history" label="История" />
      </Tabs>
      {tab === "info" ? (
        <StockItemInfo item={item} />
      ) : (
        <StockHistory itemId={item.id} unit={item.unit} />
      )}

      {editing && <StockItemFormDialog item={item} onClose={() => setEditing(false)} />}
      {operation && (
        <StockOperationDialog
          item={item}
          operation={operation}
          onClose={() => setOperation(null)}
        />
      )}
    </PageContainer>
  );
}

function StockItemInfo({ item }: { item: StockItem }) {
  const rows: [string, ReactNode][] = [
    ["Категория", item.category_name],
    ["Склад", item.location_name],
    ["Единица измерения", item.unit],
    ["Остаток", `${item.quantity} ${item.unit}`],
    ["Минимальный остаток", item.min_quantity > 0 ? `${item.min_quantity} ${item.unit}` : "—"],
    ["Статус", item.is_active ? "Активна" : "Неактивна"],
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

Создать `frontend/src/features/stock/StockItemPicker.tsx`:

```tsx
import { Autocomplete, TextField } from "@mui/material";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { useDebouncedValue } from "../../shared/lib/useDebouncedValue";
import { queryKeys } from "../../shared/lookups/queryKeys";
import { fetchStockItems } from "./api";
import type { StockItem } from "./labels";

export const stockItemLabel = (item: StockItem) =>
  `${item.name} · ${item.location_name} · остаток ${item.quantity} ${item.unit}`;

interface StockItemPickerProps {
  label?: string;
  value: StockItem | null;
  onChange: (item: StockItem | null) => void;
  /** Только позиции с остатком > 0 (для выдачи). */
  onlyAvailable?: boolean;
  /** Уже выбранные в других строках позиции — не предлагаются. */
  excludeIds?: ReadonlySet<number>;
  error?: string;
}

/** Выбор активной позиции расходников с поиском на сервере. */
export function StockItemPicker({
  label = "Позиция",
  value,
  onChange,
  onlyAvailable = false,
  excludeIds,
  error,
}: StockItemPickerProps) {
  const [open, setOpen] = useState(false);
  const [input, setInput] = useState("");
  const query = useDebouncedValue(input);
  const options = useQuery({
    queryKey: [...queryKeys.stock, "picker-options", query],
    queryFn: () => fetchStockItems({ q: query, limit: 50, offset: 0 }),
    enabled: open,
  });
  const items = (options.data?.items ?? []).filter(
    (item) => (!onlyAvailable || item.quantity > 0) && !excludeIds?.has(item.id),
  );

  return (
    <Autocomplete<StockItem>
      open={open}
      onOpen={() => setOpen(true)}
      onClose={() => setOpen(false)}
      value={value}
      options={items}
      loading={options.isFetching}
      filterOptions={(list) => list}
      isOptionEqualToValue={(option, current) => option.id === current.id}
      getOptionLabel={stockItemLabel}
      onChange={(_, item) => onChange(item)}
      onInputChange={(_, text, reason) => {
        if (reason === "input") setInput(text);
        if (reason === "clear" || reason === "reset") setInput("");
      }}
      noOptionsText={onlyAvailable ? "Нет позиций с остатком" : "Ничего не найдено"}
      loadingText="Загрузка…"
      renderInput={(params) => (
        <TextField {...params} label={label} error={Boolean(error)} helperText={error} />
      )}
    />
  );
}
```

Создать `frontend/src/features/stock/StockOperationDialog.tsx`:

```tsx
import { Typography } from "@mui/material";
import { useSnackbar } from "notistack";
import { useState } from "react";
import { Controller, useForm } from "react-hook-form";

import { ApiError } from "../../api/errors";
import { applyApiErrors, fieldByCode } from "../../shared/lib/applyApiErrors";
import { localDateIso } from "../../shared/lib/format";
import { useLocations, useStockIssueReasons } from "../../shared/lookups/directories";
import { FormDialog } from "../../shared/ui/FormDialog";
import { FormSelect } from "../../shared/ui/form/FormSelect";
import { FormTextField } from "../../shared/ui/form/FormTextField";
import { useStockOperation, type StockOperationBody } from "./api";
import { formatDelta, STOCK_OPERATION_LABELS, type StockItem, type StockOperation } from "./labels";
import { StockItemPicker } from "./StockItemPicker";

interface OperationFormValues {
  item: StockItem | null;
  quantity: string;
  actual_quantity: string;
  document_date: string;
  reason_id: number | null;
  to_location_id: number | null;
  comment: string;
}

const fieldForError = fieldByCode<OperationFormValues>({
  document_date_in_future: "document_date",
  reason_required: "reason_id",
  reason_invalid: "reason_id",
  comment_required: "comment",
  adjustment_no_change: "actual_quantity",
  same_location: "to_location_id",
  location_invalid: "to_location_id",
});

const FIELDS = [
  "quantity",
  "actual_quantity",
  "document_date",
  "reason_id",
  "to_location_id",
  "comment",
] as const;

const required = { required: "Обязательное поле" };
const INTEGER = /^\d{1,7}$/;

function buildBody(operation: StockOperation, values: OperationFormValues): StockOperationBody {
  const comment = values.comment.trim() || null;
  const quantity = Number(values.quantity);
  switch (operation) {
    case "receipt":
      return { operation, quantity, document_date: values.document_date || null, comment };
    case "write_off":
      return { operation, quantity, reason_id: values.reason_id, comment };
    case "adjustment":
      return { operation, actual_quantity: Number(values.actual_quantity), comment };
    case "transfer":
      return { operation, quantity, to_location_id: values.to_location_id!, comment };
  }
}

interface StockOperationDialogProps {
  /** Позиция; null — выбирается в диалоге (приход со страницы списка). */
  item: StockItem | null;
  operation: StockOperation;
  onClose: () => void;
}

export function StockOperationDialog({ item, operation, onClose }: StockOperationDialogProps) {
  const { enqueueSnackbar } = useSnackbar();
  const mutation = useStockOperation();
  const reasons = useStockIssueReasons();
  const locations = useLocations();
  const [formError, setFormError] = useState<string | null>(null);
  const {
    control,
    handleSubmit,
    setError,
    watch,
    formState: { isSubmitting },
  } = useForm<OperationFormValues>({
    defaultValues: {
      item,
      quantity: "",
      actual_quantity: "",
      document_date: localDateIso(),
      reason_id: null,
      to_location_id: null,
      comment: "",
    },
  });
  const current = watch("item");
  const unit = current?.unit ?? "шт";
  const actual = watch("actual_quantity");
  const label = STOCK_OPERATION_LABELS[operation];
  const outgoing = operation === "write_off" || operation === "transfer";

  const onSubmit = handleSubmit(async (values) => {
    setFormError(null);
    try {
      await mutation.mutateAsync({ id: values.item!.id, body: buildBody(operation, values) });
      enqueueSnackbar(`${label}: готово`, { variant: "success" });
      onClose();
    } catch (error) {
      if (
        error instanceof ApiError &&
        (error.code === "insufficient_stock" || error.code === "stock_item_inactive")
      ) {
        enqueueSnackbar("Остаток изменился — данные обновлены", { variant: "warning" });
        onClose();
        return;
      }
      setFormError(applyApiErrors(error, setError, { fields: FIELDS, fieldForError }));
    }
  });

  return (
    <FormDialog
      open
      title={item ? `${label}: ${item.name}` : label}
      submitting={isSubmitting}
      formError={formError}
      onSubmit={onSubmit}
      onClose={onClose}
      submitLabel={label}
    >
      {!item && (
        <Controller
          control={control}
          name="item"
          rules={{ required: "Выберите позицию" }}
          render={({ field, fieldState }) => (
            <StockItemPicker
              value={field.value}
              onChange={field.onChange}
              error={fieldState.error?.message}
            />
          )}
        />
      )}
      {operation === "adjustment" ? (
        <>
          {current && (
            <Typography color="text.secondary">
              Учётный остаток: {current.quantity} {unit}
            </Typography>
          )}
          <FormTextField
            control={control}
            name="actual_quantity"
            label={`Фактический остаток, ${unit}`}
            rules={{
              required: "Обязательное поле",
              validate: (value) => INTEGER.test(value.trim()) || "Целое число от 0",
            }}
          />
          {current && INTEGER.test(actual.trim()) && Number(actual) !== current.quantity && (
            <Typography>
              Изменение: {formatDelta(Number(actual) - current.quantity, unit)}
            </Typography>
          )}
        </>
      ) : (
        <FormTextField
          control={control}
          name="quantity"
          label={`Количество, ${unit}`}
          rules={{
            required: "Обязательное поле",
            validate: (value) => {
              if (!INTEGER.test(value.trim()) || Number(value) < 1) return "Целое число от 1";
              if (outgoing && current && Number(value) > current.quantity) {
                return `Не больше остатка: ${current.quantity} ${unit}`;
              }
              return true;
            },
          }}
        />
      )}
      {operation === "receipt" && (
        <FormTextField
          control={control}
          name="document_date"
          label="Дата документа"
          type="date"
          rules={required}
          slotProps={{ inputLabel: { shrink: true }, htmlInput: { max: localDateIso() } }}
        />
      )}
      {operation === "write_off" && (
        <FormSelect
          control={control}
          name="reason_id"
          label="Причина"
          options={(reasons.data ?? []).map((reason) => ({ value: reason.id, label: reason.name }))}
          rules={required}
        />
      )}
      {operation === "transfer" && (
        <FormSelect
          control={control}
          name="to_location_id"
          label="Куда"
          options={(locations.data ?? [])
            .filter((location) => location.id !== current?.location_id)
            .map((location) => ({ value: location.id, label: location.name }))}
          rules={required}
        />
      )}
      <FormTextField
        control={control}
        name="comment"
        label="Комментарий"
        multiline
        minRows={2}
        rules={operation === "adjustment" ? required : undefined}
      />
    </FormDialog>
  );
}
```

Изменить `frontend/src/features/stock/StockPage.tsx` (применить дифф):

```diff
@@ -18,6 +18,7 @@ import { PageContainer } from "../../shared/ui/PageContainer";
 import { useStockItems } from "./api";
 import type { StockItem } from "./labels";
 import { StockItemFormDialog } from "./StockItemFormDialog";
+import { StockOperationDialog } from "./StockOperationDialog";
 import { StockQuantityChip } from "./StockQuantityChip";
 
 const FILTERS = {
@@ -70,6 +71,7 @@ export function StockPage() {
   const categories = useStockCategories();
   const locations = useLocations();
   const [creating, setCreating] = useState(false);
+  const [receiving, setReceiving] = useState(false);
 
   const toggle = (key: "low" | "inactive", label: string) => (
     <FormControlLabel
@@ -88,13 +90,18 @@ export function StockPage() {
       title="Расходники"
       breadcrumbs={[{ label: "Склад и техника" }, { label: "Расходники" }]}
       actions={
-        <Button
-          variant="contained"
-          startIcon={<IconPlus size={18} />}
-          onClick={() => setCreating(true)}
-        >
-          Добавить позицию
-        </Button>
+        <>
+          <Button variant="outlined" onClick={() => setReceiving(true)}>
+            Приход
+          </Button>
+          <Button
+            variant="contained"
+            startIcon={<IconPlus size={18} />}
+            onClick={() => setCreating(true)}
+          >
+            Добавить позицию
+          </Button>
+        </>
       }
     >
       <FilterBar>
@@ -137,6 +144,9 @@ export function StockPage() {
           onSaved={(item) => void navigate(`/equipment/stock/${item.id}`)}
         />
       )}
+      {receiving && (
+        <StockOperationDialog item={null} operation="receipt" onClose={() => setReceiving(false)} />
+      )}
     </PageContainer>
   );
 }
```

Изменить `frontend/src/features/stock/index.ts` (применить дифф):

```diff
@@ -1 +1,2 @@
+export { StockItemPage } from "./StockItemPage";
 export { StockPage } from "./StockPage";
```

Изменить `frontend/src/shared/lib/format.ts` (применить дифф):

```diff
@@ -31,3 +31,9 @@ export function initialsOf(fullName: string): string {
     .map((part) => part[0]?.toUpperCase() ?? "")
     .join("");
 }
+
+/** Дата «YYYY-MM-DD» по часам браузера (toISOString дал бы дату по UTC). */
+export function localDateIso(date: Date = new Date()): string {
+  const pad = (value: number) => String(value).padStart(2, "0");
+  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
+}
```

- [ ] **Step 4: Проверить**

Run: `cd frontend && npx vitest run src/features/stock src/shared/lib/format.test.ts`
Expected: `Tests 19 passed`

Run: `cd frontend && npm run format && npm run check`
Expected: `Tests 106 passed`

- [ ] **Step 5: Коммит**

```bash
git add frontend/src/app/routes.tsx frontend/src/features/stock/StockHistory.tsx frontend/src/features/stock/StockItemPage.test.tsx frontend/src/features/stock/StockItemPage.tsx frontend/src/features/stock/StockItemPicker.tsx frontend/src/features/stock/StockOperationDialog.tsx frontend/src/features/stock/StockPage.tsx frontend/src/features/stock/index.ts frontend/src/shared/lib/format.test.ts frontend/src/shared/lib/format.ts
git commit -m "feat(frontend): карточка позиции — история, правка, приход, списание, корректировка, перемещение"
```

---

### Task 9: Фронтенд: «Выдать» — техника и расходники одной операцией

Блок «Выдать» получает строки «позиция + количество» (`StockLinesField`, до 50 строк): в выборе — только активные позиции с остатком, уже выбранные в других строках исключены, количество больше остатка не отправляется. Причины фильтруются по составу выдачи (пустая выдача — как техника), неподходящая причина сбрасывается при смене состава. При 409 `checkout_unavailable` подсвечиваются и активы, и строки («На складе осталось N»).

**Files:**
- Modify: `frontend/src/features/assets/IssuePage.tsx`
- Create: `frontend/src/features/stock/StockLinesField.tsx`
- Modify: `frontend/src/features/stock/index.ts`
- Test (modify): `frontend/src/features/assets/IssuePage.test.tsx`

**Interfaces:**
- Consumes: `StockItemPicker` (Task 8), `useCheckout` (Task 4), `useIssueReasons`, `reasonFits` (Task 6).
- Produces: `features/stock/index.ts` — `StockLinesField({value, onChange, unavailable, showErrors, maxLines})`, `stockLineError(line)`, тип `StockLineValue {key, item, quantity}`.

- [ ] **Step 1: Написать падающие тесты**

Изменить `frontend/src/features/assets/IssuePage.test.tsx` (применить дифф):

```diff
@@ -3,7 +3,7 @@ import { http, HttpResponse } from "msw";
 
 import { renderApp } from "../../test/app";
 import { makeMe, mockSignedIn } from "../../test/auth";
-import { makeAsset, page } from "../../test/fixtures";
+import { makeAsset, makeStockItem, page } from "../../test/fixtures";
 import { errorBody } from "../../test/http";
 import { server } from "../../test/server";
 import { mockAssetLookups } from "./testing";
@@ -53,7 +53,7 @@ test("выдача: при 409 недоступная техника подсв
   await user.click(await screen.findByRole("option", { name: "INV-002 — Dell Latitude" }));
   await user.click(within(section).getByRole("button", { name: "Выдать" }));
 
-  expect(await within(section).findByText(/выделена красным/)).toBeInTheDocument();
+  expect(await within(section).findByText(/выделены красным/)).toBeInTheDocument();
   expect(body).toEqual({
     recipient_id: 10,
     asset_ids: [100, 101],
@@ -88,6 +88,129 @@ test("выдача: 422 recipient_invalid показывает ошибку у 
   expect(within(section).queryByRole("alert")).not.toBeInTheDocument();
 });
 
+function mockStockOptions() {
+  server.use(
+    http.get("*/api/stock-items", () =>
+      HttpResponse.json(
+        page([
+          makeStockItem(),
+          makeStockItem({ id: 201, name: "Бумага A4", unit: "пачка", quantity: 0 }),
+        ]),
+      ),
+    ),
+  );
+}
+
+async function addStockLine(
+  user: ReturnType<typeof renderApp>["user"],
+  section: HTMLElement,
+  quantity: string,
+) {
+  await user.click(within(section).getByRole("button", { name: "Добавить расходник" }));
+  const pickers = within(section).getAllByLabelText("Расходник");
+  await user.click(pickers.at(-1)!);
+  await user.click(
+    await screen.findByRole("option", { name: "Картридж HP 85A · Склад · остаток 12 шт" }),
+  );
+  const quantities = within(section).getAllByLabelText("Количество");
+  await user.type(quantities.at(-1)!, quantity);
+}
+
+test("выдача техники и расходников одной отправкой; причины — только общие", async () => {
+  mockSignedIn();
+  mockAssetLookups();
+  mockStockOptions();
+  let body: unknown = null;
+  server.use(
+    http.get("*/api/assets", () => HttpResponse.json(page(FREE))),
+    http.post("*/api/equipment/checkout", async ({ request }) => {
+      body = await request.json();
+      return HttpResponse.json({
+        assets: [makeAsset({ id: 100, status: "in_use" })],
+        stock_items: [makeStockItem({ quantity: 10 })],
+      });
+    }),
+  );
+  const { user } = renderApp("/equipment/issue");
+
+  const section = await screen.findByRole("region", { name: "Выдать" });
+  await pickEmployee(user, section, "Кому");
+  await user.click(within(section).getByLabelText("Техника"));
+  await user.click(await screen.findByRole("option", { name: "INV-001 — Lenovo ThinkPad T14" }));
+  await addStockLine(user, section, "2");
+  await user.click(within(section).getByLabelText("Причина"));
+  const reasons = (await screen.findAllByRole("option")).map((option) => option.textContent);
+  expect(reasons).toEqual(["Не указана", "Новый сотрудник"]);
+  await user.click(screen.getByRole("option", { name: "Новый сотрудник" }));
+  await user.click(within(section).getByRole("button", { name: "Выдать" }));
+
+  expect(await screen.findByText("Выдано позиций: 2")).toBeInTheDocument();
+  expect(body).toEqual({
+    recipient_id: 10,
+    asset_ids: [100],
+    stock_lines: [{ stock_item_id: 200, quantity: 2 }],
+    reason_id: 7,
+    comment: null,
+  });
+});
+
+test("расходники: количество больше остатка не отправляется, позиции без остатка не предлагаются", async () => {
+  mockSignedIn();
+  mockAssetLookups();
+  mockStockOptions();
+  let posted = false;
+  server.use(
+    http.post("*/api/equipment/checkout", () => {
+      posted = true;
+      return HttpResponse.json({ assets: [], stock_items: [] });
+    }),
+  );
+  const { user } = renderApp("/equipment/issue");
+
+  const section = await screen.findByRole("region", { name: "Выдать" });
+  await pickEmployee(user, section, "Кому");
+  await user.click(within(section).getByRole("button", { name: "Добавить расходник" }));
+  await user.click(within(section).getByLabelText("Расходник"));
+  expect(await screen.findByRole("option", { name: /Картридж HP 85A/ })).toBeInTheDocument();
+  expect(screen.queryByRole("option", { name: /Бумага A4/ })).not.toBeInTheDocument();
+  await user.click(screen.getByRole("option", { name: /Картридж HP 85A/ }));
+  await user.type(within(section).getByLabelText("Количество"), "13");
+  await user.click(within(section).getByRole("button", { name: "Выдать" }));
+
+  expect(await within(section).findByText("Доступно 12 шт")).toBeInTheDocument();
+  expect(posted).toBe(false);
+});
+
+test("расходники: при 409 у строки показывается остаток на сервере", async () => {
+  mockSignedIn();
+  mockAssetLookups();
+  mockStockOptions();
+  server.use(
+    http.post("*/api/equipment/checkout", () =>
+      HttpResponse.json(
+        errorBody("checkout_unavailable", "Часть недоступна", {
+          assets: [],
+          stock: [{ stock_item_id: 200, name: "Картридж HP 85A", requested: 5, available: 1 }],
+        }),
+        { status: 409 },
+      ),
+    ),
+  );
+  const { user } = renderApp("/equipment/issue");
+
+  const section = await screen.findByRole("region", { name: "Выдать" });
+  await pickEmployee(user, section, "Кому");
+  await addStockLine(user, section, "5");
+  await user.click(within(section).getByLabelText("Причина"));
+  const reasons = (await screen.findAllByRole("option")).map((option) => option.textContent);
+  expect(reasons).toEqual(["Не указана", "Новый сотрудник", "Заправка"]);
+  await user.keyboard("{Escape}");
+  await user.click(within(section).getByRole("button", { name: "Выдать" }));
+
+  expect(await within(section).findByText(/выделены красным/)).toBeInTheDocument();
+  expect(within(section).getByText("На складе осталось 1 шт")).toBeInTheDocument();
+});
+
 test("выдача без сотрудника и техники подсказывает поля и не отправляет запрос", async () => {
   mockSignedIn();
   mockAssetLookups();
@@ -97,7 +220,7 @@ test("выдача без сотрудника и техники подсказ
   await user.click(within(section).getByRole("button", { name: "Выдать" }));
 
   expect(within(section).getByText("Выберите сотрудника")).toBeInTheDocument();
-  expect(within(section).getByText("Выберите технику")).toBeInTheDocument();
+  expect(within(section).getByText("Выберите технику или расходники")).toBeInTheDocument();
 });
 
 test("приём: техника сотрудника в работе, отмеченное уходит на склад", async () => {
```

- [ ] **Step 2: Убедиться, что тесты падают**

Run: `cd frontend && npx vitest run src/features/assets/IssuePage.test.tsx`
Expected: FAIL — `Failed Tests 5` — нет кнопки «Добавить расходник», старые тексты

- [ ] **Step 3: Реализация**

Изменить `frontend/src/features/assets/IssuePage.tsx` (применить дифф):

```diff
@@ -12,9 +12,15 @@ import { useSnackbar } from "notistack";
 import { useState } from "react";
 import { Controller, useForm } from "react-hook-form";
 
+import { StockLinesField, stockLineError, type StockLineValue } from "../stock";
 import { ApiError, UNKNOWN_ERROR_MESSAGE } from "../../api/errors";
 import { applyApiErrors, fieldByCode } from "../../shared/lib/applyApiErrors";
-import { useAssetIssueReasons, useLocations } from "../../shared/lookups/directories";
+import {
+  reasonFits,
+  useIssueReasons,
+  useLocations,
+  type ReasonScope,
+} from "../../shared/lookups/directories";
 import {
   ACTIVE_USER_OPTIONS_KEY,
   searchActiveUserOptions,
@@ -32,20 +38,37 @@ import type { Asset } from "./labels";
 const errorMessage = (error: unknown) =>
   error instanceof ApiError ? error.message : UNKNOWN_ERROR_MESSAGE;
 
-/** Backend принимает 1..50 asset_ids за раз (issue/return). */
+/** Backend принимает до 50 активов и до 50 строк расходников за раз (checkout/return). */
 const MAX_BULK_SELECTION = 50;
 const BULK_LIMIT_MESSAGE = `Не больше ${MAX_BULK_SELECTION} единиц за раз`;
 
 /** details ошибки checkout_unavailable (backend: CheckoutUnavailable). */
 interface CheckoutUnavailable {
   assets: { asset_id: number }[];
+  stock: { stock_item_id: number; available: number | null }[];
+}
+
+interface Unavailable {
+  assets: ReadonlySet<number>;
+  /** id позиции → остаток на сервере (null — позиция не найдена). */
+  stock: ReadonlyMap<number, number | null>;
 }
 
-/** id активов из details ошибки checkout_unavailable. */
-function unavailableOf(error: unknown): Set<number> {
-  if (!(error instanceof ApiError) || error.code !== "checkout_unavailable") return new Set();
+const NOTHING_UNAVAILABLE: Unavailable = { assets: new Set(), stock: new Map() };
+
+/** Недоступные активы и строки расходников из details ошибки checkout_unavailable. */
+function unavailableOf(error: ApiError): Unavailable {
   const details = error.details as CheckoutUnavailable | null;
-  return new Set((details?.assets ?? []).map((item) => item.asset_id));
+  return {
+    assets: new Set((details?.assets ?? []).map((item) => item.asset_id)),
+    stock: new Map((details?.stock ?? []).map((line) => [line.stock_item_id, line.available])),
+  };
+}
+
+/** Состав выдачи для фильтра причин; пустая выдача — как техника (прежнее поведение формы). */
+function scopeOf(assets: Asset[], lines: StockLineValue[]): ReasonScope {
+  const stock = lines.length > 0;
+  return { assets: assets.length > 0 || !stock, stock };
 }
 
 export function IssuePage() {
@@ -65,6 +88,7 @@ export function IssuePage() {
 interface IssueFormValues {
   owner_id: number | null;
   asset_ids: Asset[];
+  stock_lines: StockLineValue[];
   reason_id: number | null;
   comment: string;
 }
@@ -78,19 +102,34 @@ const issueFieldForError = fieldByCode<IssueFormValues>({
 function IssueSection() {
   const { enqueueSnackbar } = useSnackbar();
   const { nameOf } = useUserNames();
-  const reasons = useAssetIssueReasons();
+  const reasons = useIssueReasons();
   const issue = useCheckout();
-  const [unavailable, setUnavailable] = useState<ReadonlySet<number>>(new Set());
+  const [unavailable, setUnavailable] = useState<Unavailable>(NOTHING_UNAVAILABLE);
   const [formError, setFormError] = useState<string | null>(null);
   const {
     control,
     handleSubmit,
     setError,
+    setValue,
+    getValues,
+    watch,
     reset,
-    formState: { isSubmitting },
+    formState: { isSubmitting, submitCount },
   } = useForm<IssueFormValues>({
-    defaultValues: { owner_id: null, asset_ids: [], reason_id: null, comment: "" },
+    defaultValues: { owner_id: null, asset_ids: [], stock_lines: [], reason_id: null, comment: "" },
   });
+  const scope = scopeOf(watch("asset_ids"), watch("stock_lines"));
+  const reasonOptions = (reasons.data ?? []).filter((reason) =>
+    reasonFits(reason.applicability, scope),
+  );
+
+  /** После смены состава выдачи сбрасывает причину, которая к нему больше не подходит. */
+  const dropUnfitReason = (assets: Asset[], lines: StockLineValue[]) => {
+    const reason = reasons.data?.find((item) => item.id === getValues("reason_id"));
+    if (reason && !reasonFits(reason.applicability, scopeOf(assets, lines))) {
+      setValue("reason_id", null);
+    }
+  };
 
   const submit = handleSubmit(async (values) => {
     setFormError(null);
@@ -98,18 +137,29 @@ function IssueSection() {
       const issued = await issue.mutateAsync({
         recipient_id: values.owner_id!,
         asset_ids: values.asset_ids.map((asset) => asset.id),
-        stock_lines: [],
+        stock_lines: values.stock_lines.map((line) => ({
+          stock_item_id: line.item!.id,
+          quantity: Number(line.quantity),
+        })),
         reason_id: values.reason_id,
         comment: values.comment.trim() || null,
       });
-      enqueueSnackbar(`Выдано: ${issued.assets.length}`, { variant: "success" });
-      reset({ owner_id: values.owner_id, asset_ids: [], reason_id: null, comment: "" });
-      setUnavailable(new Set());
+      enqueueSnackbar(`Выдано позиций: ${issued.assets.length + issued.stock_items.length}`, {
+        variant: "success",
+      });
+      reset({
+        owner_id: values.owner_id,
+        asset_ids: [],
+        stock_lines: [],
+        reason_id: null,
+        comment: "",
+      });
+      setUnavailable(NOTHING_UNAVAILABLE);
     } catch (caught) {
       if (caught instanceof ApiError && caught.code === "checkout_unavailable") {
         setUnavailable(unavailableOf(caught));
         setFormError(
-          "Часть техники уже недоступна — она выделена красным. Уберите её и повторите.",
+          "Часть техники или расходников уже недоступна — они выделены красным. Исправьте и повторите.",
         );
         return;
       }
@@ -142,7 +192,12 @@ function IssueSection() {
           <Controller
             control={control}
             name="asset_ids"
-            rules={{ validate: (value) => value.length > 0 || "Выберите технику" }}
+            rules={{
+              validate: (value, form) =>
+                value.length > 0 ||
+                form.stock_lines.length > 0 ||
+                "Выберите технику или расходники",
+            }}
             render={({ field, fieldState }) => (
               <AssetMultiPicker
                 value={field.value}
@@ -152,20 +207,44 @@ function IssueSection() {
                     return;
                   }
                   field.onChange(next);
-                  setUnavailable(new Set());
+                  dropUnfitReason(next, getValues("stock_lines"));
+                  setUnavailable(NOTHING_UNAVAILABLE);
                   setFormError(null);
                 }}
-                unavailableIds={unavailable}
+                unavailableIds={unavailable.assets}
                 error={fieldState.error?.message}
               />
             )}
           />
+          <Controller
+            control={control}
+            name="stock_lines"
+            rules={{
+              validate: (lines) =>
+                lines.every((line) => stockLineError(line) === null) ||
+                "Проверьте строки расходников",
+            }}
+            render={({ field }) => (
+              <StockLinesField
+                value={field.value}
+                onChange={(next) => {
+                  field.onChange(next);
+                  dropUnfitReason(getValues("asset_ids"), next);
+                  setUnavailable(NOTHING_UNAVAILABLE);
+                  setFormError(null);
+                }}
+                unavailable={unavailable.stock}
+                showErrors={submitCount > 0}
+                maxLines={MAX_BULK_SELECTION}
+              />
+            )}
+          />
           <FormSelect
             control={control}
             name="reason_id"
             label="Причина"
             emptyLabel="Не указана"
-            options={(reasons.data ?? []).map((item) => ({ value: item.id, label: item.name }))}
+            options={reasonOptions.map((item) => ({ value: item.id, label: item.name }))}
           />
           <FormTextField
             control={control}
```

Создать `frontend/src/features/stock/StockLinesField.tsx`:

```tsx
import { Box, Button, IconButton, Stack, TextField } from "@mui/material";
import { IconPlus, IconTrash } from "@tabler/icons-react";

import type { StockItem } from "./labels";
import { StockItemPicker } from "./StockItemPicker";

export interface StockLineValue {
  /** Ключ строки для React: позиции в строке может ещё не быть. */
  key: number;
  item: StockItem | null;
  quantity: string;
}

/** Ошибка строки, видимая до отправки: не выбрана позиция, неверное количество, мало остатка. */
export function stockLineError(line: StockLineValue): string | null {
  if (!line.item) return "Выберите позицию";
  if (!/^\d{1,7}$/.test(line.quantity.trim()) || Number(line.quantity) < 1) {
    return "Целое число от 1";
  }
  if (Number(line.quantity) > line.item.quantity) {
    return `Доступно ${line.item.quantity} ${line.item.unit}`;
  }
  return null;
}

let nextKey = 1;

export function newStockLine(): StockLineValue {
  return { key: nextKey++, item: null, quantity: "" };
}

interface StockLinesFieldProps {
  value: StockLineValue[];
  onChange: (lines: StockLineValue[]) => void;
  /** Остаток на сервере для строк, отклонённых ответом 409 (null — позиция не найдена). */
  unavailable: ReadonlyMap<number, number | null>;
  /** Показывать ошибки строк (после попытки отправки). */
  showErrors: boolean;
  maxLines: number;
}

/** Строки «позиция + количество» для единой выдачи. */
export function StockLinesField({
  value,
  onChange,
  unavailable,
  showErrors,
  maxLines,
}: StockLinesFieldProps) {
  const update = (key: number, patch: Partial<StockLineValue>) =>
    onChange(value.map((line) => (line.key === key ? { ...line, ...patch } : line)));

  const serverHint = (line: StockLineValue) => {
    if (!line.item || !unavailable.has(line.item.id)) return null;
    const available = unavailable.get(line.item.id);
    return available === null || available === undefined
      ? "Позиция недоступна"
      : `На складе осталось ${available} ${line.item.unit}`;
  };

  return (
    <Stack spacing={1.5}>
      {value.map((line) => {
        const chosen = new Set(
          value.filter((other) => other.key !== line.key && other.item).map((o) => o.item!.id),
        );
        const hint = serverHint(line) ?? (showErrors ? stockLineError(line) : null);
        return (
          <Stack key={line.key} direction={{ xs: "column", sm: "row" }} spacing={1.5}>
            <Box sx={{ flex: 1 }}>
              <StockItemPicker
                label="Расходник"
                value={line.item}
                onChange={(item) => update(line.key, { item })}
                onlyAvailable
                excludeIds={chosen}
                error={showErrors && !line.item ? "Выберите позицию" : undefined}
              />
            </Box>
            <TextField
              label="Количество"
              value={line.quantity}
              onChange={(event) => update(line.key, { quantity: event.target.value })}
              error={Boolean(hint) && Boolean(line.item)}
              helperText={line.item ? hint : undefined}
              sx={{ width: { sm: 180 } }}
              slotProps={{ htmlInput: { inputMode: "numeric" } }}
            />
            <IconButton
              aria-label="Удалить строку"
              onClick={() => onChange(value.filter((other) => other.key !== line.key))}
              sx={{ alignSelf: { sm: "flex-start" }, mt: { sm: 1 } }}
            >
              <IconTrash size={18} />
            </IconButton>
          </Stack>
        );
      })}
      <Box>
        <Button
          startIcon={<IconPlus size={18} />}
          disabled={value.length >= maxLines}
          onClick={() => onChange([...value, newStockLine()])}
        >
          Добавить расходник
        </Button>
      </Box>
    </Stack>
  );
}
```

Изменить `frontend/src/features/stock/index.ts` (применить дифф):

```diff
@@ -1,2 +1,3 @@
 export { StockItemPage } from "./StockItemPage";
+export { StockLinesField, stockLineError, type StockLineValue } from "./StockLinesField";
 export { StockPage } from "./StockPage";
```

- [ ] **Step 4: Проверить**

Run: `cd frontend && npx vitest run src/features/assets/IssuePage.test.tsx`
Expected: `Tests 11 passed`

Run: `cd frontend && npm run format && npm run check`
Expected: `Tests 109 passed`

- [ ] **Step 5: Коммит**

```bash
git add frontend/src/features/assets/IssuePage.test.tsx frontend/src/features/assets/IssuePage.tsx frontend/src/features/stock/StockLinesField.tsx frontend/src/features/stock/index.ts
git commit -m "feat(frontend): «Выдать» — техника и расходники одной операцией"
```

---

### Task 10: Фронтенд: «История движений»

Отдельная фича `features/movements` (не `stock`, как в спецификации): журналу нужны подписи и техники, и расходников, а `assets` уже импортирует `stock` — журнал внутри `stock` дал бы цикл `assets → stock → assets`. Фильтры в URL (`dateParam` — новый параметр `useUrlFilters`), объект в строке — ссылка на карточку актива или позиции. Пункт меню «История движений».

**Files:**
- Modify: `frontend/src/app/routes.tsx`
- Modify: `frontend/src/features/assets/index.ts`
- Modify: `frontend/src/features/assets/labels.ts`
- Create: `frontend/src/features/movements/MovementsPage.tsx`
- Create: `frontend/src/features/movements/api.ts`
- Create: `frontend/src/features/movements/index.ts`
- Create: `frontend/src/features/movements/labels.ts`
- Modify: `frontend/src/features/stock/index.ts`
- Modify: `frontend/src/layout/menu.ts`
- Modify: `frontend/src/shared/lib/useUrlFilters.ts`
- Test (modify): `frontend/src/app/shell.test.tsx`
- Test (create): `frontend/src/features/movements/MovementsPage.test.tsx`
- Test (create): `frontend/src/features/movements/labels.test.ts`
- Test (modify): `frontend/src/shared/lib/useUrlFilters.test.tsx`

**Interfaces:**
- Consumes: `assetEventLabel`, `STATUS_LABELS` (экспорт `features/assets/index.ts`); `formatDelta`, `movementTitle` (экспорт `features/stock/index.ts`); `makeJournalEntry` (Task 6).
- Produces: `features/assets/labels.ts` — `assetEventLabel(eventType, operation)`; `shared/lib/useUrlFilters.ts` — `dateParam`; `features/movements` — `MovementsPage`, `useJournal`, `entryTitle`, `entryDetails`, `entryLocation`, `objectLink`, `GROUP_LABELS`, `KIND_LABELS`.

- [ ] **Step 1: Написать падающие тесты**

Изменить `frontend/src/app/shell.test.tsx` (применить дифф):

```diff
@@ -52,6 +52,10 @@ test("администратор видит раздел «Администри
     "href",
     "/equipment/stock",
   );
+  expect(within(nav).getByRole("link", { name: "История движений" })).toHaveAttribute(
+    "href",
+    "/equipment/movements",
+  );
   expect(screen.getByRole("heading", { name: "Главная" })).toBeInTheDocument();
   expect(screen.getByText("Здравствуйте, Иванов Иван")).toBeInTheDocument();
 });
@@ -65,7 +69,7 @@ test("сотрудник не видит раздел «Администриро
   expect(within(nav).queryByText("Администрирование")).not.toBeInTheDocument();
 });
 
-test("раздел «Склад и техника»: реестр всем, расходники и выдача только администратору", async () => {
+test("раздел «Склад и техника»: реестр всем, расходники, журнал и выдача только администратору", async () => {
   mockSignedIn(makeMe({ role: "manager" }));
   renderShell("/");
 
@@ -76,6 +80,7 @@ test("раздел «Склад и техника»: реестр всем, ра
   );
   expect(within(nav).queryByRole("link", { name: "Выдать / принять" })).not.toBeInTheDocument();
   expect(within(nav).queryByRole("link", { name: "Расходники" })).not.toBeInTheDocument();
+  expect(within(nav).queryByRole("link", { name: "История движений" })).not.toBeInTheDocument();
 });
 
 test("неизвестный путь показывает страницу 404", async () => {
```

Создать `frontend/src/features/movements/MovementsPage.test.tsx`:

```tsx
import { screen, waitFor, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";

import { renderApp } from "../../test/app";
import { makeMe, mockSignedIn } from "../../test/auth";
import { makeJournalEntry, makeUser, page } from "../../test/fixtures";
import { server } from "../../test/server";

function mockJournal(seen: URL[] = []) {
  server.use(
    http.get("*/api/directories/locations", () =>
      HttpResponse.json([{ id: 5, name: "Склад", description: null, is_active: true }]),
    ),
    http.get("*/api/admin/users", () =>
      HttpResponse.json(page([makeUser({ id: 10, full_name: "Петров Пётр" })])),
    ),
    http.get("*/api/equipment/movements", ({ request }) => {
      seen.push(new URL(request.url));
      return HttpResponse.json(
        page([
          makeJournalEntry({ id: 7, reason_name: "Новый сотрудник" }),
          makeJournalEntry({
            kind: "asset",
            id: 3,
            asset_event_type: "issued",
            asset_operation: "issue",
            movement_type: null,
            object_id: 100,
            object_label: "INV-001 — Lenovo ThinkPad T14",
            delta: null,
            quantity_after: null,
            unit: null,
            from_status: "in_stock",
            to_status: "in_use",
            to_location_id: null,
            to_location_name: null,
          }),
        ]),
      );
    }),
  );
  return seen;
}

test("журнал: техника и расходники, ссылки на карточки, фильтры из URL", async () => {
  mockSignedIn();
  const seen = mockJournal();
  const { user, router } = renderApp(
    "/equipment/movements?from=2026-09-01&to=2026-09-22&kind=stock&group=issue&person=10&location=5",
  );

  const stockRow = (await screen.findByRole("link", { name: "Картридж HP 85A" })).closest("tr")!;
  expect(within(stockRow).getByText("Выдача")).toBeInTheDocument();
  expect(within(stockRow).getByText("−2 шт")).toBeInTheDocument();
  expect(within(stockRow).getByText("Кому: Петров Пётр")).toBeInTheDocument();
  expect(within(stockRow).getByText("Причина: Новый сотрудник")).toBeInTheDocument();
  const assetLink = screen.getByRole("link", { name: "INV-001 — Lenovo ThinkPad T14" });
  expect(assetLink).toHaveAttribute("href", "/equipment/assets/100");
  expect(
    within(assetLink.closest("tr")!).getByText("Статус: На складе → В работе"),
  ).toBeInTheDocument();

  const params = seen.at(-1)!.searchParams;
  expect(params.get("date_from")).toBe("2026-09-01");
  expect(params.get("date_to")).toBe("2026-09-22");
  expect(params.get("kind")).toBe("stock");
  expect(params.getAll("group")).toEqual(["issue"]);
  expect(params.get("person_id")).toBe("10");
  expect(params.get("location_id")).toBe("5");

  await user.click(screen.getByLabelText("Операция"));
  await user.click(await screen.findByRole("option", { name: "Списание" }));
  await waitFor(() => expect(seen.at(-1)!.searchParams.getAll("group")).toEqual(["write_off"]));
  expect(router.state.location.search).toContain("group=write_off");

  await user.click(assetLink);
  expect(router.state.location.pathname).toBe("/equipment/assets/100");
});

test("журнал доступен только администратору", async () => {
  mockSignedIn(makeMe({ role: "employee" }));
  renderApp("/equipment/movements");

  expect(await screen.findByRole("heading", { name: "Нет доступа" })).toBeInTheDocument();
});
```

Создать `frontend/src/features/movements/labels.test.ts`:

```ts
import { makeJournalEntry } from "../../test/fixtures";
import { entryDetails, entryLocation, entryTitle, objectLink } from "./labels";

const assetEntry = makeJournalEntry({
  kind: "asset",
  asset_event_type: "returned",
  asset_operation: "repair_to_stock",
  movement_type: null,
  object_id: 100,
  object_label: "INV-001 — Lenovo ThinkPad T14",
  delta: null,
  quantity_after: null,
  unit: null,
  from_owner_name: "Петров Пётр",
  to_owner_id: null,
  to_owner_name: null,
  from_status: "in_repair",
  to_status: "in_stock",
  from_location_name: "Сервис",
  to_location_name: "Склад",
});

test("заголовок: операция техники, тип события или тип движения", () => {
  expect(entryTitle(assetEntry)).toBe("Вернуть из ремонта на склад");
  expect(entryTitle({ ...assetEntry, asset_operation: null, asset_event_type: "created" })).toBe(
    "Поставлена на учёт",
  );
  expect(entryTitle(makeJournalEntry())).toBe("Выдача");
});

test("подробности: статус, владелец, получатель, причина, дата документа", () => {
  expect(entryDetails(assetEntry)).toEqual([
    "Статус: В ремонте → На складе",
    "Владелец: Петров Пётр → —",
  ]);
  expect(entryDetails(makeJournalEntry({ reason_name: "Новый сотрудник" }))).toEqual([
    "Кому: Петров Пётр",
    "Причина: Новый сотрудник",
  ]);
  expect(
    entryDetails(
      makeJournalEntry({
        movement_type: "receipt",
        to_owner_name: null,
        document_date: "2026-09-01",
      }),
    ),
  ).toEqual(["Дата документа: 01.09.2026"]);
});

test("склад или локация и ссылка на карточку", () => {
  expect(entryLocation(assetEntry)).toBe("Сервис → Склад");
  expect(entryLocation(makeJournalEntry())).toBe("Склад");
  expect(entryLocation({ ...assetEntry, from_location_name: null, to_location_name: null })).toBe(
    "—",
  );
  expect(objectLink(assetEntry)).toBe("/equipment/assets/100");
  expect(objectLink(makeJournalEntry())).toBe("/equipment/stock/200");
});
```

Изменить `frontend/src/shared/lib/useUrlFilters.test.tsx` (применить дифф):

```diff
@@ -1,7 +1,7 @@
 import { screen } from "@testing-library/react";
 
 import { renderWithProviders } from "../../test/render";
-import { booleanParam, enumParam, textParam, useUrlFilters } from "./useUrlFilters";
+import { booleanParam, dateParam, enumParam, textParam, useUrlFilters } from "./useUrlFilters";
 
 const schema = {
   q: textParam,
@@ -43,3 +43,10 @@ test("смена фильтра пишет его в URL и сбрасывает
   await user.click(screen.getByRole("button", { name: "роль" }));
   expect(router.state.location.search).toBe("?q=%D0%B8%D0%B2&limit=50&role=manager");
 });
+
+test("dateParam принимает только дату YYYY-MM-DD", () => {
+  expect(dateParam.parse("2026-09-22")).toBe("2026-09-22");
+  expect(dateParam.parse("22.09.2026")).toBeNull();
+  expect(dateParam.parse(null)).toBeNull();
+  expect(dateParam.serialize(null)).toBeNull();
+});
```

- [ ] **Step 2: Убедиться, что тесты падают**

Run: `cd frontend && npx vitest run src/features/movements src/shared/lib/useUrlFilters.test.tsx`
Expected: FAIL — `Failed to resolve import "./labels"`, `dateParam` не экспортируется

- [ ] **Step 3: Реализация**

Изменить `frontend/src/app/routes.tsx` (применить дифф):

```diff
@@ -13,6 +13,7 @@ import { AssetPage, AssetsPage, IssuePage } from "../features/assets";
 import { DepartmentsPage } from "../features/departments";
 import { DirectoriesPage } from "../features/directories";
 import { HomePage } from "../features/home";
+import { MovementsPage } from "../features/movements";
 import { StockItemPage, StockPage } from "../features/stock";
 import { UsersPage } from "../features/users";
 import { BlankLayout } from "../layout/BlankLayout";
@@ -56,6 +57,7 @@ export const routes: RouteObject[] = [
             children: [
               { path: "/equipment/stock", element: <StockPage /> },
               { path: "/equipment/stock/:id", element: <StockItemPage /> },
+              { path: "/equipment/movements", element: <MovementsPage /> },
               { path: "/equipment/issue", element: <IssuePage /> },
               { path: "/admin/users", element: <UsersPage /> },
               { path: "/admin/departments", element: <DepartmentsPage /> },
```

Изменить `frontend/src/features/assets/index.ts` (применить дифф):

```diff
@@ -1,3 +1,4 @@
 export { AssetPage } from "./AssetPage";
 export { AssetsPage } from "./AssetsPage";
 export { IssuePage } from "./IssuePage";
+export { assetEventLabel, STATUS_LABELS } from "./labels";
```

Изменить `frontend/src/features/assets/labels.ts` (применить дифф):

```diff
@@ -48,9 +48,17 @@ const EVENT_LABELS: Record<Schemas["AssetEventType"], string> = {
   written_off: "Списание",
 };
 
+/** Название события техники: операция, если есть, иначе тип события. */
+export function assetEventLabel(
+  eventType: Schemas["AssetEventType"],
+  operation: Operation | null,
+): string {
+  return operation ? OPERATION_LABELS[operation] : EVENT_LABELS[eventType];
+}
+
 /** Заголовок события: название операции, если есть, иначе тип события. */
 export function eventTitle(event: AssetEvent): string {
-  return event.operation ? OPERATION_LABELS[event.operation] : EVENT_LABELS[event.event_type];
+  return assetEventLabel(event.event_type, event.operation);
 }
 
 export const FIELD_LABELS: Record<string, string> = {
```

Создать `frontend/src/features/movements/MovementsPage.tsx`:

```tsx
import { Box, Link as MuiLink, Stack, TextField, Typography } from "@mui/material";
import { Link } from "react-router";

import { formatDateTime } from "../../shared/lib/format";
import { dateParam, enumParam, idParam, useUrlFilters } from "../../shared/lib/useUrlFilters";
import { useLocations } from "../../shared/lookups/directories";
import {
  ACTIVE_USER_OPTIONS_KEY,
  searchActiveUserOptions,
  useUserNames,
} from "../../shared/lookups/users";
import { DataTable, type Column } from "../../shared/ui/DataTable";
import { EntityAutocomplete } from "../../shared/ui/EntityAutocomplete";
import { FilterBar, FilterSelect } from "../../shared/ui/FilterBar";
import { PageContainer } from "../../shared/ui/PageContainer";
import { formatDelta } from "../stock";
import { useJournal } from "./api";
import {
  entryDetails,
  entryLocation,
  entryTitle,
  GROUP_LABELS,
  JOURNAL_GROUPS,
  JOURNAL_KINDS,
  KIND_LABELS,
  objectLink,
  type JournalEntry,
} from "./labels";

const FILTERS = {
  from: dateParam,
  to: dateParam,
  kind: enumParam(JOURNAL_KINDS),
  group: enumParam(JOURNAL_GROUPS),
  person: idParam,
  performer: idParam,
  location: idParam,
};

const columns: Column<JournalEntry>[] = [
  {
    key: "created_at",
    header: "Когда",
    width: 150,
    render: (entry) => formatDateTime(entry.created_at),
  },
  {
    key: "operation",
    header: "Операция",
    render: (entry) => (
      <Stack spacing={0.5}>
        <Typography sx={{ fontWeight: 600 }}>{entryTitle(entry)}</Typography>
        {entryDetails(entry).map((line) => (
          <Typography key={line} variant="body2" color="text.secondary">
            {line}
          </Typography>
        ))}
        {entry.comment && (
          <Box component="q" sx={{ typography: "body2" }}>
            {entry.comment}
          </Box>
        )}
      </Stack>
    ),
  },
  {
    key: "object",
    header: "Объект",
    render: (entry) => (
      <MuiLink component={Link} to={objectLink(entry)}>
        {entry.object_label}
      </MuiLink>
    ),
  },
  {
    key: "delta",
    header: "Количество",
    render: (entry) =>
      entry.delta !== null && entry.unit !== null ? formatDelta(entry.delta, entry.unit) : "—",
  },
  { key: "location", header: "Склад / локация", render: entryLocation },
  { key: "performed_by", header: "Кто", render: (entry) => entry.performed_by_name },
];

export function MovementsPage() {
  const { filters, limit, offset, setFilter, setPage } = useUrlFilters(FILTERS);
  const journal = useJournal({
    dateFrom: filters.from,
    dateTo: filters.to,
    kind: filters.kind,
    group: filters.group,
    personId: filters.person,
    performedBy: filters.performer,
    locationId: filters.location,
    limit,
    offset,
  });
  const locations = useLocations();
  const { nameOf } = useUserNames();

  const dateField = (key: "from" | "to", label: string) => (
    <TextField
      size="small"
      type="date"
      label={label}
      value={filters[key] ?? ""}
      onChange={(event) => setFilter(key, event.target.value || null)}
      slotProps={{ inputLabel: { shrink: true } }}
    />
  );

  return (
    <PageContainer
      title="История движений"
      breadcrumbs={[{ label: "Склад и техника" }, { label: "История движений" }]}
    >
      <FilterBar>
        {dateField("from", "С")}
        {dateField("to", "По")}
        <FilterSelect
          label="Вид"
          value={filters.kind}
          options={JOURNAL_KINDS.map((kind) => ({ value: kind, label: KIND_LABELS[kind] }))}
          onChange={(value) => setFilter("kind", value)}
        />
        <FilterSelect
          label="Операция"
          value={filters.group}
          options={JOURNAL_GROUPS.map((group) => ({ value: group, label: GROUP_LABELS[group] }))}
          onChange={(value) => setFilter("group", value)}
        />
      </FilterBar>
      <FilterBar>
        <EntityAutocomplete
          label="Сотрудник"
          value={filters.person}
          onChange={(id) => setFilter("person", id)}
          fetchOptions={searchActiveUserOptions}
          queryKey={ACTIVE_USER_OPTIONS_KEY}
          labelFor={nameOf}
        />
        <EntityAutocomplete
          label="Кто выполнил"
          value={filters.performer}
          onChange={(id) => setFilter("performer", id)}
          fetchOptions={searchActiveUserOptions}
          queryKey={ACTIVE_USER_OPTIONS_KEY}
          labelFor={nameOf}
        />
        <FilterSelect
          label="Склад / локация"
          value={filters.location}
          options={(locations.data ?? []).map((item) => ({ value: item.id, label: item.name }))}
          onChange={(value) => setFilter("location", value)}
        />
      </FilterBar>

      <DataTable
        columns={columns}
        rows={journal.data?.items}
        getRowId={(entry) => `${entry.kind}-${entry.id}`}
        loading={journal.isLoading}
        error={journal.error}
        onRetry={() => void journal.refetch()}
        emptyText="Движений не найдено"
        paging={{ limit, offset, total: journal.data?.total ?? 0, onChange: setPage }}
      />
    </PageContainer>
  );
}
```

Создать `frontend/src/features/movements/api.ts`:

```ts
import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { api, unwrap } from "../../api/client";
import { queryKeys } from "../../shared/lookups/queryKeys";
import type { JournalGroup, JournalKind } from "./labels";

export interface JournalParams {
  dateFrom: string | null;
  dateTo: string | null;
  kind: JournalKind | null;
  group: JournalGroup | null;
  personId: number | null;
  performedBy: number | null;
  locationId: number | null;
  limit: number;
  offset: number;
}

export function useJournal(params: JournalParams) {
  return useQuery({
    queryKey: [...queryKeys.movements, "journal", params],
    queryFn: () =>
      unwrap(
        api.GET("/api/equipment/movements", {
          params: {
            query: {
              date_from: params.dateFrom ?? undefined,
              date_to: params.dateTo ?? undefined,
              kind: params.kind ?? undefined,
              group: params.group ? [params.group] : undefined,
              person_id: params.personId ?? undefined,
              performed_by: params.performedBy ?? undefined,
              location_id: params.locationId ?? undefined,
              limit: params.limit,
              offset: params.offset,
            },
          },
        }),
      ),
    placeholderData: keepPreviousData,
  });
}
```

Создать `frontend/src/features/movements/index.ts`:

```ts
export { MovementsPage } from "./MovementsPage";
```

Создать `frontend/src/features/movements/labels.ts`:

```ts
import type { Schemas } from "../../api/types";
import { formatDate } from "../../shared/lib/format";
import { assetEventLabel, STATUS_LABELS } from "../assets";
import { movementTitle } from "../stock";

export type JournalEntry = Schemas["JournalEntryRead"];
export type JournalGroup = Schemas["JournalGroup"];
export type JournalKind = Schemas["JournalKind"];

export const GROUP_LABELS: Record<JournalGroup, string> = {
  issue: "Выдача",
  return: "Возврат",
  receipt: "Приход",
  write_off: "Списание",
  adjustment: "Корректировка",
  transfer: "Перемещение",
  status: "Смена статуса",
  record: "Создание и правка",
};

export const JOURNAL_GROUPS = Object.keys(GROUP_LABELS) as JournalGroup[];

export const KIND_LABELS: Record<JournalKind, string> = {
  asset: "Техника",
  stock: "Расходники",
};

export const JOURNAL_KINDS = Object.keys(KIND_LABELS) as JournalKind[];

export function entryTitle(entry: JournalEntry): string {
  if (entry.kind === "asset" && entry.asset_event_type) {
    return assetEventLabel(entry.asset_event_type, entry.asset_operation);
  }
  return entry.movement_type ? movementTitle(entry.movement_type) : "";
}

/** Строки подробностей: «было → стало» для техники, получатель расходника, причина, дата. */
export function entryDetails(entry: JournalEntry): string[] {
  const lines: string[] = [];
  const pair = (label: string, from: string | null, to: string | null) => {
    if (from !== null || to !== null) lines.push(`${label}: ${from ?? "—"} → ${to ?? "—"}`);
  };
  if (entry.kind === "asset") {
    pair(
      "Статус",
      entry.from_status ? STATUS_LABELS[entry.from_status] : null,
      entry.to_status ? STATUS_LABELS[entry.to_status] : null,
    );
    pair("Владелец", entry.from_owner_name, entry.to_owner_name);
  } else if (entry.to_owner_name) {
    lines.push(`Кому: ${entry.to_owner_name}`);
  }
  if (entry.document_date) lines.push(`Дата документа: ${formatDate(entry.document_date)}`);
  if (entry.reason_name) lines.push(`Причина: ${entry.reason_name}`);
  return lines;
}

/** Склад или локация: «откуда → куда», если менялись, иначе одно значение. */
export function entryLocation(entry: JournalEntry): string {
  const { from_location_name: from, to_location_name: to } = entry;
  if (from && to) return `${from} → ${to}`;
  return from ?? to ?? "—";
}

export function objectLink(entry: JournalEntry): string {
  return entry.kind === "asset"
    ? `/equipment/assets/${entry.object_id}`
    : `/equipment/stock/${entry.object_id}`;
}
```

Изменить `frontend/src/features/stock/index.ts` (применить дифф):

```diff
@@ -1,3 +1,4 @@
 export { StockItemPage } from "./StockItemPage";
 export { StockLinesField, stockLineError, type StockLineValue } from "./StockLinesField";
+export { formatDelta, movementTitle } from "./labels";
 export { StockPage } from "./StockPage";
```

Изменить `frontend/src/layout/menu.ts` (применить дифф):

```diff
@@ -3,6 +3,7 @@ import {
   IconBook2,
   IconBuildingCommunity,
   IconDeviceLaptop,
+  IconHistory,
   IconLayoutDashboard,
   IconPackage,
   IconUserCircle,
@@ -37,6 +38,12 @@ export const MENU: readonly MenuSection[] = [
     items: [
       { label: "Реестр техники", to: "/equipment/assets", icon: IconDeviceLaptop },
       { label: "Расходники", to: "/equipment/stock", icon: IconPackage, roles: ["admin"] },
+      {
+        label: "История движений",
+        to: "/equipment/movements",
+        icon: IconHistory,
+        roles: ["admin"],
+      },
       {
         label: "Выдать / принять",
         to: "/equipment/issue",
```

Изменить `frontend/src/shared/lib/useUrlFilters.ts` (применить дифф):

```diff
@@ -30,6 +30,12 @@ export const idParam: UrlParam<number | null> = {
   serialize: (value) => (value === null ? null : String(value)),
 };
 
+/** Дата «YYYY-MM-DD» (значение input type="date"). */
+export const dateParam: UrlParam<string | null> = {
+  parse: (raw) => (raw && /^\d{4}-\d{2}-\d{2}$/.test(raw) ? raw : null),
+  serialize: (value) => value,
+};
+
 export const booleanParam: UrlParam<boolean | null> = {
   parse: (raw) => (raw === "true" ? true : raw === "false" ? false : null),
   serialize: (value) => (value === null ? null : String(value)),
```

- [ ] **Step 4: Проверить**

Run: `cd frontend && npx vitest run src/features/movements src/app/shell.test.tsx src/shared/lib/useUrlFilters.test.tsx`
Expected: все зелёные

Run: `cd frontend && npm run format && npm run check && npm run build`
Expected: `Tests 115 passed`, сборка успешна

- [ ] **Step 5: Коммит**

```bash
git add frontend/src/app/routes.tsx frontend/src/app/shell.test.tsx frontend/src/features/assets/index.ts frontend/src/features/assets/labels.ts frontend/src/features/movements/MovementsPage.test.tsx frontend/src/features/movements/MovementsPage.tsx frontend/src/features/movements/api.ts frontend/src/features/movements/index.ts frontend/src/features/movements/labels.test.ts frontend/src/features/movements/labels.ts frontend/src/features/stock/index.ts frontend/src/layout/menu.ts frontend/src/shared/lib/useUrlFilters.test.tsx frontend/src/shared/lib/useUrlFilters.ts
git commit -m "feat(frontend): «История движений» — журнал техники и расходников с фильтрами"
```

---

### Task 11: README, полная проверка, ручная проверка в браузере

Описание расходников, единой выдачи и журнала; чек-лист ручной проверки — пункты 14–21. Затем полная проверка всех слоёв.

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Изменения**

Изменить `README.md` (применить дифф):

```diff
@@ -82,6 +82,14 @@ make gen-api           # после изменения API: openapi.json + src/a
 11. Конфликт двух вкладок: одна выдаёт актив, вторая пытается зарезервировать его же → «Статус техники изменился», карточка обновилась.
 12. Под сотрудником виден только свой реестр, под руководителем — техника отдела; «Выдать / принять» и «Действия» им недоступны.
 13. Деактивация сотрудника с техникой «В работе» → в списке причин блокировки есть эта техника.
+14. Расходники: создание позиции (категории и склады — из справочников), дубль наименования на том же складе показывается под полем; на другом складе — создаётся.
+15. Приход со страницы списка и из карточки: дата документа по умолчанию сегодня, будущая не принимается; остаток растёт, в истории видна дата документа.
+16. «Выдать»: технику и расходники одному сотруднику одной операцией; в списке причин только подходящие к составу; количество больше остатка не отправляется.
+17. Списание (без причины не проходит), корректировка (изменение считается на форме, без комментария не проходит), перемещение на склад, где такой позиции ещё нет → позиция появилась там с перемещённым количеством.
+18. Позиция с остатком ниже или равным минимуму подсвечена красным; фильтр «Только низкий остаток».
+19. Конфликт двух вкладок: одна выдаёт последние единицы, вторая пытается их списать → «Остаток изменился», карточка обновилась.
+20. «История движений»: выдача, приход, перемещение и операции с техникой в одном списке; фильтры по периоду, операции, сотруднику, складу; ссылка ведёт в карточку.
+21. Под сотрудником и руководителем пунктов «Расходники», «История движений», «Выдать / принять» нет, прямые ссылки показывают «Нет доступа».
 
 Структура `frontend/src`: `app/` (провайдеры, маршруты), `layout/` (каркас), `api/` (клиент и сгенерированные типы), `shared/ui`, `shared/lib`, `shared/lookups` (общие справочные запросы), `features/<модуль>/`. Фича импортирует другую фичу только через её `index.ts`; `api`, `theme` и `shared` не зависят от фич — это проверяет ESLint (`import/no-restricted-paths`).
 
@@ -91,7 +99,11 @@ Refresh-токен ротируется при каждом `POST /api/auth/refr
 
 ## Оргтехника
 
-Модуль `backend/app/modules/assets` (схема БД `equipment`), экраны — `frontend/src/features/assets`. Правила переходов статусов (п. 4.2.2 ТЗ) описаны одной таблицей в `assets/transitions.py`: из неё backend проверяет операции и отдаёт в карточке `allowed_operations`, по которым фронтенд строит меню «Действия». Статус, владелец и локация меняются только операциями (`POST /api/assets/{id}/operations`, массово — `/api/assets/issue` и `/api/assets/return`); `PATCH` меняет только описательные поля с проверкой `version`. Строки активов блокируются `SELECT … FOR UPDATE`, поэтому параллельная выдача одного актива даёт 409.
+Модуль `backend/app/modules/assets` (схема БД `equipment`), экраны — `frontend/src/features/assets`. Правила переходов статусов (п. 4.2.2 ТЗ) описаны одной таблицей в `assets/transitions.py`: из неё backend проверяет операции и отдаёт в карточке `allowed_operations`, по которым фронтенд строит меню «Действия». Статус, владелец и локация меняются только операциями (`POST /api/assets/{id}/operations`, массовый возврат — `/api/assets/return`); `PATCH` меняет только описательные поля с проверкой `version`. Строки активов блокируются `SELECT … FOR UPDATE`, поэтому параллельная выдача одного актива даёт 409.
+
+Расходники — в том же модуле (`stock_*.py`), экраны — `frontend/src/features/stock`. Позиция — это наименование на конкретном складе (уникально без учёта регистра). Остаток меняется только движениями (`POST /api/stock-items/{id}/operations`: приход, списание, корректировка по фактическому остатку, перемещение), каждое пишет `stock_movements` с остатком после операции; `CHECK (quantity >= 0)` страхует от ухода в минус. У прихода две даты: `document_date` — по накладной, `created_at` — момент внесения; журнал и цепочка остатков строятся по `created_at`. Перемещение на склад, где позиции нет, создаёт её.
+
+Единая выдача `POST /api/equipment/checkout` выдаёт технику и расходники одному сотруднику одной транзакцией: если хоть что-то недоступно, 409 `checkout_unavailable` перечисляет все проблемы и ничего не меняется. Журнал `GET /api/equipment/movements` — один запрос `UNION ALL` по событиям техники и движениям расходников; экран — `frontend/src/features/movements`. Расходники, выдача и журнал доступны только Admin.
 
 ## Архитектура
```

- [ ] **Step 2: Проверить**

Run: `make lint && make test`
Expected: `Contracts: 5 kept, 0 broken.`, `296 passed`

Run: `cd backend && DATABASE_URL=postgresql+asyncpg://app:app@localhost:5432/it_platform_test uv run alembic check`
Expected: `No new upgrade operations detected.`

Run: `cd frontend && npm run check && npm run build`
Expected: `Tests 115 passed`, сборка успешна

Run: `docker compose up -d --build`
Expected: стек на http://localhost:8080; пункты 14–21 README проходит пользователь (агент браузер не проверяет)

- [ ] **Step 3: Коммит**

```bash
git add README.md
git commit -m "docs: расходники, единая выдача и журнал в README, чек-лист ручной проверки 14–21"
```
