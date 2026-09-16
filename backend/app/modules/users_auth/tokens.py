import hashlib
import secrets
from datetime import UTC, datetime, timedelta

import jwt

from app.core.config import get_settings
from app.core.errors import UnauthorizedError

ALGORITHM = "HS256"


def create_access_token(user_id: int, *, now: datetime | None = None) -> str:
    settings = get_settings()
    issued_at = now or datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "type": "access",
        "iat": int(issued_at.timestamp()),
        "exp": int((issued_at + timedelta(minutes=settings.access_token_ttl_minutes)).timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)


def decode_access_token(token: str) -> int:
    invalid = UnauthorizedError("Сессия недействительна, войдите снова", code="invalid_token")
    try:
        payload = jwt.decode(
            token,
            get_settings().jwt_secret,
            algorithms=[ALGORITHM],
            options={"require": ["sub", "exp", "type"]},
        )
    except jwt.PyJWTError as exc:
        raise invalid from exc
    if payload.get("type") != "access":
        raise invalid
    try:
        return int(payload["sub"])
    except (TypeError, ValueError) as exc:
        raise invalid from exc


def hash_refresh_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def new_refresh_token() -> tuple[str, str]:
    raw = secrets.token_urlsafe(32)
    return raw, hash_refresh_token(raw)
