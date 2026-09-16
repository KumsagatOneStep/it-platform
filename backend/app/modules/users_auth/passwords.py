import secrets
from functools import cache

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from app.core.errors import ValidationFailedError

PASSWORD_MIN_LENGTH = 10

_hasher = PasswordHasher()  # Argon2id с параметрами по умолчанию (RFC 9106)


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


@cache
def _dummy_hash() -> str:
    return hash_password(secrets.token_urlsafe(16))


def dummy_verify(password: str) -> None:
    """Выравнивает время ответа, когда пользователь не найден."""
    verify_password(_dummy_hash(), password)


def validate_password_strength(password: str) -> None:
    if len(password) < PASSWORD_MIN_LENGTH:
        raise ValidationFailedError(
            f"Пароль должен содержать не менее {PASSWORD_MIN_LENGTH} символов",
            code="weak_password",
        )


def generate_temporary_password() -> str:
    return secrets.token_urlsafe(12)
