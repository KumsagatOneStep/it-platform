import json
import logging
import re
from uuid import uuid4

from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.errors import error_payload
from app.core.logging import request_id_var

logger = logging.getLogger(__name__)

_VALID_REQUEST_ID = re.compile(r"^[A-Za-z0-9._-]{1,128}$")


class RequestIdMiddleware:
    """request_id для логов и заголовка X-Request-ID; перехват необработанных исключений.

    Чистый ASGI-middleware (не BaseHTTPMiddleware): исключение логируется, пока
    request_id ещё установлен, а клиент получает 500 в едином формате с X-Request-ID.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        incoming = ""
        for name, value in scope["headers"]:
            if name == b"x-request-id":
                incoming = value.decode("latin-1")
                break
        request_id = incoming if _VALID_REQUEST_ID.fullmatch(incoming) else uuid4().hex
        response_started = False

        async def send_with_request_id(message: Message) -> None:
            nonlocal response_started
            if message["type"] == "http.response.start":
                response_started = True
                MutableHeaders(scope=message)["X-Request-ID"] = request_id
            await send(message)

        token = request_id_var.set(request_id)
        try:
            await self.app(scope, receive, send_with_request_id)
        except Exception:
            logger.exception("request.unhandled_exception")
            if response_started:
                raise
            body = json.dumps(
                error_payload("internal_error", "Внутренняя ошибка сервера"), ensure_ascii=False
            ).encode()
            await send_with_request_id(
                {
                    "type": "http.response.start",
                    "status": 500,
                    "headers": [
                        (b"content-type", b"application/json"),
                        (b"content-length", str(len(body)).encode()),
                    ],
                }
            )
            await send({"type": "http.response.body", "body": body})
        finally:
            request_id_var.reset(token)
