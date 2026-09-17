import json
import logging

from fastapi import FastAPI, HTTPException
from httpx import AsyncClient

from app.core.errors import ConflictError, UnauthorizedError
from app.core.logging import JsonFormatter
from app.main import create_app
from app.modules.users_auth.models import User


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


async def test_body_validation_error_uses_envelope(client: AsyncClient) -> None:
    response = await client.post("/api/auth/login", json={"email": "a@b.ru"})

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "validation_failed"
    assert error["message"] == "Некорректные данные запроса"
    assert error["details"] == [
        {"loc": ["body", "password"], "msg": "Field required", "type": "missing"}
    ]


async def test_validation_error_details_do_not_echo_input(client: AsyncClient) -> None:
    response = await client.post("/api/auth/login", json={"email": "a@b.ru", "password": "x" * 300})

    assert response.status_code == 422
    assert "x" * 300 not in response.text


async def test_query_validation_error_uses_envelope(
    client: AsyncClient, admin_headers: dict[str, str]
) -> None:
    response = await client.get("/api/admin/users", headers=admin_headers, params={"limit": 0})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_failed"
    assert response.json()["error"]["details"][0]["loc"] == ["query", "limit"]


async def test_model_validator_error_is_json_safe(
    client: AsyncClient, admin_headers: dict[str, str], admin_user: User
) -> None:
    response = await client.patch(
        f"/api/admin/users/{admin_user.id}", headers=admin_headers, json={"full_name": None}
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_failed"


async def test_unknown_route_uses_envelope(client: AsyncClient) -> None:
    response = await client.get("/api/does-not-exist")

    assert response.status_code == 404
    assert response.json() == {
        "error": {"code": "not_found", "message": "Ресурс не найден", "details": None}
    }


async def test_wrong_method_uses_envelope(client: AsyncClient) -> None:
    response = await client.get("/api/auth/login")

    assert response.status_code == 405
    assert response.json()["error"]["code"] == "method_not_allowed"
    assert response.json()["error"]["message"] == "Метод не поддерживается"
    assert "POST" in response.headers["allow"]


async def test_other_http_exception_uses_status_code(app: FastAPI, client: AsyncClient) -> None:
    async def teapot() -> None:
        raise HTTPException(status_code=418)

    app.add_api_route("/_probe/teapot", teapot, methods=["GET"])

    response = await client.get("/_probe/teapot")

    assert response.status_code == 418
    assert response.json()["error"]["code"] == "http_418"
    assert response.json()["error"]["message"] == "Ошибка обработки запроса"


async def test_unhandled_exception_returns_500_envelope_with_request_id(
    app: FastAPI, client: AsyncClient
) -> None:
    async def boom() -> None:
        raise RuntimeError("секретная деталь")

    app.add_api_route("/_probe/boom", boom, methods=["GET"])
    records: list[str] = []

    class _Collect(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            records.append(JsonFormatter().format(record))

    handler = _Collect()
    logger = logging.getLogger("app.core.middleware")
    logger.addHandler(handler)
    try:
        response = await client.get("/_probe/boom", headers={"X-Request-ID": "boom-1"})
    finally:
        logger.removeHandler(handler)

    assert response.status_code == 500
    assert response.headers["x-request-id"] == "boom-1"
    assert response.headers["content-type"] == "application/json"
    assert response.json() == {
        "error": {
            "code": "internal_error",
            "message": "Внутренняя ошибка сервера",
            "details": None,
        }
    }
    assert "секретная деталь" not in response.text
    logged = [json.loads(line) for line in records]
    assert len(logged) == 1
    assert logged[0]["request_id"] == "boom-1"
    assert logged[0]["level"] == "ERROR"
    assert "RuntimeError: секретная деталь" in logged[0]["exc_info"]


def test_openapi_uses_error_envelope_instead_of_default_422() -> None:
    schema = create_app().openapi()

    assert "HTTPValidationError" not in schema["components"]["schemas"]
    assert "ErrorResponse" in schema["components"]["schemas"]
    login_responses = schema["paths"]["/api/auth/login"]["post"]["responses"]
    assert login_responses["422"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/ErrorResponse"
    }
