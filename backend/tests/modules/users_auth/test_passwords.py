import pytest

from app.core.errors import ValidationFailedError
from app.modules.users_auth.passwords import (
    PASSWORD_MIN_LENGTH,
    dummy_verify_async,
    generate_temporary_password,
    hash_password,
    hash_password_async,
    validate_password_strength,
    verify_password,
    verify_password_async,
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


async def test_async_wrappers_hash_and_verify() -> None:
    password_hash = await hash_password_async("Correct-Horse-1")

    assert password_hash.startswith("$argon2id$")
    assert await verify_password_async(password_hash, "Correct-Horse-1")
    assert not await verify_password_async(password_hash, "wrong-password")


async def test_dummy_verify_async_runs_without_raising() -> None:
    await dummy_verify_async("whatever")
