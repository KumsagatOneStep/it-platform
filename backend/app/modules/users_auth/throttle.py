import logging
import re
from dataclasses import dataclass

from redis.asyncio import Redis

from app.core.redis import resolve

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ThrottleLimits:
    account_ip_attempts: int = 5
    ip_attempts: int = 20
    window_seconds: int = 15 * 60
    lock_seconds: int = 15 * 60
    account_alert_attempts: int = 50
    account_alert_window_seconds: int = 60 * 60


def _glob_escape(value: str) -> str:
    return re.sub(r"([*?\[\]\\])", r"\\\1", value)


class LoginThrottle:
    """Счётчики неудачных входов в Redis (п. 2.4 ТЗ)."""

    def __init__(self, redis: Redis, limits: ThrottleLimits | None = None) -> None:
        self._redis = redis
        self._limits = limits or ThrottleLimits()

    async def is_locked(self, email: str, ip: str) -> bool:
        count = await resolve(
            self._redis.exists(f"login:lock:acct_ip:{email}:{ip}", f"login:lock:ip:{ip}")
        )
        return bool(count)

    async def register_failure(self, email: str, ip: str) -> None:
        limits = self._limits

        pair_key = f"login:fail:acct_ip:{email}:{ip}"
        if await self._increment(pair_key, limits.window_seconds) >= limits.account_ip_attempts:
            await self._lock(f"login:lock:acct_ip:{email}:{ip}", pair_key)

        ip_key = f"login:fail:ip:{ip}"
        if await self._increment(ip_key, limits.window_seconds) >= limits.ip_attempts:
            await self._lock(f"login:lock:ip:{ip}", ip_key)

        account_failures = await self._increment(
            f"login:fail:acct:{email}", limits.account_alert_window_seconds
        )
        # ТЗ п. 2.4: «более 50 попыток за час» — сигнал на 51-й
        if account_failures > limits.account_alert_attempts:
            first_alert = await resolve(
                self._redis.set(
                    f"login:alerted:acct:{email}",
                    "1",
                    ex=limits.account_alert_window_seconds,
                    nx=True,
                )
            )
            if first_alert:
                logger.warning(
                    "auth.login_bruteforce_suspected",
                    extra={"email": email, "failed_attempts": account_failures},
                )

    async def register_success(self, email: str, ip: str) -> None:
        await resolve(self._redis.delete(f"login:fail:acct_ip:{email}:{ip}"))

    async def unlock_account(self, email: str) -> int:
        pattern = f"login:*:acct_ip:{_glob_escape(email)}:*"
        keys = [key async for key in self._redis.scan_iter(match=pattern)]
        if not keys:
            return 0
        return int(await resolve(self._redis.delete(*keys)))

    async def _increment(self, key: str, ttl_seconds: int) -> int:
        # MULTI/EXEC: счётчик не может остаться без TTL; NX — окно отсчитывается от первой ошибки
        async with self._redis.pipeline(transaction=True) as pipe:
            pipe.incr(key)
            pipe.expire(key, ttl_seconds, nx=True)
            count, _ = await pipe.execute()
        return int(count)

    async def _lock(self, lock_key: str, counter_key: str) -> None:
        await resolve(self._redis.set(lock_key, "1", ex=self._limits.lock_seconds))
        await resolve(self._redis.delete(counter_key))
