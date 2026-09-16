import pytest

from app.core.errors import ValidationFailedError
from app.modules.users_auth.passwords import (
    PASSWORD_MIN_LENGTH,
    generate_temporary_password,
    hash_password,
    validate_password_strength,
    verify_password,
)


def test_hash_is_argon2id_and_verifies() -> None:
    password_hash = hash_password("Correct-Horse-1")

    assert password_hash.startswith("$argon2id$")
    assert verify_password(password_hash, "Correct-Horse-1")
    assert not verify_password(password_hash, "wrong-password")


def test_verify_returns_false_for_garbage_hash() -> None:
    assert not verify_password("not-a-hash", "whatever")


def test_short_password_rejected() -> None:
    with pytest.raises(ValidationFailedError) as exc_info:
        validate_password_strength("x" * (PASSWORD_MIN_LENGTH - 1))

    assert exc_info.value.code == "weak_password"


def test_temporary_password_is_long_enough_and_random() -> None:
    first, second = generate_temporary_password(), generate_temporary_password()

    assert len(first) >= PASSWORD_MIN_LENGTH
    assert first != second
