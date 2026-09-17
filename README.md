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

## Развёртывание (staging/production)

Образ `backend/Dockerfile` по умолчанию запускается с `APP_ENV=production`. В этом режиме приложение не стартует, если:

- `JWT_SECRET` не задан или короче 32 символов;
- `COOKIE_SECURE=false` (refresh-cookie должна быть `Secure`);
- `CORS_ORIGINS` не пустой (фронтенд и API на одном домене);
- в `TRUSTED_PROXIES` есть некорректный адрес или сеть (проверяется в любом окружении).

### TRUSTED_PROXIES

IP клиента нужен для защиты от перебора паролей (блокировка по паре «учётная запись + IP» и по IP). Заголовок `X-Forwarded-For` учитывается только от адресов из `TRUSTED_PROXIES`.

- Формат — JSON-список адресов или сетей: `TRUSTED_PROXIES='["172.16.0.0/12"]'`.
- Список должен включать Docker-сеть, из которой обратный прокси (nginx и т. п.) обращается к backend.
- Прокси обязан перезаписывать `X-Forwarded-For` реальным адресом клиента или дописывать его в конец (`proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;`).

Если прокси не указан в `TRUSTED_PROXIES`, все запросы выглядят как пришедшие с IP прокси: 20 неудачных входов любых пользователей за 15 минут заблокируют вход всем.

## Фронтенд: обновление токена

Refresh-токен ротируется при каждом `POST /api/auth/refresh`. Фронтенд должен выполнять refresh в режиме single-flight: один запрос на вкладку (и координация между вкладками, например через `BroadcastChannel` или Web Locks), остальные ждут его результата. Повтор уже использованного токена в течение 30 секунд возвращает 401 без побочных эффектов; более поздний повтор считается кражей и отзывает все сессии пользователя.

## Архитектура

Модульный монолит (`backend/app/modules/*`). Модуль используется другими модулями только через `service.py` и `events.py` — это проверяет `lint-imports` в CI. Обратные связи между модулями — через доменные события (`app/core/events.py`).
