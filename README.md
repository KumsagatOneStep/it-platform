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
