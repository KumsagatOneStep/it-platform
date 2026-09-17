from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException


class AppError(Exception):
    status_code: int = 400
    code: str = "bad_request"

    def __init__(self, message: str, *, code: str | None = None, details: Any = None) -> None:
        super().__init__(message)
        self.message = message
        if code is not None:
            self.code = code
        self.details = details


class UnauthorizedError(AppError):
    status_code = 401
    code = "unauthorized"


class ForbiddenError(AppError):
    status_code = 403
    code = "forbidden"


class NotFoundError(AppError):
    status_code = 404
    code = "not_found"


class ConflictError(AppError):
    status_code = 409
    code = "conflict"


class ValidationFailedError(AppError):
    status_code = 422
    code = "validation_failed"


class TooManyRequestsError(AppError):
    status_code = 429
    code = "too_many_requests"


class ErrorBody(BaseModel):
    code: str
    message: str
    details: Any = None


class ErrorResponse(BaseModel):
    """Единый формат ошибки API (п. 7 ТЗ)."""

    error: ErrorBody


# Подставляется в include_router: заменяет стандартный 422 HTTPValidationError в OpenAPI.
ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    422: {"model": ErrorResponse, "description": "Некорректные данные запроса"},
    "4XX": {"model": ErrorResponse, "description": "Ошибка запроса"},
    500: {"model": ErrorResponse, "description": "Внутренняя ошибка сервера"},
}

_HTTP_ERRORS: dict[int, tuple[str, str]] = {
    404: ("not_found", "Ресурс не найден"),
    405: ("method_not_allowed", "Метод не поддерживается"),
}


def error_payload(code: str, message: str, details: Any = None) -> dict[str, Any]:
    return {"error": {"code": code, "message": message, "details": details}}


async def app_error_handler(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, AppError)
    headers = {"WWW-Authenticate": "Bearer"} if isinstance(exc, UnauthorizedError) else None
    return JSONResponse(
        error_payload(exc.code, exc.message, exc.details),
        status_code=exc.status_code,
        headers=headers,
    )


async def request_validation_error_handler(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)
    # Только loc/msg/type: input и ctx могут содержать пароли и не сериализуемые объекты.
    details = [
        {
            "loc": [part if isinstance(part, int) else str(part) for part in error["loc"]],
            "msg": str(error["msg"]),
            "type": str(error["type"]),
        }
        for error in exc.errors()
    ]
    return JSONResponse(
        error_payload("validation_failed", "Некорректные данные запроса", details),
        status_code=422,
    )


async def http_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, StarletteHTTPException)
    code, message = _HTTP_ERRORS.get(
        exc.status_code, (f"http_{exc.status_code}", "Ошибка обработки запроса")
    )
    return JSONResponse(
        error_payload(code, message), status_code=exc.status_code, headers=exc.headers
    )


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(RequestValidationError, request_validation_error_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
