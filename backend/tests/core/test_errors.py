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
