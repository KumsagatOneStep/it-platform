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

    with caplog.at_level(logging.WARNING, logger="app.modules.users_auth.throttle"):
        for index in range(5):
            await throttle.register_failure(EMAIL, f"10.0.1.{index}")

    alerts = [r for r in caplog.records if r.getMessage() == "auth.login_bruteforce_suspected"]
    assert len(alerts) == 1
    assert not await throttle.is_locked(EMAIL, "10.0.2.1")


async def test_unlock_account_removes_locks_and_counters(redis_client: Redis) -> None:
    throttle = LoginThrottle(redis_client)
    for _ in range(5):
        await throttle.register_failure(EMAIL, "10.0.0.1")

    removed = await throttle.unlock_account(EMAIL)

    assert removed >= 1
    assert not await throttle.is_locked(EMAIL, "10.0.0.1")
