from datetime import UTC, datetime, timedelta

import jwt
import pytest

from app.core.config import get_settings
from app.core.errors import UnauthorizedError
from app.modules.users_auth.tokens import (
    create_access_token,
    decode_access_token,
    hash_refresh_token,
    new_refresh_token,
)


def test_access_token_roundtrip() -> None:
    assert decode_access_token(create_access_token(42)) == 42


def test_access_token_expires_after_15_minutes() -> None:
    issued = datetime.now(UTC) - timedelta(minutes=16)

    with pytest.raises(UnauthorizedError):
        decode_access_token(create_access_token(42, now=issued))


def test_tampered_token_rejected() -> None:
    token = create_access_token(42)

    with pytest.raises(UnauthorizedError):
        decode_access_token(token[:-2] + ("aa" if token[-2:] != "aa" else "bb"))


def test_token_of_other_type_rejected() -> None:
    token = jwt.encode(
        {"sub": "42", "type": "refresh", "exp": datetime.now(UTC) + timedelta(minutes=5)},
        get_settings().jwt_secret,
        algorithm="HS256",
    )

    with pytest.raises(UnauthorizedError):
        decode_access_token(token)


def test_refresh_token_hash_is_sha256_of_raw() -> None:
    raw, token_hash = new_refresh_token()

    assert len(raw) >= 40
    assert token_hash == hash_refresh_token(raw)
    assert len(token_hash) == 64
