import logging

import pytest
from redis.asyncio import Redis

from app.core.redis import resolve
from app.modules.users_auth.throttle import LoginThrottle, ThrottleLimits

EMAIL = "ivanov@company.ru"


async def test_account_ip_pair_locked_after_5_failures(redis_client: Redis) -> None:
    throttle = LoginThrottle(redis_client)

    for _ in range(4):
        await throttle.register_failure(EMAIL, "10.0.0.1")
    assert not await throttle.is_locked(EMAIL, "10.0.0.1")

    await throttle.register_failure(EMAIL, "10.0.0.1")

    assert await throttle.is_locked(EMAIL, "10.0.0.1")
    assert not await throttle.is_locked(EMAIL, "10.0.0.2")
    ttl = await resolve(redis_client.ttl(f"login:lock:acct_ip:{EMAIL}:10.0.0.1"))
    assert 0 < ttl <= 900


async def test_ip_locked_after_20_failures_across_accounts(redis_client: Redis) -> None:
    throttle = LoginThrottle(redis_client)

    for index in range(20):
        await throttle.register_failure(f"user{index}@company.ru", "10.0.0.9")

    assert await throttle.is_locked("someone-else@company.ru", "10.0.0.9")


async def test_success_resets_pair_counter(redis_client: Redis) -> None:
    throttle = LoginThrottle(redis_client)

    for _ in range(4):
        await throttle.register_failure(EMAIL, "10.0.0.1")
    await throttle.register_success(EMAIL, "10.0.0.1")
    for _ in range(4):
        await throttle.register_failure(EMAIL, "10.0.0.1")

    assert not await throttle.is_locked(EMAIL, "10.0.0.1")


async def test_bruteforce_alert_logged_once_without_locking(
    redis_client: Redis, caplog: pytest.LogCaptureFixture
) -> None:
    limits = ThrottleLimits(account_alert_attempts=3, account_ip_attempts=100, ip_attempts=100)
    throttle = LoginThrottle(redis_client, limits)

    def alerts() -> list[logging.LogRecord]:
        return [r for r in caplog.records if r.getMessage() == "auth.login_bruteforce_suspected"]

    with caplog.at_level(logging.WARNING, logger="app.modules.users_auth.throttle"):
        for index in range(3):
            await throttle.register_failure(EMAIL, f"10.0.1.{index}")
        # ТЗ: сигнал при «более N» попытках, ровно N — ещё не сигнал
        assert alerts() == []
        for index in range(3, 6):
            await throttle.register_failure(EMAIL, f"10.0.1.{index}")

    assert len(alerts()) == 1
    assert alerts()[0].__dict__["failed_attempts"] == 4
    assert not await throttle.is_locked(EMAIL, "10.0.2.1")


async def test_unlock_account_removes_locks_and_counters(redis_client: Redis) -> None:
    throttle = LoginThrottle(redis_client)
    for _ in range(5):
        await throttle.register_failure(EMAIL, "10.0.0.1")

    removed = await throttle.unlock_account(EMAIL)

    assert removed >= 1
    assert not await throttle.is_locked(EMAIL, "10.0.0.1")


async def test_failure_counters_always_have_ttl(redis_client: Redis) -> None:
    throttle = LoginThrottle(redis_client)

    for _ in range(3):
        await throttle.register_failure(EMAIL, "10.0.0.1")

    for key in (
        f"login:fail:acct_ip:{EMAIL}:10.0.0.1",
        "login:fail:ip:10.0.0.1",
        f"login:fail:acct:{EMAIL}",
    ):
        assert await resolve(redis_client.get(key)) == "3"
        assert await resolve(redis_client.ttl(key)) > 0
    assert 900 - 5 < await resolve(redis_client.ttl("login:fail:ip:10.0.0.1")) <= 900
    assert 3600 - 5 < await resolve(redis_client.ttl(f"login:fail:acct:{EMAIL}")) <= 3600


async def test_increment_does_not_extend_existing_ttl(redis_client: Redis) -> None:
    throttle = LoginThrottle(redis_client)
    await throttle.register_failure(EMAIL, "10.0.0.1")
    await resolve(redis_client.expire("login:fail:ip:10.0.0.1", 100))

    await throttle.register_failure(EMAIL, "10.0.0.1")

    assert await resolve(redis_client.ttl("login:fail:ip:10.0.0.1")) <= 100


async def test_counter_never_left_without_ttl_when_separate_expire_fails(
    redis_client: Redis, monkeypatch: pytest.MonkeyPatch
) -> None:
    """INCR и EXPIRE выполняются атомарно: отдельный вызов EXPIRE не используется."""

    async def failing_expire(*args: object, **kwargs: object) -> bool:
        raise ConnectionError("соединение прервано между INCR и EXPIRE")

    monkeypatch.setattr(redis_client, "expire", failing_expire)
    throttle = LoginThrottle(redis_client)

    await throttle.register_failure(EMAIL, "10.0.0.1")

    assert await resolve(redis_client.ttl("login:fail:ip:10.0.0.1")) > 0
