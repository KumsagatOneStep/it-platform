# Спринт 2, часть 2a: оргтехника — дизайн

Дата: 2026-09-21. Основание: ТЗ v1.2 (`docs/spec/TZ_IT_platforma_v1.2.md`) — п. 2.2 (модульный монолит), 2.3 (роли и область видимости), 3.1 (`Asset`, `AssetEvent`), 3.2 (целостность и конкурентный доступ), 4.2 (склад и техника), 11 (вопрос 2). База — ветка `feature/sprint1-frontend` (спринт 1 целиком, ещё не слит в main).

## 1. Цель и объём

Модуль «Оргтехника» разбит на две части. Часть 2a — техника: реестр, карточка с историей, статусы и переходы (п. 4.2.2 ТЗ), выдача и возврат, в том числе массовые. Backend и frontend.

Часть 2b (отдельная спецификация): расходники (`StockItem`, `StockMovement`), вкладка «История движений», единая форма «Выдать» для техники и расходников.

Вне объёма 2a:

| Что | Когда |
|---|---|
| Расходники, общий журнал движений, выдача расходников | 2b |
| `AssetEvent.ticket_id`, выдача по заявке, `TicketItem.fulfilled`, вкладка «Связанные заявки» | вместе с модулем заявок |
| Создание `Notification` при выдаче | спринт 4 (Telegram) |
| Массовый импорт; `needs_review` выставляется импортом | спринт 4 (импорт из 1С) |
| Мониторинг гарантий, дайджесты, виджеты дашборда | спринт 5 |
| Экспорт реестра | «Отчёты», спринты 5–6 |

## 2. Модель данных

Модуль `app/modules/assets`, схема БД `equipment`, одна миграция `0005_assets`.

### 2.1. `equipment.assets`

| Поле | Тип | Правила |
|---|---|---|
| id | bigint PK | |
| asset_type_id | FK `common.asset_types` | обязательно |
| inventory_number | varchar(64) | обязательно, обрезается по краям, не пустое, уникальный индекс |
| serial_number | varchar(128) null | обрезается; пустая строка → null; частичный уникальный индекс `WHERE serial_number IS NOT NULL` |
| model | varchar(200) | обязательно, обрезается, не пустое |
| status | enum `asset_status` | `in_stock`, `reserved`, `in_use`, `in_repair`, `written_off` |
| location_id | FK `common.locations` | обязательно |
| owner_id | FK `common.users` null | см. п. 3 |
| accepted_at | date | дата принятия к учёту, обязательно |
| purchased_at | date null | |
| warranty_until | date null | |
| initial_cost | numeric(12,2) null | `CHECK >= 0` |
| needs_review | bool | по умолчанию false |
| version | int | начинается с 1, растёт при каждой правке и операции |
| created_at, updated_at | timestamptz | |

`CHECK`: `status = 'in_use' → owner_id IS NOT NULL`; `status IN ('in_stock', 'reserved', 'written_off') → owner_id IS NULL`; у `in_repair` владелец может быть или не быть. Индексы: `status`, `owner_id`, `asset_type_id`, `location_id`.

Инвентарный номер вводится вручную и совпадает с номером в 1С (значение по умолчанию вопроса 2 п. 11 ТЗ).

### 2.2. `equipment.asset_events`

| Поле | Тип |
|---|---|
| id | bigint PK |
| asset_id | FK `equipment.assets`, индекс `(asset_id, id)` |
| event_type | enum: `created`, `issued`, `returned`, `status_changed`, `moved`, `edited`, `written_off` |
| operation | varchar(32) null — код операции (п. 3), для `status_changed` различает резерв, ремонт и т. д. |
| from_owner_id, to_owner_id | FK `common.users` null |
| from_status, to_status | `asset_status` null |
| from_location_id, to_location_id | FK `common.locations` null |
| reason_id | FK `common.issue_reasons` null |
| changes | jsonb null — только для `edited`: `{поле: [было, стало]}` |
| comment | text null |
| performed_by | FK `common.users` |
| created_at | timestamptz |

Отступление от ТЗ 3.1: добавлены `operation` и `changes` — без них история не показывает, какой переход или какие поля изменились. `ticket_id` добавляется миграцией модуля заявок.

Каждое изменение актива дополнительно пишется в `common.audit_log` (как в спринте 1).

## 3. Операции и переходы

Таблица переходов — единственный источник правил, живёт в `assets/transitions.py`:

| Операция | Из статуса | В статус | Владелец | Поля запроса |
|---|---|---|---|---|
| `issue` | in_stock, reserved | in_use | = `owner_id` (обязателен) | owner_id, reason_id?, comment? |
| `return` | in_use | in_stock | очищается | location_id?, comment? |
| `reserve` | in_stock | reserved | не меняется (null) | comment? |
| `unreserve` | reserved | in_stock | не меняется (null) | comment? |
| `to_repair` | in_stock, in_use, reserved | in_repair | сохраняется | comment? |
| `repair_to_owner` | in_repair | in_use | сохраняется; операция доступна, только если владелец есть (деактивировать его не даст блокер, п. 4) | comment? |
| `repair_to_stock` | in_repair | in_stock | очищается | location_id?, comment? |
| `write_off` | in_stock, in_repair | written_off | очищается | reason_id (обязателен), comment? |
| `move` | все, кроме written_off | не меняется | не меняется | location_id (обязателен), comment? |

Тип события: `issue` → `issued`; `return`, `repair_to_stock` → `returned`; `write_off` → `written_off`; `move` → `moved`; остальные → `status_changed`. `location_id` у `return` и `repair_to_stock` меняет локацию в том же событии.

`allowed_operations(asset, user)` возвращает операции, допустимые из текущего статуса, для Admin; для остальных ролей — пустой список.

## 4. API

Все ответы и ошибки — в формате спринта 1 (`{"error": {code, message, details}}`), списки — `Page[T]` с `limit`/`offset`.

| Запрос | Кто | Описание |
|---|---|---|
| `GET /api/assets` | все | Фильтры: `status` (повторяемый), `asset_type_id`, `owner_id`, `location_id`, `needs_review`, `q` (≤ 100 символов, `ILIKE` по инв. номеру, серийному номеру, модели). Сортировка по `inventory_number`. Без фильтра `status` списанные не показываются |
| `GET /api/assets/{id}` | все в своей области | `AssetRead` + `allowed_operations` |
| `GET /api/assets/{id}/events` | все в своей области | `Page[AssetEventRead]`, новые сверху |
| `POST /api/assets` | Admin | Создание. Статус `in_stock`, событие `created` |
| `PATCH /api/assets/{id}` | Admin | Поля: тип, инв. номер, серийный номер, модель, даты, стоимость, `needs_review`; обязателен `version`. Статус, владелец и локация меняются только операциями |
| `POST /api/assets/{id}/operations` | Admin | Тело — размеченное объединение по полю `operation` (п. 3) |
| `POST /api/assets/issue` | Admin | `{owner_id, asset_ids[1..50], reason_id?, comment?}` — выдача из `in_stock`, всё или ничего |
| `POST /api/assets/return` | Admin | `{asset_ids[1..50], location_id?, comment?}` — возврат из `in_use`, всё или ничего |

`AssetRead` содержит id и названия связанных сущностей плоскими полями (`asset_type_name`, `location_name`, `owner_name`), `AssetEventRead` — имена владельцев, локаций, причины и исполнителя. Названия подставляет backend через `service.py` других модулей: Employee и Manager не имеют доступа к списку пользователей.

**Область видимости** (п. 2.3 ТЗ): Employee — `owner_id = self`; Manager — `owner_id` среди сотрудников своего отдела; Admin — всё. Актив вне области — 404.

**Межмодульные вызовы** (только через `service.py`, контракты import-linter):
- `users_auth.service`: `get_user_info` (есть), новые `get_user_names(session, user_ids)` и `list_department_user_ids(session, department_id)`.
- `directories.service`: новые `get_reference_item(session, kind, item_id)` — существование, `is_active`, `applicability` для причин — и `get_reference_names(session, kind, item_ids)`.
- `directories` и `users_auth` не импортируют `assets`.
- Новый контракт import-linter: `assets` не импортирует модели, схемы и внутренние файлы других модулей.

**Блокер деактивации:** `assets/handlers.py` подписан на `UserDeactivationRequested` и добавляет `Blocker(kind="asset_owner", entity_id=asset.id, title="Техника <инв. номер> — <модель>")` для каждого актива в статусах `in_use` и `in_repair`, где пользователь — владелец.

## 5. Ошибки и конкурентный доступ

- **Одна операция:** строка актива блокируется `SELECT … FOR UPDATE`, статус проверяется под блокировкой (гарантия та же, что у условного `UPDATE` из п. 3.2 ТЗ: параллельная операция ждёт коммита и видит новый статус). Недопустимый статус — 409 `operation_not_allowed`, `details: {status}` (текущий). Событие и аудит — в той же транзакции. Операции увеличивают `version`.
- **Массовые выдача и возврат:** `SELECT … WHERE id = ANY(:ids) ORDER BY id FOR UPDATE`; если какой-то актив не найден или не в нужном статусе — 409 `assets_unavailable`, `details: [{asset_id, inventory_number, status}]`, ничего не меняется.
- **Правка:** строка блокируется `SELECT … FOR UPDATE`, затем сравнивается `version`; расхождение — 409 `version_conflict`. Правка без фактических изменений не меняет `version` и не пишет событие. Правка списанного — 409 `asset_written_off`.
- **Уникальность:** нарушение уникального индекса перехватывается и превращается в 409 `inventory_number_taken` / `serial_number_taken` (как `email_taken` в спринте 1; отдельная проверка перед записью не нужна). Пустой после обрезки номер или модель — 422 `inventory_number_blank` / `model_blank`.
- **Проверки (422):** `recipient_invalid` (получатель не найден или деактивирован), `reason_invalid` (неактивна или `applicability = stock`), `reason_required` (списание без причины), `location_invalid`, `asset_type_invalid` (неактивное значение; при правке проверяется только изменённое поле).
- **Роли:** операции, создание и правка не-Admin — 403 `insufficient_role`.

## 6. Фронтенд

Фича `features/assets`, раздел меню «Склад и техника». Для Employee и Manager в разделе только реестр.

**Реестр** `/equipment/assets`: `DataTable` — инв. номер, тип, модель, статус (`Chip`, цвета: на складе — success, резерв — info, в работе — primary, в ремонте — warning, списана — default), владелец, локация, гарантия до. Фильтры в URL (`useUrlFilters`): статус (один из; по умолчанию «Все, кроме списанных» — пяти статусов хватает одиночного выбора, API при этом принимает несколько), тип, локация, поиск (`SearchField`); только Admin — владелец (`EntityAutocomplete`, варианты из `/api/admin/users`) и «Требует проверки». Подпись области: «Ваша техника» (Employee), «Техника сотрудников вашего отдела» (Manager). Admin: кнопка «Добавить» → `AssetFormDialog`, после создания открывается карточка. Инвентарный номер в строке — ссылка на карточку (общий `DataTable` не меняется).

**Карточка** `/equipment/assets/:id`: шапка — инв. номер, модель, статус; для Admin «Редактировать» и меню «Действия» из `allowed_operations`. Вкладки «Информация» и «История». Один `AssetOperationDialog`: поля по операции (п. 3), для `write_off` — предупреждение о финальном статусе. 409 `operation_not_allowed` → уведомление «Статус актива изменился» и перезагрузка карточки. 409 `version_conflict` в форме правки → форма закрывается, уведомление «Данные изменил другой пользователь — карточка обновлена, внесите правки заново», карточка перезагружается.

**Выдать / принять** `/equipment/issue`, только Admin:
- «Выдать»: кому (активные сотрудники), что (множественный автокомплит активов `in_stock`), причина (`applicability` assets/both), комментарий. 409 `assets_unavailable` — форма остаётся открытой, недоступные активы подсвечены.
- «Принять»: сотрудник → список его техники `in_use` с флажками, локация (необязательно), комментарий.

Коды ошибок полей раскладываются через `applyApiErrors`. Типы — из `openapi.json` (`make gen-api`).

## 7. Тесты

Backend (pytest, реальный Postgres):
- параметризованный тест таблицы переходов: все пары «статус × операция», правила владельца;
- гонка двух выдач одного актива в параллельных сессиях: одна успешна, вторая — 409;
- массовые операции: один недоступный актив — ничего не меняется;
- область видимости по ролям, 404 и 403;
- `AssetEvent` (с `changes` для правки) и `AuditLog` на каждое изменение;
- блокер деактивации;
- уникальность номеров, в том числе через индекс;
- миграция вверх и вниз, import-linter.

Frontend (Vitest + MSW): фильтры реестра и URL, подписи области по ролям, меню «Действия» из `allowed_operations`, поля диалога операции, реакция на 409 в карточке и в форме выдачи, «Принять».

## 8. Ветка и порядок работ

Ветка `feature/sprint2a-assets` от `feature/sprint1-frontend`. Порядок: миграция и модели → таблица переходов → сервис и API → блокер → фронтенд (реестр → карточка → операции → «Выдать / принять») → README (чек-лист ручной проверки).

## 9. Критерии готовности

- `make test`, `make lint` (включая import-linter), `make frontend-check` зелёные; `openapi.json` и типы фронтенда актуальны.
- Все переходы п. 4.2.2 ТЗ работают, недопустимые блокируются backend.
- Ручная проверка в браузере по чек-листу README: создание актива, выдача нескольких активов, возврат, ремонт и возврат владельцу, списание, история в карточке, конфликт двух вкладок, видимость под Employee и Manager, блокер деактивации.
