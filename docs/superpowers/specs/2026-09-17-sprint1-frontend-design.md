# Спринт 1, план 2: фронтенд — дизайн

Дата: 2026-09-17. Основание: ТЗ v1.2 (`docs/spec/TZ_IT_platforma_v1.2.md`) — п. 1.2 (язык интерфейса), 2.1 (стек), 2.4 (аутентификация), 3.2 (деактивация), 4.7 (администрирование), 7.3 (один домен, CORS), 8 (спринт 1), 9 (DoD). Backend спринта 1 — ветка `feature/sprint1-backend`, API — `backend/openapi.json`.

## 1. Цель и объём

Скелет фронтенда, генерация типов из OpenAPI, общие UI-компоненты, которые переиспользуют все модули, и рабочие экраны на уже готовом backend: вход, смена пароля, профиль, заглушка главной, администрирование пользователей, отделов и справочников.

Вне объёма: дашборд (спринт 5), сквозной Playwright-сценарий (спринт 7), экраны модулей «Оргтехника», «Заявки», «Kanban», «Отчёты», HTTPS/домен staging, AuditLog UI и прочие пункты п. 4.7, для которых нет backend.

Визуальный стиль — шаблон Modernize Free React MUI Dashboard (AdminMart, MIT, github.com/adminmart/modernize-react-lite). Шаблон не клонируется: в свой TypeScript-проект переносятся тема (палитра, типографика, тени, скругления) и каркас (сайдбар, шапка, страница входа, карточки, вид таблиц). Демо-контент (графики, «Upgrade»-баннеры, ссылки AdminMart) не переносится; apexcharts, react-helmet, lodash не подключаются.

## 2. Стек

- Vite, React 19, TypeScript 5.9 (`strict: true`; openapi-typescript и typescript-eslint не поддерживают 6+).
- MUI 9 (`@mui/material`, emotion), иконки `@tabler/icons-react`, шрифт Manrope через `@fontsource/manrope` (в Plus Jakarta Sans из шаблона нет кириллицы).
- `react-router` 7.
- `@tanstack/react-query` 5 — загрузка, кэш, инвалидация.
- `openapi-typescript` (генерация типов) + `openapi-fetch` (типизированный клиент).
- `react-hook-form` — формы.
- `notistack` — всплывающие уведомления.
- Vitest, `@testing-library/react`, `@testing-library/user-event`, MSW — тесты.
- ESLint 9 (typescript-eslint, react-hooks, `eslint-plugin-import`; плагин не поддерживает ESLint 10), Prettier.
- Менеджер пакетов npm, Node 24 (`.nvmrc`).

## 3. Структура

Код в `frontend/` того же репозитория. Структура `frontend/src` — по функциональным модулям:

```
app/            точка входа, провайдеры (тема, QueryClient, SnackbarProvider, AuthProvider), роутер
theme/          тема Modernize на TS (palette, typography, shadows, components overrides)
layout/         FullLayout (сайдбар + шапка), BlankLayout, конфиг меню, страницы 404 и «Нет доступа»
api/            schema.d.ts (сгенерирован), client.ts (openapi-fetch + middleware), errors.ts (ApiError)
shared/ui/      DataTable, FilterBar, поля форм, FormDialog, EntityAutocomplete, ConfirmDialog,
                BlockersDialog, PageContainer, DashboardCard, StatusPage, FullScreenLoader
shared/lib/     useUrlFilters, форматирование дат/чисел (ru-RU), applyApiErrors, useDocumentTitle
shared/lookups/ общие запросы для нескольких фич: список отделов, имена пользователей, варианты ответственных
features/
  auth/         AuthProvider, useAuth, вход, смена пароля, профиль, RequireAuth, RequireRole
  home/         заглушка главной
  users/        администрирование пользователей
  departments/  администрирование отделов
  directories/  справочники (один экран с вкладками)
```

Каждая фича экспортирует публичное API через `features/<name>/index.ts`. Правило границ (ESLint `import/no-restricted-paths`, ошибка ломает CI):
- фича импортирует другую фичу только через её `index.ts`;
- `shared/`, `api/`, `theme/` не импортируют `features/`, `layout/`, `app/`;
- `layout/` не импортирует `features/`, кроме `features/auth` через `index.ts`;
- фичи не импортируют `layout/` и `app/` (поэтому страница «Нет доступа» — `shared/ui/StatusPage`).

## 4. Каркас

- **FullLayout** (стиль Modernize): сайдбар 270 px с логотипом «IT-платформа» и меню; шапка с кнопкой сворачивания меню, именем и ролью пользователя, меню профиля («Профиль», «Сменить пароль», «Выйти»). На ширине < `lg` сайдбар — временная выдвижная панель (`Drawer`).
- **Меню:** «Главная», «Профиль»; для роли `admin` — группа «Администрирование»: «Пользователи», «Отделы», «Справочники». Пункты скрываются по роли.
- **BlankLayout** — для входа и обязательной смены пароля.
- Страницы «Страница не найдена» (404) и «Нет доступа» (403).
- Весь интерфейс на русском; даты и числа — `Intl` с локалью `ru-RU`. Названия ролей: `employee` — «Сотрудник», `manager` — «Руководитель», `admin` — «Администратор».
- `document.title` задаётся страницей: «<Раздел> — IT-платформа».

Маршруты:

| Путь | Экран | Доступ |
|---|---|---|
| `/login` | Вход | гость |
| `/change-password` | Смена пароля | вошедший (в т. ч. с `must_change_password`) |
| `/` | Главная | вошедший |
| `/profile` | Профиль | вошедший |
| `/admin/users` | Пользователи | admin |
| `/admin/departments` | Отделы | admin |
| `/admin/directories/:kind` | Справочники (`locations`, `asset-types`, `stock-categories`, `issue-reasons`, `ticket-types`); `/admin/directories` → `/admin/directories/locations` | admin |
| `*` | 404 | все |

## 5. Типы API

- `npm run gen:api` — `openapi-typescript ../backend/openapi.json -o src/api/schema.d.ts`; файл коммитится.
- `npm run check:api` — генерирует во временный файл и сравнивает с закоммиченным; расхождение — ошибка (запускается в CI).
- Makefile: цель `gen-api` = `make openapi` + `npm run gen:api`.
- Типы сущностей в коде берутся только из `components["schemas"][...]`, ручные дубли DTO запрещены.

## 6. Аутентификация и сессия

**Хранение.** Access-токен — только в памяти (модуль `api/client.ts`), не в localStorage/sessionStorage. Refresh-токен — HttpOnly-cookie от backend (`Path=/api/auth`, `SameSite=Strict`), JS его не видит.

**Старт приложения.** `AuthProvider` вызывает `POST /api/auth/refresh`; при успехе — `GET /api/auth/me`. До окончания проверки показывается полноэкранный индикатор загрузки. 401 на refresh — состояние «гость».

**Вход.** `POST /api/auth/login` → access-токен + `must_change_password` → `GET /api/auth/me` → переход на исходную страницу (`?next=`, только относительные пути внутри приложения) или `/`. Если `must_change_password` — на `/change-password`.

**Single-flight refresh** (требование backend: параллельные refresh с одним cookie недопустимы):
- middleware клиента при 401 на любом запросе, кроме `/auth/login`, `/auth/refresh`, `/auth/logout`, `/auth/change-password`, вызывает общий `refreshAccessToken()`;
- внутри вкладки — один промис на все параллельные вызовы; между вкладками — `navigator.locks.request('it-platform-refresh', …)`; если после получения lock токен уже обновлён другим вызовом (сравнение с токеном на момент 401), повторный refresh не делается;
  - вкладки не делят access-токен: каждая вкладка обновляет свой токен сама, но строго по очереди под общим lock, поэтому backend никогда не получает два refresh с одним cookie одновременно;
- исходный запрос повторяется один раз с новым токеном; повторный 401 — выход;
- неудачный refresh → сессия очищается, кэш Query очищается, переход на `/login?next=<текущий путь>`.

**Выход.** `POST /api/auth/logout` (ошибки игнорируются), очистка токена и кэша Query, сообщение `logout` в `BroadcastChannel('it-platform-auth')` — остальные вкладки очищают сессию и переходят на `/login`. Вход в одной вкладке другие вкладки не синхронизирует.

**Смена пароля.** Форма: текущий пароль, новый, повтор (совпадение проверяется на клиенте). `POST /api/auth/change-password`. Backend отзывает все прежние refresh-токены и возвращает новую пару (access-токен в ответе, refresh — новым cookie): клиент сохраняет новый access-токен, перезапрашивает `GET /api/auth/me`, показывает уведомление «Пароль изменён» и переходит на `?next=` или `/`. Остальные вкладки при следующем 401 обновятся через refresh уже с новым cookie. Режим обязательной смены (при `must_change_password` или ответе `403 password_change_required` на любом запросе) — отдельная страница в BlankLayout, остальные маршруты перенаправляют на неё, доступна кнопка «Выйти».

**Guard'ы.** `RequireAuth` (гость → `/login?next=`), `RequireRole('admin')` (иначе страница «Нет доступа»), `GuestOnly` для `/login` (вошедший → `/`). Guard'ы — удобство UI; права проверяет backend.

## 7. Клиент API и ошибки

- Один экземпляр `openapi-fetch` с `baseUrl` = `""` (пути в схеме уже начинаются с `/api`), `credentials: "same-origin"`.
- Middleware: подстановка `Authorization: Bearer`, обработка 401 (п. 6), приведение ошибок.
- Все неуспешные ответы превращаются в `ApiError { status, code, message, details, requestId }`; сетевой сбой — `ApiError` со `status: 0`, `code: "network_error"`, сообщение «Нет связи с сервером». Ответ без ожидаемого формата — `code: "unknown_error"`, сообщение «Не удалось выполнить запрос».
- Хуки фич оборачивают вызовы клиента в TanStack Query (`queryKey` по фиче: `["users", "list", filters]` и т. п.); мутации инвалидируют ключи своей фичи.
- QueryClient: `retry` только для сетевых ошибок и 5xx (до 2 раз), без retry для 4xx; `refetchOnWindowFocus: false`; `staleTime` 30 с.

Отображение:
- **422** — `applyApiErrors(error, setError, options)`: элементы `details` с путём поля (`loc`) ставят на поле «Некорректное значение» (`msg` pydantic — на английском); остальное — сообщение над формой (`Alert`). Коды backend с известным полем (`department_name_taken` → `name`, `email_taken` → `email`, `head_not_found`/`head_invalid_role` → `head_id`, `invalid_default_assignee` → `default_assignee_id`, `*_blank` → соответствующее поле) сопоставляются через словарь в фиче.
- **409** — сообщение `message` над формой; `deactivation_blocked` и `role_change_blocked` — `BlockersDialog` со списком из `details`.
- **429 `login_locked`** — на форме входа сообщение backend.
- **401 на `/auth/login`** — «Неверный email или пароль» (текст backend).
- **Сеть / 5xx** — сообщение там, где выполнялось действие (ошибка с «Повторить» в таблице, `Alert` в форме, snackbar для действий в меню строки); `requestId` из заголовка `X-Request-ID` пишется в `console.error` для всех запросов и мутаций (кэши TanStack Query).
- Тексты ошибок берутся из `message` backend; собственные тексты фронтенда — только для `network_error`/`unknown_error` и клиентской валидации.

## 8. Общие компоненты (`shared/ui`)

- **`DataTable<T>`** — MUI `Table` в стиле Modernize. Пропсы: `columns` (заголовок, рендер ячейки, ширина, выравнивание), `rows`, `getRowId`, `loading`, `error` (с кнопкой «Повторить»), `emptyText`, `rowActions` (меню «⋯»: подпись, иконка, скрытие/блокировка по строке), `pagination` — серверный режим (`total`, `limit`, `offset`, `onChange`) или клиентский. Размеры страницы 25/50/100, подписи `TablePagination` на русском.
- **`useUrlFilters(schema)`** — типизированное чтение/запись фильтров и пагинации в search params; смена фильтра сбрасывает `offset`; невалидные значения отбрасываются.
- **`FilterBar`** — поиск (debounce 300 мс), селекты, переключатели; связан с `useUrlFilters`.
- **Поля форм** — `FormTextField`, `FormSelect`, `FormSwitch`, `FormAutocomplete` поверх `Controller` react-hook-form, показывают ошибку поля.
- **`FormDialog`** — модальная форма: заголовок, тело, «Отмена»/«Сохранить», блокировка на время отправки, `Alert` с общей ошибкой, закрытие по Esc запрещено во время отправки.
- **`EntityAutocomplete`** — асинхронный выбор: `fetchOptions(q)`, debounce 300 мс, минимум 0 символов (первые результаты при открытии), варианты `{ id, label }`, подпись текущего значения через `labelFor(id)`. Первое применение — выбор ответственного (руководитель отдела, исполнитель по умолчанию) через `GET /api/admin/users?q=&is_active=true` с отбором Manager/Admin на клиенте: `GET /api/users` требует непустой `q` и не фильтрует по роли.
- **`ConfirmDialog`**, **`BlockersDialog`** (заголовок + список `details`), **`PageContainer`** (заголовок, хлебные крошки, слот действий), **`DashboardCard`** (карточка Modernize).
- Уведомления — `notistack` (`enqueueSnackbar`), успех операций — «Сохранено», «Пользователь деактивирован» и т. п.

## 9. Экраны

1. **Вход** (`/login`) — карточка Modernize по центру: логотип, email, пароль, «Войти». Клиентская проверка: поля не пустые. Ошибки по п. 7.
2. **Смена пароля** (`/change-password`) — п. 6.
3. **Профиль** (`/profile`) — ФИО, email, роль, отдел (название из `GET /api/departments`), кнопка «Сменить пароль».
4. **Главная** (`/`) — приветствие «Здравствуйте, <имя>» и 3–4 `DashboardCard`-заглушки с текстом «Появится в следующих версиях».
5. **Пользователи** (`/admin/users`):
   - таблица: ФИО, email, роль, отдел, статус (чип «Активен»/«Деактивирован»; пометка «Временный пароль» при `must_change_password`), дата создания;
   - фильтры: поиск `q`, роль, отдел, статус (все/активные/деактивированные); серверная пагинация `GET /api/admin/users`;
   - «Добавить»: ФИО, email, роль, отдел (селект из `GET /api/departments`, пусто — «Без отдела») → `POST /api/admin/users` → диалог с временным паролем, кнопкой «Скопировать» и предупреждением, что пароль показывается один раз;
   - «Редактировать»: ФИО, роль, отдел → `PATCH /api/admin/users/{id}` (отправляются только изменённые поля);
   - «Деактивировать» (подтверждение; `deactivation_blocked` → `BlockersDialog`; `cannot_deactivate_self`/`last_admin` → сообщение), «Активировать»;
   - «Выдать временный пароль» (подтверждение → диалог с паролем), «Снять блокировку входа» (подтверждение → уведомление).
6. **Отделы** (`/admin/departments`):
   - таблица: название, руководитель; клиентская пагинация и поиск по названию;
   - «Добавить»/«Редактировать»: название, руководитель (`EntityAutocomplete`, можно очистить) → `POST /api/admin/departments` / `PATCH /api/admin/departments/{id}`;
   - имена руководителей — из `GET /api/admin/users?limit=200` (кэшируется); если руководитель не найден в ответе — «Пользователь #<id>».
7. **Справочники** (`/admin/directories/:kind`) — вкладки: «Локации», «Типы техники», «Категории расходников», «Причины выдачи», «Типы заявок». Один компонент экрана и конфиг на справочник:
   - общие поля: название, статус; дополнительные: локации — описание; причины выдачи — применимость («Техника»/«Расходники»/«Техника и расходники»); типы заявок — код (только при создании, в таблице отображается), «Требует согласования», исполнитель по умолчанию (`EntityAutocomplete`);
   - переключатель «Показывать неактивные» (`include_inactive`), клиентская пагинация;
   - действия: «Добавить», «Редактировать», «Деактивировать»/«Активировать» (`PATCH` с `is_active`); удаления нет;
   - имена исполнителей по умолчанию — как для руководителей отделов.

## 10. Тесты

Vitest + Testing Library + MSW (`msw/node` в тестах). Обработчики MSW типизируются типами из `schema.d.ts`.

Обязательные тесты:
- **api/client:** подстановка токена; несколько параллельных 401 → ровно один refresh, все запросы повторены; неудачный refresh → сессия очищена и вызван обработчик выхода; повторный 401 после refresh → выход; разбор `ApiError` (формат backend, не-JSON, сетевой сбой).
- **shared/lib:** `applyApiErrors` (поле из `loc`, поле из словаря кодов, общее сообщение); `useUrlFilters` (чтение, запись, сброс offset, невалидные значения).
- **shared/ui:** `DataTable` (строки, пусто, ошибка с повтором, серверная пагинация); `EntityAutocomplete` (поиск, выбор, очистка); `FormDialog` с ошибкой 422 по полю.
- **auth:** вход — успех, 401, 429; старт с действующим cookie; `must_change_password` → принудительная смена; `RequireRole` для не-admin → «Нет доступа»; выход.
- **users:** создание → показ временного пароля; деактивация с `deactivation_blocked` → список причин; фильтр в URL влияет на запрос.
- **departments:** 409 `department_name_taken` → ошибка под полем.
- **directories:** переключение вкладок; деактивация элемента; поле «код» только при создании типа заявки.

## 11. Качество и CI

- `npm run check` = `tsc --noEmit` + `eslint .` (max-warnings 0) + `prettier --check .` + `vitest run` + `check:api`.
- `npm run build` — `tsc -b && vite build`.
- `.github/workflows/ci.yml` — новая задача `frontend`: `actions/setup-node` (Node из `.nvmrc`, кэш npm), `npm ci`, `npm run check`, `npm run build`. `check:api` читает `backend/openapi.json` из репозитория, backend в этой задаче не запускается.
- Makefile: `frontend-dev`, `frontend-check`, `gen-api`. README — раздел «Фронтенд» (запуск, генерация типов, структура, правила границ).

## 12. Локальная разработка

- `npm run dev` — Vite на `localhost:5173`, `server.proxy['/api'] = 'http://localhost:8000'` (`changeOrigin: false`, чтобы cookie оставались first-party для `localhost:5173`).
- Backend локально запускается как раньше; `COOKIE_SECURE=false` в локальном окружении уже задан.

## 13. Production-образ и compose

- `frontend/Dockerfile`: этап `node:24-alpine` (`npm ci`, `npm run build`) → `nginx:1.29-alpine` со статикой из `dist/` и `nginx.conf`. Имя `backend` разрешается при запросе (`resolver 127.0.0.11` и переменная в `proxy_pass`), чтобы nginx стартовал без backend.
- `frontend/nginx.conf`:
  - `location /api/` → проксирование на `http://backend:8000` с `proxy_set_header Host $host`, `X-Forwarded-For $remote_addr` (перезапись, не добавление), `X-Forwarded-Proto $scheme`; `/health` и `/ready` наружу не проксируются;
  - SPA-fallback: `try_files $uri /index.html;`;
  - `/assets/` — `Cache-Control: public, max-age=31536000, immutable`; `index.html` — `no-cache`;
  - заголовки: `X-Content-Type-Options: nosniff`, `Referrer-Policy: same-origin`, `X-Frame-Options: DENY`, `Content-Security-Policy: default-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'self'; frame-ancestors 'none'`.
- `frontend/.dockerignore`: `node_modules`, `dist`, `coverage`.
- `compose.yaml`: сервис `frontend` (build `./frontend`, порт `127.0.0.1:8080:80`, `depends_on: backend`). Подсеть сети compose фиксируется (`172.28.0.0/16`), сервису `backend` задаётся `TRUSTED_PROXIES='["172.28.0.0/16"]'`, чтобы IP клиента брался из `X-Forwarded-For` nginx.
- HTTPS, домен и staging-развёртывание — вне этого плана.

## 14. Ветка и порядок работ

Ветка `feature/sprint1-frontend` от `feature/sprint1-backend`. Изменения backend в этом плане не предполагаются; если для экрана не хватит API — фиксируется отдельной задачей плана с изменением backend, `openapi.json` и типов.

## 15. Критерии готовности

- `npm run check` и `npm run build` проходят; CI-задача `frontend` описана.
- `docker compose up` поднимает стек; на `http://localhost:8080` работают вход, смена пароля, выход, админка пользователей, отделов и справочников против реального backend (ручная проверка по сценарию из README).
- Типы API совпадают с `backend/openapi.json`.
- Нарушение границ фич ломает `eslint`.
