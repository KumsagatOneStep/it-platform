import io
import json
import logging

from httpx import AsyncClient

from app.core.logging import JsonFormatter, configure_logging, request_id_var


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


def test_configure_logging_routes_uvicorn_loggers_to_json_root() -> None:
    root = logging.getLogger()
    saved_root = (root.handlers[:], root.level)
    uvicorn_names = ("uvicorn", "uvicorn.error", "uvicorn.access")
    saved = {
        name: (logging.getLogger(name).handlers[:], logging.getLogger(name).propagate)
        for name in uvicorn_names
    }
    stream = io.StringIO()
    for name in ("uvicorn", "uvicorn.access"):
        # Так их настраивает uvicorn до импорта приложения (propagate=False, свои handlers)
        logging.getLogger(name).handlers = [logging.StreamHandler(io.StringIO())]
        logging.getLogger(name).propagate = False
    try:
        configure_logging()
        root_handler = root.handlers[0]
        assert isinstance(root_handler, logging.StreamHandler)
        root_handler.setStream(stream)

        logging.getLogger("uvicorn.error").info("Started server process")
        logging.getLogger("uvicorn.access").info(
            '%s - "%s %s HTTP/%s" %d', "127.0.0.1:1", "GET", "/health", "1.1", 200
        )
    finally:
        root.handlers, level = saved_root
        root.setLevel(level)
        for name, (handlers, propagate) in saved.items():
            logging.getLogger(name).handlers = handlers
            logging.getLogger(name).propagate = propagate

    lines = [json.loads(line) for line in stream.getvalue().splitlines()]
    assert [line["logger"] for line in lines] == ["uvicorn.error", "uvicorn.access"]
    assert lines[1]["message"] == '127.0.0.1:1 - "GET /health HTTP/1.1" 200'
    assert all("color_message" not in line for line in lines)


def test_json_formatter_skips_uvicorn_color_message() -> None:
    record = logging.LogRecord("uvicorn.error", logging.INFO, __file__, 1, "msg", None, None)
    record.color_message = "\x1b[32mmsg\x1b[0m"

    assert "color_message" not in json.loads(JsonFormatter().format(record))
