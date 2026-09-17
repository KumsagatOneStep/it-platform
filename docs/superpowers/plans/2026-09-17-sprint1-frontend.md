# Спринт 1, план 2 — фронтенд: план реализации

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Фронтенд IT-платформы в стиле шаблона Modernize: скелет на React + TypeScript, типы из OpenAPI, общие UI-компоненты (таблица с фильтрами и пагинацией, формы, автокомплит) и рабочие экраны на готовом backend — вход, смена пароля, профиль, администрирование пользователей, отделов и справочников; Docker-образ, compose и CI.

**Architecture:** Одностраничное приложение `frontend/` (Vite). Слои: `api/` (типизированный клиент openapi-fetch с single-flight refresh), `theme/`, `shared/` (ui, lib, lookups), `layout/` (каркас), `features/<модуль>/`, `app/` (провайдеры и маршруты). Серверное состояние — TanStack Query, формы — react-hook-form, фильтры списков — в URL. Границы слоёв и фич проверяет ESLint. В production nginx отдаёт статику и проксирует `/api` на backend (один домен).

**Tech Stack:** Node 24, npm, Vite 8, React 19, TypeScript 5.9 (strict), MUI 9, @tabler/icons-react, @fontsource/manrope, react-router 7, @tanstack/react-query 5, openapi-typescript 7 + openapi-fetch 0.17, react-hook-form 7, notistack 3, Vitest 5 + Testing Library + MSW 2 (jsdom), ESLint 9 + typescript-eslint + eslint-plugin-import, Prettier 3, nginx (alpine), GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-09-17-sprint1-frontend-design.md` (дизайн фронтенда); ТЗ — `docs/spec/TZ_IT_platforma_v1.2.md` (п. 1.2, 2.1, 2.4, 3.2, 4.7, 7.3, 8, 9). API — `backend/openapi.json` ветки `feature/sprint1-backend`.

**Как проверен план.** Весь код плана собран и прогнан до записи: задачи применялись по порядку к пустому каталогу, после каждой — `tsc`, ESLint, Prettier, Vitest и `check:api` без ошибок (итого 56 тестов); `vite build` без предупреждений; Docker-образ собран, `nginx -t` успешен, SPA-fallback и заголовки проверены. Если после `npm install` версия пакета отличается и поведение расходится с планом — адаптировать минимально и описать в отчёте.

## Уточнения к спецификации

Выявлены при проверке кода плана; дизайн-документ обновлён в том же коммите.

1. **Шрифт — Manrope** вместо Plus Jakarta Sans: в Plus Jakarta Sans нет базовой кириллицы (только `cyrillic-ext`), русский текст рисовался бы запасным шрифтом. Manrope близок по начертанию.
2. **Кнопки без `textTransform: capitalize`** из шаблона: для русского текста получается «Сменить Пароль».
3. **Выбор руководителя и исполнителя по умолчанию** — через `GET /api/admin/users?q=&is_active=true` с отбором Manager/Admin на клиенте, а не `GET /api/users?q=`: публичный поиск требует непустой `q` и не фильтрует по роли. Все такие формы — только для администратора.
4. **`shared/lookups/`** — общие запросы, нужные нескольким фичам (список отделов, имена пользователей, варианты ответственных), чтобы фичи не импортировали друг друга по кругу.
5. **`StatusPage` и `FullScreenLoader` — в `shared/ui`**: страница «Нет доступа» показывается guard'ом из `features/auth`, а фичам запрещено импортировать `layout/`. `layout/NotFoundPage` использует `StatusPage`.
6. **Ошибки валидации pydantic под полем** показываются как «Некорректное значение»: `msg` из `details` — на английском. Над формой — русское `message` backend.
7. **Версии:** TypeScript 5.9 (openapi-typescript и typescript-eslint не поддерживают 6+/7), ESLint 9 (eslint-plugin-import не поддерживает 10), react-router 7.
8. **nginx разрешает имя `backend` при запросе** (`resolver 127.0.0.11`), чтобы контейнер фронтенда стартовал независимо от backend.
9. **compose фиксирует подсеть** `172.28.0.0/16`, и backend получает её в `TRUSTED_PROXIES` — иначе nginx в той же сети не считается доверенным прокси и все пользователи делят один IP для защиты от перебора.

## Global Constraints

- Node 24 (`frontend/.nvmrc`), npm; все команды фронтенда выполняются из каталога `frontend/`, если не сказано иное.
- React + TypeScript (Vite), `strict: true`; типы API — только из `src/api/schema.d.ts`, сгенерированного `openapi-typescript` из `backend/openapi.json`; ручные дубли DTO запрещены; `npm run check:api` проверяет актуальность в CI.
- Структура `frontend/src`: `app/`, `theme/`, `layout/`, `api/`, `shared/{ui,lib,lookups}`, `features/{auth,home,users,departments,directories}`. Фича импортирует другую фичу только через её `index.ts`; `api`, `theme`, `shared` не импортируют `features`, `layout`, `app`; `layout` использует из фич только `features/auth` через `index.ts`; фичи не импортируют `layout` и `app` — нарушение ломает `eslint` (CI).
- Интерфейс на русском; даты и числа — `Intl` с локалью `ru-RU`; роли: `employee` — «Сотрудник», `manager` — «Руководитель», `admin` — «Администратор». Заголовок вкладки: «<Раздел> — IT-платформа».
- Визуальный стиль — Modernize (MUI): палитра `primary #5D87FF`, скругление 7 px, тени и типографика шаблона; шрифт Manrope.
- Access-токен — только в памяти, не в localStorage/sessionStorage. Refresh — HttpOnly-cookie backend; refresh выполняется single-flight (промис внутри вкладки, Web Locks между вкладками).
- Формат ошибок API — `{"error": {"code", "message", "details"}}`; тексты ошибок для пользователя берутся из `message` backend; собственные тексты фронтенда — только для сетевых сбоев («Нет связи с сервером», «Не удалось выполнить запрос») и клиентской валидации.
- Элементы справочников не удаляются, а деактивируются (`is_active`).
- Фронтенд и API на одном домене: dev — прокси Vite `/api` → `localhost:8000`; production — nginx проксирует `/api/` на backend; CORS не используется.
- Каждая задача: тесты пишутся до кода (RED → GREEN); перед коммитом `npm run format && npm run check`; вывод тестов без предупреждений.
- Сообщения коммитов заканчиваются строкой `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>` (в шагах опущено для краткости).

## Структура файлов

```
frontend/
├── package.json, package-lock.json, .nvmrc, tsconfig.json, vite.config.ts, index.html
├── eslint.config.js, .prettierrc.json, .prettierignore
├── Dockerfile, .dockerignore, nginx.conf
├── scripts/check-api.mjs          сверка schema.d.ts с backend/openapi.json
└── src/
    ├── main.tsx
    ├── app/        App.tsx, providers.tsx, routes.tsx, queryClient.ts (+ тесты маршрутов и каркаса)
    ├── theme/      theme.ts
    ├── api/        schema.d.ts, types.ts, errors.ts, session.ts, refresh.ts, client.ts
    ├── layout/     FullLayout, BlankLayout, Sidebar, SidebarMenu, Header, UserMenu, Logo, menu.ts, NotFoundPage
    ├── shared/
    │   ├── lib/    format, applyApiErrors, useUrlFilters, useDebouncedValue, useDocumentTitle
    │   ├── lookups/ queryKeys, departments (useDepartments), users (useUserNames, searchResponsibleOptions)
    │   └── ui/     DataTable, FilterBar, EntityAutocomplete, FormDialog, ConfirmDialog, BlockersDialog,
    │               PageContainer, DashboardCard, StatusPage, FullScreenLoader, form/*
    ├── features/
    │   ├── auth/        AuthProvider, AuthContext, guards, next, LoginPage, ChangePasswordPage, ProfilePage
    │   ├── home/        HomePage
    │   ├── users/       UsersPage, UserFormDialog, TemporaryPasswordDialog, api
    │   ├── departments/ DepartmentsPage, DepartmentFormDialog, api
    │   └── directories/ DirectoriesPage, DirectoryFormDialog, config, api
    └── test/       setup.ts, server.ts, http.ts, render.tsx, auth.ts, app.tsx, fixtures.ts
```

Также меняются: `compose.yaml`, `.github/workflows/ci.yml`, `Makefile`, `README.md`.

---


### Task 1: Скелет проекта `frontend/`, инструменты, генерация типов API

**Files:**
- Create: `frontend/package.json`, `frontend/package-lock.json` (создаёт npm), `frontend/.nvmrc`
- Create: `frontend/tsconfig.json`, `frontend/vite.config.ts`, `frontend/index.html`
- Create: `frontend/eslint.config.js`, `frontend/.prettierrc.json`, `frontend/.prettierignore`
- Create: `frontend/scripts/check-api.mjs`, `frontend/src/api/schema.d.ts` (генерируется)
- Create: `frontend/src/main.tsx`, `frontend/src/app/App.tsx` (временный, заменяется в Task 7)
- Create: `frontend/src/test/setup.ts`, `frontend/src/test/server.ts`
- Test: `frontend/src/app/App.test.tsx` (временный, удаляется в Task 7)

**Interfaces:**
- Consumes: `backend/openapi.json` (спринт 1 backend).
- Produces: npm-скрипты `dev`, `build`, `typecheck`, `lint`, `format`, `format:check`, `test`, `gen:api`, `check:api`, `check`; тип `paths`/`components` в `src/api/schema.d.ts`; MSW-сервер `server` из `src/test/server.ts` (запущен для всех тестов, `onUnhandledRequest: "error"`); эмуляция `window.matchMedia` для ширины 1280px в тестах; правило границ `import/no-restricted-paths` в ESLint.

- [ ] **Step 1: Конфигурация проекта**

Все команды этого плана выполняются из каталога `frontend/`, если не сказано иное. Версии зафиксированы и проверены на совместимость: TypeScript 5.9 (openapi-typescript и typescript-eslint не поддерживают TypeScript 6+), ESLint 9 (eslint-plugin-import не поддерживает ESLint 10), react-router 7 (как в ТЗ-дизайне).

`frontend/package.json`:
```json
{
  "name": "it-platform-frontend",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "engines": {
    "node": ">=24"
  },
  "scripts": {
    "dev": "vite",
    "build": "tsc --noEmit && vite build",
    "preview": "vite preview",
    "typecheck": "tsc --noEmit",
    "lint": "eslint . --max-warnings 0",
    "format": "prettier --write .",
    "format:check": "prettier --check .",
    "test": "vitest run",
    "test:watch": "vitest",
    "gen:api": "openapi-typescript ../backend/openapi.json -o src/api/schema.d.ts",
    "check:api": "node scripts/check-api.mjs",
    "check": "npm run typecheck && npm run lint && npm run format:check && npm run test && npm run check:api"
  },
  "dependencies": {
    "@emotion/react": "^11.14.0",
    "@emotion/styled": "^11.14.1",
    "@fontsource/manrope": "^5.3.0",
    "@mui/material": "^9.4.0",
    "@tabler/icons-react": "^3.46.0",
    "@tanstack/react-query": "^5.103.1",
    "notistack": "^3.0.2",
    "openapi-fetch": "^0.17.0",
    "react": "^19.3.0",
    "react-dom": "^19.3.0",
    "react-hook-form": "^7.88.0",
    "react-router": "^7.18.4"
  },
  "devDependencies": {
    "@eslint/js": "^9.39.5",
    "@testing-library/dom": "^10.4.2",
    "@testing-library/jest-dom": "^7.0.1",
    "@testing-library/react": "^16.3.3",
    "@testing-library/user-event": "^14.6.7",
    "@types/node": "^24.13.5",
    "@types/react": "^19.3.0",
    "@types/react-dom": "^19.3.0",
    "@vitejs/plugin-react": "^6.1.1",
    "eslint": "^9.39.5",
    "eslint-import-resolver-typescript": "^4.4.5",
    "eslint-plugin-import": "^2.32.0",
    "eslint-plugin-react-hooks": "^7.1.1",
    "globals": "^17.12.0",
    "jsdom": "^30.1.0",
    "msw": "^2.15.0",
    "openapi-typescript": "^7.13.0",
    "prettier": "^3.9.7",
    "typescript": "~5.9.3",
    "typescript-eslint": "^8.70.0",
    "vite": "^8.3.0",
    "vitest": "^5.0.1"
  }
}
```

`frontend/.nvmrc`:
```
24
```

`frontend/tsconfig.json`:
```json
{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["ES2023", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "moduleResolution": "bundler",
    "jsx": "react-jsx",
    "strict": true,
    "noUncheckedIndexedAccess": true,
    "verbatimModuleSyntax": true,
    "noEmit": true,
    "skipLibCheck": true,
    "types": ["vitest/globals", "@testing-library/jest-dom/vitest"]
  },
  "include": ["src", "vite.config.ts"]
}
```

`frontend/vite.config.ts`:
```ts
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react()],
  // MUI + TanStack Query + react-router дают один чанк ~700 КБ; для внутреннего инструмента это приемлемо.
  build: { chunkSizeWarningLimit: 1000 },
  server: {
    port: 5173,
    strictPort: true,
    proxy: { "/api": { target: "http://localhost:8000", changeOrigin: false } },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test/setup.ts"],
  },
});
```

`frontend/index.html`:
```html
<!doctype html>
<html lang="ru">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>IT-платформа</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

`frontend/.prettierrc.json`:
```json
{ "printWidth": 100 }
```

`frontend/.prettierignore`:
```
dist
coverage
node_modules
package-lock.json
src/api/schema.d.ts
```

`frontend/eslint.config.js`:
```js
import js from "@eslint/js";
import importPlugin from "eslint-plugin-import";
import reactHooks from "eslint-plugin-react-hooks";
import globals from "globals";
import tseslint from "typescript-eslint";

const FEATURES = ["auth", "home", "users", "departments", "directories"];

// Фича импортирует другую фичу только через её публичный index.ts.
const featureZones = FEATURES.flatMap((target) =>
  FEATURES.filter((from) => from !== target).map((from) => ({
    target: `./src/features/${target}`,
    from: `./src/features/${from}`,
    except: ["./index.ts"],
    message: "Другая фича импортируется только через её index.ts",
  })),
);

export default tseslint.config(
  { ignores: ["dist", "coverage", "src/api/schema.d.ts"] },
  {
    files: ["src/**/*.{ts,tsx}", "vite.config.ts"],
    extends: [js.configs.recommended, ...tseslint.configs.recommended],
    languageOptions: { globals: globals.browser },
    plugins: { "react-hooks": reactHooks, import: importPlugin },
    settings: { "import/resolver": { typescript: { project: "./tsconfig.json" } } },
    rules: {
      "react-hooks/rules-of-hooks": "error",
      "react-hooks/exhaustive-deps": "error",
      "@typescript-eslint/consistent-type-imports": "error",
      "import/no-restricted-paths": [
        "error",
        {
          zones: [
            {
              target: ["./src/api", "./src/theme", "./src/shared"],
              from: ["./src/features", "./src/layout", "./src/app"],
              message: "api, theme и shared не зависят от features, layout и app",
            },
            {
              target: "./src/layout",
              from: "./src/features",
              except: ["./auth/index.ts"],
              message: "layout использует из фич только features/auth через index.ts",
            },
            {
              target: "./src/features",
              from: ["./src/layout", "./src/app"],
              message: "Фичи не зависят от layout и app",
            },
            ...featureZones,
          ],
        },
      ],
    },
  },
);
```

`frontend/scripts/check-api.mjs`:
```js
// Проверяет, что src/api/schema.d.ts сгенерирован из актуального backend/openapi.json.
import { execFileSync } from "node:child_process";
import { mkdtempSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const COMMITTED = "src/api/schema.d.ts";
const dir = mkdtempSync(join(tmpdir(), "openapi-types-"));
const generated = join(dir, "schema.d.ts");

try {
  execFileSync(
    join("node_modules", ".bin", "openapi-typescript"),
    [process.env.OPENAPI_PATH ?? "../backend/openapi.json", "-o", generated],
    { stdio: "ignore" },
  );
  if (readFileSync(generated, "utf8") !== readFileSync(COMMITTED, "utf8")) {
    console.error(`${COMMITTED} устарел: выполните \`npm run gen:api\` и закоммитьте результат`);
    process.exitCode = 1;
  }
} finally {
  rmSync(dir, { recursive: true, force: true });
}
```

- [ ] **Step 2: Установить зависимости и сгенерировать типы API**

```bash
node --version   # v24.x
npm install
npm run gen:api
```

Ожидается: создан `package-lock.json`, `src/api/schema.d.ts` содержит `export interface paths` с ключом `"/api/admin/users"`. npm 11 может предупредить `allow-scripts` про install-скрипты `msw` и `unrs-resolver` — это не ошибка, скрипты для работы не нужны, одобрять их не требуется.

- [ ] **Step 3: Написать смоук-тест и тестовое окружение**

`frontend/src/test/server.ts`:
```ts
import { setupServer } from "msw/node";

export const server = setupServer();
```

`frontend/src/test/setup.ts`:
```ts
import "@testing-library/jest-dom/vitest";

import { server } from "./server";

// jsdom не реализует matchMedia: эмулируем окно шириной 1280px (десктоп, брейкпоинт lg),
// чтобы useMediaQuery в тестах вёл себя как в браузере.
const TEST_VIEWPORT_WIDTH = 1280;

function matchesQuery(query: string): boolean {
  const min = /min-width:\s*([\d.]+)px/.exec(query);
  const max = /max-width:\s*([\d.]+)px/.exec(query);
  return (
    (!min || TEST_VIEWPORT_WIDTH >= Number(min[1])) &&
    (!max || TEST_VIEWPORT_WIDTH <= Number(max[1]))
  );
}

Object.defineProperty(window, "matchMedia", {
  writable: true,
  value: (query: string): MediaQueryList =>
    ({
      matches: matchesQuery(query),
      media: query,
      onchange: null,
      addEventListener: () => undefined,
      removeEventListener: () => undefined,
      addListener: () => undefined,
      removeListener: () => undefined,
      dispatchEvent: () => false,
    }) as MediaQueryList,
});

beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());
```

`frontend/src/app/App.test.tsx`:
```tsx
import { render, screen } from "@testing-library/react";

import { App } from "./App";

test("приложение рендерится", () => {
  render(<App />);

  expect(screen.getByRole("heading", { name: "IT-платформа" })).toBeInTheDocument();
});
```

- [ ] **Step 4: Запустить тест — он падает**

Run: `npx vitest run src/app/App.test.tsx`
Expected: FAIL — `Failed to resolve import "./App"`.

- [ ] **Step 5: Точка входа и временный `App`**

`frontend/src/app/App.tsx`:
```tsx
export function App() {
  return <h1>IT-платформа</h1>;
}
```

`frontend/src/main.tsx`:
```tsx
import "@fontsource/manrope/400.css";
import "@fontsource/manrope/500.css";
import "@fontsource/manrope/600.css";
import "@fontsource/manrope/700.css";

import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { App } from "./app/App";

const root = document.getElementById("root");
if (!root) throw new Error("Не найден элемент #root");

createRoot(root).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
```

`src/main.tsx` импортирует `./app/App` — в Task 7 `App` заменяется полноценным, `main.tsx` больше не меняется. Шрифт — Manrope: в Plus Jakarta Sans из шаблона Modernize нет кириллицы (см. «Уточнения к спецификации»).

- [ ] **Step 6: Тест проходит, проверки зелёные**

Run: `npx vitest run src/app/App.test.tsx` → PASS.

Run: `npm run format && npm run check && npm run build`
Expected: `tsc` без ошибок, ESLint без предупреждений, Prettier чистый, 1 тест пройден, `check:api` молчит (код 0), `vite build` без предупреждений.

- [ ] **Step 7: Убедиться, что правило границ работает**

```bash
mkdir -p src/shared && printf 'import { App } from "../app/App";\nexport const x = App;\n' > src/shared/boundary-probe.ts
npx eslint src/shared/boundary-probe.ts
```

Expected: `error  Unexpected path "../app/App" imported in restricted zone. api, theme и shared не зависят от features, layout и app  import/no-restricted-paths`. Затем удалить пробный файл: `rm src/shared/boundary-probe.ts`.

- [ ] **Step 8: Проверить генерацию в режиме проверки**

```bash
printf '\n// stale\n' >> src/api/schema.d.ts && npm run check:api; echo "exit=$?"
git checkout -- src/api/schema.d.ts 2>/dev/null || npm run gen:api
npm run check:api && echo ok
```

Expected: первый запуск печатает `src/api/schema.d.ts устарел: выполните \`npm run gen:api\` и закоммитьте результат` и `exit=1`; после восстановления — `ok`.

- [ ] **Step 9: Commit**

```bash
cd .. && git add frontend && git commit -m "feat(frontend): скелет проекта, инструменты, типы из OpenAPI"
```


### Task 2: Клиент API: ошибки, сессия, single-flight refresh

**Files:**
- Create: `frontend/src/api/types.ts`, `frontend/src/api/errors.ts`, `frontend/src/api/session.ts`, `frontend/src/api/refresh.ts`, `frontend/src/api/client.ts`
- Create: `frontend/src/test/http.ts`
- Modify: `frontend/src/test/setup.ts` (сброс сессии после каждого теста)
- Test: `frontend/src/api/client.test.ts`, `frontend/src/api/errors.test.ts`

**Interfaces:**
- Consumes: `paths`, `components` из `src/api/schema.d.ts` (Task 1); `server` (Task 1).
- Produces:
  - `types.ts`: `Schemas = components["schemas"]`, `UserRole`, `Me`.
  - `errors.ts`: `class ApiError { status; code; message; details: unknown; requestId: string | null }`, `NETWORK_ERROR_MESSAGE`, `UNKNOWN_ERROR_MESSAGE`, `interface Blocker { kind; entity_id; title }`, `interface ValidationIssue { loc; msg; type }`, `apiErrorFromBody(status, body, requestId)`, `networkError()`, `toApiError(error)`, `isRetryableError(error): boolean`, `blockersOf(error): Blocker[]`, `validationIssuesOf(error): ValidationIssue[]`.
  - `session.ts`: `getAccessToken()`, `setAccessToken(token | null)`, `setSessionHandlers({ onSessionExpired, onPasswordChangeRequired }): () => void` (возвращает функцию отписки), `sessionHandlers()`, `resetSession()`.
  - `refresh.ts`: `refreshAccessToken(staleToken: string | null): Promise<string | null>`.
  - `client.ts`: `api` (openapi-fetch клиент `paths`), `unwrap<D>(request): Promise<D>` — данные или `throw ApiError`.
  - `test/http.ts`: `errorBody(code, message, details = null)`.

- [ ] **Step 1: Написать падающие тесты**

Тесты клиента фиксируют требования дизайна (п. 6–7): токен в `Authorization`, ровно один refresh на параллельные 401, повтор запроса с телом, завершение сессии при неудачном refresh или повторном 401, отсутствие refresh для `/api/auth/login`, сигнал `password_change_required`. Обработчики MSW задаются шаблоном `*/api/...`: в jsdom origin — `http://localhost:3000`.

`frontend/src/test/http.ts`:
```ts
export function errorBody(code: string, message: string, details: unknown = null) {
  return { error: { code, message, details } };
}
```

`frontend/src/api/client.test.ts`:
```ts
import { delay, http, HttpResponse } from "msw";

import { errorBody } from "../test/http";
import { server } from "../test/server";
import { api, unwrap } from "./client";
import { ApiError } from "./errors";
import { getAccessToken, setAccessToken, setSessionHandlers } from "./session";
import type { Schemas } from "./types";

const department: Schemas["DepartmentRead"] = { id: 1, name: "ИТ", head_id: null };

function refreshHandler(counter: { calls: number }, token = "fresh") {
  return http.post("*/api/auth/refresh", async () => {
    counter.calls += 1;
    await delay(10);
    return HttpResponse.json<Schemas["AccessTokenResponse"]>({
      access_token: token,
      token_type: "bearer",
      must_change_password: false,
    });
  });
}

function departmentsRequiring(token: string) {
  return http.get("*/api/departments", ({ request }) =>
    request.headers.get("Authorization") === `Bearer ${token}`
      ? HttpResponse.json<Schemas["DepartmentRead"][]>([department])
      : HttpResponse.json(errorBody("unauthorized", "Требуется вход"), { status: 401 }),
  );
}

function trackSession() {
  const calls = { expired: 0, passwordChange: 0 };
  setSessionHandlers({
    onSessionExpired: () => (calls.expired += 1),
    onPasswordChangeRequired: () => (calls.passwordChange += 1),
  });
  return calls;
}

test("подставляет access-токен в заголовок Authorization", async () => {
  setAccessToken("t1");
  server.use(departmentsRequiring("t1"));

  await expect(unwrap(api.GET("/api/departments"))).resolves.toEqual([department]);
});

test("параллельные 401 приводят ровно к одному refresh и повтору всех запросов", async () => {
  setAccessToken("stale");
  const refresh = { calls: 0 };
  server.use(refreshHandler(refresh), departmentsRequiring("fresh"));

  const results = await Promise.all([
    unwrap(api.GET("/api/departments")),
    unwrap(api.GET("/api/departments")),
    unwrap(api.GET("/api/departments")),
  ]);

  expect(results).toEqual([[department], [department], [department]]);
  expect(refresh.calls).toBe(1);
  expect(getAccessToken()).toBe("fresh");
});

test("повтор запроса отправляет тело исходного запроса", async () => {
  setAccessToken("stale");
  server.use(
    refreshHandler({ calls: 0 }),
    http.patch("*/api/admin/departments/:id", async ({ request }) => {
      if (request.headers.get("Authorization") !== "Bearer fresh") {
        return HttpResponse.json(errorBody("unauthorized", "Требуется вход"), { status: 401 });
      }
      const body = (await request.json()) as Schemas["DepartmentUpdate"];
      return HttpResponse.json<Schemas["DepartmentRead"]>({ ...department, name: body.name ?? "" });
    }),
  );

  const updated = await unwrap(
    api.PATCH("/api/admin/departments/{department_id}", {
      params: { path: { department_id: 1 } },
      body: { name: "Бухгалтерия" },
    }),
  );

  expect(updated.name).toBe("Бухгалтерия");
});

test("неудачный refresh завершает сессию и отдаёт ошибку 401", async () => {
  setAccessToken("stale");
  const session = trackSession();
  server.use(
    http.post("*/api/auth/refresh", () =>
      HttpResponse.json(errorBody("invalid_refresh_token", "Сессия истекла, войдите снова"), {
        status: 401,
      }),
    ),
    departmentsRequiring("fresh"),
  );

  const error = await unwrap(api.GET("/api/departments")).catch((e: unknown) => e);

  expect(error).toBeInstanceOf(ApiError);
  expect((error as ApiError).status).toBe(401);
  expect(session.expired).toBe(1);
  expect(getAccessToken()).toBeNull();
});

test("401 после успешного refresh тоже завершает сессию", async () => {
  setAccessToken("stale");
  const session = trackSession();
  server.use(refreshHandler({ calls: 0 }), departmentsRequiring("never"));

  await expect(unwrap(api.GET("/api/departments"))).rejects.toMatchObject({ status: 401 });
  expect(session.expired).toBe(1);
});

test("401 на вход не запускает refresh", async () => {
  const refresh = { calls: 0 };
  server.use(
    refreshHandler(refresh),
    http.post("*/api/auth/login", () =>
      HttpResponse.json(errorBody("invalid_credentials", "Неверный email или пароль"), {
        status: 401,
      }),
    ),
  );

  await expect(
    unwrap(api.POST("/api/auth/login", { body: { email: "a@b.ru", password: "x" } })),
  ).rejects.toMatchObject({ code: "invalid_credentials", message: "Неверный email или пароль" });
  expect(refresh.calls).toBe(0);
});

test("403 password_change_required сообщает о необходимости сменить пароль", async () => {
  setAccessToken("t1");
  const session = trackSession();
  server.use(
    http.get("*/api/departments", () =>
      HttpResponse.json(errorBody("password_change_required", "Необходимо сменить пароль"), {
        status: 403,
      }),
    ),
  );

  await expect(unwrap(api.GET("/api/departments"))).rejects.toMatchObject({
    code: "password_change_required",
  });
  expect(session.passwordChange).toBe(1);
});
```

`frontend/src/api/errors.test.ts`:
```ts
import { http, HttpResponse } from "msw";

import { server } from "../test/server";
import { api, unwrap } from "./client";
import { ApiError, blockersOf, isRetryableError, validationIssuesOf } from "./errors";

test("ошибка в формате backend превращается в ApiError с request id", async () => {
  server.use(
    http.get("*/api/departments", () =>
      HttpResponse.json(
        { error: { code: "department_not_found", message: "Отдел не найден", details: null } },
        { status: 404, headers: { "X-Request-ID": "req-1" } },
      ),
    ),
  );

  const error = (await unwrap(api.GET("/api/departments")).catch((e: unknown) => e)) as ApiError;

  expect(error).toBeInstanceOf(ApiError);
  expect(error).toMatchObject({
    status: 404,
    code: "department_not_found",
    message: "Отдел не найден",
    requestId: "req-1",
  });
});

test("ответ не в формате backend даёт unknown_error", async () => {
  server.use(http.get("*/api/departments", () => new HttpResponse("Bad gateway", { status: 502 })));

  const error = (await unwrap(api.GET("/api/departments")).catch((e: unknown) => e)) as ApiError;

  expect(error).toMatchObject({
    status: 502,
    code: "unknown_error",
    message: "Не удалось выполнить запрос",
  });
  expect(isRetryableError(error)).toBe(true);
});

test("сетевой сбой даёт network_error", async () => {
  server.use(http.get("*/api/departments", () => HttpResponse.error()));

  const error = (await unwrap(api.GET("/api/departments")).catch((e: unknown) => e)) as ApiError;

  expect(error).toMatchObject({
    status: 0,
    code: "network_error",
    message: "Нет связи с сервером",
  });
  expect(isRetryableError(error)).toBe(true);
});

test("blockersOf и validationIssuesOf отбрасывают элементы неверной формы", () => {
  const blocked = new ApiError({
    status: 409,
    code: "deactivation_blocked",
    message: "Перед деактивацией нужно передать ответственность другим сотрудникам",
    details: [{ kind: "department_head", entity_id: 3, title: "Отдел «ИТ»" }, { kind: 1 }],
  });
  const invalid = new ApiError({
    status: 422,
    code: "validation_failed",
    message: "Некорректные данные запроса",
    details: [
      { loc: ["body", "email"], msg: "value is not a valid email", type: "value_error" },
      "x",
    ],
  });

  expect(blockersOf(blocked)).toEqual([
    { kind: "department_head", entity_id: 3, title: "Отдел «ИТ»" },
  ]);
  expect(validationIssuesOf(invalid)).toHaveLength(1);
  expect(isRetryableError(invalid)).toBe(false);
});
```

- [ ] **Step 2: Запустить тесты — падают**

Run: `npx vitest run src/api`
Expected: FAIL — `Failed to resolve import "./client"`.

- [ ] **Step 3: Реализация**

Важные детали, проверенные на этих версиях библиотек:
- `openapi-fetch` запоминает `fetch` при создании клиента, поэтому передаём обёртку `(request) => globalThis.fetch(request)` — иначе MSW в тестах не перехватит запросы.
- `baseUrl` — `window.location.origin`: `Request` в Node/jsdom не принимает относительные URL; в браузере это тот же домен.
- Для повтора после 401 middleware сохраняет `request.clone()` до отправки (тело запроса читается один раз).
- В jsdom нет `navigator.locks`: `refresh.ts` тогда работает только с промисом внутри вкладки.
- `unwrap` берёт тело ошибки из `result.error` (openapi-fetch уже прочитал ответ).

`frontend/src/api/types.ts`:
```ts
import type { components } from "./schema";

export type Schemas = components["schemas"];
export type UserRole = Schemas["UserRole"];
export type Me = Schemas["MeRead"];
```

`frontend/src/api/errors.ts`:
```ts
export const NETWORK_ERROR_MESSAGE = "Нет связи с сервером";
export const UNKNOWN_ERROR_MESSAGE = "Не удалось выполнить запрос";

export interface Blocker {
  kind: string;
  entity_id: number;
  title: string;
}

export interface ValidationIssue {
  loc: (string | number)[];
  msg: string;
  type: string;
}

interface ApiErrorInit {
  status: number;
  code: string;
  message: string;
  details?: unknown;
  requestId?: string | null;
}

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly details: unknown;
  readonly requestId: string | null;

  constructor(init: ApiErrorInit) {
    super(init.message);
    this.name = "ApiError";
    this.status = init.status;
    this.code = init.code;
    this.details = init.details ?? null;
    this.requestId = init.requestId ?? null;
  }
}

interface ErrorEnvelope {
  error: { code: string; message: string; details?: unknown };
}

function isErrorEnvelope(body: unknown): body is ErrorEnvelope {
  if (typeof body !== "object" || body === null || !("error" in body)) return false;
  const error = (body as { error: unknown }).error;
  return (
    typeof error === "object" &&
    error !== null &&
    typeof (error as { code?: unknown }).code === "string" &&
    typeof (error as { message?: unknown }).message === "string"
  );
}

export function apiErrorFromBody(
  status: number,
  body: unknown,
  requestId: string | null,
): ApiError {
  if (isErrorEnvelope(body)) {
    return new ApiError({
      status,
      code: body.error.code,
      message: body.error.message,
      details: body.error.details,
      requestId,
    });
  }
  return new ApiError({ status, code: "unknown_error", message: UNKNOWN_ERROR_MESSAGE, requestId });
}

export function networkError(): ApiError {
  return new ApiError({ status: 0, code: "network_error", message: NETWORK_ERROR_MESSAGE });
}

export function toApiError(error: unknown): ApiError {
  if (error instanceof ApiError) return error;
  return new ApiError({ status: 0, code: "unknown_error", message: UNKNOWN_ERROR_MESSAGE });
}

export function isRetryableError(error: unknown): boolean {
  return error instanceof ApiError && (error.status === 0 || error.status >= 500);
}

export function blockersOf(error: ApiError): Blocker[] {
  if (!Array.isArray(error.details)) return [];
  return error.details.filter(
    (item): item is Blocker =>
      typeof item === "object" &&
      item !== null &&
      typeof (item as Blocker).kind === "string" &&
      typeof (item as Blocker).entity_id === "number" &&
      typeof (item as Blocker).title === "string",
  );
}

export function validationIssuesOf(error: ApiError): ValidationIssue[] {
  if (error.code !== "validation_failed" || !Array.isArray(error.details)) return [];
  return error.details.filter(
    (item): item is ValidationIssue =>
      typeof item === "object" && item !== null && Array.isArray((item as ValidationIssue).loc),
  );
}
```

`frontend/src/api/session.ts`:
```ts
export interface SessionHandlers {
  onSessionExpired: () => void;
  onPasswordChangeRequired: () => void;
}

const noopHandlers: SessionHandlers = {
  onSessionExpired: () => undefined,
  onPasswordChangeRequired: () => undefined,
};

let accessToken: string | null = null;
let handlers: SessionHandlers = noopHandlers;

export function getAccessToken(): string | null {
  return accessToken;
}

export function setAccessToken(token: string | null): void {
  accessToken = token;
}

export function setSessionHandlers(next: SessionHandlers): () => void {
  handlers = next;
  return () => {
    if (handlers === next) handlers = noopHandlers;
  };
}

export function sessionHandlers(): SessionHandlers {
  return handlers;
}

export function resetSession(): void {
  accessToken = null;
  handlers = noopHandlers;
}
```

`frontend/src/api/refresh.ts`:
```ts
import { networkError } from "./errors";
import { getAccessToken, setAccessToken } from "./session";
import type { Schemas } from "./types";

const REFRESH_LOCK = "it-platform-refresh";

let inflight: Promise<string | null> | null = null;

/**
 * Обновляет access-токен по refresh-cookie. Одновременно выполняется не больше одного refresh:
 * внутри вкладки — общий промис, между вкладками — Web Locks API.
 * `staleToken` — токен, с которым запрос получил 401: если к моменту получения блокировки
 * токен уже сменился, сетевой refresh не нужен.
 * Возвращает новый токен или null, если сессия недействительна.
 */
export function refreshAccessToken(staleToken: string | null): Promise<string | null> {
  inflight ??= withRefreshLock(() => refreshUnlessUpdated(staleToken)).finally(() => {
    inflight = null;
  });
  return inflight;
}

async function refreshUnlessUpdated(staleToken: string | null): Promise<string | null> {
  const current = getAccessToken();
  if (current !== null && current !== staleToken) return current;

  let response: Response;
  try {
    response = await globalThis.fetch(`${window.location.origin}/api/auth/refresh`, {
      method: "POST",
      credentials: "same-origin",
    });
  } catch {
    throw networkError();
  }
  if (!response.ok) {
    setAccessToken(null);
    return null;
  }
  const body = (await response.json()) as Schemas["AccessTokenResponse"];
  setAccessToken(body.access_token);
  return body.access_token;
}

async function withRefreshLock(task: () => Promise<string | null>): Promise<string | null> {
  const locks = (navigator as Partial<Navigator>).locks;
  if (!locks) return task();
  return await locks.request(REFRESH_LOCK, task);
}
```

`frontend/src/api/client.ts`:
```ts
import createClient, { type Middleware } from "openapi-fetch";

import { apiErrorFromBody, networkError, toApiError, ApiError } from "./errors";
import { refreshAccessToken } from "./refresh";
import { getAccessToken, sessionHandlers } from "./session";
import type { paths } from "./schema";

const NO_REFRESH_PATHS = new Set([
  "/api/auth/login",
  "/api/auth/refresh",
  "/api/auth/logout",
  "/api/auth/change-password",
]);

const replayableRequests = new Map<string, Request>();

function bearerOf(request: Request): string | null {
  const header = request.headers.get("Authorization");
  return header?.startsWith("Bearer ") ? header.slice("Bearer ".length) : null;
}

async function isPasswordChangeRequired(response: Response): Promise<boolean> {
  try {
    const body = (await response.clone().json()) as { error?: { code?: string } };
    return body.error?.code === "password_change_required";
  } catch {
    return false;
  }
}

const authMiddleware: Middleware = {
  onRequest({ request, id }) {
    const token = getAccessToken();
    if (token) request.headers.set("Authorization", `Bearer ${token}`);
    if (!NO_REFRESH_PATHS.has(new URL(request.url).pathname)) {
      replayableRequests.set(id, request.clone());
    }
    return request;
  },

  async onResponse({ response, id }) {
    const original = replayableRequests.get(id);
    replayableRequests.delete(id);

    if (response.status === 403 && (await isPasswordChangeRequired(response))) {
      sessionHandlers().onPasswordChangeRequired();
    }
    if (response.status !== 401 || !original) return response;

    const token = await refreshAccessToken(bearerOf(original));
    if (!token) {
      sessionHandlers().onSessionExpired();
      return response;
    }
    const retry = new Request(original, { headers: new Headers(original.headers) });
    retry.headers.set("Authorization", `Bearer ${token}`);
    const retried = await globalThis.fetch(retry);
    if (retried.status === 401) sessionHandlers().onSessionExpired();
    return retried;
  },

  onError({ id }) {
    replayableRequests.delete(id);
  },
};

export const api = createClient<paths>({
  baseUrl: window.location.origin,
  credentials: "same-origin",
  // Ссылка на fetch берётся в момент запроса: так MSW в тестах перехватывает вызовы.
  fetch: (request) => globalThis.fetch(request),
});
api.use(authMiddleware);

interface ClientResult<D> {
  data?: D;
  error?: unknown;
  response: Response;
}

/** Возвращает данные успешного ответа или бросает ApiError. */
export async function unwrap<D>(request: Promise<ClientResult<D>>): Promise<D> {
  let result: ClientResult<D>;
  try {
    result = await request;
  } catch (error) {
    throw error instanceof ApiError
      ? error
      : error instanceof TypeError
        ? networkError()
        : toApiError(error);
  }
  if (result.response.ok) return result.data as D;
  throw apiErrorFromBody(
    result.response.status,
    result.error,
    result.response.headers.get("X-Request-ID"),
  );
}
```

`frontend/src/test/setup.ts`:
```ts
import "@testing-library/jest-dom/vitest";

import { resetSession } from "../api/session";
import { server } from "./server";

// jsdom не реализует matchMedia: эмулируем окно шириной 1280px (десктоп, брейкпоинт lg),
// чтобы useMediaQuery в тестах вёл себя как в браузере.
const TEST_VIEWPORT_WIDTH = 1280;

function matchesQuery(query: string): boolean {
  const min = /min-width:\s*([\d.]+)px/.exec(query);
  const max = /max-width:\s*([\d.]+)px/.exec(query);
  return (
    (!min || TEST_VIEWPORT_WIDTH >= Number(min[1])) &&
    (!max || TEST_VIEWPORT_WIDTH <= Number(max[1]))
  );
}

Object.defineProperty(window, "matchMedia", {
  writable: true,
  value: (query: string): MediaQueryList =>
    ({
      matches: matchesQuery(query),
      media: query,
      onchange: null,
      addEventListener: () => undefined,
      removeEventListener: () => undefined,
      addListener: () => undefined,
      removeListener: () => undefined,
      dispatchEvent: () => false,
    }) as MediaQueryList,
});

beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => {
  server.resetHandlers();
  resetSession();
});
afterAll(() => server.close());
```

- [ ] **Step 4: Тесты проходят**

Run: `npx vitest run src/api` → PASS (11 тестов), без вывода в stderr.

- [ ] **Step 5: Проверки и commit**

```bash
npm run format && npm run check
cd .. && git add frontend && git commit -m "feat(frontend): клиент API с single-flight refresh и единым разбором ошибок"
```


### Task 3: Тема Modernize, QueryClient, форматирование, тестовый рендер

**Files:**
- Create: `frontend/src/theme/theme.ts`, `frontend/src/app/queryClient.ts`, `frontend/src/shared/lib/format.ts`, `frontend/src/test/render.tsx`
- Test: `frontend/src/theme/theme.test.ts`, `frontend/src/app/queryClient.test.ts`, `frontend/src/shared/lib/format.test.ts`

**Interfaces:**
- Consumes: `ApiError`, `isRetryableError`, `Schemas`, `UserRole` (Task 2).
- Produces:
  - `theme` (MUI-тема Modernize + `ruRU`).
  - `createQueryClient(): QueryClient` (`staleTime` 30 с, без refetch при фокусе, retry только для `isRetryableError` и не более 2 раз, мутации без retry; сбои сети и 5xx любых запросов и мутаций логируются `logServerError`), `logServerError(error)` — `console.error("Ошибка запроса к API", { status, code, requestId })`.
  - `format.ts`: `formatDate(iso)`, `formatDateTime(iso)`, `ROLE_LABELS: Record<UserRole, string>`, `APPLICABILITY_LABELS`, `initialsOf(fullName)`.
  - `test/render.tsx`: `createTestQueryClient()`, `TestProviders`, `renderRoutes(routes, { initialEntries?, wrapper? }) → { ...RenderResult, router, user }`, `renderWithProviders(ui, { path?, initialEntries?, wrapper? })`.

- [ ] **Step 1: Написать падающие тесты**

`frontend/src/theme/theme.test.ts`:
```ts
import { theme } from "./theme";

test("тема использует палитру и шрифт Modernize", () => {
  expect(theme.palette.primary.main).toBe("#5D87FF");
  expect(theme.typography.fontFamily).toContain("Manrope");
  expect(theme.shadows).toHaveLength(25);
});

test("тема подключает русскую локализацию компонентов MUI", () => {
  expect(theme.components?.MuiTablePagination?.defaultProps?.labelRowsPerPage).toBe(
    "Строк на странице:",
  );
});
```

`frontend/src/app/queryClient.test.ts`:
```ts
import { ApiError } from "../api/errors";
import { createQueryClient, logServerError } from "./queryClient";

const error = (status: number) =>
  new ApiError({ status, code: "x", message: "x", requestId: "req-7" });

test("запросы повторяются только при сетевых ошибках и 5xx, не более двух раз", () => {
  const retry = createQueryClient().getDefaultOptions().queries?.retry as (
    failureCount: number,
    error: unknown,
  ) => boolean;

  expect(retry(0, error(0))).toBe(true);
  expect(retry(1, error(503))).toBe(true);
  expect(retry(2, error(503))).toBe(false);
  expect(retry(0, error(404))).toBe(false);
  expect(retry(0, new Error("x"))).toBe(false);
});

test("сбои сети и сервера логируются с request id, ошибки 4xx — нет", () => {
  const log = vi.spyOn(console, "error").mockImplementation(() => undefined);

  logServerError(error(404));
  logServerError(error(502));

  expect(log).toHaveBeenCalledTimes(1);
  expect(log).toHaveBeenCalledWith("Ошибка запроса к API", {
    status: 502,
    code: "x",
    requestId: "req-7",
  });
  log.mockRestore();
});
```

`frontend/src/shared/lib/format.test.ts`:
```ts
import { formatDate, formatDateTime, initialsOf, ROLE_LABELS } from "./format";

test("даты форматируются по-русски", () => {
  expect(formatDate("2026-09-17T10:00:00Z")).toBe("17.09.2026");
  expect(formatDateTime("2026-09-17T10:00:00Z")).toMatch(/^17\.09\.2026, \d{2}:\d{2}$/);
});

test("названия ролей и инициалы", () => {
  expect(ROLE_LABELS.manager).toBe("Руководитель");
  expect(initialsOf("Иванов  Пётр Сергеевич")).toBe("ИП");
});
```

- [ ] **Step 2: Запустить тесты — падают**

Run: `npx vitest run src/theme src/app/queryClient.test.ts src/shared/lib`
Expected: FAIL — не найдены модули `./theme`, `./queryClient`, `./format`.

- [ ] **Step 3: Реализация**

Тема переносит палитру, тени, типографику и переопределения компонентов из `modernize-react-lite/package/src/theme/*` (MIT). Отличия от шаблона: шрифт Manrope (кириллица), `button.textTransform: "none"` (иначе «Сменить Пароль»), убраны нестандартные ключи палитры (`primary.transparent`, `purple`) и стили simplebar. Русская локализация компонентов MUI (`ruRU`) подключается вторым аргументом `createTheme`.

`frontend/src/theme/theme.ts`:
```ts
import { ruRU } from "@mui/material/locale";
import { createTheme, type Shadows } from "@mui/material/styles";

// В шаблоне Modernize — Plus Jakarta Sans, но в нём нет кириллицы; Manrope близок по начертанию.
const fontFamily = "'Manrope', sans-serif";

// Тени шаблона Modernize (MUI требует ровно 25 значений).
const shadows = [
  "none",
  "0px 2px 3px rgba(0,0,0,0.10)",
  "0 0 1px 0 rgba(0,0,0,0.31), 0 2px 2px -2px rgba(0,0,0,0.25)",
  "0 0 1px 0 rgba(0,0,0,0.31), 0 3px 4px -2px rgba(0,0,0,0.25)",
  "0 0 1px 0 rgba(0,0,0,0.31), 0 3px 4px -2px rgba(0,0,0,0.25)",
  "0 0 1px 0 rgba(0,0,0,0.31), 0 4px 6px -2px rgba(0,0,0,0.25)",
  "0 0 1px 0 rgba(0,0,0,0.31), 0 4px 6px -2px rgba(0,0,0,0.25)",
  "0 0 1px 0 rgba(0,0,0,0.31), 0 4px 8px -2px rgba(0,0,0,0.25)",
  "0 9px 17.5px rgb(0,0,0,0.05)",
  "rgb(145 158 171 / 30%) 0px 0px 2px 0px, rgb(145 158 171 / 12%) 0px 12px 24px -4px",
  "0 0 1px 0 rgba(0,0,0,0.31), 0 7px 12px -4px rgba(0,0,0,0.25)",
  "0 0 1px 0 rgba(0,0,0,0.31), 0 6px 16px -4px rgba(0,0,0,0.25)",
  "0 0 1px 0 rgba(0,0,0,0.31), 0 7px 16px -4px rgba(0,0,0,0.25)",
  "0 0 1px 0 rgba(0,0,0,0.31), 0 8px 18px -8px rgba(0,0,0,0.25)",
  "0 0 1px 0 rgba(0,0,0,0.31), 0 9px 18px -8px rgba(0,0,0,0.25)",
  "0 0 1px 0 rgba(0,0,0,0.31), 0 10px 20px -8px rgba(0,0,0,0.25)",
  "0 0 1px 0 rgba(0,0,0,0.31), 0 11px 20px -8px rgba(0,0,0,0.25)",
  "0 0 1px 0 rgba(0,0,0,0.31), 0 12px 22px -8px rgba(0,0,0,0.25)",
  "0 0 1px 0 rgba(0,0,0,0.31), 0 13px 22px -8px rgba(0,0,0,0.25)",
  "0 0 1px 0 rgba(0,0,0,0.31), 0 14px 24px -8px rgba(0,0,0,0.25)",
  "0 0 1px 0 rgba(0,0,0,0.31), 0 16px 28px -8px rgba(0,0,0,0.25)",
  "0 0 1px 0 rgba(0,0,0,0.31), 0 18px 30px -8px rgba(0,0,0,0.25)",
  "0 0 1px 0 rgba(0,0,0,0.31), 0 20px 32px -8px rgba(0,0,0,0.25)",
  "0 0 1px 0 rgba(0,0,0,0.31), 0 22px 34px -8px rgba(0,0,0,0.25)",
  "0 0 1px 0 rgba(0,0,0,0.31), 0 24px 36px -8px rgba(0,0,0,0.25)",
] as Shadows;

export const theme = createTheme(
  {
    palette: {
      primary: { main: "#5D87FF", light: "#ECF2FF", dark: "#4570EA", contrastText: "#ffffff" },
      secondary: { main: "#49BEFF", light: "#E8F7FF", dark: "#23afdb", contrastText: "#ffffff" },
      success: { main: "#13DEB9", light: "#E6FFFA", dark: "#02b3a9", contrastText: "#ffffff" },
      info: { main: "#539BFF", light: "#EBF3FE", dark: "#1682d4", contrastText: "#ffffff" },
      error: { main: "#FA896B", light: "#FDEDE8", dark: "#f3704d", contrastText: "#ffffff" },
      warning: { main: "#FFAE1F", light: "#FEF5E5", dark: "#ae8e59", contrastText: "#ffffff" },
      grey: {
        100: "#F2F6FA",
        200: "#EAEFF4",
        300: "#DFE5EF",
        400: "#7C8FAC",
        500: "#5A6A85",
        600: "#2A3547",
      },
      text: { primary: "#2A3547", secondary: "#5A6A85" },
      action: { disabledBackground: "rgba(73,82,88,0.12)", hoverOpacity: 0.02, hover: "#f6f9fc" },
      divider: "#e5eaef",
      background: { default: "#ffffff" },
    },
    shape: { borderRadius: 7 },
    typography: {
      fontFamily,
      h1: { fontWeight: 600, fontSize: "2.25rem", lineHeight: "2.75rem" },
      h2: { fontWeight: 600, fontSize: "1.875rem", lineHeight: "2.25rem" },
      h3: { fontWeight: 600, fontSize: "1.5rem", lineHeight: "1.75rem" },
      h4: { fontWeight: 600, fontSize: "1.3125rem", lineHeight: "1.6rem" },
      h5: { fontWeight: 600, fontSize: "1.125rem", lineHeight: "1.6rem" },
      h6: { fontWeight: 600, fontSize: "1rem", lineHeight: "1.2rem" },
      // В шаблоне textTransform: capitalize — для русского интерфейса это «Сменить Пароль».
      button: { textTransform: "none", fontWeight: 500 },
      body1: { fontSize: "0.875rem", fontWeight: 400, lineHeight: "1.334rem" },
      body2: { fontSize: "0.75rem", letterSpacing: "0rem", fontWeight: 400, lineHeight: "1rem" },
      subtitle1: { fontSize: "0.875rem", fontWeight: 400 },
      subtitle2: { fontSize: "0.875rem", fontWeight: 400 },
    },
    shadows,
    components: {
      MuiCssBaseline: { styleOverrides: { a: { textDecoration: "none" } } },
      MuiButton: {
        styleOverrides: { root: { boxShadow: "none", "&:hover": { boxShadow: "none" } } },
      },
      MuiCard: { styleOverrides: { root: { boxShadow: "0 9px 17.5px rgb(0,0,0,0.05)" } } },
      MuiOutlinedInput: {
        styleOverrides: {
          root: {
            "& .MuiOutlinedInput-notchedOutline": { borderColor: "#e5eaef" },
            "&:hover .MuiOutlinedInput-notchedOutline, &.Mui-focused .MuiOutlinedInput-notchedOutline":
              { borderColor: "#5D87FF" },
          },
        },
      },
    },
  },
  ruRU,
);
```

`frontend/src/app/queryClient.ts`:
```ts
import { MutationCache, QueryCache, QueryClient } from "@tanstack/react-query";

import { isRetryableError, type ApiError } from "../api/errors";

/** Сбои сети и сервера пишутся в консоль с X-Request-ID — по нему ищется запись в логах backend. */
export function logServerError(error: unknown): void {
  if (!isRetryableError(error)) return;
  const { status, code, requestId } = error as ApiError;
  console.error("Ошибка запроса к API", { status, code, requestId });
}

export function createQueryClient(): QueryClient {
  return new QueryClient({
    queryCache: new QueryCache({ onError: logServerError }),
    mutationCache: new MutationCache({ onError: logServerError }),
    defaultOptions: {
      queries: {
        staleTime: 30_000,
        refetchOnWindowFocus: false,
        retry: (failureCount, error) => isRetryableError(error) && failureCount < 2,
      },
      mutations: { retry: false },
    },
  });
}
```

`frontend/src/shared/lib/format.ts`:
```ts
import type { Schemas, UserRole } from "../../api/types";

const dateFormat = new Intl.DateTimeFormat("ru-RU");
const dateTimeFormat = new Intl.DateTimeFormat("ru-RU", { dateStyle: "short", timeStyle: "short" });

export function formatDate(iso: string): string {
  return dateFormat.format(new Date(iso));
}

export function formatDateTime(iso: string): string {
  return dateTimeFormat.format(new Date(iso));
}

export const ROLE_LABELS: Record<UserRole, string> = {
  employee: "Сотрудник",
  manager: "Руководитель",
  admin: "Администратор",
};

export const APPLICABILITY_LABELS: Record<Schemas["IssueReasonApplicability"], string> = {
  assets: "Техника",
  stock: "Расходники",
  both: "Техника и расходники",
};

export function initialsOf(fullName: string): string {
  return fullName
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? "")
    .join("");
}
```

`frontend/src/test/render.tsx`:
```tsx
import { CssBaseline, ThemeProvider } from "@mui/material";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { SnackbarProvider } from "notistack";
import type { ReactElement, ReactNode } from "react";
import { createMemoryRouter, RouterProvider, type RouteObject } from "react-router";

import { theme } from "../theme/theme";

export function createTestQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: { queries: { retry: false, staleTime: 0 }, mutations: { retry: false } },
  });
}

export function TestProviders({
  children,
  queryClient = createTestQueryClient(),
}: {
  children: ReactNode;
  queryClient?: QueryClient;
}) {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <QueryClientProvider client={queryClient}>
        <SnackbarProvider>{children}</SnackbarProvider>
      </QueryClientProvider>
    </ThemeProvider>
  );
}

interface RenderRoutesOptions {
  initialEntries?: string[];
  wrapper?: (children: ReactNode) => ReactNode;
}

/** Рендерит маршруты в memory-роутере со всеми провайдерами приложения. */
export function renderRoutes(routes: RouteObject[], options: RenderRoutesOptions = {}) {
  const router = createMemoryRouter(routes, { initialEntries: options.initialEntries ?? ["/"] });
  const user = userEvent.setup();
  const content = <RouterProvider router={router} />;
  const view = render(
    <TestProviders>{options.wrapper ? options.wrapper(content) : content}</TestProviders>,
  );
  return { ...view, router, user };
}

/** Рендерит один элемент на маршруте `path` (по умолчанию «*»). */
export function renderWithProviders(
  ui: ReactElement,
  options: RenderRoutesOptions & { path?: string } = {},
) {
  return renderRoutes([{ path: options.path ?? "*", element: ui }], options);
}
```

- [ ] **Step 4: Тесты проходят, commit**

```bash
npx vitest run src/theme src/app/queryClient.test.ts src/shared/lib   # PASS
npm run format && npm run check
cd .. && git add frontend && git commit -m "feat(frontend): тема Modernize, QueryClient, форматирование"
```


### Task 4: Поля форм, разбор ошибок API по полям, диалоги

**Files:**
- Create: `frontend/src/shared/lib/applyApiErrors.ts`
- Create: `frontend/src/shared/ui/form/FormTextField.tsx`, `FormSelect.tsx`, `FormSwitch.tsx`
- Create: `frontend/src/shared/ui/FormDialog.tsx`, `ConfirmDialog.tsx`, `BlockersDialog.tsx`
- Test: `frontend/src/shared/lib/applyApiErrors.test.ts`, `frontend/src/shared/ui/dialogs.test.tsx`

**Interfaces:**
- Consumes: `ApiError`, `UNKNOWN_ERROR_MESSAGE`, `validationIssuesOf`, `Blocker` (Task 2); `renderWithProviders` (Task 3).
- Produces:
  - `applyApiErrors<T>(error: unknown, setError: UseFormSetError<T>, { fields: readonly FieldPath<T>[]; fieldForError?: (error: ApiError) => FieldPath<T> | undefined }): string | null` — возвращает сообщение над формой или `null`; `fieldByCode<T>(map)`; `INVALID_FIELD_MESSAGE = "Некорректное значение"`.
  - `FormTextField<T, N>({ control, name, rules?, ...TextFieldProps })`, `FormSelect<T, V>({ control, name, label, options: readonly { value: V; label }[], emptyLabel?, disabled? })` (пустое значение ↔ `null`), `FormSwitch<T>({ control, name, label })`, тип `SelectOption<V>`.
  - `FormDialog({ open, title, submitting, formError, onSubmit, onClose, submitLabel = "Сохранить", children })`, `ConfirmDialog({ open, title, text, confirmLabel, confirmColor?, pending?, onConfirm, onClose })`, `BlockersDialog({ open, message, blockers, onClose })`.

- [ ] **Step 1: Написать падающие тесты**

В тестах диалоги открываются действием пользователя: MUI 9 FocusTrap в jsdom падает (`nodeToRestore.current.focus is not a function`) при размонтировании диалога, открытого сразу при рендере без предшествующего фокуса. Поля ошибок валидации pydantic приходят с английским `msg`, поэтому под полем показывается «Некорректное значение», а над формой — русское `message` backend.

`frontend/src/shared/lib/applyApiErrors.test.ts`:
```ts
import { act, renderHook } from "@testing-library/react";
import { useForm } from "react-hook-form";

import { ApiError } from "../../api/errors";
import { applyApiErrors, fieldByCode, INVALID_FIELD_MESSAGE } from "./applyApiErrors";

interface Values {
  name: string;
  email: string;
}

function setup() {
  return renderHook(() => useForm<Values>({ defaultValues: { name: "", email: "" } })).result;
}

test("422 validation_failed раскладывается по полям из loc", () => {
  const form = setup();
  const error = new ApiError({
    status: 422,
    code: "validation_failed",
    message: "Некорректные данные запроса",
    details: [{ loc: ["body", "email"], msg: "value is not a valid email", type: "value_error" }],
  });

  let formMessage: string | null = "";
  act(() => {
    formMessage = applyApiErrors(error, form.current.setError, { fields: ["name", "email"] });
  });

  expect(formMessage).toBeNull();
  expect(form.current.getFieldState("email").error?.message).toBe(INVALID_FIELD_MESSAGE);
});

test("ошибка, которую нельзя отнести к полю, возвращается сообщением формы", () => {
  const form = setup();
  const error = new ApiError({
    status: 422,
    code: "validation_failed",
    message: "Некорректные данные запроса",
    details: [{ loc: ["query", "limit"], msg: "bad", type: "x" }],
  });

  expect(applyApiErrors(error, form.current.setError, { fields: ["name"] })).toBe(
    "Некорректные данные запроса",
  );
});

test("доменный код ошибки ставится на поле по словарю", () => {
  const form = setup();
  const error = new ApiError({
    status: 409,
    code: "email_taken",
    message: "Пользователь с таким email уже существует",
  });

  act(() => {
    applyApiErrors(error, form.current.setError, {
      fields: ["name", "email"],
      fieldForError: fieldByCode<Values>({ email_taken: "email" }),
    });
  });

  expect(form.current.getFieldState("email").error?.message).toBe(
    "Пользователь с таким email уже существует",
  );
});

test("прочие ошибки возвращают message backend, не-ApiError — общий текст", () => {
  const form = setup();
  const conflict = new ApiError({ status: 409, code: "last_admin", message: "Нужен админ" });

  expect(applyApiErrors(conflict, form.current.setError, { fields: [] })).toBe("Нужен админ");
  expect(applyApiErrors(new Error("x"), form.current.setError, { fields: [] })).toBe(
    "Не удалось выполнить запрос",
  );
});
```

`frontend/src/shared/ui/dialogs.test.tsx`:
```tsx
import { screen } from "@testing-library/react";
import { useState } from "react";
import { useForm } from "react-hook-form";

import { ApiError } from "../../api/errors";
import { renderWithProviders } from "../../test/render";
import { applyApiErrors, fieldByCode } from "../lib/applyApiErrors";
import { BlockersDialog } from "./BlockersDialog";
import { FormDialog } from "./FormDialog";
import { FormSelect } from "./form/FormSelect";
import { FormTextField } from "./form/FormTextField";

interface Values {
  name: string;
  role: "employee" | "admin" | null;
}

function DepartmentForm({ submit }: { submit: (values: Values) => Promise<void> }) {
  const { control, handleSubmit, setError } = useForm<Values>({
    defaultValues: { name: "", role: null },
  });
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const onSubmit = handleSubmit(async (values) => {
    setSubmitting(true);
    setFormError(null);
    try {
      await submit(values);
    } catch (error) {
      setFormError(
        applyApiErrors(error, setError, {
          fields: ["name", "role"],
          fieldForError: fieldByCode<Values>({ department_name_taken: "name" }),
        }),
      );
    } finally {
      setSubmitting(false);
    }
  });
  return (
    <FormDialog
      open
      title="Новый отдел"
      submitting={submitting}
      formError={formError}
      onSubmit={onSubmit}
      onClose={() => undefined}
    >
      <FormTextField control={control} name="name" label="Название" />
      <FormSelect
        control={control}
        name="role"
        label="Роль"
        emptyLabel="Не выбрана"
        options={[
          { value: "employee", label: "Сотрудник" },
          { value: "admin", label: "Администратор" },
        ]}
      />
    </FormDialog>
  );
}

test("FormDialog показывает ошибку backend под полем и сообщение над формой", async () => {
  const submit = vi
    .fn<(values: Values) => Promise<void>>()
    .mockRejectedValueOnce(
      new ApiError({
        status: 409,
        code: "department_name_taken",
        message: "Отдел с таким названием уже существует",
      }),
    )
    .mockRejectedValueOnce(new ApiError({ status: 409, code: "other", message: "Что-то не так" }));
  const { user } = renderWithProviders(<DepartmentForm submit={submit} />);

  await user.type(screen.getByLabelText("Название"), "ИТ");
  await user.click(screen.getByLabelText("Роль"));
  await user.click(await screen.findByRole("option", { name: "Администратор" }));
  await user.click(screen.getByRole("button", { name: "Сохранить" }));

  expect(await screen.findByText("Отдел с таким названием уже существует")).toBeInTheDocument();
  expect(submit).toHaveBeenCalledWith({ name: "ИТ", role: "admin" });

  await user.click(screen.getByRole("button", { name: "Сохранить" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("Что-то не так");
});

function BlockersDemo() {
  const [open, setOpen] = useState(false);
  return (
    <>
      <button onClick={() => setOpen(true)}>Деактивировать</button>
      <BlockersDialog
        open={open}
        message="Перед деактивацией нужно передать ответственность другим сотрудникам"
        blockers={[{ kind: "department_head", entity_id: 2, title: "Отдел «Бухгалтерия»" }]}
        onClose={() => setOpen(false)}
      />
    </>
  );
}

// Диалоги в тестах открываются действием пользователя, как в приложении: MUI FocusTrap
// в jsdom падает при размонтировании диалога, открытого сразу при рендере.
test("BlockersDialog перечисляет причины блокировки", async () => {
  const { user } = renderWithProviders(<BlockersDemo />);

  await user.click(screen.getByRole("button", { name: "Деактивировать" }));

  expect(await screen.findByText("Отдел «Бухгалтерия»")).toBeInTheDocument();
  expect(screen.getByText("Руководитель отдела")).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Понятно" }));
});
```

- [ ] **Step 2: Запустить тесты — падают**

Run: `npx vitest run src/shared`
Expected: FAIL — не найдены `./applyApiErrors`, `./BlockersDialog` и др.

- [ ] **Step 3: Реализация**

MUI 9: у `Switch` нет `inputRef`, у `Dialog` нет `disableEscapeKeyDown` — закрытие во время отправки блокирует обработчик `onClose`. `Button` поддерживает `loading`.

`frontend/src/shared/lib/applyApiErrors.ts`:
```ts
import type { FieldPath, FieldValues, UseFormSetError } from "react-hook-form";

import { ApiError, UNKNOWN_ERROR_MESSAGE, validationIssuesOf } from "../../api/errors";

export const INVALID_FIELD_MESSAGE = "Некорректное значение";

interface ApplyApiErrorsOptions<T extends FieldValues> {
  /** Поля формы, совпадающие по имени с полями тела запроса. */
  fields: readonly FieldPath<T>[];
  /** Поле, к которому относится доменная ошибка backend (по коду или деталям). */
  fieldForError?: (error: ApiError) => FieldPath<T> | undefined;
}

/**
 * Раскладывает ошибку API по полям формы. Возвращает сообщение для показа над формой
 * или null, если всё разложено по полям.
 */
export function applyApiErrors<T extends FieldValues>(
  error: unknown,
  setError: UseFormSetError<T>,
  { fields, fieldForError }: ApplyApiErrorsOptions<T>,
): string | null {
  if (!(error instanceof ApiError)) return UNKNOWN_ERROR_MESSAGE;

  const field = fieldForError?.(error);
  if (field) {
    setError(field, { type: "server", message: error.message });
    return null;
  }

  const issues = validationIssuesOf(error);
  if (issues.length === 0) return error.message;

  let unmapped = false;
  for (const issue of issues) {
    const [location, name] = issue.loc;
    const target = fields.find((candidate) => candidate === name);
    if (location === "body" && target) {
      setError(target, { type: "server", message: INVALID_FIELD_MESSAGE });
    } else {
      unmapped = true;
    }
  }
  return unmapped ? error.message : null;
}

/** Строит `fieldForError` по словарю «код ошибки → поле». */
export function fieldByCode<T extends FieldValues>(
  map: Partial<Record<string, FieldPath<T>>>,
): (error: ApiError) => FieldPath<T> | undefined {
  return (error) => map[error.code];
}
```

`frontend/src/shared/ui/form/FormTextField.tsx`:
```tsx
import { TextField, type TextFieldProps } from "@mui/material";
import {
  Controller,
  type Control,
  type FieldPath,
  type FieldValues,
  type RegisterOptions,
} from "react-hook-form";

type FormTextFieldProps<T extends FieldValues, N extends FieldPath<T>> = {
  control: Control<T>;
  name: N;
  rules?: RegisterOptions<T, N>;
} & Omit<TextFieldProps, "name" | "value" | "onChange" | "onBlur" | "error" | "defaultValue">;

export function FormTextField<T extends FieldValues, N extends FieldPath<T>>({
  control,
  name,
  rules,
  helperText,
  ...props
}: FormTextFieldProps<T, N>) {
  return (
    <Controller
      control={control}
      name={name}
      rules={rules}
      render={({ field, fieldState }) => (
        <TextField
          {...props}
          name={field.name}
          inputRef={field.ref}
          value={field.value ?? ""}
          onChange={field.onChange}
          onBlur={field.onBlur}
          error={Boolean(fieldState.error)}
          helperText={fieldState.error?.message ?? helperText}
          fullWidth
        />
      )}
    />
  );
}
```

`frontend/src/shared/ui/form/FormSelect.tsx`:
```tsx
import { MenuItem, TextField } from "@mui/material";
import { Controller, type Control, type FieldPath, type FieldValues } from "react-hook-form";

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
}

export function FormSelect<T extends FieldValues, V extends string | number>({
  control,
  name,
  label,
  options,
  emptyLabel,
  disabled,
}: FormSelectProps<T, V>) {
  return (
    <Controller
      control={control}
      name={name}
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

`frontend/src/shared/ui/form/FormSwitch.tsx`:
```tsx
import { FormControlLabel, Switch } from "@mui/material";
import { Controller, type Control, type FieldPath, type FieldValues } from "react-hook-form";

interface FormSwitchProps<T extends FieldValues> {
  control: Control<T>;
  name: FieldPath<T>;
  label: string;
}

export function FormSwitch<T extends FieldValues>({ control, name, label }: FormSwitchProps<T>) {
  return (
    <Controller
      control={control}
      name={name}
      render={({ field }) => (
        <FormControlLabel
          label={label}
          control={
            <Switch
              name={field.name}
              checked={Boolean(field.value)}
              onChange={(event) => field.onChange(event.target.checked)}
            />
          }
        />
      )}
    />
  );
}
```

`frontend/src/shared/ui/FormDialog.tsx`:
```tsx
import {
  Alert,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Stack,
} from "@mui/material";
import type { FormEventHandler, ReactNode } from "react";

interface FormDialogProps {
  open: boolean;
  title: string;
  submitting: boolean;
  formError: string | null;
  onSubmit: FormEventHandler<HTMLFormElement>;
  onClose: () => void;
  submitLabel?: string;
  children: ReactNode;
}

export function FormDialog({
  open,
  title,
  submitting,
  formError,
  onSubmit,
  onClose,
  submitLabel = "Сохранить",
  children,
}: FormDialogProps) {
  const close = () => {
    if (!submitting) onClose();
  };
  return (
    <Dialog open={open} onClose={close} fullWidth maxWidth="sm">
      <form onSubmit={onSubmit} noValidate aria-label={title}>
        <DialogTitle>{title}</DialogTitle>
        <DialogContent>
          <Stack spacing={2.5} sx={{ pt: 1 }}>
            {formError && <Alert severity="error">{formError}</Alert>}
            {children}
          </Stack>
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button onClick={close} disabled={submitting} color="inherit">
            Отмена
          </Button>
          <Button type="submit" variant="contained" loading={submitting}>
            {submitLabel}
          </Button>
        </DialogActions>
      </form>
    </Dialog>
  );
}
```

`frontend/src/shared/ui/ConfirmDialog.tsx`:
```tsx
import {
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
} from "@mui/material";

interface ConfirmDialogProps {
  open: boolean;
  title: string;
  text: string;
  confirmLabel: string;
  confirmColor?: "primary" | "error";
  pending?: boolean;
  onConfirm: () => void;
  onClose: () => void;
}

export function ConfirmDialog({
  open,
  title,
  text,
  confirmLabel,
  confirmColor = "primary",
  pending = false,
  onConfirm,
  onClose,
}: ConfirmDialogProps) {
  return (
    <Dialog open={open} onClose={() => !pending && onClose()} maxWidth="xs" fullWidth>
      <DialogTitle>{title}</DialogTitle>
      <DialogContent>
        <DialogContentText>{text}</DialogContentText>
      </DialogContent>
      <DialogActions sx={{ px: 3, pb: 2 }}>
        <Button onClick={onClose} disabled={pending} color="inherit">
          Отмена
        </Button>
        <Button onClick={onConfirm} variant="contained" color={confirmColor} loading={pending}>
          {confirmLabel}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
```

`frontend/src/shared/ui/BlockersDialog.tsx`:
```tsx
import {
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
  List,
  ListItem,
  ListItemText,
} from "@mui/material";

import type { Blocker } from "../../api/errors";

const KIND_LABELS: Record<string, string> = {
  department_head: "Руководитель отдела",
  ticket_type_default_assignee: "Исполнитель по умолчанию для типа заявки",
};

interface BlockersDialogProps {
  open: boolean;
  message: string;
  blockers: Blocker[];
  onClose: () => void;
}

export function BlockersDialog({ open, message, blockers, onClose }: BlockersDialogProps) {
  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>Операция невозможна</DialogTitle>
      <DialogContent>
        <DialogContentText>{message}</DialogContentText>
        <List dense>
          {blockers.map((blocker) => (
            <ListItem key={`${blocker.kind}-${blocker.entity_id}`} disableGutters>
              <ListItemText
                primary={blocker.title}
                secondary={KIND_LABELS[blocker.kind] ?? blocker.kind}
              />
            </ListItem>
          ))}
        </List>
      </DialogContent>
      <DialogActions sx={{ px: 3, pb: 2 }}>
        <Button onClick={onClose} variant="contained">
          Понятно
        </Button>
      </DialogActions>
    </Dialog>
  );
}
```

- [ ] **Step 4: Тесты проходят, commit**

```bash
npx vitest run src/shared   # PASS
npm run format && npm run check
cd .. && git add frontend && git commit -m "feat(frontend): поля форм, ошибки API по полям, диалоги"
```


### Task 5: Сессия пользователя: AuthProvider и guard'ы маршрутов

**Files:**
- Create: `frontend/src/shared/lib/useDocumentTitle.ts`, `frontend/src/shared/ui/FullScreenLoader.tsx`, `frontend/src/shared/ui/StatusPage.tsx`
- Create: `frontend/src/features/auth/next.ts`, `AuthContext.ts`, `AuthProvider.tsx`, `guards.tsx`, `index.ts`
- Create: `frontend/src/test/auth.ts`
- Test: `frontend/src/features/auth/guards.test.tsx`

**Interfaces:**
- Consumes: `api`, `unwrap` (Task 2), `refreshAccessToken`, `setAccessToken`, `setSessionHandlers`, `Me`, `UserRole` (Task 2); `renderRoutes` (Task 3).
- Produces:
  - `useDocumentTitle(title)` (заголовок «<title> — IT-платформа»), `APP_TITLE`; `FullScreenLoader`; `StatusPage({ code, title, text })` (кнопка «На главную»).
  - `features/auth` (публично через `index.ts`): `useAuth(): { state: AuthState; user: Me | null; login(email, password): Promise<Me>; logout(): Promise<void>; changePassword(current, next): Promise<Me> }`, `AuthState = { status: "loading" } | { status: "guest" } | { status: "authenticated"; user: Me }`, `AuthProvider` (должен быть внутри `QueryClientProvider`), `RequireAuth`, `RequireRole({ role })`, `GuestOnly`, `CHANGE_PASSWORD_PATH`.
  - внутренние: `safeNext(next, fallback = "/")`, `loginPathFor(pathname, search)`, `AUTH_CHANNEL = "it-platform-auth"`.
  - `test/auth.ts`: `makeMe(overrides)`, `tokenResponse(accessToken?)`, `mockSignedIn(me?)`, `mockSignedOut()`.

- [ ] **Step 1: Написать падающие тесты**

Тест собирает маршруты сам (без `app/routes.tsx`, который появится в Task 7) и проверяет п. 6 дизайна: переход гостя на `/login?next=`, восстановление сессии по refresh-cookie, уход со страницы входа на `next`, «Нет доступа» для не-admin, принудительную смену пароля, выход с сообщением в `BroadcastChannel` и выход по сообщению из другой вкладки.

`frontend/src/test/auth.ts`:
```ts
import { http, HttpResponse } from "msw";

import type { Me, Schemas } from "../api/types";
import { errorBody } from "./http";
import { server } from "./server";

export function makeMe(overrides: Partial<Me> = {}): Me {
  return {
    id: 1,
    email: "admin@company.ru",
    full_name: "Иванов Иван",
    role: "admin",
    department_id: null,
    must_change_password: false,
    ...overrides,
  };
}

export function tokenResponse(accessToken = "token-1"): Schemas["AccessTokenResponse"] {
  return { access_token: accessToken, token_type: "bearer", must_change_password: false };
}

/** Сессия восстанавливается по refresh-cookie: refresh выдаёт токен, /me возвращает пользователя. */
export function mockSignedIn(me: Me = makeMe()): void {
  server.use(
    http.post("*/api/auth/refresh", () => HttpResponse.json(tokenResponse())),
    http.get("*/api/auth/me", () => HttpResponse.json(me)),
  );
}

/** Refresh-cookie нет: пользователь — гость. */
export function mockSignedOut(): void {
  server.use(
    http.post("*/api/auth/refresh", () =>
      HttpResponse.json(errorBody("invalid_refresh_token", "Сессия истекла, войдите снова"), {
        status: 401,
      }),
    ),
  );
}
```

`frontend/src/features/auth/guards.test.tsx`:
```tsx
import { screen, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { useLocation } from "react-router";

import { makeMe, mockSignedIn, mockSignedOut } from "../../test/auth";
import { renderRoutes } from "../../test/render";
import { server } from "../../test/server";
import { useAuth } from "./AuthContext";
import { AUTH_CHANNEL, AuthProvider } from "./AuthProvider";
import { GuestOnly, RequireAuth, RequireRole } from "./guards";
import { safeNext } from "./next";

function Where() {
  const location = useLocation();
  const { user, logout } = useAuth();
  return (
    <>
      <p>
        путь: {location.pathname}
        {location.search}
      </p>
      <p>пользователь: {user?.full_name ?? "гость"}</p>
      <button onClick={() => void logout()}>Выйти</button>
    </>
  );
}

const routes = [
  { element: <GuestOnly />, children: [{ path: "/login", element: <Where /> }] },
  {
    element: <RequireAuth />,
    children: [
      { path: "/", element: <Where /> },
      { path: "/change-password", element: <Where /> },
      {
        element: <RequireRole role="admin" />,
        children: [{ path: "/admin/users", element: <Where /> }],
      },
    ],
  },
];

function renderApp(path: string) {
  return renderRoutes(routes, {
    initialEntries: [path],
    wrapper: (children) => <AuthProvider>{children}</AuthProvider>,
  });
}

test("гость перенаправляется на вход с возвратом на исходную страницу", async () => {
  mockSignedOut();
  renderApp("/admin/users?q=1");

  expect(await screen.findByText("путь: /login?next=%2Fadmin%2Fusers%3Fq%3D1")).toBeInTheDocument();
});

test("действующая refresh-cookie восстанавливает сессию", async () => {
  mockSignedIn(makeMe({ full_name: "Петров Пётр" }));
  renderApp("/admin/users");

  expect(await screen.findByText("пользователь: Петров Пётр")).toBeInTheDocument();
  expect(screen.getByText("путь: /admin/users")).toBeInTheDocument();
});

test("вошедший пользователь со страницы входа уходит на next", async () => {
  mockSignedIn();
  renderApp("/login?next=%2Fadmin%2Fusers");

  expect(await screen.findByText("путь: /admin/users")).toBeInTheDocument();
});

test("не-admin видит «Нет доступа» в админке", async () => {
  mockSignedIn(makeMe({ role: "employee" }));
  renderApp("/admin/users");

  expect(await screen.findByRole("heading", { name: "Нет доступа" })).toBeInTheDocument();
});

test("must_change_password отправляет на смену пароля", async () => {
  mockSignedIn(makeMe({ must_change_password: true }));
  renderApp("/");

  expect(await screen.findByText("путь: /change-password")).toBeInTheDocument();
});

test("выход очищает сессию и сообщает другим вкладкам", async () => {
  mockSignedIn();
  const logoutCalls: string[] = [];
  server.use(
    http.post("*/api/auth/logout", () => {
      logoutCalls.push("logout");
      return new HttpResponse(null, { status: 204 });
    }),
  );
  const otherTab = new BroadcastChannel(AUTH_CHANNEL);
  const received = new Promise((resolve) => (otherTab.onmessage = (e) => resolve(e.data)));
  const { user } = renderApp("/");

  await user.click(await screen.findByRole("button", { name: "Выйти" }));

  expect(await screen.findByText("путь: /login")).toBeInTheDocument();
  await expect(received).resolves.toBe("logout");
  expect(logoutCalls).toHaveLength(1);
  otherTab.close();
});

test("выход в другой вкладке завершает сессию в этой", async () => {
  mockSignedIn();
  renderApp("/");
  await screen.findByText("пользователь: Иванов Иван");

  const otherTab = new BroadcastChannel(AUTH_CHANNEL);
  otherTab.postMessage("logout");
  otherTab.close();

  await waitFor(() => expect(screen.getByText("пользователь: гость")).toBeInTheDocument());
});

test("safeNext пропускает только относительные пути", () => {
  expect(safeNext("/admin/users?q=1")).toBe("/admin/users?q=1");
  expect(safeNext("//evil.example")).toBe("/");
  expect(safeNext("https://evil.example")).toBe("/");
  expect(safeNext(null)).toBe("/");
});
```

- [ ] **Step 2: Запустить тесты — падают**

Run: `npx vitest run src/features/auth`
Expected: FAIL — не найдены `./AuthContext`, `./AuthProvider`, `./guards`, `./next`.

- [ ] **Step 3: Реализация**

`AuthProvider` не использует хуки роутера: переходы делают guard'ы по смене состояния. Восстановление сессии вызывает `refreshAccessToken(null)`; в StrictMode эффект запускается дважды, но single-flight из Task 2 не даёт отправить два refresh. `StatusPage` и `FullScreenLoader` лежат в `shared/ui`: фичам запрещено импортировать `layout/` (правило ESLint), а 403 показывает `RequireRole`.

`frontend/src/shared/lib/useDocumentTitle.ts`:
```ts
import { useEffect } from "react";

export const APP_TITLE = "IT-платформа";

export function useDocumentTitle(title: string): void {
  useEffect(() => {
    document.title = `${title} — ${APP_TITLE}`;
  }, [title]);
}
```

`frontend/src/shared/ui/FullScreenLoader.tsx`:
```tsx
import { Box, CircularProgress } from "@mui/material";

export function FullScreenLoader() {
  return (
    <Box
      role="progressbar"
      aria-label="Загрузка"
      sx={{ minHeight: "100vh", display: "grid", placeItems: "center" }}
    >
      <CircularProgress />
    </Box>
  );
}
```

`frontend/src/shared/ui/StatusPage.tsx`:
```tsx
import { Box, Button, Typography } from "@mui/material";
import { Link } from "react-router";

import { useDocumentTitle } from "../lib/useDocumentTitle";

interface StatusPageProps {
  code: number;
  title: string;
  text: string;
}

export function StatusPage({ code, title, text }: StatusPageProps) {
  useDocumentTitle(title);
  return (
    <Box sx={{ minHeight: "60vh", display: "grid", placeItems: "center", textAlign: "center" }}>
      <Box>
        <Typography variant="h1" color="primary" sx={{ fontSize: "4rem", lineHeight: 1 }}>
          {code}
        </Typography>
        <Typography variant="h4" component="h1" sx={{ mt: 2 }}>
          {title}
        </Typography>
        <Typography color="text.secondary" sx={{ mt: 1, mb: 3 }}>
          {text}
        </Typography>
        <Button component={Link} to="/" variant="contained">
          На главную
        </Button>
      </Box>
    </Box>
  );
}
```

`frontend/src/features/auth/next.ts`:
```ts
/** Возвращает безопасный путь для перехода после входа: только относительный путь приложения. */
export function safeNext(next: string | null | undefined, fallback = "/"): string {
  if (!next || !next.startsWith("/") || next.startsWith("//") || next.startsWith("/\\")) {
    return fallback;
  }
  return next;
}

export function loginPathFor(pathname: string, search: string): string {
  const target = `${pathname}${search}`;
  return target === "/" ? "/login" : `/login?next=${encodeURIComponent(target)}`;
}
```

`frontend/src/features/auth/AuthContext.ts`:
```ts
import { createContext, useContext } from "react";

import type { Me } from "../../api/types";

export type AuthState =
  { status: "loading" } | { status: "guest" } | { status: "authenticated"; user: Me };

export interface AuthContextValue {
  state: AuthState;
  user: Me | null;
  login: (email: string, password: string) => Promise<Me>;
  logout: () => Promise<void>;
  changePassword: (currentPassword: string, newPassword: string) => Promise<Me>;
}

export const AuthContext = createContext<AuthContextValue | null>(null);

export function useAuth(): AuthContextValue {
  const value = useContext(AuthContext);
  if (!value) throw new Error("useAuth должен использоваться внутри AuthProvider");
  return value;
}
```

`frontend/src/features/auth/AuthProvider.tsx`:
```tsx
import { useQueryClient } from "@tanstack/react-query";
import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from "react";

import { api, unwrap } from "../../api/client";
import { refreshAccessToken } from "../../api/refresh";
import { setAccessToken, setSessionHandlers } from "../../api/session";
import type { Me } from "../../api/types";
import { AuthContext, type AuthContextValue, type AuthState } from "./AuthContext";

export const AUTH_CHANNEL = "it-platform-auth";
const LOGOUT_MESSAGE = "logout";

function fetchMe(): Promise<Me> {
  return unwrap(api.GET("/api/auth/me"));
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const [state, setState] = useState<AuthState>({ status: "loading" });
  const channelRef = useRef<BroadcastChannel | null>(null);

  const endSession = useCallback(() => {
    setAccessToken(null);
    queryClient.clear();
    setState({ status: "guest" });
  }, [queryClient]);

  useEffect(() => {
    return setSessionHandlers({
      onSessionExpired: endSession,
      onPasswordChangeRequired: () =>
        setState((current) =>
          current.status === "authenticated"
            ? { status: "authenticated", user: { ...current.user, must_change_password: true } }
            : current,
        ),
    });
  }, [endSession]);

  useEffect(() => {
    const channel = new BroadcastChannel(AUTH_CHANNEL);
    channel.onmessage = (event: MessageEvent) => {
      if (event.data === LOGOUT_MESSAGE) endSession();
    };
    channelRef.current = channel;
    return () => {
      channel.close();
      channelRef.current = null;
    };
  }, [endSession]);

  useEffect(() => {
    let cancelled = false;
    const restore = async () => {
      try {
        const token = await refreshAccessToken(null);
        const user = token ? await fetchMe() : null;
        if (!cancelled) setState(user ? { status: "authenticated", user } : { status: "guest" });
      } catch {
        if (!cancelled) setState({ status: "guest" });
      }
    };
    void restore();
    return () => {
      cancelled = true;
    };
  }, []);

  const startSession = useCallback(async (accessToken: string) => {
    setAccessToken(accessToken);
    const user = await fetchMe();
    setState({ status: "authenticated", user });
    return user;
  }, []);

  const login = useCallback(
    async (email: string, password: string) => {
      const tokens = await unwrap(api.POST("/api/auth/login", { body: { email, password } }));
      return startSession(tokens.access_token);
    },
    [startSession],
  );

  const changePassword = useCallback(
    async (currentPassword: string, newPassword: string) => {
      const tokens = await unwrap(
        api.POST("/api/auth/change-password", {
          body: { current_password: currentPassword, new_password: newPassword },
        }),
      );
      return startSession(tokens.access_token);
    },
    [startSession],
  );

  const logout = useCallback(async () => {
    try {
      await api.POST("/api/auth/logout");
    } catch {
      // Выход на клиенте выполняется даже без ответа сервера.
    }
    endSession();
    channelRef.current?.postMessage(LOGOUT_MESSAGE);
  }, [endSession]);

  const value = useMemo<AuthContextValue>(
    () => ({
      state,
      user: state.status === "authenticated" ? state.user : null,
      login,
      logout,
      changePassword,
    }),
    [state, login, logout, changePassword],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
```

`frontend/src/features/auth/guards.tsx`:
```tsx
import { Navigate, Outlet, useLocation, useSearchParams } from "react-router";

import type { UserRole } from "../../api/types";
import { FullScreenLoader } from "../../shared/ui/FullScreenLoader";
import { StatusPage } from "../../shared/ui/StatusPage";
import { useAuth } from "./AuthContext";
import { loginPathFor, safeNext } from "./next";

export const CHANGE_PASSWORD_PATH = "/change-password";

export function RequireAuth() {
  const { state } = useAuth();
  const location = useLocation();

  if (state.status === "loading") return <FullScreenLoader />;
  if (state.status === "guest") {
    return <Navigate to={loginPathFor(location.pathname, location.search)} replace />;
  }
  if (state.user.must_change_password && location.pathname !== CHANGE_PASSWORD_PATH) {
    return <Navigate to={CHANGE_PASSWORD_PATH} replace />;
  }
  return <Outlet />;
}

export function RequireRole({ role }: { role: UserRole }) {
  const { user } = useAuth();
  if (user?.role !== role) {
    return (
      <StatusPage
        code={403}
        title="Нет доступа"
        text="У вас нет прав для просмотра этой страницы."
      />
    );
  }
  return <Outlet />;
}

export function GuestOnly() {
  const { state } = useAuth();
  const [searchParams] = useSearchParams();

  if (state.status === "loading") return <FullScreenLoader />;
  if (state.status === "authenticated") {
    return <Navigate to={safeNext(searchParams.get("next"))} replace />;
  }
  return <Outlet />;
}
```

`frontend/src/features/auth/index.ts`:
```ts
export { useAuth } from "./AuthContext";
export type { AuthState } from "./AuthContext";
export { AuthProvider } from "./AuthProvider";
export { CHANGE_PASSWORD_PATH, GuestOnly, RequireAuth, RequireRole } from "./guards";
```

- [ ] **Step 4: Тесты проходят, commit**

```bash
npx vitest run src/features/auth   # PASS (8 тестов)
npm run format && npm run check
cd .. && git add frontend && git commit -m "feat(frontend): сессия пользователя и guard'ы маршрутов"
```


### Task 6: Каркас Modernize: сайдбар, шапка, главная, профиль, 404

**Files:**
- Create: `frontend/src/shared/lookups/queryKeys.ts`, `frontend/src/shared/lookups/departments.ts`
- Create: `frontend/src/shared/ui/PageContainer.tsx`, `frontend/src/shared/ui/DashboardCard.tsx`
- Create: `frontend/src/layout/menu.ts`, `SidebarMenu.tsx`, `Logo.tsx`, `Sidebar.tsx`, `UserMenu.tsx`, `Header.tsx`, `FullLayout.tsx`, `BlankLayout.tsx`, `NotFoundPage.tsx`
- Create: `frontend/src/features/home/HomePage.tsx`, `frontend/src/features/home/index.ts`, `frontend/src/features/auth/ProfilePage.tsx`
- Modify: `frontend/src/features/auth/index.ts` (экспорт `ProfilePage`)
- Test: `frontend/src/app/shell.test.tsx`

**Interfaces:**
- Consumes: `useAuth`, `RequireAuth`, `AuthProvider` (Task 5); `ROLE_LABELS`, `initialsOf` (Task 3); `useDocumentTitle`, `StatusPage` (Task 5); `api`, `unwrap` (Task 2).
- Produces:
  - `queryKeys = { users: ["users"], departments: ["departments"], directories: ["directories"] }` — корни ключей кэша; мутации фич инвалидируют свой корень.
  - `useDepartments()` — `GET /api/departments` (ключ `["departments", "list"]`).
  - `PageContainer({ title, breadcrumbs?: { label; to? }[], actions?, children })` (ставит `document.title`), `DashboardCard({ title?, subtitle?, action?, children? })`.
  - `FullLayout({ children? })`, `BlankLayout({ children? })` — рендерят `children` или `<Outlet />`; `NotFoundPage`; `MENU`, `menuForRole(role)`; навигация с `aria-label="Основное меню"`; кнопка «Меню пользователя» с пунктами «Профиль», «Сменить пароль», «Выйти».
  - `features/home`: `HomePage`; `features/auth`: `ProfilePage`.

- [ ] **Step 1: Написать падающие тесты**

Тест лежит в `src/app/`: только `app` может импортировать и `layout`, и несколько фич. В jsdom нет `matchMedia` — эмуляция из `src/test/setup.ts` (Task 1) делает окно десктопным, поэтому сайдбар постоянный и меню видно сразу.

`frontend/src/app/shell.test.tsx`:
```tsx
import { screen, waitFor, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";

import type { Schemas } from "../api/types";
import { AuthProvider, ProfilePage, RequireAuth } from "../features/auth";
import { HomePage } from "../features/home";
import { makeMe, mockSignedIn } from "../test/auth";
import { renderRoutes } from "../test/render";
import { server } from "../test/server";
import { FullLayout } from "../layout/FullLayout";
import { NotFoundPage } from "../layout/NotFoundPage";

const routes = [
  {
    element: <RequireAuth />,
    children: [
      {
        element: <FullLayout />,
        children: [
          { path: "/", element: <HomePage /> },
          { path: "/profile", element: <ProfilePage /> },
          { path: "*", element: <NotFoundPage /> },
        ],
      },
    ],
  },
];

function renderShell(path: string) {
  return renderRoutes(routes, {
    initialEntries: [path],
    wrapper: (children) => <AuthProvider>{children}</AuthProvider>,
  });
}

function mockDepartments(departments: Schemas["DepartmentRead"][] = []) {
  server.use(http.get("*/api/departments", () => HttpResponse.json(departments)));
}

test("администратор видит раздел «Администрирование» в меню", async () => {
  mockSignedIn(makeMe({ role: "admin" }));
  renderShell("/");

  const nav = await screen.findByRole("navigation", { name: "Основное меню" });
  expect(within(nav).getByRole("link", { name: "Пользователи" })).toHaveAttribute(
    "href",
    "/admin/users",
  );
  expect(within(nav).getByText("Администрирование")).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "Главная" })).toBeInTheDocument();
  expect(screen.getByText("Здравствуйте, Иванов Иван")).toBeInTheDocument();
});

test("сотрудник не видит раздел «Администрирование»", async () => {
  mockSignedIn(makeMe({ role: "employee" }));
  renderShell("/");

  const nav = await screen.findByRole("navigation", { name: "Основное меню" });
  expect(within(nav).getByRole("link", { name: "Главная" })).toBeInTheDocument();
  expect(within(nav).queryByText("Администрирование")).not.toBeInTheDocument();
});

test("неизвестный путь показывает страницу 404", async () => {
  mockSignedIn();
  renderShell("/nowhere");

  expect(await screen.findByRole("heading", { name: "Страница не найдена" })).toBeInTheDocument();
  // Заголовок ставится в эффекте после отрисовки — ждём его, а не проверяем сразу.
  await waitFor(() => expect(document.title).toBe("Страница не найдена — IT-платформа"));
});

test("профиль показывает данные пользователя и название отдела", async () => {
  mockSignedIn(makeMe({ role: "manager", department_id: 7, email: "m@company.ru" }));
  mockDepartments([{ id: 7, name: "Бухгалтерия", head_id: 1 }]);
  renderShell("/profile");

  const main = await screen.findByRole("main");
  expect(await within(main).findByText("Бухгалтерия")).toBeInTheDocument();
  expect(within(main).getByText("m@company.ru")).toBeInTheDocument();
  expect(within(main).getByText("Руководитель")).toBeInTheDocument();
});

test("меню пользователя: выход ведёт на страницу входа", async () => {
  mockSignedIn();
  server.use(http.post("*/api/auth/logout", () => new HttpResponse(null, { status: 204 })));
  const { user, router } = renderRoutes(
    [...routes, { path: "/login", element: <p>страница входа</p> }],
    { initialEntries: ["/"], wrapper: (children) => <AuthProvider>{children}</AuthProvider> },
  );

  await user.click(await screen.findByRole("button", { name: "Меню пользователя" }));
  await user.click(await screen.findByRole("menuitem", { name: "Выйти" }));

  expect(await screen.findByText("страница входа")).toBeInTheDocument();
  expect(router.state.location.pathname).toBe("/login");
});
```

- [ ] **Step 2: Запустить тесты — падают**

Run: `npx vitest run src/app/shell.test.tsx`
Expected: FAIL — не найдены `../layout/FullLayout`, `../features/home`, экспорт `ProfilePage`.

- [ ] **Step 3: Реализация**

Каркас повторяет вид `modernize-react-lite/package/src/layouts/full/*`: сайдбар 270 px (постоянный `Drawer` от `lg`, временный ниже), активный пункт — заливка `primary.main` со скруглением 7 px, шапка 70 px с размытием фона. Библиотеки `react-mui-sidebar` и `simplebar` из шаблона не подключаются — меню собрано из `List`/`ListItemButton` MUI. Пункт «Справочники» ведёт на `/admin/directories` (маршрут появится в Task 11).

`frontend/src/shared/lookups/queryKeys.ts`:
```ts
export const queryKeys = {
  users: ["users"] as const,
  departments: ["departments"] as const,
  directories: ["directories"] as const,
};
```

`frontend/src/shared/lookups/departments.ts`:
```ts
import { useQuery } from "@tanstack/react-query";

import { api, unwrap } from "../../api/client";
import { queryKeys } from "./queryKeys";

export function useDepartments() {
  return useQuery({
    queryKey: [...queryKeys.departments, "list"],
    queryFn: () => unwrap(api.GET("/api/departments")),
  });
}
```

`frontend/src/shared/ui/PageContainer.tsx`:
```tsx
import { Box, Breadcrumbs, Link as MuiLink, Stack, Typography } from "@mui/material";
import type { ReactNode } from "react";
import { Link } from "react-router";

import { useDocumentTitle } from "../lib/useDocumentTitle";

export interface Breadcrumb {
  label: string;
  to?: string;
}

interface PageContainerProps {
  title: string;
  breadcrumbs?: Breadcrumb[];
  actions?: ReactNode;
  children: ReactNode;
}

export function PageContainer({ title, breadcrumbs = [], actions, children }: PageContainerProps) {
  useDocumentTitle(title);
  return (
    <Box>
      <Stack
        direction={{ xs: "column", sm: "row" }}
        spacing={2}
        sx={{ mb: 3, justifyContent: "space-between", alignItems: { sm: "center" } }}
      >
        <Box>
          <Typography variant="h3" component="h1">
            {title}
          </Typography>
          {breadcrumbs.length > 0 && (
            <Breadcrumbs sx={{ mt: 0.5 }}>
              {breadcrumbs.map((crumb) =>
                crumb.to ? (
                  <MuiLink key={crumb.label} component={Link} to={crumb.to} color="inherit">
                    {crumb.label}
                  </MuiLink>
                ) : (
                  <Typography key={crumb.label} color="text.secondary">
                    {crumb.label}
                  </Typography>
                ),
              )}
            </Breadcrumbs>
          )}
        </Box>
        {actions && (
          <Stack direction="row" spacing={1}>
            {actions}
          </Stack>
        )}
      </Stack>
      {children}
    </Box>
  );
}
```

`frontend/src/shared/ui/DashboardCard.tsx`:
```tsx
import { Card, CardContent, Stack, Typography } from "@mui/material";
import type { ReactNode } from "react";

interface DashboardCardProps {
  title?: string;
  subtitle?: string;
  action?: ReactNode;
  children?: ReactNode;
}

export function DashboardCard({ title, subtitle, action, children }: DashboardCardProps) {
  return (
    <Card variant="outlined" sx={{ height: "100%" }}>
      <CardContent sx={{ p: "30px" }}>
        {(title || action) && (
          <Stack direction="row" spacing={2} sx={{ mb: 3, justifyContent: "space-between" }}>
            <div>
              {title && <Typography variant="h5">{title}</Typography>}
              {subtitle && (
                <Typography variant="subtitle2" color="text.secondary">
                  {subtitle}
                </Typography>
              )}
            </div>
            {action}
          </Stack>
        )}
        {children}
      </CardContent>
    </Card>
  );
}
```

`frontend/src/layout/menu.ts`:
```ts
import {
  IconBook2,
  IconBuildingCommunity,
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
    title: "Администрирование",
    roles: ["admin"],
    items: [
      { label: "Пользователи", to: "/admin/users", icon: IconUsers },
      { label: "Отделы", to: "/admin/departments", icon: IconBuildingCommunity },
      { label: "Справочники", to: "/admin/directories", icon: IconBook2 },
    ],
  },
];

export function menuForRole(role: UserRole): MenuSection[] {
  return MENU.filter((section) => !section.roles || section.roles.includes(role));
}
```

`frontend/src/layout/SidebarMenu.tsx`:
```tsx
import { List, ListItemButton, ListItemIcon, ListItemText, ListSubheader } from "@mui/material";
import { NavLink } from "react-router";

import { useAuth } from "../features/auth";
import { menuForRole } from "./menu";

export function SidebarMenu({ onNavigate }: { onNavigate?: () => void }) {
  const { user } = useAuth();
  if (!user) return null;

  return (
    <nav aria-label="Основное меню">
      {menuForRole(user.role).map((section) => (
        <List
          key={section.title ?? "main"}
          sx={{ px: 3 }}
          subheader={
            section.title ? (
              <ListSubheader
                disableSticky
                sx={{ px: 0, fontWeight: 700, fontSize: "0.75rem", textTransform: "uppercase" }}
              >
                {section.title}
              </ListSubheader>
            ) : undefined
          }
        >
          {section.items.map(({ label, to, icon: Icon }) => (
            <ListItemButton
              key={to}
              component={NavLink}
              to={to}
              end={to === "/"}
              onClick={onNavigate}
              sx={{
                borderRadius: "7px",
                mb: 0.5,
                color: "text.secondary",
                "&.active": {
                  bgcolor: "primary.main",
                  color: "primary.contrastText",
                  "&:hover": { bgcolor: "primary.dark" },
                  "& .MuiListItemIcon-root": { color: "inherit" },
                },
              }}
            >
              <ListItemIcon sx={{ minWidth: 36, color: "inherit" }}>
                <Icon size="1.3rem" stroke={1.5} />
              </ListItemIcon>
              <ListItemText primary={label} />
            </ListItemButton>
          ))}
        </List>
      ))}
    </nav>
  );
}
```

`frontend/src/layout/Logo.tsx`:
```tsx
import { Box, Typography } from "@mui/material";
import { IconDeviceDesktopCog } from "@tabler/icons-react";
import { Link } from "react-router";

export function Logo() {
  return (
    <Box
      component={Link}
      to="/"
      sx={{
        display: "flex",
        alignItems: "center",
        gap: 1,
        height: 70,
        px: 3,
        color: "text.primary",
      }}
    >
      <Box sx={{ color: "primary.main", display: "flex" }}>
        <IconDeviceDesktopCog size={28} stroke={1.5} />
      </Box>
      <Typography variant="h5" component="span">
        IT-платформа
      </Typography>
    </Box>
  );
}
```

`frontend/src/layout/Sidebar.tsx`:
```tsx
import { Box, Drawer, useMediaQuery, type Theme } from "@mui/material";

import { Logo } from "./Logo";
import { SidebarMenu } from "./SidebarMenu";

export const SIDEBAR_WIDTH = 270;

interface SidebarProps {
  mobileOpen: boolean;
  onMobileClose: () => void;
}

export function Sidebar({ mobileOpen, onMobileClose }: SidebarProps) {
  const lgUp = useMediaQuery((theme: Theme) => theme.breakpoints.up("lg"));
  const content = (
    <>
      <Logo />
      <SidebarMenu onNavigate={lgUp ? undefined : onMobileClose} />
    </>
  );

  if (lgUp) {
    return (
      <Box sx={{ width: SIDEBAR_WIDTH, flexShrink: 0 }}>
        <Drawer
          variant="permanent"
          anchor="left"
          slotProps={{ paper: { sx: { width: SIDEBAR_WIDTH, boxSizing: "border-box" } } }}
        >
          {content}
        </Drawer>
      </Box>
    );
  }
  return (
    <Drawer
      variant="temporary"
      anchor="left"
      open={mobileOpen}
      onClose={onMobileClose}
      slotProps={{
        paper: { sx: { width: SIDEBAR_WIDTH, boxShadow: (theme) => theme.shadows[8] } },
      }}
    >
      {content}
    </Drawer>
  );
}
```

`frontend/src/layout/UserMenu.tsx`:
```tsx
import {
  Avatar,
  Box,
  Button,
  Divider,
  ListItemIcon,
  Menu,
  MenuItem,
  Typography,
} from "@mui/material";
import { IconKey, IconLogout, IconUserCircle } from "@tabler/icons-react";
import { useState } from "react";
import { useNavigate } from "react-router";

import { useAuth } from "../features/auth";
import { initialsOf, ROLE_LABELS } from "../shared/lib/format";

export function UserMenu() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [anchor, setAnchor] = useState<HTMLElement | null>(null);
  if (!user) return null;

  const go = (path: string) => {
    setAnchor(null);
    void navigate(path);
  };
  const signOut = async () => {
    setAnchor(null);
    await logout();
    void navigate("/login", { replace: true });
  };

  return (
    <>
      <Button
        color="inherit"
        onClick={(event) => setAnchor(event.currentTarget)}
        aria-label="Меню пользователя"
        sx={{ gap: 1.5, textAlign: "left" }}
      >
        <Avatar sx={{ width: 35, height: 35, bgcolor: "primary.main", fontSize: "0.875rem" }}>
          {initialsOf(user.full_name)}
        </Avatar>
        <Box sx={{ display: { xs: "none", sm: "block" } }}>
          <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
            {user.full_name}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            {ROLE_LABELS[user.role]}
          </Typography>
        </Box>
      </Button>
      <Menu
        anchorEl={anchor}
        open={Boolean(anchor)}
        onClose={() => setAnchor(null)}
        anchorOrigin={{ horizontal: "right", vertical: "bottom" }}
        transformOrigin={{ horizontal: "right", vertical: "top" }}
      >
        <MenuItem onClick={() => go("/profile")}>
          <ListItemIcon>
            <IconUserCircle size={20} stroke={1.5} />
          </ListItemIcon>
          Профиль
        </MenuItem>
        <MenuItem onClick={() => go("/change-password")}>
          <ListItemIcon>
            <IconKey size={20} stroke={1.5} />
          </ListItemIcon>
          Сменить пароль
        </MenuItem>
        <Divider />
        <MenuItem onClick={() => void signOut()}>
          <ListItemIcon>
            <IconLogout size={20} stroke={1.5} />
          </ListItemIcon>
          Выйти
        </MenuItem>
      </Menu>
    </>
  );
}
```

`frontend/src/layout/Header.tsx`:
```tsx
import { AppBar, Box, IconButton, Toolbar } from "@mui/material";
import { IconMenu2 } from "@tabler/icons-react";

import { UserMenu } from "./UserMenu";

export function Header({ onOpenSidebar }: { onOpenSidebar: () => void }) {
  return (
    <AppBar
      position="sticky"
      color="default"
      elevation={0}
      sx={{ bgcolor: "rgba(255,255,255,0.85)", backdropFilter: "blur(4px)" }}
    >
      <Toolbar sx={{ minHeight: 70 }}>
        <IconButton
          aria-label="Открыть меню"
          onClick={onOpenSidebar}
          sx={{ display: { lg: "none" } }}
        >
          <IconMenu2 size={22} stroke={1.5} />
        </IconButton>
        <Box sx={{ flexGrow: 1 }} />
        <UserMenu />
      </Toolbar>
    </AppBar>
  );
}
```

`frontend/src/layout/FullLayout.tsx`:
```tsx
import { Box, Container } from "@mui/material";
import { useState, type ReactNode } from "react";
import { Outlet } from "react-router";

import { Header } from "./Header";
import { Sidebar } from "./Sidebar";

export function FullLayout({ children }: { children?: ReactNode }) {
  const [mobileOpen, setMobileOpen] = useState(false);
  return (
    <Box sx={{ display: "flex", minHeight: "100vh" }}>
      <Sidebar mobileOpen={mobileOpen} onMobileClose={() => setMobileOpen(false)} />
      <Box sx={{ display: "flex", flexDirection: "column", flexGrow: 1, minWidth: 0 }}>
        <Header onOpenSidebar={() => setMobileOpen(true)} />
        <Container component="main" maxWidth="lg" sx={{ py: 3 }}>
          {children ?? <Outlet />}
        </Container>
      </Box>
    </Box>
  );
}
```

`frontend/src/layout/BlankLayout.tsx`:
```tsx
import { Box } from "@mui/material";
import type { ReactNode } from "react";
import { Outlet } from "react-router";

export function BlankLayout({ children }: { children?: ReactNode }) {
  return (
    <Box
      component="main"
      sx={{
        minHeight: "100vh",
        display: "grid",
        placeItems: "center",
        p: 2,
        background: "radial-gradient(#d2f1df, #d3d7fa, #bad8f4) 0% 0% / 400% 400%",
      }}
    >
      {children ?? <Outlet />}
    </Box>
  );
}
```

`frontend/src/layout/NotFoundPage.tsx`:
```tsx
import { StatusPage } from "../shared/ui/StatusPage";

export function NotFoundPage() {
  return (
    <StatusPage
      code={404}
      title="Страница не найдена"
      text="Возможно, ссылка устарела или в адресе опечатка."
    />
  );
}
```

`frontend/src/features/home/HomePage.tsx`:
```tsx
import { Grid, Typography } from "@mui/material";

import { useAuth } from "../auth";
import { DashboardCard } from "../../shared/ui/DashboardCard";
import { PageContainer } from "../../shared/ui/PageContainer";

const PLACEHOLDERS = ["Мои заявки", "Заявки на мне", "Мои задачи", "Моя техника"];

export function HomePage() {
  const { user } = useAuth();
  return (
    <PageContainer title="Главная">
      <Typography variant="h5" sx={{ mb: 3 }}>
        Здравствуйте, {user?.full_name}
      </Typography>
      <Grid container spacing={3}>
        {PLACEHOLDERS.map((title) => (
          <Grid key={title} size={{ xs: 12, sm: 6, lg: 3 }}>
            <DashboardCard title={title}>
              <Typography color="text.secondary">Появится в следующих версиях</Typography>
            </DashboardCard>
          </Grid>
        ))}
      </Grid>
    </PageContainer>
  );
}
```

`frontend/src/features/home/index.ts`:
```ts
export { HomePage } from "./HomePage";
```

`frontend/src/features/auth/ProfilePage.tsx`:
```tsx
import { Button, Stack, Typography } from "@mui/material";
import { Link } from "react-router";

import { ROLE_LABELS } from "../../shared/lib/format";
import { useDepartments } from "../../shared/lookups/departments";
import { DashboardCard } from "../../shared/ui/DashboardCard";
import { PageContainer } from "../../shared/ui/PageContainer";
import { useAuth } from "./AuthContext";

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <Typography variant="body2" color="text.secondary">
        {label}
      </Typography>
      <Typography>{value}</Typography>
    </div>
  );
}

export function ProfilePage() {
  const { user } = useAuth();
  const departments = useDepartments();
  if (!user) return null;

  const department =
    user.department_id === null
      ? "Без отдела"
      : (departments.data?.find((item) => item.id === user.department_id)?.name ?? "…");

  return (
    <PageContainer title="Профиль">
      <DashboardCard>
        <Stack spacing={2}>
          <Field label="ФИО" value={user.full_name} />
          <Field label="Email" value={user.email} />
          <Field label="Роль" value={ROLE_LABELS[user.role]} />
          <Field label="Отдел" value={department} />
          <div>
            <Button component={Link} to="/change-password" variant="outlined">
              Сменить пароль
            </Button>
          </div>
        </Stack>
      </DashboardCard>
    </PageContainer>
  );
}
```

`frontend/src/features/auth/index.ts`:
```ts
export { useAuth } from "./AuthContext";
export type { AuthState } from "./AuthContext";
export { AuthProvider } from "./AuthProvider";
export { CHANGE_PASSWORD_PATH, GuestOnly, RequireAuth, RequireRole } from "./guards";
export { ProfilePage } from "./ProfilePage";
```

- [ ] **Step 4: Тесты проходят, commit**

```bash
npx vitest run src/app/shell.test.tsx   # PASS (5 тестов)
npm run format && npm run check
cd .. && git add frontend && git commit -m "feat(frontend): каркас Modernize, главная, профиль, 404"
```


### Task 7: Маршруты приложения, вход и смена пароля

**Files:**
- Create: `frontend/src/features/auth/LoginPage.tsx`, `frontend/src/features/auth/ChangePasswordPage.tsx`
- Create: `frontend/src/app/providers.tsx`, `frontend/src/app/routes.tsx`, `frontend/src/test/app.tsx`
- Modify: `frontend/src/app/App.tsx` (полная замена), `frontend/src/features/auth/index.ts`
- Delete: `frontend/src/app/App.test.tsx`
- Test: `frontend/src/app/routes.test.tsx`

**Interfaces:**
- Consumes: всё из Tasks 2–6; `applyApiErrors`, `fieldByCode`, `FormTextField` (Task 4); `createQueryClient` (Task 3).
- Produces:
  - `routes: RouteObject[]` — `/login` (GuestOnly + BlankLayout), `/change-password` (в BlankLayout при `must_change_password`, иначе в FullLayout), `/`, `/profile`, `*` → 404 внутри каркаса. Tasks 9–11 добавляют блок `RequireRole role="admin"`.
  - `AppProviders({ queryClient, children })` — тема, CssBaseline, QueryClientProvider, SnackbarProvider, AuthProvider.
  - `App` — `createBrowserRouter(routes)` внутри `AppProviders`.
  - `features/auth`: `LoginPage`, `ChangePasswordPage({ forced? })`.
  - `test/app.tsx`: `renderApp(path)` — всё приложение в memory-роутере.

- [ ] **Step 1: Написать падающие тесты и удалить смоук-тест**

```bash
rm src/app/App.test.tsx
```

`frontend/src/test/app.tsx`:
```tsx
import { AuthProvider } from "../features/auth";
import { routes } from "../app/routes";
import { renderRoutes } from "./render";

/** Рендерит приложение целиком (все маршруты, AuthProvider) на пути `path`. */
export function renderApp(path: string) {
  return renderRoutes(routes, {
    initialEntries: [path],
    wrapper: (children) => <AuthProvider>{children}</AuthProvider>,
  });
}
```

`frontend/src/app/routes.test.tsx`:
```tsx
import { screen } from "@testing-library/react";
import { http, HttpResponse } from "msw";

import type { Schemas } from "../api/types";
import { renderApp } from "../test/app";
import { makeMe, mockSignedOut, mockSignedIn, tokenResponse } from "../test/auth";
import { errorBody } from "../test/http";
import { server } from "../test/server";

test("вход: успешный вход ведёт на исходную страницу", async () => {
  mockSignedOut();
  server.use(http.get("*/api/departments", () => HttpResponse.json([])));
  server.use(
    http.post("*/api/auth/login", () => HttpResponse.json(tokenResponse("t-login"))),
    http.get("*/api/auth/me", ({ request }) =>
      request.headers.get("Authorization") === "Bearer t-login"
        ? HttpResponse.json(makeMe({ full_name: "Сидоров Сидор" }))
        : HttpResponse.json(errorBody("unauthorized", "Требуется вход"), { status: 401 }),
    ),
  );
  const { user, router } = renderApp("/profile");

  await user.type(await screen.findByLabelText("Email"), "admin@company.ru");
  await user.type(screen.getByLabelText("Пароль"), "secret");
  await user.click(screen.getByRole("button", { name: "Войти" }));

  expect(await screen.findByText("Сидоров Сидор", { selector: "p" })).toBeInTheDocument();
  expect(router.state.location.pathname).toBe("/profile");
});

test("вход: неверный пароль и блокировка показывают сообщение backend", async () => {
  mockSignedOut();
  server.use(
    http.post("*/api/auth/login", () =>
      HttpResponse.json(errorBody("invalid_credentials", "Неверный email или пароль"), {
        status: 401,
      }),
    ),
  );
  const { user } = renderApp("/login");

  await user.click(await screen.findByRole("button", { name: "Войти" }));
  expect(await screen.findByText("Введите email")).toBeInTheDocument();

  await user.type(screen.getByLabelText("Email"), "admin@company.ru");
  await user.type(screen.getByLabelText("Пароль"), "wrong");
  await user.click(screen.getByRole("button", { name: "Войти" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("Неверный email или пароль");

  server.use(
    http.post("*/api/auth/login", () =>
      HttpResponse.json(
        errorBody("login_locked", "Слишком много попыток входа, попробуйте позже"),
        {
          status: 429,
        },
      ),
    ),
  );
  await user.click(screen.getByRole("button", { name: "Войти" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("Слишком много попыток входа");
});

test("обязательная смена пароля: форма без меню, после смены — главная", async () => {
  mockSignedIn(makeMe({ must_change_password: true }));
  server.use(
    http.post("*/api/auth/change-password", async ({ request }) => {
      const body = (await request.json()) as Schemas["ChangePasswordRequest"];
      if (body.current_password !== "temp") {
        return HttpResponse.json(
          errorBody("invalid_current_password", "Текущий пароль указан неверно"),
          {
            status: 422,
          },
        );
      }
      server.use(http.get("*/api/auth/me", () => HttpResponse.json(makeMe())));
      return HttpResponse.json(tokenResponse("t-new"));
    }),
  );
  const { user, router } = renderApp("/");

  expect(await screen.findByText(/Администратор выдал вам временный пароль/)).toBeInTheDocument();
  expect(screen.queryByRole("navigation", { name: "Основное меню" })).not.toBeInTheDocument();

  await user.type(screen.getByLabelText("Текущий пароль"), "wrong");
  await user.type(screen.getByLabelText("Новый пароль"), "N3w-password!");
  await user.type(screen.getByLabelText("Повторите новый пароль"), "other");
  await user.click(screen.getByRole("button", { name: "Сменить пароль" }));
  expect(await screen.findByText("Пароли не совпадают")).toBeInTheDocument();

  await user.clear(screen.getByLabelText("Повторите новый пароль"));
  await user.type(screen.getByLabelText("Повторите новый пароль"), "N3w-password!");
  await user.click(screen.getByRole("button", { name: "Сменить пароль" }));
  expect(await screen.findByText("Текущий пароль указан неверно")).toBeInTheDocument();

  await user.clear(screen.getByLabelText("Текущий пароль"));
  await user.type(screen.getByLabelText("Текущий пароль"), "temp");
  await user.click(screen.getByRole("button", { name: "Сменить пароль" }));

  expect(await screen.findByRole("heading", { name: "Главная" })).toBeInTheDocument();
  expect(router.state.location.pathname).toBe("/");
});

test("неизвестный путь внутри приложения показывает 404 в каркасе", async () => {
  mockSignedIn();
  renderApp("/nowhere");

  expect(await screen.findByRole("heading", { name: "Страница не найдена" })).toBeInTheDocument();
  expect(screen.getByRole("navigation", { name: "Основное меню" })).toBeInTheDocument();
});
```

- [ ] **Step 2: Запустить тесты — падают**

Run: `npx vitest run src/app/routes.test.tsx`
Expected: FAIL — не найден `../app/routes`.

- [ ] **Step 3: Реализация**

После успешного входа `LoginPage` сам никуда не переходит: `GuestOnly` видит состояние `authenticated` и уводит на `?next=` (или `/`), а `RequireAuth` при `must_change_password` — на `/change-password`. Имена полей формы смены пароля совпадают с полями тела запроса (`current_password`, `new_password`), чтобы ошибки 422 из `loc` раскладывались по полям. Коды backend: `invalid_current_password` → текущий пароль; `password_reused`, `weak_password` → новый пароль.

`frontend/src/features/auth/LoginPage.tsx`:
```tsx
import { Alert, Box, Button, Card, CardContent, Stack, Typography } from "@mui/material";
import { useState } from "react";
import { useForm } from "react-hook-form";

import { applyApiErrors } from "../../shared/lib/applyApiErrors";
import { useDocumentTitle } from "../../shared/lib/useDocumentTitle";
import { FormTextField } from "../../shared/ui/form/FormTextField";
import { useAuth } from "./AuthContext";

interface LoginValues {
  email: string;
  password: string;
}

export function LoginPage() {
  useDocumentTitle("Вход");
  const { login } = useAuth();
  const [formError, setFormError] = useState<string | null>(null);
  const {
    control,
    handleSubmit,
    setError,
    formState: { isSubmitting },
  } = useForm<LoginValues>({ defaultValues: { email: "", password: "" } });

  // После успешного входа GuestOnly сам переведёт на ?next= или на главную.
  const onSubmit = handleSubmit(async ({ email, password }) => {
    setFormError(null);
    try {
      await login(email.trim(), password);
    } catch (error) {
      setFormError(applyApiErrors(error, setError, { fields: ["email", "password"] }));
    }
  });

  return (
    <Card sx={{ width: "100%", maxWidth: 450 }}>
      <CardContent sx={{ p: 4 }}>
        <Box sx={{ textAlign: "center", mb: 3 }}>
          <Typography variant="h3" component="h1">
            IT-платформа
          </Typography>
          <Typography color="text.secondary" sx={{ mt: 1 }}>
            Вход в систему
          </Typography>
        </Box>
        <form onSubmit={onSubmit} noValidate>
          <Stack spacing={2.5}>
            {formError && <Alert severity="error">{formError}</Alert>}
            <FormTextField
              control={control}
              name="email"
              label="Email"
              type="email"
              autoComplete="username"
              autoFocus
              rules={{ required: "Введите email" }}
            />
            <FormTextField
              control={control}
              name="password"
              label="Пароль"
              type="password"
              autoComplete="current-password"
              rules={{ required: "Введите пароль" }}
            />
            <Button type="submit" variant="contained" size="large" loading={isSubmitting}>
              Войти
            </Button>
          </Stack>
        </form>
      </CardContent>
    </Card>
  );
}
```

`frontend/src/features/auth/ChangePasswordPage.tsx`:
```tsx
import { Alert, Button, Card, CardContent, Stack, Typography } from "@mui/material";
import { useSnackbar } from "notistack";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { useNavigate, useSearchParams } from "react-router";

import { applyApiErrors, fieldByCode } from "../../shared/lib/applyApiErrors";
import { useDocumentTitle } from "../../shared/lib/useDocumentTitle";
import { FormTextField } from "../../shared/ui/form/FormTextField";
import { useAuth } from "./AuthContext";
import { safeNext } from "./next";

interface ChangePasswordValues {
  current_password: string;
  new_password: string;
  repeat_password: string;
}

const fieldForError = fieldByCode<ChangePasswordValues>({
  invalid_current_password: "current_password",
  password_reused: "new_password",
  weak_password: "new_password",
});

export function ChangePasswordPage({ forced = false }: { forced?: boolean }) {
  useDocumentTitle("Смена пароля");
  const { changePassword, logout } = useAuth();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { enqueueSnackbar } = useSnackbar();
  const [formError, setFormError] = useState<string | null>(null);
  const {
    control,
    handleSubmit,
    setError,
    getValues,
    formState: { isSubmitting },
  } = useForm<ChangePasswordValues>({
    defaultValues: { current_password: "", new_password: "", repeat_password: "" },
  });

  const onSubmit = handleSubmit(async ({ current_password, new_password }) => {
    setFormError(null);
    try {
      await changePassword(current_password, new_password);
      enqueueSnackbar("Пароль изменён", { variant: "success" });
      void navigate(safeNext(searchParams.get("next")), { replace: true });
    } catch (error) {
      setFormError(
        applyApiErrors(error, setError, {
          fields: ["current_password", "new_password"],
          fieldForError,
        }),
      );
    }
  });

  return (
    <Card sx={{ width: "100%", maxWidth: 480 }}>
      <CardContent sx={{ p: 4 }}>
        <Typography variant="h4" component="h1" sx={{ mb: 2 }}>
          Смена пароля
        </Typography>
        <form onSubmit={onSubmit} noValidate>
          <Stack spacing={2.5}>
            {forced && (
              <Alert severity="info">
                Администратор выдал вам временный пароль. Задайте новый пароль, чтобы продолжить.
              </Alert>
            )}
            {formError && <Alert severity="error">{formError}</Alert>}
            <FormTextField
              control={control}
              name="current_password"
              label="Текущий пароль"
              type="password"
              autoComplete="current-password"
              rules={{ required: "Введите текущий пароль" }}
            />
            <FormTextField
              control={control}
              name="new_password"
              label="Новый пароль"
              type="password"
              autoComplete="new-password"
              rules={{ required: "Введите новый пароль" }}
            />
            <FormTextField
              control={control}
              name="repeat_password"
              label="Повторите новый пароль"
              type="password"
              autoComplete="new-password"
              rules={{
                required: "Повторите новый пароль",
                validate: (value) => value === getValues("new_password") || "Пароли не совпадают",
              }}
            />
            <Stack direction="row" spacing={1} sx={{ justifyContent: "flex-end" }}>
              {forced && (
                <Button color="inherit" onClick={() => void logout()}>
                  Выйти
                </Button>
              )}
              <Button type="submit" variant="contained" loading={isSubmitting}>
                Сменить пароль
              </Button>
            </Stack>
          </Stack>
        </form>
      </CardContent>
    </Card>
  );
}
```

`frontend/src/features/auth/index.ts`:
```ts
export { useAuth } from "./AuthContext";
export type { AuthState } from "./AuthContext";
export { AuthProvider } from "./AuthProvider";
export { ChangePasswordPage } from "./ChangePasswordPage";
export { CHANGE_PASSWORD_PATH, GuestOnly, RequireAuth, RequireRole } from "./guards";
export { LoginPage } from "./LoginPage";
export { ProfilePage } from "./ProfilePage";
```

`frontend/src/app/providers.tsx`:
```tsx
import { CssBaseline, ThemeProvider } from "@mui/material";
import { QueryClientProvider, type QueryClient } from "@tanstack/react-query";
import { SnackbarProvider } from "notistack";
import type { ReactNode } from "react";

import { AuthProvider } from "../features/auth";
import { theme } from "../theme/theme";

export function AppProviders({
  queryClient,
  children,
}: {
  queryClient: QueryClient;
  children: ReactNode;
}) {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <QueryClientProvider client={queryClient}>
        <SnackbarProvider maxSnack={3} anchorOrigin={{ vertical: "bottom", horizontal: "right" }}>
          <AuthProvider>{children}</AuthProvider>
        </SnackbarProvider>
      </QueryClientProvider>
    </ThemeProvider>
  );
}
```

`frontend/src/app/routes.tsx`:
```tsx
import type { RouteObject } from "react-router";

import {
  ChangePasswordPage,
  GuestOnly,
  LoginPage,
  ProfilePage,
  RequireAuth,
  useAuth,
} from "../features/auth";
import { HomePage } from "../features/home";
import { BlankLayout } from "../layout/BlankLayout";
import { FullLayout } from "../layout/FullLayout";
import { NotFoundPage } from "../layout/NotFoundPage";

function ChangePasswordRoute() {
  const { user } = useAuth();
  return user?.must_change_password ? (
    <BlankLayout>
      <ChangePasswordPage forced />
    </BlankLayout>
  ) : (
    <FullLayout>
      <ChangePasswordPage />
    </FullLayout>
  );
}

export const routes: RouteObject[] = [
  {
    element: <GuestOnly />,
    children: [
      { element: <BlankLayout />, children: [{ path: "/login", element: <LoginPage /> }] },
    ],
  },
  {
    element: <RequireAuth />,
    children: [
      { path: "/change-password", element: <ChangePasswordRoute /> },
      {
        element: <FullLayout />,
        children: [
          { path: "/", element: <HomePage /> },
          { path: "/profile", element: <ProfilePage /> },
          { path: "*", element: <NotFoundPage /> },
        ],
      },
    ],
  },
];
```

`frontend/src/app/App.tsx`:
```tsx
import { useState } from "react";
import { createBrowserRouter, RouterProvider } from "react-router";

import { AppProviders } from "./providers";
import { createQueryClient } from "./queryClient";
import { routes } from "./routes";

export function App() {
  const [queryClient] = useState(createQueryClient);
  const [router] = useState(() => createBrowserRouter(routes));
  return (
    <AppProviders queryClient={queryClient}>
      <RouterProvider router={router} />
    </AppProviders>
  );
}
```

- [ ] **Step 4: Тесты проходят**

Run: `npx vitest run src/app` → PASS.

- [ ] **Step 5: Ручная проверка против реального backend**

Из корня репозитория: `make up`, backend запущен (`cd backend && uv run uvicorn app.main:app --reload`), в БД есть администратор (`make create-admin ...`). Затем `cd frontend && npm run dev` и в браузере `http://localhost:5173`:
- `/` без входа уводит на `/login`;
- вход администратором открывает главную, в меню есть «Администрирование»;
- перезагрузка страницы не разлогинивает (refresh-cookie через прокси Vite);
- «Выйти» возвращает на `/login`.

Если браузер недоступен (агент), выполнить проверку прокси и cookie через curl:

```bash
curl -si -X POST localhost:5173/api/auth/login -H 'Content-Type: application/json' \
  -d '{"email":"admin@company.ru","password":"<пароль>"}' | grep -i -E '^HTTP|set-cookie'
```

Expected: `HTTP/1.1 200` и `set-cookie: refresh_token=...; HttpOnly; Path=/api/auth; SameSite=strict`.

- [ ] **Step 6: Commit**

```bash
npm run format && npm run check && npm run build
cd .. && git add frontend && git commit -m "feat(frontend): маршруты, вход и смена пароля"
```


### Task 8: Таблица, фильтры в URL, асинхронный автокомплит

**Files:**
- Create: `frontend/src/shared/lib/useDebouncedValue.ts`, `frontend/src/shared/lib/useUrlFilters.ts`
- Create: `frontend/src/shared/ui/DataTable.tsx`, `FilterBar.tsx`, `EntityAutocomplete.tsx`, `form/FormAutocomplete.tsx`
- Test: `frontend/src/shared/lib/useUrlFilters.test.tsx`, `frontend/src/shared/ui/DataTable.test.tsx`, `frontend/src/shared/ui/EntityAutocomplete.test.tsx`

**Interfaces:**
- Consumes: `ApiError`, `UNKNOWN_ERROR_MESSAGE` (Task 2); `renderWithProviders` (Task 3).
- Produces:
  - `useDebouncedValue(value, delay = 300)`, `DEBOUNCE_MS = 300`.
  - `useUrlFilters(schema) → { filters, limit, offset, setFilter(key, value), setPage(offset, limit) }`; параметры `textParam`, `enumParam(values)`, `idParam`, `booleanParam`; `PAGE_SIZES = [25, 50, 100]`; тип `UrlParam<V>`. Смена фильтра удаляет `offset`; `limit` 25 и `offset` 0 в URL не пишутся.
  - `DataTable<T>({ columns: Column<T>[], rows, getRowId, loading?, error?, onRetry?, emptyText?, rowActions?: RowAction<T>[], paging?: { limit; offset; onChange(offset, limit); total? } })` — без `total` пагинация на клиенте; `Column<T> = { key; header; render(row); width?; align? }`; `RowAction<T> = { label; icon?; onClick(row); hidden?(row); color?: "error" }`; меню строки — кнопка «Действия».
  - `FilterBar({ children })`, `SearchField({ value, onChange, placeholder = "Поиск" })` (debounce 300 мс, `aria-label` = placeholder), `FilterSelect<V>({ label, value, options, onChange, allLabel = "Все" })`.
  - `EntityAutocomplete({ label, value: number | null, onChange(id | null), fetchOptions(query): Promise<EntityOption[]>, queryKey, labelFor(id), error?, helperText?, disabled?, onBlur? })`, `EntityOption = { id: number; label: string }`; `FormAutocomplete<T>({ control, name, ...те же без value/onChange })`.

- [ ] **Step 1: Написать падающие тесты**

Подписи пагинации и автокомплита берутся из `ruRU` темы: «1–25 из 120», «Перейти на предыдущую страницу», «Очистить».

`frontend/src/shared/lib/useUrlFilters.test.tsx`:
```tsx
import { screen } from "@testing-library/react";

import { renderWithProviders } from "../../test/render";
import { booleanParam, enumParam, textParam, useUrlFilters } from "./useUrlFilters";

const schema = {
  q: textParam,
  role: enumParam(["employee", "manager", "admin"] as const),
  active: booleanParam,
};

function Probe() {
  const { filters, limit, offset, setFilter, setPage } = useUrlFilters(schema);
  return (
    <>
      <output>{JSON.stringify({ ...filters, limit, offset })}</output>
      <button onClick={() => setFilter("role", "manager")}>роль</button>
      <button onClick={() => setPage(50, 50)}>страница</button>
    </>
  );
}

test("читает фильтры из URL и отбрасывает невалидные значения", () => {
  renderWithProviders(<Probe />, {
    initialEntries: ["/?q=ив&role=boss&active=false&limit=33&offset=-1"],
  });

  expect(JSON.parse(screen.getByRole("status").textContent ?? "")).toEqual({
    q: "ив",
    role: null,
    active: false,
    limit: 25,
    offset: 0,
  });
});

test("смена фильтра пишет его в URL и сбрасывает страницу", async () => {
  const { user, router } = renderWithProviders(<Probe />, { initialEntries: ["/?q=ив"] });

  await user.click(screen.getByRole("button", { name: "страница" }));
  expect(router.state.location.search).toBe("?q=%D0%B8%D0%B2&offset=50&limit=50");

  await user.click(screen.getByRole("button", { name: "роль" }));
  expect(router.state.location.search).toBe("?q=%D0%B8%D0%B2&limit=50&role=manager");
});
```

`frontend/src/shared/ui/DataTable.test.tsx`:
```tsx
import { screen, within } from "@testing-library/react";

import { ApiError } from "../../api/errors";
import { renderWithProviders } from "../../test/render";
import { DataTable, type Column } from "./DataTable";

interface Row {
  id: number;
  name: string;
}

const columns: Column<Row>[] = [{ key: "name", header: "Название", render: (row) => row.name }];
const rows: Row[] = Array.from({ length: 30 }, (_, index) => ({
  id: index + 1,
  name: `Отдел ${index + 1}`,
}));

test("показывает строки, действия и клиентскую пагинацию", async () => {
  const onChange = vi.fn();
  const onEdit = vi.fn();
  const { user } = renderWithProviders(
    <DataTable
      columns={columns}
      rows={rows}
      getRowId={(row) => row.id}
      rowActions={[{ label: "Редактировать", onClick: onEdit }]}
      paging={{ limit: 25, offset: 25, onChange }}
    />,
  );

  const table = screen.getByRole("table");
  expect(within(table).getAllByRole("row")).toHaveLength(6); // заголовок + 5 строк второй страницы
  expect(screen.getByText("26–30 из 30")).toBeInTheDocument();

  await user.click(within(table).getAllByRole("button", { name: "Действия" })[0]!);
  await user.click(await screen.findByRole("menuitem", { name: "Редактировать" }));
  expect(onEdit).toHaveBeenCalledWith({ id: 26, name: "Отдел 26" });

  await user.click(screen.getByRole("button", { name: "Перейти на предыдущую страницу" }));
  expect(onChange).toHaveBeenCalledWith(0, 25);
});

test("серверная пагинация берёт total из ответа", () => {
  renderWithProviders(
    <DataTable
      columns={columns}
      rows={rows.slice(0, 25)}
      getRowId={(row) => row.id}
      paging={{ limit: 25, offset: 0, total: 120, onChange: vi.fn() }}
    />,
  );

  expect(screen.getAllByRole("row")).toHaveLength(26);
  expect(screen.getByText("1–25 из 120")).toBeInTheDocument();
});

test("пустой список и ошибка с повтором", async () => {
  const onRetry = vi.fn();
  const { user, rerender } = renderWithProviders(
    <DataTable columns={columns} rows={[]} getRowId={(row) => row.id} emptyText="Отделов нет" />,
  );
  expect(screen.getByText("Отделов нет")).toBeInTheDocument();

  rerender(
    <DataTable
      columns={columns}
      rows={undefined}
      getRowId={(row) => row.id}
      error={new ApiError({ status: 500, code: "internal_error", message: "Внутренняя ошибка" })}
      onRetry={onRetry}
    />,
  );
  await user.click(screen.getByRole("button", { name: "Повторить" }));
  expect(screen.getByText("Внутренняя ошибка")).toBeInTheDocument();
  expect(onRetry).toHaveBeenCalled();
});
```

`frontend/src/shared/ui/EntityAutocomplete.test.tsx`:
```tsx
import { screen, waitFor } from "@testing-library/react";
import { useState } from "react";

import { renderWithProviders } from "../../test/render";
import { EntityAutocomplete, type EntityOption } from "./EntityAutocomplete";

const PEOPLE: EntityOption[] = [
  { id: 1, label: "Иванов Иван" },
  { id: 2, label: "Петров Пётр" },
];

function Demo({ fetchOptions }: { fetchOptions: (q: string) => Promise<EntityOption[]> }) {
  const [value, setValue] = useState<number | null>(2);
  return (
    <>
      <EntityAutocomplete
        label="Руководитель"
        value={value}
        onChange={setValue}
        fetchOptions={fetchOptions}
        queryKey={["people"]}
        labelFor={(id) => PEOPLE.find((person) => person.id === id)?.label ?? `#${id}`}
      />
      <output>{String(value)}</output>
    </>
  );
}

test("ищет на сервере, выбирает и очищает значение", async () => {
  const fetchOptions = vi.fn(async (query: string) =>
    PEOPLE.filter((person) => person.label.toLowerCase().includes(query.toLowerCase())),
  );
  const { user } = renderWithProviders(<Demo fetchOptions={fetchOptions} />);
  const input = screen.getByLabelText("Руководитель");
  expect(input).toHaveValue("Петров Пётр");

  await user.clear(input);
  await user.type(input, "иван");
  await waitFor(() => expect(fetchOptions).toHaveBeenLastCalledWith("иван"));
  await user.click(await screen.findByRole("option", { name: "Иванов Иван" }));
  expect(screen.getByRole("status")).toHaveTextContent("1");

  await user.click(screen.getByRole("button", { name: "Очистить" }));
  expect(screen.getByRole("status")).toHaveTextContent("null");
});
```

- [ ] **Step 2: Запустить тесты — падают**

Run: `npx vitest run src/shared/lib/useUrlFilters.test.tsx src/shared/ui/DataTable.test.tsx src/shared/ui/EntityAutocomplete.test.tsx`
Expected: FAIL — не найдены модули.

- [ ] **Step 3: Реализация**

`UrlParam` объявлен методами, а не свойствами-функциями: так `UrlParam<string>` совместим с `UrlParam<unknown>` при `strictFunctionTypes`. `EntityAutocomplete` фильтрует варианты на сервере (`filterOptions={(items) => items}`) и загружает их только в открытом состоянии.

`frontend/src/shared/lib/useDebouncedValue.ts`:
```ts
import { useEffect, useState } from "react";

export const DEBOUNCE_MS = 300;

export function useDebouncedValue<T>(value: T, delay = DEBOUNCE_MS): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(timer);
  }, [value, delay]);
  return debounced;
}
```

`frontend/src/shared/lib/useUrlFilters.ts`:
```ts
import { useCallback, useMemo } from "react";
import { useSearchParams } from "react-router";

export const PAGE_SIZES = [25, 50, 100] as const;
const DEFAULT_LIMIT = PAGE_SIZES[0];

// Методы (а не свойства-функции), чтобы UrlParam<string> был совместим с UrlParam<unknown>.
export interface UrlParam<V> {
  parse(raw: string | null): V;
  serialize(value: V): string | null;
}

export const textParam: UrlParam<string> = {
  parse: (raw) => raw ?? "",
  serialize: (value) => (value.trim() ? value : null),
};

export function enumParam<T extends string>(values: readonly T[]): UrlParam<T | null> {
  return {
    parse: (raw) => values.find((value) => value === raw) ?? null,
    serialize: (value) => value,
  };
}

export const idParam: UrlParam<number | null> = {
  parse: (raw) => {
    const value = Number(raw);
    return raw && Number.isInteger(value) && value > 0 ? value : null;
  },
  serialize: (value) => (value === null ? null : String(value)),
};

export const booleanParam: UrlParam<boolean | null> = {
  parse: (raw) => (raw === "true" ? true : raw === "false" ? false : null),
  serialize: (value) => (value === null ? null : String(value)),
};

type ParamValues<S extends Record<string, UrlParam<unknown>>> = {
  [K in keyof S]: S[K] extends UrlParam<infer V> ? V : never;
};

function parseLimit(raw: string | null): number {
  const value = Number(raw);
  return PAGE_SIZES.find((size) => size === value) ?? DEFAULT_LIMIT;
}

function parseOffset(raw: string | null): number {
  const value = Number(raw);
  return raw && Number.isInteger(value) && value >= 0 ? value : 0;
}

/** Фильтры и пагинация списка в search params: ссылкой можно поделиться, перезагрузка их не теряет. */
export function useUrlFilters<S extends Record<string, UrlParam<unknown>>>(schema: S) {
  const [searchParams, setSearchParams] = useSearchParams();

  const filters = useMemo(() => {
    const values: Record<string, unknown> = {};
    for (const [key, param] of Object.entries(schema)) {
      values[key] = param.parse(searchParams.get(key));
    }
    return values as ParamValues<S>;
  }, [schema, searchParams]);

  const limit = parseLimit(searchParams.get("limit"));
  const offset = parseOffset(searchParams.get("offset"));

  const setFilter = useCallback(
    <K extends keyof S & string>(key: K, value: ParamValues<S>[K]) => {
      setSearchParams(
        (current) => {
          const next = new URLSearchParams(current);
          const serialized = schema[key]!.serialize(value);
          if (serialized === null) next.delete(key);
          else next.set(key, serialized);
          next.delete("offset");
          return next;
        },
        { replace: true },
      );
    },
    [schema, setSearchParams],
  );

  const setPage = useCallback(
    (nextOffset: number, nextLimit: number) => {
      setSearchParams(
        (current) => {
          const next = new URLSearchParams(current);
          if (nextOffset > 0) next.set("offset", String(nextOffset));
          else next.delete("offset");
          if (nextLimit !== DEFAULT_LIMIT) next.set("limit", String(nextLimit));
          else next.delete("limit");
          return next;
        },
        { replace: true },
      );
    },
    [setSearchParams],
  );

  return { filters, limit, offset, setFilter, setPage };
}
```

`frontend/src/shared/ui/DataTable.tsx`:
```tsx
import {
  Alert,
  Box,
  Button,
  CircularProgress,
  IconButton,
  ListItemIcon,
  Menu,
  MenuItem,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TablePagination,
  TableRow,
  Typography,
} from "@mui/material";
import { IconDotsVertical } from "@tabler/icons-react";
import { useState, type ReactNode } from "react";

import { ApiError, UNKNOWN_ERROR_MESSAGE } from "../../api/errors";
import { PAGE_SIZES } from "../lib/useUrlFilters";

export interface Column<T> {
  key: string;
  header: string;
  render: (row: T) => ReactNode;
  width?: number | string;
  align?: "left" | "right" | "center";
}

export interface RowAction<T> {
  label: string;
  icon?: ReactNode;
  onClick: (row: T) => void;
  hidden?: (row: T) => boolean;
  color?: "error";
}

export interface TablePaging {
  limit: number;
  offset: number;
  onChange: (offset: number, limit: number) => void;
  /** Общее число строк на сервере; если не задано — пагинация по `rows` на клиенте. */
  total?: number;
}

interface DataTableProps<T> {
  columns: Column<T>[];
  rows: T[] | undefined;
  getRowId: (row: T) => string | number;
  loading?: boolean;
  error?: unknown;
  onRetry?: () => void;
  emptyText?: string;
  rowActions?: RowAction<T>[];
  paging?: TablePaging;
}

function RowActionsMenu<T>({ row, actions }: { row: T; actions: RowAction<T>[] }) {
  const [anchor, setAnchor] = useState<HTMLElement | null>(null);
  const visible = actions.filter((action) => !action.hidden?.(row));
  if (visible.length === 0) return null;
  return (
    <>
      <IconButton aria-label="Действия" onClick={(event) => setAnchor(event.currentTarget)}>
        <IconDotsVertical size={18} stroke={1.5} />
      </IconButton>
      <Menu anchorEl={anchor} open={Boolean(anchor)} onClose={() => setAnchor(null)}>
        {visible.map((action) => (
          <MenuItem
            key={action.label}
            onClick={() => {
              setAnchor(null);
              action.onClick(row);
            }}
            sx={action.color === "error" ? { color: "error.main" } : undefined}
          >
            {action.icon && <ListItemIcon sx={{ color: "inherit" }}>{action.icon}</ListItemIcon>}
            {action.label}
          </MenuItem>
        ))}
      </Menu>
    </>
  );
}

export function DataTable<T>({
  columns,
  rows,
  getRowId,
  loading = false,
  error,
  onRetry,
  emptyText = "Нет данных",
  rowActions,
  paging,
}: DataTableProps<T>) {
  const clientPaging = paging !== undefined && paging.total === undefined;
  const visibleRows =
    rows && clientPaging ? rows.slice(paging.offset, paging.offset + paging.limit) : rows;
  const columnCount = columns.length + (rowActions ? 1 : 0);

  let body: ReactNode;
  if (error) {
    body = (
      <TableRow>
        <TableCell colSpan={columnCount}>
          <Alert
            severity="error"
            action={
              onRetry && (
                <Button color="inherit" size="small" onClick={onRetry}>
                  Повторить
                </Button>
              )
            }
          >
            {error instanceof ApiError ? error.message : UNKNOWN_ERROR_MESSAGE}
          </Alert>
        </TableCell>
      </TableRow>
    );
  } else if (loading && !rows) {
    body = (
      <TableRow>
        <TableCell colSpan={columnCount} align="center" sx={{ py: 6 }}>
          <CircularProgress size={28} aria-label="Загрузка" />
        </TableCell>
      </TableRow>
    );
  } else if (!visibleRows || visibleRows.length === 0) {
    body = (
      <TableRow>
        <TableCell colSpan={columnCount} align="center" sx={{ py: 6 }}>
          <Typography color="text.secondary">{emptyText}</Typography>
        </TableCell>
      </TableRow>
    );
  } else {
    body = visibleRows.map((row) => (
      <TableRow key={getRowId(row)} hover>
        {columns.map((column) => (
          <TableCell key={column.key} align={column.align}>
            {column.render(row)}
          </TableCell>
        ))}
        {rowActions && (
          <TableCell align="right" sx={{ width: 56 }}>
            <RowActionsMenu row={row} actions={rowActions} />
          </TableCell>
        )}
      </TableRow>
    ));
  }

  return (
    <Paper variant="outlined">
      <TableContainer>
        <Table>
          <TableHead>
            <TableRow>
              {columns.map((column) => (
                <TableCell
                  key={column.key}
                  align={column.align}
                  sx={{ width: column.width, fontWeight: 600, whiteSpace: "nowrap" }}
                >
                  {column.header}
                </TableCell>
              ))}
              {rowActions && (
                <TableCell>
                  <Box component="span" sx={visuallyHidden}>
                    Действия
                  </Box>
                </TableCell>
              )}
            </TableRow>
          </TableHead>
          <TableBody>{body}</TableBody>
        </Table>
      </TableContainer>
      {paging && (
        <TablePagination
          component="div"
          count={paging.total ?? rows?.length ?? 0}
          page={Math.floor(paging.offset / paging.limit)}
          rowsPerPage={paging.limit}
          rowsPerPageOptions={[...PAGE_SIZES]}
          onPageChange={(_, page) => paging.onChange(page * paging.limit, paging.limit)}
          onRowsPerPageChange={(event) => paging.onChange(0, Number(event.target.value))}
        />
      )}
    </Paper>
  );
}

const visuallyHidden = {
  position: "absolute",
  width: 1,
  height: 1,
  overflow: "hidden",
  clip: "rect(0 0 0 0)",
  whiteSpace: "nowrap",
} as const;
```

`frontend/src/shared/ui/FilterBar.tsx`:
```tsx
import { InputAdornment, MenuItem, Stack, TextField } from "@mui/material";
import { IconSearch } from "@tabler/icons-react";
import { useEffect, useState, type ReactNode } from "react";

import { DEBOUNCE_MS } from "../lib/useDebouncedValue";

export function FilterBar({ children }: { children: ReactNode }) {
  return (
    <Stack
      direction={{ xs: "column", md: "row" }}
      spacing={2}
      sx={{ mb: 2, alignItems: { md: "center" } }}
    >
      {children}
    </Stack>
  );
}

interface SearchFieldProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
}

/** Поле поиска: сообщает значение не чаще раза в 300 мс. */
export function SearchField({ value, onChange, placeholder = "Поиск" }: SearchFieldProps) {
  const [text, setText] = useState(value);

  useEffect(() => {
    setText(value);
  }, [value]);

  useEffect(() => {
    if (text === value) return;
    const timer = setTimeout(() => onChange(text), DEBOUNCE_MS);
    return () => clearTimeout(timer);
  }, [text, value, onChange]);

  return (
    <TextField
      size="small"
      value={text}
      onChange={(event) => setText(event.target.value)}
      placeholder={placeholder}
      sx={{ minWidth: 260 }}
      slotProps={{
        htmlInput: { "aria-label": placeholder },
        input: {
          startAdornment: (
            <InputAdornment position="start">
              <IconSearch size={18} stroke={1.5} />
            </InputAdornment>
          ),
        },
      }}
    />
  );
}

interface FilterSelectProps<V extends string | number> {
  label: string;
  value: V | null;
  options: readonly { value: V; label: string }[];
  onChange: (value: V | null) => void;
  allLabel?: string;
}

export function FilterSelect<V extends string | number>({
  label,
  value,
  options,
  onChange,
  allLabel = "Все",
}: FilterSelectProps<V>) {
  return (
    <TextField
      select
      size="small"
      label={label}
      value={value === null ? "" : String(value)}
      onChange={(event) =>
        onChange(
          options.find((option) => String(option.value) === event.target.value)?.value ?? null,
        )
      }
      sx={{ minWidth: 200 }}
    >
      <MenuItem value="">{allLabel}</MenuItem>
      {options.map((option) => (
        <MenuItem key={String(option.value)} value={String(option.value)}>
          {option.label}
        </MenuItem>
      ))}
    </TextField>
  );
}
```

`frontend/src/shared/ui/EntityAutocomplete.tsx`:
```tsx
import { Autocomplete, CircularProgress, TextField } from "@mui/material";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { useDebouncedValue } from "../lib/useDebouncedValue";

export interface EntityOption {
  id: number;
  label: string;
}

export interface EntityAutocompleteProps {
  label: string;
  value: number | null;
  onChange: (id: number | null) => void;
  /** Поиск вариантов на сервере; вызывается с пустой строкой при открытии. */
  fetchOptions: (query: string) => Promise<EntityOption[]>;
  /** Уникальный ключ источника вариантов для кэша TanStack Query. */
  queryKey: readonly unknown[];
  /** Подпись для текущего значения, если его нет среди загруженных вариантов. */
  labelFor: (id: number) => string;
  error?: boolean;
  helperText?: string;
  disabled?: boolean;
  onBlur?: () => void;
}

export function EntityAutocomplete({
  label,
  value,
  onChange,
  fetchOptions,
  queryKey,
  labelFor,
  error,
  helperText,
  disabled,
  onBlur,
}: EntityAutocompleteProps) {
  const [open, setOpen] = useState(false);
  const [input, setInput] = useState("");
  const query = useDebouncedValue(input);

  const options = useQuery({
    queryKey: [...queryKey, "options", query],
    queryFn: () => fetchOptions(query),
    enabled: open,
  });

  const selected: EntityOption | null =
    value === null ? null : { id: value, label: labelFor(value) };

  return (
    <Autocomplete<EntityOption>
      open={open}
      onOpen={() => setOpen(true)}
      onClose={() => setOpen(false)}
      value={selected}
      options={options.data ?? []}
      loading={options.isFetching}
      filterOptions={(items) => items}
      isOptionEqualToValue={(option, current) => option.id === current.id}
      getOptionLabel={(option) => option.label}
      onChange={(_, option) => onChange(option?.id ?? null)}
      onInputChange={(_, text, reason) => {
        if (reason === "input") setInput(text);
        if (reason === "clear" || reason === "reset") setInput("");
      }}
      disabled={disabled}
      noOptionsText="Ничего не найдено"
      loadingText="Загрузка…"
      renderInput={(params) => (
        <TextField
          {...params}
          label={label}
          error={error}
          helperText={helperText}
          onBlur={onBlur}
          slotProps={{
            ...params.slotProps,
            input: {
              ...params.slotProps.input,
              endAdornment: (
                <>
                  {options.isFetching && <CircularProgress size={18} />}
                  {params.slotProps.input.endAdornment}
                </>
              ),
            },
          }}
        />
      )}
    />
  );
}
```

`frontend/src/shared/ui/form/FormAutocomplete.tsx`:
```tsx
import { Controller, type Control, type FieldPath, type FieldValues } from "react-hook-form";

import { EntityAutocomplete, type EntityAutocompleteProps } from "../EntityAutocomplete";

type FormAutocompleteProps<T extends FieldValues> = {
  control: Control<T>;
  name: FieldPath<T>;
} & Omit<EntityAutocompleteProps, "value" | "onChange" | "error" | "helperText" | "onBlur">;

export function FormAutocomplete<T extends FieldValues>({
  control,
  name,
  ...props
}: FormAutocompleteProps<T>) {
  return (
    <Controller
      control={control}
      name={name}
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

- [ ] **Step 4: Тесты проходят, commit**

```bash
npx vitest run src/shared   # PASS
npm run format && npm run check
cd .. && git add frontend && git commit -m "feat(frontend): таблица, фильтры в URL, автокомплит"
```


### Task 9: Администрирование пользователей

**Files:**
- Create: `frontend/src/features/users/api.ts`, `UserFormDialog.tsx`, `TemporaryPasswordDialog.tsx`, `UsersPage.tsx`, `index.ts`
- Create: `frontend/src/test/fixtures.ts`
- Modify: `frontend/src/app/routes.tsx` (блок `RequireRole` с `/admin/users`)
- Test: `frontend/src/features/users/UsersPage.test.tsx`

**Interfaces:**
- Consumes: `api`, `unwrap`, `ApiError`, `blockersOf`, `Blocker`, `Schemas` (Task 2); `ROLE_LABELS`, `formatDate` (Task 3); формы и диалоги (Task 4); `PageContainer`, `useDepartments`, `queryKeys` (Task 6); `DataTable`, `FilterBar`, `SearchField`, `FilterSelect`, `useUrlFilters` и параметры (Task 8); `renderApp` (Task 7); `mockSignedIn` (Task 5).
- Produces:
  - `features/users` (публично): `UsersPage`.
  - `test/fixtures.ts`: `makeUser(overrides)`, `page(items, total?)`.
  - маршрут `/admin/users` под `RequireRole role="admin"`.

- [ ] **Step 1: Написать падающие тесты**

`frontend/src/test/fixtures.ts`:
```ts
import type { Schemas } from "../api/types";

export function makeUser(overrides: Partial<Schemas["UserRead"]> = {}): Schemas["UserRead"] {
  return {
    id: 10,
    email: "petrov@company.ru",
    full_name: "Петров Пётр",
    role: "employee",
    department_id: null,
    is_active: true,
    must_change_password: false,
    created_at: "2026-09-01T09:00:00Z",
    ...overrides,
  };
}

export function page<T>(items: T[], total = items.length) {
  return { items, total, limit: 25, offset: 0 };
}
```

`frontend/src/features/users/UsersPage.test.tsx`:
```tsx
import { screen, waitFor, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";

import type { Schemas } from "../../api/types";
import { renderApp } from "../../test/app";
import { mockSignedIn } from "../../test/auth";
import { makeUser, page } from "../../test/fixtures";
import { errorBody } from "../../test/http";
import { server } from "../../test/server";

const DEPARTMENTS: Schemas["DepartmentRead"][] = [{ id: 3, name: "Бухгалтерия", head_id: null }];

function mockUsers(users: Schemas["UserRead"][], seen: URL[] = []) {
  server.use(
    http.get("*/api/departments", () => HttpResponse.json(DEPARTMENTS)),
    http.get("*/api/admin/users", ({ request }) => {
      seen.push(new URL(request.url));
      return HttpResponse.json(page(users));
    }),
  );
  return seen;
}

async function openRowMenu(user: ReturnType<typeof renderApp>["user"], fullName: string) {
  const row = (await screen.findByText(fullName)).closest("tr")!;
  await user.click(within(row).getByRole("button", { name: "Действия" }));
}

test("список пользователей с фильтрами из URL", async () => {
  mockSignedIn();
  const seen = mockUsers([makeUser({ department_id: 3, must_change_password: true })]);
  const { user, router } = renderApp("/admin/users?role=employee");

  const row = (await screen.findByText("Петров Пётр")).closest("tr")!;
  expect(within(row).getByText("Бухгалтерия")).toBeInTheDocument();
  expect(within(row).getByText("Временный пароль")).toBeInTheDocument();
  expect(seen.at(-1)?.searchParams.get("role")).toBe("employee");

  await user.type(screen.getByLabelText("Поиск по ФИО и email"), "пет");
  await waitFor(() => expect(seen.at(-1)?.searchParams.get("q")).toBe("пет"));
  expect(router.state.location.search).toContain("q=");
});

test("создание пользователя показывает временный пароль", async () => {
  mockSignedIn();
  mockUsers([]);
  let created: Schemas["UserCreate"] | null = null;
  server.use(
    http.post("*/api/admin/users", async ({ request }) => {
      created = (await request.json()) as Schemas["UserCreate"];
      return HttpResponse.json<Schemas["UserCreatedResponse"]>(
        { user: makeUser({ full_name: created.full_name }), temporary_password: "Tmp-12345" },
        { status: 201 },
      );
    }),
  );
  const { user } = renderApp("/admin/users");

  await user.click(await screen.findByRole("button", { name: "Добавить" }));
  const dialog = await screen.findByRole("dialog");
  await user.type(within(dialog).getByLabelText("ФИО"), "Сидоров Сидор");
  await user.type(within(dialog).getByLabelText("Email"), "sidorov@company.ru");
  await user.click(within(dialog).getByLabelText("Отдел"));
  await user.click(await screen.findByRole("option", { name: "Бухгалтерия" }));
  await user.click(within(dialog).getByRole("button", { name: "Создать" }));

  expect(await screen.findByDisplayValue("Tmp-12345")).toBeInTheDocument();
  expect(created).toEqual({
    full_name: "Сидоров Сидор",
    email: "sidorov@company.ru",
    role: "employee",
    department_id: 3,
  });
});

test("email_taken показывается под полем email", async () => {
  mockSignedIn();
  mockUsers([]);
  server.use(
    http.post("*/api/admin/users", () =>
      HttpResponse.json(errorBody("email_taken", "Пользователь с таким email уже существует"), {
        status: 409,
      }),
    ),
  );
  const { user } = renderApp("/admin/users");

  await user.click(await screen.findByRole("button", { name: "Добавить" }));
  const dialog = await screen.findByRole("dialog");
  await user.type(within(dialog).getByLabelText("ФИО"), "Сидоров Сидор");
  await user.type(within(dialog).getByLabelText("Email"), "petrov@company.ru");
  await user.click(within(dialog).getByRole("button", { name: "Создать" }));

  expect(
    await within(dialog).findByText("Пользователь с таким email уже существует"),
  ).toBeInTheDocument();
});

test("деактивация с блокирующими причинами показывает их список", async () => {
  mockSignedIn();
  mockUsers([makeUser()]);
  server.use(
    http.post("*/api/admin/users/:id/deactivate", () =>
      HttpResponse.json(
        errorBody(
          "deactivation_blocked",
          "Перед деактивацией нужно передать ответственность другим сотрудникам",
          [{ kind: "department_head", entity_id: 3, title: "Отдел «Бухгалтерия»" }],
        ),
        { status: 409 },
      ),
    ),
  );
  const { user } = renderApp("/admin/users");

  await openRowMenu(user, "Петров Пётр");
  await user.click(await screen.findByRole("menuitem", { name: "Деактивировать" }));
  await user.click(
    within(await screen.findByRole("dialog")).getByRole("button", { name: "Деактивировать" }),
  );

  expect(await screen.findByText("Отдел «Бухгалтерия»")).toBeInTheDocument();
  expect(screen.getByText("Руководитель отдела")).toBeInTheDocument();
});

test("редактирование отправляет только изменённые поля", async () => {
  mockSignedIn();
  mockUsers([makeUser({ role: "employee", department_id: 3 })]);
  let patched: Schemas["UserUpdate"] | null = null;
  server.use(
    http.patch("*/api/admin/users/:id", async ({ request }) => {
      patched = (await request.json()) as Schemas["UserUpdate"];
      return HttpResponse.json(makeUser({ role: "manager", department_id: 3 }));
    }),
  );
  const { user } = renderApp("/admin/users");

  await openRowMenu(user, "Петров Пётр");
  await user.click(await screen.findByRole("menuitem", { name: "Редактировать" }));
  const dialog = await screen.findByRole("dialog");
  await user.click(within(dialog).getByLabelText("Роль"));
  await user.click(await screen.findByRole("option", { name: "Руководитель" }));
  await user.click(within(dialog).getByRole("button", { name: "Сохранить" }));

  await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
  expect(patched).toEqual({ role: "manager" });
});
```

- [ ] **Step 2: Запустить тесты — падают**

Run: `npx vitest run src/features/users`
Expected: FAIL — на `/admin/users` рендерится страница 404 (маршрута ещё нет), `findByText("Петров Пётр")` не находит строку.

- [ ] **Step 3: Реализация**

Дизайн п. 9.5: фильтры в URL (`q`, `role`, `department`, `active`), серверная пагинация; создание показывает временный пароль один раз; редактирование отправляет только изменённые поля (`dirtyFields`), email после создания не меняется (backend `UserUpdate` его не принимает); `deactivation_blocked` и `role_change_blocked` показываются через `BlockersDialog`; `cannot_deactivate_self` и `last_admin` — уведомлением с текстом backend.

`frontend/src/features/users/api.ts`:
```ts
import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api, unwrap } from "../../api/client";
import type { Schemas, UserRole } from "../../api/types";
import { queryKeys } from "../../shared/lookups/queryKeys";

export interface UserListParams {
  q: string;
  role: UserRole | null;
  departmentId: number | null;
  isActive: boolean | null;
  limit: number;
  offset: number;
}

export function useAdminUsers(params: UserListParams) {
  return useQuery({
    queryKey: [...queryKeys.users, "admin-list", params],
    queryFn: () =>
      unwrap(
        api.GET("/api/admin/users", {
          params: {
            query: {
              q: params.q.trim() || undefined,
              role: params.role ?? undefined,
              department_id: params.departmentId ?? undefined,
              is_active: params.isActive ?? undefined,
              limit: params.limit,
              offset: params.offset,
            },
          },
        }),
      ),
    placeholderData: keepPreviousData,
  });
}

function useUsersMutation<V, R>(mutationFn: (variables: V) => Promise<R>) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: queryKeys.users }),
  });
}

export function useCreateUser() {
  return useUsersMutation((body: Schemas["UserCreate"]) =>
    unwrap(api.POST("/api/admin/users", { body })),
  );
}

export function useUpdateUser() {
  return useUsersMutation(({ id, body }: { id: number; body: Schemas["UserUpdate"] }) =>
    unwrap(api.PATCH("/api/admin/users/{user_id}", { params: { path: { user_id: id } }, body })),
  );
}

export function useSetUserActive() {
  return useUsersMutation(({ id, active }: { id: number; active: boolean }) => {
    const params = { params: { path: { user_id: id } } };
    return active
      ? unwrap(api.POST("/api/admin/users/{user_id}/activate", params))
      : unwrap(api.POST("/api/admin/users/{user_id}/deactivate", params));
  });
}

export function useIssueTemporaryPassword() {
  return useUsersMutation((id: number) =>
    unwrap(
      api.POST("/api/admin/users/{user_id}/temporary-password", {
        params: { path: { user_id: id } },
      }),
    ),
  );
}

export function useUnlockLogin() {
  return useMutation({
    mutationFn: (id: number) =>
      unwrap(
        api.POST("/api/admin/users/{user_id}/unlock-login", { params: { path: { user_id: id } } }),
      ),
  });
}
```

`frontend/src/features/users/UserFormDialog.tsx`:
```tsx
import { useState } from "react";
import { useForm } from "react-hook-form";

import type { Schemas, UserRole } from "../../api/types";
import { applyApiErrors, fieldByCode } from "../../shared/lib/applyApiErrors";
import { ROLE_LABELS } from "../../shared/lib/format";
import { useDepartments } from "../../shared/lookups/departments";
import { FormDialog } from "../../shared/ui/FormDialog";
import { FormSelect } from "../../shared/ui/form/FormSelect";
import { FormTextField } from "../../shared/ui/form/FormTextField";
import { useCreateUser, useUpdateUser } from "./api";

export const ROLE_OPTIONS = (Object.keys(ROLE_LABELS) as UserRole[]).map((role) => ({
  value: role,
  label: ROLE_LABELS[role],
}));

interface UserFormValues {
  full_name: string;
  email: string;
  role: UserRole;
  department_id: number | null;
}

const fieldForError = fieldByCode<UserFormValues>({
  email_taken: "email",
  full_name_blank: "full_name",
  department_not_found: "department_id",
});

interface UserFormDialogProps {
  /** Пользователь для редактирования; без него диалог создаёт нового. */
  user: Schemas["UserRead"] | null;
  onClose: () => void;
  onCreated: (result: Schemas["UserCreatedResponse"]) => void;
  onBlocked: (error: unknown) => boolean;
}

export function UserFormDialog({ user, onClose, onCreated, onBlocked }: UserFormDialogProps) {
  const createUser = useCreateUser();
  const updateUser = useUpdateUser();
  const departments = useDepartments();
  const [formError, setFormError] = useState<string | null>(null);
  const {
    control,
    handleSubmit,
    setError,
    formState: { isSubmitting, dirtyFields },
  } = useForm<UserFormValues>({
    defaultValues: {
      full_name: user?.full_name ?? "",
      email: user?.email ?? "",
      role: user?.role ?? "employee",
      department_id: user?.department_id ?? null,
    },
  });

  const onSubmit = handleSubmit(async (values) => {
    setFormError(null);
    try {
      if (user) {
        const body: Schemas["UserUpdate"] = {};
        if (dirtyFields.full_name) body.full_name = values.full_name;
        if (dirtyFields.role) body.role = values.role;
        if (dirtyFields.department_id) body.department_id = values.department_id;
        await updateUser.mutateAsync({ id: user.id, body });
        onClose();
      } else {
        onCreated(await createUser.mutateAsync(values));
      }
    } catch (error) {
      if (onBlocked(error)) return;
      setFormError(
        applyApiErrors(error, setError, {
          fields: ["full_name", "email", "role", "department_id"],
          fieldForError,
        }),
      );
    }
  });

  return (
    <FormDialog
      open
      title={user ? "Редактирование пользователя" : "Новый пользователь"}
      submitting={isSubmitting}
      formError={formError}
      onSubmit={onSubmit}
      onClose={onClose}
      submitLabel={user ? "Сохранить" : "Создать"}
    >
      <FormTextField
        control={control}
        name="full_name"
        label="ФИО"
        rules={{ validate: (value) => value.trim() !== "" || "Введите ФИО" }}
      />
      <FormTextField
        control={control}
        name="email"
        label="Email"
        type="email"
        disabled={Boolean(user)}
        rules={{ required: "Введите email" }}
      />
      <FormSelect control={control} name="role" label="Роль" options={ROLE_OPTIONS} />
      <FormSelect
        control={control}
        name="department_id"
        label="Отдел"
        emptyLabel="Без отдела"
        options={(departments.data ?? []).map((item) => ({ value: item.id, label: item.name }))}
      />
    </FormDialog>
  );
}
```

`frontend/src/features/users/TemporaryPasswordDialog.tsx`:
```tsx
import {
  Alert,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Stack,
  TextField,
} from "@mui/material";
import { useSnackbar } from "notistack";

interface TemporaryPasswordDialogProps {
  fullName: string;
  password: string;
  onClose: () => void;
}

export function TemporaryPasswordDialog({
  fullName,
  password,
  onClose,
}: TemporaryPasswordDialogProps) {
  const { enqueueSnackbar } = useSnackbar();
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(password);
      enqueueSnackbar("Пароль скопирован", { variant: "success" });
    } catch {
      enqueueSnackbar("Не удалось скопировать, выделите пароль вручную", { variant: "warning" });
    }
  };
  return (
    <Dialog open onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>Временный пароль</DialogTitle>
      <DialogContent>
        <Stack spacing={2} sx={{ pt: 1 }}>
          <Alert severity="warning">
            Пароль показывается один раз. Передайте его пользователю «{fullName}» — при входе
            система попросит задать новый пароль.
          </Alert>
          <TextField
            label="Временный пароль"
            value={password}
            fullWidth
            slotProps={{ htmlInput: { readOnly: true } }}
          />
        </Stack>
      </DialogContent>
      <DialogActions sx={{ px: 3, pb: 2 }}>
        <Button onClick={() => void copy()}>Скопировать</Button>
        <Button onClick={onClose} variant="contained">
          Готово
        </Button>
      </DialogActions>
    </Dialog>
  );
}
```

`frontend/src/features/users/UsersPage.tsx`:
```tsx
import { Button, Chip, Stack } from "@mui/material";
import { IconPlus } from "@tabler/icons-react";
import { useSnackbar } from "notistack";
import { useState } from "react";

import { ApiError, blockersOf, type Blocker } from "../../api/errors";
import type { Schemas } from "../../api/types";
import { formatDate, ROLE_LABELS } from "../../shared/lib/format";
import {
  booleanParam,
  enumParam,
  idParam,
  textParam,
  useUrlFilters,
} from "../../shared/lib/useUrlFilters";
import { useDepartments } from "../../shared/lookups/departments";
import { BlockersDialog } from "../../shared/ui/BlockersDialog";
import { ConfirmDialog } from "../../shared/ui/ConfirmDialog";
import { DataTable, type Column, type RowAction } from "../../shared/ui/DataTable";
import { FilterBar, FilterSelect, SearchField } from "../../shared/ui/FilterBar";
import { PageContainer } from "../../shared/ui/PageContainer";
import { useAdminUsers, useIssueTemporaryPassword, useSetUserActive, useUnlockLogin } from "./api";
import { TemporaryPasswordDialog } from "./TemporaryPasswordDialog";
import { ROLE_OPTIONS, UserFormDialog } from "./UserFormDialog";

type User = Schemas["UserRead"];
type Confirmation = { kind: "deactivate" | "activate" | "password" | "unlock"; user: User };

const FILTERS = {
  q: textParam,
  role: enumParam(["employee", "manager", "admin"] as const),
  department: idParam,
  active: booleanParam,
};

const STATUS_OPTIONS = [
  { value: "true", label: "Активные" },
  { value: "false", label: "Деактивированные" },
] as const;

const CONFIRM_TEXT: Record<Confirmation["kind"], { title: string; text: string; label: string }> = {
  deactivate: {
    title: "Деактивировать пользователя?",
    text: "Пользователь не сможет войти, его сессии будут завершены.",
    label: "Деактивировать",
  },
  activate: {
    title: "Активировать пользователя?",
    text: "Пользователь снова сможет войти в систему.",
    label: "Активировать",
  },
  password: {
    title: "Выдать временный пароль?",
    text: "Текущий пароль перестанет действовать, сессии пользователя будут завершены.",
    label: "Выдать пароль",
  },
  unlock: {
    title: "Снять блокировку входа?",
    text: "Счётчики неудачных попыток входа для этого пользователя будут сброшены.",
    label: "Снять блокировку",
  },
};

export function UsersPage() {
  const { enqueueSnackbar } = useSnackbar();
  const { filters, limit, offset, setFilter, setPage } = useUrlFilters(FILTERS);
  const users = useAdminUsers({
    q: filters.q,
    role: filters.role,
    departmentId: filters.department,
    isActive: filters.active,
    limit,
    offset,
  });
  const departments = useDepartments();
  const setActive = useSetUserActive();
  const issuePassword = useIssueTemporaryPassword();
  const unlockLogin = useUnlockLogin();

  const [editing, setEditing] = useState<User | "new" | null>(null);
  const [confirmation, setConfirmation] = useState<Confirmation | null>(null);
  const [password, setPassword] = useState<{ fullName: string; value: string } | null>(null);
  const [blocked, setBlocked] = useState<{ message: string; blockers: Blocker[] } | null>(null);

  const departmentName = (id: number | null) =>
    id === null ? "—" : (departments.data?.find((item) => item.id === id)?.name ?? "…");

  /** Показывает диалог причин, если операция заблокирована; возвращает true, если показал. */
  const showBlockers = (error: unknown) => {
    if (
      error instanceof ApiError &&
      (error.code === "deactivation_blocked" || error.code === "role_change_blocked")
    ) {
      setBlocked({ message: error.message, blockers: blockersOf(error) });
      return true;
    }
    return false;
  };

  const confirm = async () => {
    if (!confirmation) return;
    const { kind, user } = confirmation;
    try {
      if (kind === "deactivate" || kind === "activate") {
        await setActive.mutateAsync({ id: user.id, active: kind === "activate" });
        enqueueSnackbar(
          kind === "activate" ? "Пользователь активирован" : "Пользователь деактивирован",
          {
            variant: "success",
          },
        );
      } else if (kind === "password") {
        const result = await issuePassword.mutateAsync(user.id);
        setPassword({ fullName: user.full_name, value: result.temporary_password });
      } else {
        await unlockLogin.mutateAsync(user.id);
        enqueueSnackbar("Блокировка входа снята", { variant: "success" });
      }
    } catch (error) {
      if (!showBlockers(error)) {
        enqueueSnackbar(error instanceof ApiError ? error.message : "Не удалось выполнить запрос", {
          variant: "error",
        });
      }
    } finally {
      setConfirmation(null);
    }
  };

  const columns: Column<User>[] = [
    { key: "full_name", header: "ФИО", render: (user) => user.full_name },
    { key: "email", header: "Email", render: (user) => user.email },
    { key: "role", header: "Роль", render: (user) => ROLE_LABELS[user.role] },
    { key: "department", header: "Отдел", render: (user) => departmentName(user.department_id) },
    {
      key: "status",
      header: "Статус",
      render: (user) => (
        <Stack direction="row" spacing={1}>
          <Chip
            size="small"
            label={user.is_active ? "Активен" : "Деактивирован"}
            color={user.is_active ? "success" : "default"}
          />
          {user.must_change_password && (
            <Chip size="small" label="Временный пароль" color="warning" />
          )}
        </Stack>
      ),
    },
    { key: "created_at", header: "Создан", render: (user) => formatDate(user.created_at) },
  ];

  const rowActions: RowAction<User>[] = [
    { label: "Редактировать", onClick: (user) => setEditing(user) },
    {
      label: "Выдать временный пароль",
      onClick: (user) => setConfirmation({ kind: "password", user }),
    },
    {
      label: "Снять блокировку входа",
      onClick: (user) => setConfirmation({ kind: "unlock", user }),
    },
    {
      label: "Деактивировать",
      color: "error",
      hidden: (user) => !user.is_active,
      onClick: (user) => setConfirmation({ kind: "deactivate", user }),
    },
    {
      label: "Активировать",
      hidden: (user) => user.is_active,
      onClick: (user) => setConfirmation({ kind: "activate", user }),
    },
  ];

  const pending = setActive.isPending || issuePassword.isPending || unlockLogin.isPending;
  const confirmText = confirmation ? CONFIRM_TEXT[confirmation.kind] : null;

  return (
    <PageContainer
      title="Пользователи"
      breadcrumbs={[{ label: "Администрирование" }, { label: "Пользователи" }]}
      actions={
        <Button
          variant="contained"
          startIcon={<IconPlus size={18} />}
          onClick={() => setEditing("new")}
        >
          Добавить
        </Button>
      }
    >
      <FilterBar>
        <SearchField
          value={filters.q}
          onChange={(value) => setFilter("q", value)}
          placeholder="Поиск по ФИО и email"
        />
        <FilterSelect
          label="Роль"
          value={filters.role}
          options={ROLE_OPTIONS}
          onChange={(value) => setFilter("role", value)}
        />
        <FilterSelect
          label="Отдел"
          value={filters.department}
          options={(departments.data ?? []).map((item) => ({ value: item.id, label: item.name }))}
          onChange={(value) => setFilter("department", value)}
        />
        <FilterSelect
          label="Статус"
          value={filters.active === null ? null : filters.active ? "true" : "false"}
          options={STATUS_OPTIONS}
          onChange={(value) => setFilter("active", value === null ? null : value === "true")}
        />
      </FilterBar>

      <DataTable
        columns={columns}
        rows={users.data?.items}
        getRowId={(user) => user.id}
        loading={users.isLoading}
        error={users.error}
        onRetry={() => void users.refetch()}
        emptyText="Пользователи не найдены"
        rowActions={rowActions}
        paging={{ limit, offset, total: users.data?.total ?? 0, onChange: setPage }}
      />

      {editing && (
        <UserFormDialog
          user={editing === "new" ? null : editing}
          onClose={() => setEditing(null)}
          onCreated={(result) => {
            setEditing(null);
            setPassword({ fullName: result.user.full_name, value: result.temporary_password });
          }}
          onBlocked={(error) => {
            if (!showBlockers(error)) return false;
            setEditing(null);
            return true;
          }}
        />
      )}
      {confirmation && confirmText && (
        <ConfirmDialog
          open
          title={confirmText.title}
          text={confirmText.text}
          confirmLabel={confirmText.label}
          confirmColor={confirmation.kind === "deactivate" ? "error" : "primary"}
          pending={pending}
          onConfirm={() => void confirm()}
          onClose={() => setConfirmation(null)}
        />
      )}
      {password && (
        <TemporaryPasswordDialog
          fullName={password.fullName}
          password={password.value}
          onClose={() => setPassword(null)}
        />
      )}
      {blocked && (
        <BlockersDialog
          open
          message={blocked.message}
          blockers={blocked.blockers}
          onClose={() => setBlocked(null)}
        />
      )}
    </PageContainer>
  );
}
```

`frontend/src/features/users/index.ts`:
```ts
export { UsersPage } from "./UsersPage";
```

`frontend/src/app/routes.tsx`:
```tsx
import type { RouteObject } from "react-router";

import {
  ChangePasswordPage,
  GuestOnly,
  LoginPage,
  ProfilePage,
  RequireAuth,
  RequireRole,
  useAuth,
} from "../features/auth";
import { HomePage } from "../features/home";
import { UsersPage } from "../features/users";
import { BlankLayout } from "../layout/BlankLayout";
import { FullLayout } from "../layout/FullLayout";
import { NotFoundPage } from "../layout/NotFoundPage";

function ChangePasswordRoute() {
  const { user } = useAuth();
  return user?.must_change_password ? (
    <BlankLayout>
      <ChangePasswordPage forced />
    </BlankLayout>
  ) : (
    <FullLayout>
      <ChangePasswordPage />
    </FullLayout>
  );
}

export const routes: RouteObject[] = [
  {
    element: <GuestOnly />,
    children: [
      { element: <BlankLayout />, children: [{ path: "/login", element: <LoginPage /> }] },
    ],
  },
  {
    element: <RequireAuth />,
    children: [
      { path: "/change-password", element: <ChangePasswordRoute /> },
      {
        element: <FullLayout />,
        children: [
          { path: "/", element: <HomePage /> },
          { path: "/profile", element: <ProfilePage /> },
          {
            element: <RequireRole role="admin" />,
            children: [{ path: "/admin/users", element: <UsersPage /> }],
          },
          { path: "*", element: <NotFoundPage /> },
        ],
      },
    ],
  },
];
```

- [ ] **Step 4: Тесты проходят, commit**

```bash
npx vitest run src/features/users   # PASS (5 тестов)
npm run format && npm run check
cd .. && git add frontend && git commit -m "feat(frontend): администрирование пользователей"
```


### Task 10: Администрирование отделов

**Files:**
- Create: `frontend/src/shared/lookups/users.ts`
- Create: `frontend/src/features/departments/api.ts`, `DepartmentFormDialog.tsx`, `DepartmentsPage.tsx`, `index.ts`
- Modify: `frontend/src/app/routes.tsx` (маршрут `/admin/departments`)
- Test: `frontend/src/features/departments/DepartmentsPage.test.tsx`

**Interfaces:**
- Consumes: `useDepartments`, `queryKeys` (Task 6); `FormAutocomplete`, `EntityOption`, `DataTable`, `useUrlFilters` (Task 8); `makeUser`, `page` (Task 9).
- Produces:
  - `shared/lookups/users.ts`: `useUserNames() → { nameOf(id): string; isLoading }` (через `GET /api/admin/users?limit=200`, только для администратора; неизвестный id → «Пользователь #<id>»), `searchResponsibleOptions(query): Promise<EntityOption[]>` (активные Manager и Admin), `RESPONSIBLE_OPTIONS_KEY`.
  - `features/departments` (публично): `DepartmentsPage`.

- [ ] **Step 1: Написать падающие тесты**

Выбор руководителя идёт через `GET /api/admin/users?q=&is_active=true` с отбором ролей на клиенте, а не через `GET /api/users?q=` из дизайна: публичный поиск требует непустой `q` и не фильтрует по роли, а руководителем может быть только Manager или Admin (см. «Уточнения к спецификации»).

`frontend/src/features/departments/DepartmentsPage.test.tsx`:
```tsx
import { screen, waitFor, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";

import type { Schemas } from "../../api/types";
import { renderApp } from "../../test/app";
import { mockSignedIn } from "../../test/auth";
import { makeUser, page } from "../../test/fixtures";
import { errorBody } from "../../test/http";
import { server } from "../../test/server";

const HEAD = makeUser({ id: 5, full_name: "Смирнова Анна", role: "manager" });

function mockDirectory(departments: Schemas["DepartmentRead"][]) {
  server.use(
    http.get("*/api/departments", () => HttpResponse.json(departments)),
    http.get("*/api/admin/users", () =>
      HttpResponse.json(page([HEAD, makeUser({ id: 6, full_name: "Козлов Олег" })])),
    ),
  );
}

test("таблица отделов показывает имя руководителя и фильтрует по названию", async () => {
  mockSignedIn();
  mockDirectory([
    { id: 1, name: "Бухгалтерия", head_id: 5 },
    { id: 2, name: "Склад", head_id: null },
  ]);
  const { user } = renderApp("/admin/departments");

  const row = (await screen.findByText("Бухгалтерия")).closest("tr")!;
  expect(await within(row).findByText("Смирнова Анна")).toBeInTheDocument();
  expect(screen.getByText("Не назначен")).toBeInTheDocument();

  await user.type(screen.getByLabelText("Поиск по названию"), "скл");
  await waitFor(() => expect(screen.queryByText("Бухгалтерия")).not.toBeInTheDocument());
  expect(screen.getByText("Склад")).toBeInTheDocument();
});

test("создание отдела с руководителем; дубль названия — ошибка под полем", async () => {
  mockSignedIn();
  mockDirectory([]);
  const bodies: Schemas["DepartmentCreate"][] = [];
  server.use(
    http.post("*/api/admin/departments", async ({ request }) => {
      const body = (await request.json()) as Schemas["DepartmentCreate"];
      bodies.push(body);
      if (bodies.length === 1) {
        return HttpResponse.json(
          errorBody("department_name_taken", "Отдел с таким названием уже существует"),
          { status: 409 },
        );
      }
      return HttpResponse.json({ id: 9, ...body }, { status: 201 });
    }),
  );
  const { user } = renderApp("/admin/departments");

  await user.click(await screen.findByRole("button", { name: "Добавить" }));
  const dialog = await screen.findByRole("dialog");
  await user.type(within(dialog).getByLabelText("Название"), "Бухгалтерия");
  await user.click(within(dialog).getByLabelText("Руководитель"));
  // Сотрудники не предлагаются: руководителем может быть только Manager или Admin.
  expect(await screen.findByRole("option", { name: "Смирнова Анна" })).toBeInTheDocument();
  expect(screen.queryByRole("option", { name: "Козлов Олег" })).not.toBeInTheDocument();
  await user.click(screen.getByRole("option", { name: "Смирнова Анна" }));
  await user.click(within(dialog).getByRole("button", { name: "Создать" }));

  expect(
    await within(dialog).findByText("Отдел с таким названием уже существует"),
  ).toBeInTheDocument();

  await user.click(within(dialog).getByRole("button", { name: "Создать" }));
  await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
  expect(bodies.at(-1)).toEqual({ name: "Бухгалтерия", head_id: 5 });
});
```

- [ ] **Step 2: Запустить тесты — падают**

Run: `npx vitest run src/features/departments`
Expected: FAIL — на `/admin/departments` рендерится 404 (маршрут ещё не подключён), строки таблицы не находятся.

- [ ] **Step 3: Реализация**

Коды ошибок: `department_name_taken`, `department_name_blank` → «Название»; `head_not_found`, `head_invalid_role` → «Руководитель». PATCH отправляет только изменённые поля; очистка руководителя отправляет `head_id: null`.

`frontend/src/shared/lookups/users.ts`:
```ts
import { useQuery } from "@tanstack/react-query";
import { useCallback, useMemo } from "react";

import { api, unwrap } from "../../api/client";
import type { EntityOption } from "../ui/EntityAutocomplete";
import { queryKeys } from "./queryKeys";

// Пользователей в компании 10–15: для подписей в админских таблицах хватает одной страницы.
const NAMES_PAGE_SIZE = 200;

/** Имена пользователей по id (только для администратора: использует /api/admin/users). */
export function useUserNames() {
  const query = useQuery({
    queryKey: [...queryKeys.users, "names"],
    queryFn: () =>
      unwrap(api.GET("/api/admin/users", { params: { query: { limit: NAMES_PAGE_SIZE } } })),
  });
  const names = useMemo(
    () => new Map(query.data?.items.map((user) => [user.id, user.full_name]) ?? []),
    [query.data],
  );
  const nameOf = useCallback((id: number) => names.get(id) ?? `Пользователь #${id}`, [names]);
  return { nameOf, isLoading: query.isLoading };
}

export const RESPONSIBLE_OPTIONS_KEY = [...queryKeys.users, "responsible-options"] as const;

/**
 * Варианты ответственного (руководитель отдела, исполнитель по умолчанию): активные Manager и Admin.
 * /api/users не подходит: требует непустой запрос и не фильтрует по роли.
 */
export async function searchResponsibleOptions(query: string): Promise<EntityOption[]> {
  const page = await unwrap(
    api.GET("/api/admin/users", {
      params: { query: { q: query.trim() || undefined, is_active: true, limit: 50 } },
    }),
  );
  return page.items
    .filter((user) => user.role !== "employee")
    .map((user) => ({ id: user.id, label: user.full_name }));
}
```

`frontend/src/features/departments/api.ts`:
```ts
import { useMutation, useQueryClient } from "@tanstack/react-query";

import { api, unwrap } from "../../api/client";
import type { Schemas } from "../../api/types";
import { queryKeys } from "../../shared/lookups/queryKeys";

function useDepartmentsMutation<V, R>(mutationFn: (variables: V) => Promise<R>) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: queryKeys.departments }),
  });
}

export function useCreateDepartment() {
  return useDepartmentsMutation((body: Schemas["DepartmentCreate"]) =>
    unwrap(api.POST("/api/admin/departments", { body })),
  );
}

export function useUpdateDepartment() {
  return useDepartmentsMutation(({ id, body }: { id: number; body: Schemas["DepartmentUpdate"] }) =>
    unwrap(
      api.PATCH("/api/admin/departments/{department_id}", {
        params: { path: { department_id: id } },
        body,
      }),
    ),
  );
}
```

`frontend/src/features/departments/DepartmentFormDialog.tsx`:
```tsx
import { useState } from "react";
import { useForm } from "react-hook-form";

import type { Schemas } from "../../api/types";
import { applyApiErrors, fieldByCode } from "../../shared/lib/applyApiErrors";
import { RESPONSIBLE_OPTIONS_KEY, searchResponsibleOptions } from "../../shared/lookups/users";
import { FormDialog } from "../../shared/ui/FormDialog";
import { FormAutocomplete } from "../../shared/ui/form/FormAutocomplete";
import { FormTextField } from "../../shared/ui/form/FormTextField";
import { useCreateDepartment, useUpdateDepartment } from "./api";

interface DepartmentFormValues {
  name: string;
  head_id: number | null;
}

const fieldForError = fieldByCode<DepartmentFormValues>({
  department_name_taken: "name",
  department_name_blank: "name",
  head_not_found: "head_id",
  head_invalid_role: "head_id",
});

interface DepartmentFormDialogProps {
  department: Schemas["DepartmentRead"] | null;
  nameOf: (userId: number) => string;
  onClose: () => void;
}

export function DepartmentFormDialog({ department, nameOf, onClose }: DepartmentFormDialogProps) {
  const createDepartment = useCreateDepartment();
  const updateDepartment = useUpdateDepartment();
  const [formError, setFormError] = useState<string | null>(null);
  const {
    control,
    handleSubmit,
    setError,
    formState: { isSubmitting, dirtyFields },
  } = useForm<DepartmentFormValues>({
    defaultValues: { name: department?.name ?? "", head_id: department?.head_id ?? null },
  });

  const onSubmit = handleSubmit(async (values) => {
    setFormError(null);
    try {
      if (department) {
        const body: Schemas["DepartmentUpdate"] = {};
        if (dirtyFields.name) body.name = values.name;
        if (dirtyFields.head_id) body.head_id = values.head_id;
        await updateDepartment.mutateAsync({ id: department.id, body });
      } else {
        await createDepartment.mutateAsync(values);
      }
      onClose();
    } catch (error) {
      setFormError(applyApiErrors(error, setError, { fields: ["name", "head_id"], fieldForError }));
    }
  });

  return (
    <FormDialog
      open
      title={department ? "Редактирование отдела" : "Новый отдел"}
      submitting={isSubmitting}
      formError={formError}
      onSubmit={onSubmit}
      onClose={onClose}
      submitLabel={department ? "Сохранить" : "Создать"}
    >
      <FormTextField
        control={control}
        name="name"
        label="Название"
        rules={{ validate: (value) => value.trim() !== "" || "Введите название" }}
      />
      <FormAutocomplete
        control={control}
        name="head_id"
        label="Руководитель"
        fetchOptions={searchResponsibleOptions}
        queryKey={RESPONSIBLE_OPTIONS_KEY}
        labelFor={nameOf}
      />
    </FormDialog>
  );
}
```

`frontend/src/features/departments/DepartmentsPage.tsx`:
```tsx
import { Button } from "@mui/material";
import { IconPlus } from "@tabler/icons-react";
import { useState } from "react";

import type { Schemas } from "../../api/types";
import { textParam, useUrlFilters } from "../../shared/lib/useUrlFilters";
import { useDepartments } from "../../shared/lookups/departments";
import { useUserNames } from "../../shared/lookups/users";
import { DataTable, type Column } from "../../shared/ui/DataTable";
import { FilterBar, SearchField } from "../../shared/ui/FilterBar";
import { PageContainer } from "../../shared/ui/PageContainer";
import { DepartmentFormDialog } from "./DepartmentFormDialog";

type Department = Schemas["DepartmentRead"];

const FILTERS = { q: textParam };

export function DepartmentsPage() {
  const departments = useDepartments();
  const { nameOf } = useUserNames();
  const { filters, limit, offset, setFilter, setPage } = useUrlFilters(FILTERS);
  const [editing, setEditing] = useState<Department | "new" | null>(null);

  const query = filters.q.trim().toLowerCase();
  const rows = departments.data?.filter((item) => item.name.toLowerCase().includes(query));

  const columns: Column<Department>[] = [
    { key: "name", header: "Название", render: (item) => item.name },
    {
      key: "head",
      header: "Руководитель",
      render: (item) => (item.head_id === null ? "Не назначен" : nameOf(item.head_id)),
    },
  ];

  return (
    <PageContainer
      title="Отделы"
      breadcrumbs={[{ label: "Администрирование" }, { label: "Отделы" }]}
      actions={
        <Button
          variant="contained"
          startIcon={<IconPlus size={18} />}
          onClick={() => setEditing("new")}
        >
          Добавить
        </Button>
      }
    >
      <FilterBar>
        <SearchField
          value={filters.q}
          onChange={(value) => setFilter("q", value)}
          placeholder="Поиск по названию"
        />
      </FilterBar>
      <DataTable
        columns={columns}
        rows={rows}
        getRowId={(item) => item.id}
        loading={departments.isLoading}
        error={departments.error}
        onRetry={() => void departments.refetch()}
        emptyText="Отделы не найдены"
        rowActions={[{ label: "Редактировать", onClick: (item) => setEditing(item) }]}
        paging={{ limit, offset, onChange: setPage }}
      />
      {editing && (
        <DepartmentFormDialog
          department={editing === "new" ? null : editing}
          nameOf={nameOf}
          onClose={() => setEditing(null)}
        />
      )}
    </PageContainer>
  );
}
```

`frontend/src/features/departments/index.ts`:
```ts
export { DepartmentsPage } from "./DepartmentsPage";
```

`frontend/src/app/routes.tsx`:
```tsx
import type { RouteObject } from "react-router";

import {
  ChangePasswordPage,
  GuestOnly,
  LoginPage,
  ProfilePage,
  RequireAuth,
  RequireRole,
  useAuth,
} from "../features/auth";
import { DepartmentsPage } from "../features/departments";
import { HomePage } from "../features/home";
import { UsersPage } from "../features/users";
import { BlankLayout } from "../layout/BlankLayout";
import { FullLayout } from "../layout/FullLayout";
import { NotFoundPage } from "../layout/NotFoundPage";

function ChangePasswordRoute() {
  const { user } = useAuth();
  return user?.must_change_password ? (
    <BlankLayout>
      <ChangePasswordPage forced />
    </BlankLayout>
  ) : (
    <FullLayout>
      <ChangePasswordPage />
    </FullLayout>
  );
}

export const routes: RouteObject[] = [
  {
    element: <GuestOnly />,
    children: [
      { element: <BlankLayout />, children: [{ path: "/login", element: <LoginPage /> }] },
    ],
  },
  {
    element: <RequireAuth />,
    children: [
      { path: "/change-password", element: <ChangePasswordRoute /> },
      {
        element: <FullLayout />,
        children: [
          { path: "/", element: <HomePage /> },
          { path: "/profile", element: <ProfilePage /> },
          {
            element: <RequireRole role="admin" />,
            children: [
              { path: "/admin/users", element: <UsersPage /> },
              { path: "/admin/departments", element: <DepartmentsPage /> },
            ],
          },
          { path: "*", element: <NotFoundPage /> },
        ],
      },
    ],
  },
];
```

- [ ] **Step 4: Тесты проходят, commit**

```bash
npx vitest run src/features/departments   # PASS (2 теста)
npm run format && npm run check
cd .. && git add frontend && git commit -m "feat(frontend): администрирование отделов"
```


### Task 11: Справочники

**Files:**
- Create: `frontend/src/features/directories/config.ts`, `api.ts`, `DirectoryFormDialog.tsx`, `DirectoriesPage.tsx`, `index.ts`
- Modify: `frontend/src/app/routes.tsx` (маршруты `/admin/directories` и `/admin/directories/:kind`)
- Test: `frontend/src/features/directories/DirectoriesPage.test.tsx`

**Interfaces:**
- Consumes: `useUserNames`, `searchResponsibleOptions`, `RESPONSIBLE_OPTIONS_KEY` (Task 10); `APPLICABILITY_LABELS` (Task 3); формы (Tasks 4, 8); `DataTable`, `FilterBar`, `useUrlFilters`, `booleanParam` (Task 8).
- Produces:
  - `features/directories` (публично): `DirectoriesPage`.
  - внутренние: `DIRECTORY_KINDS`, `DirectoryKind`, `DIRECTORIES: Record<DirectoryKind, DirectoryConfig>`, `isDirectoryKind(value)`; `DirectoryConfig = { kind; title; extraFields; list(includeInactive); create(values); update(id, values) }`.

- [ ] **Step 1: Написать падающие тесты**

`frontend/src/features/directories/DirectoriesPage.test.tsx`:
```tsx
import { screen, waitFor, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";

import type { Schemas } from "../../api/types";
import { renderApp } from "../../test/app";
import { mockSignedIn } from "../../test/auth";
import { makeUser, page } from "../../test/fixtures";
import { errorBody } from "../../test/http";
import { server } from "../../test/server";

const LOCATIONS: Schemas["LocationRead"][] = [
  { id: 1, name: "Главный офис, каб. 101", description: "3 этаж", is_active: true },
];

function mockBase() {
  mockSignedIn();
  server.use(
    http.get("*/api/admin/users", () =>
      HttpResponse.json(page([makeUser({ id: 5, full_name: "Смирнова Анна", role: "manager" })])),
    ),
  );
}

test("/admin/directories открывает локации, вкладки переключают справочник", async () => {
  mockBase();
  server.use(
    http.get("*/api/directories/locations", () => HttpResponse.json(LOCATIONS)),
    http.get("*/api/directories/asset-types", () =>
      HttpResponse.json<Schemas["AssetTypeRead"][]>([{ id: 2, name: "Ноутбук", is_active: true }]),
    ),
  );
  const { user, router } = renderApp("/admin/directories");

  expect(await screen.findByText("Главный офис, каб. 101")).toBeInTheDocument();
  expect(router.state.location.pathname).toBe("/admin/directories/locations");

  await user.click(screen.getByRole("tab", { name: "Типы техники" }));
  expect(await screen.findByText("Ноутбук")).toBeInTheDocument();
  expect(router.state.location.pathname).toBe("/admin/directories/asset-types");
});

test("деактивация элемента и переключатель «Показывать неактивные»", async () => {
  mockBase();
  const requests: URL[] = [];
  let patched: Schemas["LocationUpdate"] | null = null;
  server.use(
    http.get("*/api/directories/locations", ({ request }) => {
      requests.push(new URL(request.url));
      return HttpResponse.json(LOCATIONS);
    }),
    http.patch("*/api/admin/directories/locations/:id", async ({ request }) => {
      patched = (await request.json()) as Schemas["LocationUpdate"];
      return HttpResponse.json({ ...LOCATIONS[0]!, is_active: false });
    }),
  );
  const { user } = renderApp("/admin/directories/locations");

  const row = (await screen.findByText("Главный офис, каб. 101")).closest("tr")!;
  await user.click(within(row).getByRole("button", { name: "Действия" }));
  await user.click(await screen.findByRole("menuitem", { name: "Деактивировать" }));
  await waitFor(() => expect(patched).toEqual({ is_active: false }));

  await user.click(screen.getByLabelText("Показывать неактивные"));
  await waitFor(() => expect(requests.at(-1)?.searchParams.get("include_inactive")).toBe("true"));
});

test("тип заявки: код задаётся при создании, дубль кода — ошибка под полем «Код»", async () => {
  mockBase();
  const ticketType: Schemas["TicketTypeRead"] = {
    id: 4,
    code: "repair",
    name: "На ремонт",
    requires_approval: true,
    default_assignee_id: 5,
    is_active: true,
  };
  server.use(
    http.get("*/api/directories/ticket-types", () => HttpResponse.json([ticketType])),
    http.post("*/api/admin/directories/ticket-types", () =>
      HttpResponse.json(
        errorBody("already_exists", "Элемент с таким значением уже существует", {
          constraint: "uq_ticket_types_code",
        }),
        { status: 409 },
      ),
    ),
  );
  const { user } = renderApp("/admin/directories/ticket-types");

  const row = (await screen.findByText("На ремонт")).closest("tr")!;
  expect(await within(row).findByText("Смирнова Анна")).toBeInTheDocument();

  await user.click(within(row).getByRole("button", { name: "Действия" }));
  await user.click(await screen.findByRole("menuitem", { name: "Редактировать" }));
  let dialog = await screen.findByRole("dialog");
  expect(within(dialog).getByLabelText("Код")).toBeDisabled();
  await user.click(within(dialog).getByRole("button", { name: "Отмена" }));
  await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());

  await user.click(screen.getByRole("button", { name: "Добавить" }));
  dialog = await screen.findByRole("dialog");
  await user.type(within(dialog).getByLabelText("Код"), "repair");
  await user.type(within(dialog).getByLabelText("Название"), "Ремонт");
  await user.click(within(dialog).getByRole("button", { name: "Создать" }));

  const codeField = within(dialog).getByLabelText("Код");
  expect(
    await within(dialog).findByText("Элемент с таким значением уже существует"),
  ).toBeInTheDocument();
  expect(codeField).toHaveAttribute("aria-invalid", "true");
});
```

- [ ] **Step 2: Запустить тесты — падают**

Run: `npx vitest run src/features/directories`
Expected: FAIL — на `/admin/directories` рендерится 404.

- [ ] **Step 3: Реализация**

Пути API в openapi-fetch типизированы литералами, поэтому у каждого справочника свои функции `list`/`create`/`update` в `config.ts`, а экран и форма общие. Коды ошибок backend: `name_blank` → «Название», `code_blank` → «Код», `invalid_default_assignee` и `reference_not_found` → «Исполнитель по умолчанию», `already_exists` → поле по `details.constraint` (`uq_ticket_types_code` → «Код», иначе «Название»). Код типа заявки передаётся только при создании. Удаления нет — только «Деактивировать»/«Активировать» (`PATCH` с `is_active`).

`frontend/src/features/directories/config.ts`:
```ts
import { api, unwrap } from "../../api/client";
import type { Schemas } from "../../api/types";

export const DIRECTORY_KINDS = [
  "locations",
  "asset-types",
  "stock-categories",
  "issue-reasons",
  "ticket-types",
] as const;

export type DirectoryKind = (typeof DIRECTORY_KINDS)[number];

export type Applicability = Schemas["IssueReasonApplicability"];

/** Общая форма элемента: у каждого справочника используется своё подмножество полей. */
export interface DirectoryItem {
  id: number;
  name: string;
  is_active: boolean;
  description?: string | null;
  applicability?: Applicability;
  code?: string;
  requires_approval?: boolean;
  default_assignee_id?: number | null;
}

export interface DirectoryFormValues {
  name: string;
  description: string;
  applicability: Applicability;
  code: string;
  requires_approval: boolean;
  default_assignee_id: number | null;
}

export type ExtraField =
  "description" | "applicability" | "code" | "requires_approval" | "default_assignee_id";

export interface DirectoryConfig {
  kind: DirectoryKind;
  title: string;
  extraFields: readonly ExtraField[];
  list: (includeInactive: boolean) => Promise<DirectoryItem[]>;
  create: (values: DirectoryFormValues) => Promise<DirectoryItem>;
  /** `values` — только изменённые поля формы; `code` не меняется после создания. */
  update: (
    id: number,
    values: Partial<DirectoryFormValues> & { is_active?: boolean },
  ) => Promise<DirectoryItem>;
}

const inactive = (includeInactive: boolean) => ({
  params: { query: { include_inactive: includeInactive } },
});
const item = (id: number) => ({ path: { item_id: id } });

export const DIRECTORIES: Record<DirectoryKind, DirectoryConfig> = {
  locations: {
    kind: "locations",
    title: "Локации",
    extraFields: ["description"],
    list: (all) => unwrap(api.GET("/api/directories/locations", inactive(all))),
    create: (v) =>
      unwrap(
        api.POST("/api/admin/directories/locations", {
          body: { name: v.name, description: v.description.trim() || null },
        }),
      ),
    update: (id, v) =>
      unwrap(
        api.PATCH("/api/admin/directories/locations/{item_id}", {
          params: item(id),
          body: {
            name: v.name,
            description: v.description === undefined ? undefined : v.description.trim() || null,
            is_active: v.is_active,
          },
        }),
      ),
  },
  "asset-types": {
    kind: "asset-types",
    title: "Типы техники",
    extraFields: [],
    list: (all) => unwrap(api.GET("/api/directories/asset-types", inactive(all))),
    create: (v) =>
      unwrap(api.POST("/api/admin/directories/asset-types", { body: { name: v.name } })),
    update: (id, v) =>
      unwrap(
        api.PATCH("/api/admin/directories/asset-types/{item_id}", {
          params: item(id),
          body: { name: v.name, is_active: v.is_active },
        }),
      ),
  },
  "stock-categories": {
    kind: "stock-categories",
    title: "Категории расходников",
    extraFields: [],
    list: (all) => unwrap(api.GET("/api/directories/stock-categories", inactive(all))),
    create: (v) =>
      unwrap(api.POST("/api/admin/directories/stock-categories", { body: { name: v.name } })),
    update: (id, v) =>
      unwrap(
        api.PATCH("/api/admin/directories/stock-categories/{item_id}", {
          params: item(id),
          body: { name: v.name, is_active: v.is_active },
        }),
      ),
  },
  "issue-reasons": {
    kind: "issue-reasons",
    title: "Причины выдачи",
    extraFields: ["applicability"],
    list: (all) => unwrap(api.GET("/api/directories/issue-reasons", inactive(all))),
    create: (v) =>
      unwrap(
        api.POST("/api/admin/directories/issue-reasons", {
          body: { name: v.name, applicability: v.applicability },
        }),
      ),
    update: (id, v) =>
      unwrap(
        api.PATCH("/api/admin/directories/issue-reasons/{item_id}", {
          params: item(id),
          body: { name: v.name, applicability: v.applicability, is_active: v.is_active },
        }),
      ),
  },
  "ticket-types": {
    kind: "ticket-types",
    title: "Типы заявок",
    extraFields: ["code", "requires_approval", "default_assignee_id"],
    list: (all) => unwrap(api.GET("/api/directories/ticket-types", inactive(all))),
    create: (v) =>
      unwrap(
        api.POST("/api/admin/directories/ticket-types", {
          body: {
            code: v.code,
            name: v.name,
            requires_approval: v.requires_approval,
            default_assignee_id: v.default_assignee_id,
          },
        }),
      ),
    update: (id, v) =>
      unwrap(
        api.PATCH("/api/admin/directories/ticket-types/{item_id}", {
          params: item(id),
          body: {
            name: v.name,
            requires_approval: v.requires_approval,
            default_assignee_id: v.default_assignee_id,
            is_active: v.is_active,
          },
        }),
      ),
  },
};

export function isDirectoryKind(value: string | undefined): value is DirectoryKind {
  return DIRECTORY_KINDS.some((kind) => kind === value);
}
```

`frontend/src/features/directories/api.ts`:
```ts
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { queryKeys } from "../../shared/lookups/queryKeys";
import type { DirectoryConfig, DirectoryFormValues } from "./config";

export function useDirectoryItems(config: DirectoryConfig, includeInactive: boolean) {
  return useQuery({
    queryKey: [...queryKeys.directories, config.kind, { includeInactive }],
    queryFn: () => config.list(includeInactive),
  });
}

export function useSaveDirectoryItem(config: DirectoryConfig) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      id,
      values,
    }: {
      id: number | null;
      values: Partial<DirectoryFormValues> & { is_active?: boolean };
    }) => (id === null ? config.create(values as DirectoryFormValues) : config.update(id, values)),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: [...queryKeys.directories, config.kind] }),
  });
}
```

`frontend/src/features/directories/DirectoryFormDialog.tsx`:
```tsx
import { useState } from "react";
import { useForm } from "react-hook-form";

import type { ApiError } from "../../api/errors";
import { applyApiErrors } from "../../shared/lib/applyApiErrors";
import { APPLICABILITY_LABELS } from "../../shared/lib/format";
import { RESPONSIBLE_OPTIONS_KEY, searchResponsibleOptions } from "../../shared/lookups/users";
import { FormDialog } from "../../shared/ui/FormDialog";
import { FormAutocomplete } from "../../shared/ui/form/FormAutocomplete";
import { FormSelect } from "../../shared/ui/form/FormSelect";
import { FormSwitch } from "../../shared/ui/form/FormSwitch";
import { FormTextField } from "../../shared/ui/form/FormTextField";
import { useSaveDirectoryItem } from "./api";
import type { Applicability, DirectoryConfig, DirectoryFormValues, DirectoryItem } from "./config";

const APPLICABILITY_OPTIONS = (Object.keys(APPLICABILITY_LABELS) as Applicability[]).map(
  (value) => ({
    value,
    label: APPLICABILITY_LABELS[value],
  }),
);

const FIELDS = [
  "name",
  "description",
  "applicability",
  "code",
  "requires_approval",
  "default_assignee_id",
] as const;

function fieldForError(error: ApiError): (typeof FIELDS)[number] | undefined {
  switch (error.code) {
    case "name_blank":
      return "name";
    case "code_blank":
      return "code";
    case "invalid_default_assignee":
    case "reference_not_found":
      return "default_assignee_id";
    case "already_exists": {
      const constraint = (error.details as { constraint?: string } | null)?.constraint ?? "";
      return constraint.endsWith("_code") ? "code" : "name";
    }
    default:
      return undefined;
  }
}

interface DirectoryFormDialogProps {
  config: DirectoryConfig;
  item: DirectoryItem | null;
  nameOf: (userId: number) => string;
  onClose: () => void;
}

export function DirectoryFormDialog({ config, item, nameOf, onClose }: DirectoryFormDialogProps) {
  const save = useSaveDirectoryItem(config);
  const [formError, setFormError] = useState<string | null>(null);
  const has = (field: (typeof config.extraFields)[number]) => config.extraFields.includes(field);
  const {
    control,
    handleSubmit,
    setError,
    formState: { isSubmitting, dirtyFields },
  } = useForm<DirectoryFormValues>({
    defaultValues: {
      name: item?.name ?? "",
      description: item?.description ?? "",
      applicability: item?.applicability ?? "both",
      code: item?.code ?? "",
      requires_approval: item?.requires_approval ?? false,
      default_assignee_id: item?.default_assignee_id ?? null,
    },
  });

  const onSubmit = handleSubmit(async (values) => {
    setFormError(null);
    const changed = item
      ? Object.fromEntries(
          FIELDS.filter((field) => field !== "code" && dirtyFields[field]).map((field) => [
            field,
            values[field],
          ]),
        )
      : values;
    try {
      await save.mutateAsync({ id: item?.id ?? null, values: changed });
      onClose();
    } catch (error) {
      setFormError(applyApiErrors(error, setError, { fields: FIELDS, fieldForError }));
    }
  });

  return (
    <FormDialog
      open
      title={item ? `${config.title}: редактирование` : `${config.title}: новый элемент`}
      submitting={isSubmitting}
      formError={formError}
      onSubmit={onSubmit}
      onClose={onClose}
      submitLabel={item ? "Сохранить" : "Создать"}
    >
      {has("code") && (
        <FormTextField
          control={control}
          name="code"
          label="Код"
          disabled={Boolean(item)}
          helperText="Задаётся при создании и не меняется"
          rules={{ validate: (value) => value.trim() !== "" || "Введите код" }}
        />
      )}
      <FormTextField
        control={control}
        name="name"
        label="Название"
        rules={{ validate: (value) => value.trim() !== "" || "Введите название" }}
      />
      {has("description") && (
        <FormTextField
          control={control}
          name="description"
          label="Описание"
          multiline
          minRows={2}
        />
      )}
      {has("applicability") && (
        <FormSelect
          control={control}
          name="applicability"
          label="Применимость"
          options={APPLICABILITY_OPTIONS}
        />
      )}
      {has("requires_approval") && (
        <FormSwitch control={control} name="requires_approval" label="Требует согласования" />
      )}
      {has("default_assignee_id") && (
        <FormAutocomplete
          control={control}
          name="default_assignee_id"
          label="Исполнитель по умолчанию"
          fetchOptions={searchResponsibleOptions}
          queryKey={RESPONSIBLE_OPTIONS_KEY}
          labelFor={nameOf}
        />
      )}
    </FormDialog>
  );
}
```

`frontend/src/features/directories/DirectoriesPage.tsx`:
```tsx
import { Button, Chip, FormControlLabel, Switch, Tab, Tabs } from "@mui/material";
import { IconPlus } from "@tabler/icons-react";
import { useSnackbar } from "notistack";
import { useState } from "react";
import { Navigate, useNavigate, useParams } from "react-router";

import { ApiError } from "../../api/errors";
import { APPLICABILITY_LABELS } from "../../shared/lib/format";
import { booleanParam, useUrlFilters } from "../../shared/lib/useUrlFilters";
import { useUserNames } from "../../shared/lookups/users";
import { DataTable, type Column, type RowAction } from "../../shared/ui/DataTable";
import { FilterBar } from "../../shared/ui/FilterBar";
import { PageContainer } from "../../shared/ui/PageContainer";
import { useDirectoryItems, useSaveDirectoryItem } from "./api";
import {
  DIRECTORIES,
  DIRECTORY_KINDS,
  isDirectoryKind,
  type DirectoryConfig,
  type DirectoryItem,
} from "./config";
import { DirectoryFormDialog } from "./DirectoryFormDialog";

const FILTERS = { inactive: booleanParam };

export function DirectoriesPage() {
  const { kind } = useParams();
  if (!isDirectoryKind(kind)) return <Navigate to="/admin/directories/locations" replace />;
  return <DirectoryScreen key={kind} config={DIRECTORIES[kind]} />;
}

function DirectoryScreen({ config }: { config: DirectoryConfig }) {
  const navigate = useNavigate();
  const { enqueueSnackbar } = useSnackbar();
  const { nameOf } = useUserNames();
  const { filters, limit, offset, setFilter, setPage } = useUrlFilters(FILTERS);
  const includeInactive = filters.inactive === true;
  const items = useDirectoryItems(config, includeInactive);
  const save = useSaveDirectoryItem(config);
  const [editing, setEditing] = useState<DirectoryItem | "new" | null>(null);

  const has = (field: (typeof config.extraFields)[number]) => config.extraFields.includes(field);

  const setActive = async (item: DirectoryItem, active: boolean) => {
    try {
      await save.mutateAsync({ id: item.id, values: { is_active: active } });
      enqueueSnackbar(active ? "Элемент активирован" : "Элемент деактивирован", {
        variant: "success",
      });
    } catch (error) {
      enqueueSnackbar(error instanceof ApiError ? error.message : "Не удалось выполнить запрос", {
        variant: "error",
      });
    }
  };

  const columns: Column<DirectoryItem>[] = [
    ...(has("code")
      ? [{ key: "code", header: "Код", render: (item: DirectoryItem) => item.code }]
      : []),
    { key: "name", header: "Название", render: (item) => item.name },
    ...(has("description")
      ? [
          {
            key: "description",
            header: "Описание",
            render: (item: DirectoryItem) => item.description ?? "—",
          },
        ]
      : []),
    ...(has("applicability")
      ? [
          {
            key: "applicability",
            header: "Применимость",
            render: (item: DirectoryItem) =>
              item.applicability ? APPLICABILITY_LABELS[item.applicability] : "—",
          },
        ]
      : []),
    ...(has("requires_approval")
      ? [
          {
            key: "requires_approval",
            header: "Согласование",
            render: (item: DirectoryItem) =>
              item.requires_approval ? "Требуется" : "Не требуется",
          },
        ]
      : []),
    ...(has("default_assignee_id")
      ? [
          {
            key: "default_assignee_id",
            header: "Исполнитель по умолчанию",
            render: (item: DirectoryItem) =>
              item.default_assignee_id ? nameOf(item.default_assignee_id) : "—",
          },
        ]
      : []),
    {
      key: "status",
      header: "Статус",
      render: (item) => (
        <Chip
          size="small"
          label={item.is_active ? "Активен" : "Неактивен"}
          color={item.is_active ? "success" : "default"}
        />
      ),
    },
  ];

  const rowActions: RowAction<DirectoryItem>[] = [
    { label: "Редактировать", onClick: (item) => setEditing(item) },
    {
      label: "Деактивировать",
      color: "error",
      hidden: (item) => !item.is_active,
      onClick: (item) => void setActive(item, false),
    },
    {
      label: "Активировать",
      hidden: (item) => item.is_active,
      onClick: (item) => void setActive(item, true),
    },
  ];

  return (
    <PageContainer
      title="Справочники"
      breadcrumbs={[
        { label: "Администрирование" },
        { label: "Справочники" },
        { label: config.title },
      ]}
      actions={
        <Button
          variant="contained"
          startIcon={<IconPlus size={18} />}
          onClick={() => setEditing("new")}
        >
          Добавить
        </Button>
      }
    >
      <Tabs
        value={config.kind}
        onChange={(_, next: string) => void navigate(`/admin/directories/${next}`)}
        variant="scrollable"
        sx={{ mb: 2 }}
      >
        {DIRECTORY_KINDS.map((kind) => (
          <Tab key={kind} value={kind} label={DIRECTORIES[kind].title} />
        ))}
      </Tabs>
      <FilterBar>
        <FormControlLabel
          label="Показывать неактивные"
          control={
            <Switch
              checked={includeInactive}
              onChange={(event) => setFilter("inactive", event.target.checked ? true : null)}
            />
          }
        />
      </FilterBar>
      <DataTable
        columns={columns}
        rows={items.data}
        getRowId={(item) => item.id}
        loading={items.isLoading}
        error={items.error}
        onRetry={() => void items.refetch()}
        emptyText="Элементов нет"
        rowActions={rowActions}
        paging={{ limit, offset, onChange: setPage }}
      />
      {editing && (
        <DirectoryFormDialog
          config={config}
          item={editing === "new" ? null : editing}
          nameOf={nameOf}
          onClose={() => setEditing(null)}
        />
      )}
    </PageContainer>
  );
}
```

`frontend/src/features/directories/index.ts`:
```ts
export { DirectoriesPage } from "./DirectoriesPage";
```

`frontend/src/app/routes.tsx`:
```tsx
import { Navigate, type RouteObject } from "react-router";

import {
  ChangePasswordPage,
  GuestOnly,
  LoginPage,
  ProfilePage,
  RequireAuth,
  RequireRole,
  useAuth,
} from "../features/auth";
import { DepartmentsPage } from "../features/departments";
import { DirectoriesPage } from "../features/directories";
import { HomePage } from "../features/home";
import { UsersPage } from "../features/users";
import { BlankLayout } from "../layout/BlankLayout";
import { FullLayout } from "../layout/FullLayout";
import { NotFoundPage } from "../layout/NotFoundPage";

function ChangePasswordRoute() {
  const { user } = useAuth();
  return user?.must_change_password ? (
    <BlankLayout>
      <ChangePasswordPage forced />
    </BlankLayout>
  ) : (
    <FullLayout>
      <ChangePasswordPage />
    </FullLayout>
  );
}

export const routes: RouteObject[] = [
  {
    element: <GuestOnly />,
    children: [
      { element: <BlankLayout />, children: [{ path: "/login", element: <LoginPage /> }] },
    ],
  },
  {
    element: <RequireAuth />,
    children: [
      { path: "/change-password", element: <ChangePasswordRoute /> },
      {
        element: <FullLayout />,
        children: [
          { path: "/", element: <HomePage /> },
          { path: "/profile", element: <ProfilePage /> },
          {
            element: <RequireRole role="admin" />,
            children: [
              { path: "/admin/users", element: <UsersPage /> },
              { path: "/admin/departments", element: <DepartmentsPage /> },
              {
                path: "/admin/directories",
                element: <Navigate to="/admin/directories/locations" replace />,
              },
              { path: "/admin/directories/:kind", element: <DirectoriesPage /> },
            ],
          },
          { path: "*", element: <NotFoundPage /> },
        ],
      },
    ],
  },
];
```

- [ ] **Step 4: Тесты проходят, commit**

```bash
npx vitest run src/features/directories   # PASS (3 теста)
npm run format && npm run check && npm run build
cd .. && git add frontend && git commit -m "feat(frontend): справочники"
```


### Task 12: Docker-образ, compose, CI, Makefile, README

**Files:**
- Create: `frontend/Dockerfile`, `frontend/.dockerignore`, `frontend/nginx.conf`
- Modify: `compose.yaml` (сервис `frontend`, `TRUSTED_PROXIES` backend, подсеть сети compose)
- Modify: `.github/workflows/ci.yml` (задача `frontend`)
- Modify: `Makefile` (цели `frontend-install`, `frontend-dev`, `frontend-check`, `gen-api`)
- Modify: `README.md` (раздел «Фронтенд»)

**Interfaces:**
- Consumes: `npm run build`, `npm run check` (Task 1); backend-сервис `backend:8000` из `compose.yaml`.
- Produces: образ фронтенда (nginx, порт 80) со статикой и проксированием `/api/`; `docker compose up` поднимает стек на `http://localhost:8080`; CI-задача `frontend`.

- [ ] **Step 1: Образ фронтенда**

nginx проксирует `/api/` на backend через DNS Docker (`resolver 127.0.0.11`) с переменной в `proxy_pass`: так nginx стартует, даже если backend ещё не поднят (иначе `host not found in upstream`). `add_header` в `location` отменяет наследование заголовков уровня `server`, поэтому заголовки безопасности повторены в `location /`. `X-Forwarded-For` перезаписывается адресом клиента — backend доверяет ему только от адресов из `TRUSTED_PROXIES`. Для стилей emotion нужен `style-src 'unsafe-inline'`; шрифты и скрипты — только с того же домена.

`frontend/Dockerfile`:
```dockerfile
FROM node:24-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY . .
RUN npm run build

FROM nginx:1.29-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
```

`frontend/.dockerignore`:
```
node_modules
dist
coverage
```

`frontend/nginx.conf`:
```nginx
server {
    listen 80;
    server_name _;
    root /usr/share/nginx/html;

    # DNS Docker: имя backend разрешается при запросе, поэтому nginx стартует и без backend.
    resolver 127.0.0.11 valid=10s ipv6=off;
    set $backend_upstream http://backend:8000;

    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "same-origin" always;
    add_header X-Frame-Options "DENY" always;
    add_header Content-Security-Policy "default-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'" always;

    location /api/ {
        proxy_pass $backend_upstream;
        proxy_set_header Host $host;
        # Перезаписываем, а не дописываем: backend доверяет X-Forwarded-For только от этого прокси.
        proxy_set_header X-Forwarded-For $remote_addr;
        proxy_set_header X-Forwarded-Proto $scheme;
        client_max_body_size 10m;
    }

    location /assets/ {
        add_header Cache-Control "public, max-age=31536000, immutable";
        add_header X-Content-Type-Options "nosniff" always;
        try_files $uri =404;
    }

    location / {
        add_header Cache-Control "no-cache";
        add_header X-Content-Type-Options "nosniff" always;
        add_header Referrer-Policy "same-origin" always;
        add_header X-Frame-Options "DENY" always;
        add_header Content-Security-Policy "default-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'" always;
        try_files $uri /index.html;
    }
}
```

- [ ] **Step 2: Проверить образ отдельно**

```bash
docker build -t it-platform-frontend frontend
docker run --rm it-platform-frontend nginx -t
CID=$(docker run -d -p 18080:80 it-platform-frontend); sleep 2
curl -s -o /dev/null -w '%{http_code} %{content_type}\n' localhost:18080/admin/users
curl -sI localhost:18080/ | grep -i -E 'content-security-policy|x-frame-options|cache-control'
docker rm -f $CID
```

Expected: `nginx: configuration file /etc/nginx/nginx.conf test is successful`; `200 text/html` (SPA-fallback); заголовки `Content-Security-Policy`, `X-Frame-Options: DENY`, `Cache-Control: no-cache`.

- [ ] **Step 3: compose**

В `compose.yaml` сервису `backend` в `environment` добавить строку (после `COOKIE_SECURE`):

```yaml
      TRUSTED_PROXIES: '["172.28.0.0/16"]'
```

После сервиса `backend` добавить сервис:

```yaml
  frontend:
    build: ./frontend
    ports:
      - "127.0.0.1:8080:80"
    depends_on:
      - backend
```

Перед секцией `volumes:` в конце файла добавить фиксированную подсеть сети compose (на неё указывает `TRUSTED_PROXIES`):

```yaml
networks:
  default:
    ipam:
      config:
        - subnet: 172.28.0.0/16
```

Сеть уже существующего стека создана без этой подсети — пересоздать её: `docker compose down` (тома с данными не удаляются), затем `docker compose up -d --build`.

- [ ] **Step 4: Проверить стек целиком**

```bash
docker compose down && docker compose up -d --build
docker compose ps   # postgres, redis, backend, frontend — running
curl -s -o /dev/null -w '%{http_code}\n' localhost:8080/
curl -si -X POST localhost:8080/api/auth/login -H 'Content-Type: application/json' \
  -d '{"email":"admin@company.ru","password":"<пароль>"}' | grep -i -E '^HTTP|set-cookie'
docker compose logs backend --tail 20 | grep '/api/auth/login'
```

Expected: `200`; вход через nginx возвращает `HTTP/1.1 200` и `set-cookie: refresh_token=...; HttpOnly; Path=/api/auth; SameSite=strict` (если администратора в БД нет — `make create-admin ...`; неверный пароль даёт `401`, это тоже подтверждает проксирование). В браузере `http://localhost:8080`: вход, главная, «Пользователи», «Отделы», «Справочники» открываются, перезагрузка не разлогинивает.

- [ ] **Step 5: CI**

В `.github/workflows/ci.yml` в секцию `jobs:` после задачи `backend` добавить:

```yaml
  frontend:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: frontend
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version-file: frontend/.nvmrc
          cache: npm
          cache-dependency-path: frontend/package-lock.json
      - run: npm ci
      - run: npm run check
      - run: npm run build
```

`check:api` сверяет `src/api/schema.d.ts` с `backend/openapi.json` из того же коммита, а задача `backend` уже проверяет, что `openapi.json` соответствует коду: вместе они гарантируют актуальные типы фронтенда (п. 9 ТЗ).

- [ ] **Step 6: Makefile**

В строку `.PHONY` добавить `frontend-install frontend-dev frontend-check gen-api`, в конец файла:

```make
frontend-install:
	cd frontend && npm ci

frontend-dev:
	cd frontend && npm run dev

frontend-check:
	cd frontend && npm run check && npm run build

gen-api: openapi
	cd frontend && npm run gen:api
```

Отступы в рецептах — символ табуляции.

- [ ] **Step 7: README**

В `README.md` в «Требования» добавить строку `- Node.js 24 (\`.nvmrc\` в \`frontend/\`)`. Перед разделом «## Фронтенд: обновление токена» вставить раздел:

````markdown
## Фронтенд

React + TypeScript (Vite), MUI в стиле шаблона Modernize. Код — `frontend/`.

```bash
make frontend-install
make frontend-dev      # http://localhost:5173, /api проксируется на localhost:8000
make frontend-check    # типы, ESLint, Prettier, тесты, актуальность типов API, сборка
make gen-api           # после изменения API: openapi.json + src/api/schema.d.ts
```

Весь стек в Docker: `docker compose up -d --build` → http://localhost:8080 (nginx отдаёт фронтенд и проксирует `/api`).

Структура `frontend/src`: `app/` (провайдеры, маршруты), `layout/` (каркас), `api/` (клиент и сгенерированные типы), `shared/ui`, `shared/lib`, `shared/lookups` (общие справочные запросы), `features/<модуль>/`. Фича импортирует другую фичу только через её `index.ts`; `api`, `theme` и `shared` не зависят от фич — это проверяет ESLint (`import/no-restricted-paths`).
````

В разделе «Фронтенд: обновление токена» дописать в конец абзаца: `Реализация — \`frontend/src/api/refresh.ts\` (общий промис внутри вкладки и Web Locks между вкладками).`

- [ ] **Step 8: Итоговая проверка и commit**

```bash
make frontend-check && make lint
git add frontend compose.yaml .github/workflows/ci.yml Makefile README.md
git commit -m "feat(frontend): Docker-образ, compose, CI, документация"
```
