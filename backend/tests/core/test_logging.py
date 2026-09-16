import json
import logging

from httpx import AsyncClient

from app.core.logging import JsonFormatter, request_id_var


def test_json_formatter_includes_request_id_and_extra() -> None:
    record = logging.LogRecord("app.test", logging.INFO, __file__, 1, "событие", None, None)
    record.user_id = 7
    token = request_id_var.set("abc123")
    try:
        payload = json.loads(JsonFormatter().format(record))
    finally:
        request_id_var.reset(token)

    assert payload["message"] == "событие"
    assert payload["level"] == "INFO"
    assert payload["logger"] == "app.test"
    assert payload["request_id"] == "abc123"
    assert payload["user_id"] == 7


async def test_request_id_generated_when_missing(client: AsyncClient) -> None:
    response = await client.get("/health")

    assert len(response.headers["x-request-id"]) == 32


async def test_valid_incoming_request_id_is_echoed(client: AsyncClient) -> None:
    response = await client.get("/health", headers={"X-Request-ID": "req-1.A_b"})

    assert response.headers["x-request-id"] == "req-1.A_b"


async def test_invalid_incoming_request_id_is_replaced(client: AsyncClient) -> None:
    response = await client.get("/health", headers={"X-Request-ID": "bad id\nwith newline"})

    assert response.headers["x-request-id"] != "bad id\nwith newline"
    assert len(response.headers["x-request-id"]) == 32
