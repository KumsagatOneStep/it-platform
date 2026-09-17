FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Безопасный режим по умолчанию: проверки JWT_SECRET и COOKIE_SECURE (compose для
# локальной разработки переопределяет APP_ENV=local).
ENV APP_ENV=production \
    UV_COMPILE_BYTECODE=1 \
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
