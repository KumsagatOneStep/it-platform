from starlette.requests import Request

from app.core.net import client_ip

TRUSTED = ["127.0.0.1/32", "172.16.0.0/12"]


def _request(peer: str, forwarded: str | None = None) -> Request:
    headers = [(b"x-forwarded-for", forwarded.encode())] if forwarded else []
    return Request({"type": "http", "client": (peer, 5000), "headers": headers})


def test_untrusted_peer_ignores_forwarded_header() -> None:
    assert client_ip(_request("198.51.100.7", "203.0.113.1"), TRUSTED) == "198.51.100.7"


def test_trusted_peer_uses_forwarded_header() -> None:
    assert client_ip(_request("172.18.0.5", "203.0.113.1"), TRUSTED) == "203.0.113.1"


def test_rightmost_untrusted_address_wins_over_spoofed_prefix() -> None:
    request = _request("172.18.0.5", "10.9.9.9, 203.0.113.1, 172.18.0.2")

    assert client_ip(request, TRUSTED) == "203.0.113.1"


def test_trusted_peer_without_header_returns_peer() -> None:
    assert client_ip(_request("127.0.0.1"), TRUSTED) == "127.0.0.1"


def test_garbage_in_forwarded_header_is_not_trusted() -> None:
    assert client_ip(_request("127.0.0.1", "not-an-ip"), TRUSTED) == "not-an-ip"
